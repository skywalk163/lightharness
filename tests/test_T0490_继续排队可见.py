# -*- coding: utf-8 -*-
"""T-0490：max-steps 后「继续」排队可见 / 停止按钮 / 切回会话历史。

判据（对齐任务书）：
  1. 202 排队轮次消费完成后，GET /api/sessions/:id 能看到新增的 user/assistant
     消息 + 排队事件（开始/完成），前端当前会话视图自动刷新（node + DOM 桩真链路）。
  2. 排队超时必须有可见失败回执（不再静默丢弃）——light 驱动直调 后台消费待办。
  3. 统计帧（max-steps）到达后点「继续」必须直接发新请求（不再进本地队列），
     老请求的 finally 不得关掉新流；反跑：删掉 202 后的刷新逻辑，用例 1 立红。
  4. 切回会话：空历史给明确提示；有待办在跑时订阅刷新（静态锚点 + 行为）。
  5. GET /api/sessions/:id/queue 轻量状态端点（深度/消息数/忙）。
  6. node --check webui/app.js 与既有 T-0453/T-0454 全绿。
"""
import json
import os
import pathlib
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
SERVER_SCRIPT = os.path.join(ROOT, 'examples', '运行Web服务器.light')
APP_JS = os.path.join(ROOT, 'webui', 'app.js')
MESSAGES_JS = os.path.join(ROOT, 'webui', 'messages.js')
TOKEN = 't0490-token'
BOOT_TIMEOUT = 180

# 反跑锚点：删掉 202 分支里的 startQueuedPoll 后，前端行为用例必须变红
POLL_ANCHOR = 'startQueuedPoll(qsid);'


def _env():
    env = {k: v for k, v in os.environ.items()
           if k not in ('HARNESS_ROOT', 'HARNESS_CWD', 'HARNESS_PERMISSION_MODE',
                        'HARNESS_WEB_TOKEN', 'HARNESS_ENDPOINT', 'HARNESS_API_KEY',
                        'HARNESS_MODEL', 'HARNESS_MODEL_CONTEXT_WINDOW', 'HARNESS_MAX_STEPS')}
    here = ROOT
    for _ in range(6):
        here = os.path.dirname(here)
        if not here or here == os.path.dirname(here):
            break
        for key, repo in (('LIGHTPLUGIN', 'lightplugin'), ('LIGHT_MERGE', 'light-merge')):
            cand = os.path.join(here, repo)
            if os.path.isdir(cand) and key not in env:
                env[key] = cand
    env['PYTHONIOENCODING'] = 'utf-8'
    return env


# ---------------------------------------------------------------------------
# 后端：真起服务 + 脚本化 mock LLM（首轮慢，保证第二条走 202 入队）
# ---------------------------------------------------------------------------
_MOCK = r'''
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

class 处理器(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a):
        pass
    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        msgs = body.get("messages") or []
        user = ""
        for m in reversed(msgs):
            if m.get("role") == "user":
                c = m.get("content")
                user = c if isinstance(c, str) else "".join(
                    b.get("text", "") for b in c if isinstance(b, dict))
                break
        if "SLOW" in user:
            time.sleep(2.0)
        text = "继续轮输出 T0490" if "继续" in user else "首轮输出 T0490"
        chunks = [
            {"choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}]},
            {"choices": [{"index": 0, "delta": {"content": text}, "finish_reason": None}]},
            {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
        ]
        raw = "".join("data: " + json.dumps(c, ensure_ascii=False) + "\n\n" for c in chunks)
        raw = (raw + "data: [DONE]\n\n").encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

服务 = ThreadingHTTPServer(("127.0.0.1", 0), 处理器)
print(服务.server_address[1], flush=True)
服务.serve_forever()
'''


class _Mock:
    def __init__(self, work):
        self.script = work / 'mockllm.py'
        self.script.write_text(_MOCK, encoding='utf-8')
        self.proc = subprocess.Popen([sys.executable, '-u', str(self.script)],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     text=True, encoding='utf-8', cwd=str(work))
        line = self.proc.stdout.readline()
        if not line or not line.strip().isdigit():
            raise RuntimeError('mock 起不来：' + (self.proc.stderr.read() or '')[-500:])
        self.port = int(line.strip())

    @property
    def endpoint(self):
        return 'http://127.0.0.1:%d/chat/completions' % self.port

    def stop(self):
        try:
            self.proc.kill()
            self.proc.wait(timeout=10)
        except Exception:
            pass


class _Server:
    def __init__(self, work, llm):
        self.work = work
        self.port_file = work / 'port.txt'
        self.log_path = work / 'server.log'
        env = _env()
        env.update({
            'HARNESS_WEB_TOKEN': TOKEN, 'HARNESS_WEB_NO_OPEN': '1',
            'HARNESS_PORT_FILE': str(self.port_file), 'HARNESS_HOME': str(work),
            'HARNESS_WEB_LIFETIME': '900', 'HARNESS_WEB_MOCK': '0',
            'HARNESS_ENDPOINT': llm.endpoint, 'HARNESS_API_KEY': 'mock-key',
            'HARNESS_MODEL': 'mock',
        })
        self._log = open(self.log_path, 'w', encoding='utf-8')
        self.proc = subprocess.Popen([sys.executable, RUNNER, SERVER_SCRIPT],
                                     stdout=self._log, stderr=subprocess.STDOUT,
                                     text=True, encoding='utf-8', cwd=str(work), env=env)
        self.port = self._port()

    def _port(self):
        end = time.time() + BOOT_TIMEOUT
        while time.time() < end:
            if self.proc.poll() is not None:
                raise RuntimeError('服务提前退出：' + self.log()[-1500:])
            try:
                raw = self.port_file.read_text(encoding='utf-8').strip()
            except OSError:
                raw = ''
            if raw:
                try:
                    with socket.create_connection(('127.0.0.1', int(raw)), timeout=1):
                        return int(raw)
                except OSError:
                    pass
            time.sleep(0.2)
        raise RuntimeError('服务 180s 未起：' + self.log()[-1500:])

    def log(self):
        try:
            self._log.flush()
            return self.log_path.read_text(encoding='utf-8', errors='replace')
        except OSError:
            return ''

    def _req(self, path, method='GET', body=None):
        hs = {'X-Auth-Token': TOKEN}
        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode('utf-8')
            hs['Content-Type'] = 'application/json; charset=utf-8'
        req = urllib.request.Request('http://127.0.0.1:%d%s' % (self.port, path),
                                     data=data, method=method, headers=hs)
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return resp.status, resp.read().decode('utf-8', 'replace')
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode('utf-8', 'replace')

    def get(self, path):
        return self._req(path)

    def post(self, path, body):
        return self._req(path, 'POST', body)

    def stop(self):
        try:
            self.proc.kill()
            self.proc.wait(timeout=15)
        except Exception:
            pass
        try:
            self._log.close()
        except Exception:
            pass


@pytest.fixture(scope='module')
def work():
    p = pathlib.Path(tempfile.mkdtemp(prefix='t0490'))
    try:
        yield p
    finally:
        if os.environ.get('T0490_KEEP'):
            print('KEEP:', p)
        else:
            shutil.rmtree(p, ignore_errors=True)


@pytest.fixture(scope='module')
def llm(work):
    m = _Mock(work)
    try:
        yield m
    finally:
        m.stop()


@pytest.fixture(scope='module')
def srv(work, llm):
    s = _Server(work, llm)
    try:
        yield s
    finally:
        s.stop()


def _session_file(work, sid):
    hits = [p for p in work.rglob('session.jsonl') if p.parent.name == sid]
    assert hits, '找不到会话 JSONL：%s' % sid
    return max(hits, key=lambda p: p.stat().st_mtime)


def _rows(path):
    out = []
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out


# ---------------------------------------------------------------------------
# 判据 1/2/5：202 入队 → 后台消费落库 + 可见事件 + /queue 端点
# ---------------------------------------------------------------------------
def test_202排队后后台落库并有可见回执(srv, work):
    sid = 't0490-queue'
    result = {}
    err = {}

    def first():
        try:
            result['a'] = srv.post('/v1/chat/completions', {
                'messages': [{'role': 'user', 'content': 'SLOW 首轮 T0490'}],
                'stream': True, 'session_id': sid})
        except Exception as e:
            err['a'] = str(e)

    t = threading.Thread(target=first, daemon=True)
    t.start()
    time.sleep(0.5)
    # 首轮还在跑（mock sleep 2s）→ 这条必走 202
    status, body = srv.post('/v1/chat/completions', {
        'messages': [{'role': 'user', 'content': '继续'}],
        'stream': True, 'session_id': sid})
    t.join(timeout=120)
    assert 'a' in result or err, err
    assert status == 202, '排队消息应拿到 202（实际 %s）：%s' % (status, body[:400])
    j = json.loads(body)
    assert j.get('状态') == '排队' and j.get('会话') == sid, j

    # 队列状态端点（轻量）：消息数 / 深度 / 忙 三键齐全
    st, qb = srv.get('/api/sessions/%s/queue' % sid)
    assert st == 200, qb[:400]
    qj = json.loads(qb)
    for key in ('深度', '消息数', '忙'):
        assert key in qj, qj

    # 等后台消费把「继续」落库（最多 30s）——走 HTTP API，与前端同一视图
    deadline = time.time() + 30
    rows = []
    while time.time() < deadline:
        st, db = srv.get('/api/sessions/%s' % sid)
        if st == 200:
            rows = json.loads(db).get('消息', [])
            texts = [str(r.get('内容', '')) for r in rows]
            if any(t.startswith('[开始]') and '继续' in t for t in texts) and \
               any(t.startswith('[完成]') and '继续' in t for t in texts) and \
               any('继续轮输出' in t for t in texts):
                break
        time.sleep(0.3)

    roles = [r.get('角色') for r in rows]
    texts = [str(r.get('内容', '')) for r in rows]
    assert any(t.startswith('[排队中]') and '继续' in t for t in texts), \
        '缺入队回执：%s' % texts[-10:]
    assert any(t.startswith('[开始]') and '继续' in t for t in texts), \
        '缺开始回执：%s' % texts[-10:]
    assert any(t.startswith('[完成]') and '继续' in t for t in texts), \
        '缺完成回执（202 排队轮次跑完用户看不到）：%s' % texts[-10:]
    assert 'user' in roles and 'assistant' in roles, roles
    assert any('继续轮输出' in t for t in texts), texts[-10:]

    # 详情端点同样可见（消息数随后台落库单调增长）
    st, qb2 = srv.get('/api/sessions/%s/queue' % sid)
    assert st == 200 and json.loads(qb2)['消息数'] >= len(rows), qb2[:300]


# ---------------------------------------------------------------------------
# 判据 3：超时有可见失败回执（不静默丢弃）——light 驱动直调消费
# ---------------------------------------------------------------------------
_TIMEOUT_DRIVER = '''
从 会话队列 导入 队建闸门, 队入队, 队排队深度, 队释放占用
从 web服务器 导入 后台消费待办, 队待办超时秒, 记排队事件, 取排队状态

类 假会话库:
  属性 表 等于 []
  段落 追加消息(标识, 消息):
    己.表.追加(消息)
    返回 消息
  段落 获取会话(标识):
    返回 己.表

类 假服务:
  属性 会话库 等于 空
  属性 根 等于 ""

段落 主:
  设 闸门 为 队建闸门()
  设 键 为 "t0490超时"
  设 库 为 新建 假会话库()
  设 服务 为 新建 假服务()
  服务.会话库 为 库
  设 旧超时 为 队待办超时秒
  # 入队一条「很久以前」的待办 → 必超时
  设 忽略入 为 队入队(闸门, 键, ["文本": "超时继续", "流式": 假, "入队时刻": 时间戳() - 9999])
  设 载具 为 ["服务": 服务, "会话": 空, "客户端": 空, "注册表": 空, "会话标识": 键, "选项": 空]
  后台消费待办(载具, 闸门, 键)
  打印 "深度=" + 转字符串(队排队深度(闸门, 键))
  遍历 消息 之 库.表:
    打印 "消息=" + 转字符串(消息["内容"])
'''

# ---------------------------------------------------------------------------
# 判据 6：node --check + 静态锚点
# ---------------------------------------------------------------------------
def test_node语法检查():
    rc = subprocess.run(['node', '--check', APP_JS], capture_output=True)
    assert rc.returncode == 0, rc.stderr.decode('utf-8', errors='replace')


def test_静态契约():
    src = open(APP_JS, 'r', encoding='utf-8').read()
    assert POLL_ANCHOR in src, '202 分支缺排队轮询接线（反跑锚点丢失）'
    for token in ('startQueuedPoll', 'refreshCurrentSession', '/queue',
                  '该会话暂无历史消息', 'pendingEndReason', 'sendSerial'):
        assert token in src, ('前端缺 T-0490 契约', token)
    web = open(os.path.join(ROOT, 'src', 'web服务器.light'), 'r', encoding='utf-8').read()
    for token in ('记排队事件', '取排队状态', '排队唤醒循环', '/queue', '"失败"'):
        assert token in web, ('后端缺 T-0490 契约', token)


def test_超时回执与后端驱动(tmp_path):
    f = tmp_path / 'timeout.light'
    f.write_text(_TIMEOUT_DRIVER, encoding='utf-8')
    env = {k: v for k, v in os.environ.items() if k not in ('HARNESS_ROOT', 'HARNESS_CWD')}
    env['PYTHONIOENCODING'] = 'utf-8'
    p = subprocess.run([sys.executable, RUNNER, str(f)], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=180, cwd=str(tmp_path), env=env)
    assert p.returncode == 0, '驱动失败 rc=%d\n%s\n%s' % (p.returncode, p.stdout, p.stderr)
    assert '深度=0' in p.stdout, p.stdout
    assert '消息=[失败]' in p.stdout, '超时必须写可见失败回执，不得静默丢弃：\n' + p.stdout


# ---------------------------------------------------------------------------
# 前端行为：node + 手写 DOM 桩，跑真实 messages.js + app.js
# ---------------------------------------------------------------------------
_HARNESS = r'''/* T-0490 前端行为 harness：手写 DOM 桩，跑真实文件。 */
'use strict';
const fs = require('fs');
const path = require('path');
const appPath = process.argv[2];
const caseName = process.argv[3];

// ---------- DOM 桩 ----------
function classList() {
  const s = new Set();
  return { add(c){s.add(c);}, remove(c){s.delete(c);}, toggle(c,f){f?s.add(c):s.delete(c);}, contains(c){return s.has(c);} };
}
function makeEl(tag) {
  const h = {}, children = [];
  const el = {
    tagName:(tag||'div').toUpperCase(), children, style:{}, dataset:{}, attrs:{},
    textContent:'', innerHTML:'', value:'', hidden:false, disabled:false, className:'',
    classList:classList(), handlers:h,
    appendChild(c){children.push(c);return c;}, removeChild(c){const i=children.indexOf(c);if(i>=0)children.splice(i,1);return c;},
    insertBefore(c){children.push(c);return c;}, remove(){}, addEventListener(t,f){(h[t]=h[t]||[]).push(f);},
    removeEventListener(){}, click(){(h.click||[]).forEach(f=>f({target:el,stopPropagation(){},preventDefault(){}}));},
    focus(){}, select(){}, setAttribute(k,v){el.attrs[k]=v;}, getAttribute(k){return el.attrs[k]!==undefined?el.attrs[k]:null;},
    closest(){return null;},
    querySelector(sel){const cls=String(sel||'').replace(/^\./,'');const st=this.children.slice();while(st.length){const c=st.pop();if(cls&&String(c.className).indexOf(cls)>=0)return c;for(const x of (c.children||[]))st.push(x);}return null;},
    querySelectorAll(){return [];}, contains(){return false;},
    scrollIntoView(){}, removeAttribute(){}
  };
  return el;
}
const cache = new Map();
global.document = {
  getElementById(id){if(!cache.has(id))cache.set(id,makeEl('div'));return cache.get(id);},
  createElement(t){return makeEl(t);}, createTextNode(t){return {textContent:String(t)};},
  addEventListener(){}, removeEventListener(){}, body:makeEl('body'), documentElement:makeEl('html'),
  querySelector(){return null;}, querySelectorAll(){return [];}
};
Object.defineProperty(global,'navigator',{value:{userAgent:'t0490-stub'},configurable:true,writable:true});
Object.defineProperty(global,'location',{value:{search:'',protocol:'http:',host:'localhost:0',pathname:'/'},configurable:true,writable:true});
global.localStorage={_m:{},getItem(k){return this._m[k]!==undefined?this._m[k]:null;},setItem(k,v){this._m[k]=String(v);},removeItem(k){delete this._m[k];}};
global.window=global; global.confirm=()=>true; global.alert=()=>{};
global.requestAnimationFrame=fn=>setTimeout(fn,0);
global.matchMedia=()=>({matches:false,addEventListener(){},removeEventListener(){}});

let fetchImpl=()=>new Promise(()=>{});
global.__lhSetFetcher=fn=>{fetchImpl=fn;};
global.fetch=(u,o)=>fetchImpl(u,o);
global.__lhRequests=[];

function sse(obj){return 'data: '+JSON.stringify(obj)+'\n\n';}
function makeStream(){
  const q=[], enc=new TextEncoder(); let pending=null;
  const deliver=()=>{if(!pending||!q.length)return;const r=pending;pending=null;r(q.shift());};
  return {
    push(s){q.push({done:false,value:enc.encode(s)});deliver();},
    end(){q.push({done:true});deliver();},
    body:{getReader(){return {read(){if(q.length)return Promise.resolve(q.shift());return new Promise(r=>{pending=r;});}};}}
  };
}
global.__lhMakeStream=makeStream; global.__lhSse=sse; global.__lhDONE='data: [DONE]\n\n';

global.__LH_TEST__=true;
eval(fs.readFileSync(path.join(path.dirname(appPath),'messages.js'),'utf-8'));
eval(fs.readFileSync(appPath,'utf-8'));
const T=global.__lhTest;
if(!T){console.error('缺少 __lhTest 钩子');process.exit(1);}
function sleep(ms){return new Promise(r=>setTimeout(r,ms));}
function sysRows(){return document.getElementById('messages').children.filter(c=>String(c.className).indexOf('sys')>=0);}
function allText(){return sysRows().map(r=>String(r.textContent)).join('\n');}
function findBtn(row,cls){const st=[row];while(st.length){const c=st.pop();for(const x of c.children){if(String(x.className).indexOf(cls)>=0)return x;st.push(x);}}return null;}

const CASES={
  // 判据 1：202 后轮询 /queue → 消息数变化 → 自动刷新当前会话视图
  async queuedPollRefreshesView(){
    // 先选一个会话（fetch 会话详情返回空历史）
    global.__lhSetFetcher((u,o)=>{
      if(String(u).indexOf('/api/sessions/t0490')===0 && String(u).indexOf('/queue')<0){
        const body = global.__lhDetailCount++ > 0
          ? [{角色:'user',内容:'继续'},{角色:'assistant',内容:'继续轮输出 T0490'}]
          : [];
        return Promise.resolve({ok:true,status:200,json:()=>Promise.resolve({消息:body})});
      }
      if(String(u).indexOf('/queue')>=0){
        return Promise.resolve({ok:true,status:200,json:()=>Promise.resolve({深度:0,消息数:global.__lhDetailCount>0?2:0,忙:false})});
      }
      return new Promise(()=>{});
    });
    global.__lhDetailCount=0;
    // 先切到这个会话（空历史 → 明确提示），再模拟 202 后的轮询
    T.selectSession('t0490-view');
    await sleep(60);
    // 用测试钩子驱动 202 分支的轮询（真实 sendMessage 的 202 路径由静态锚点保证）
    T.startQueuedPoll('t0490-view');
    await sleep(60);
    // 第一次详情是空历史 → 明确提示
    if(allText().indexOf('该会话暂无历史消息')<0) throw new Error('空会话无明确提示: '+allText());
    global.__lhDetailCount=1;
    await sleep(2500);
    const root=document.getElementById('messages');
    function collect(el){let s=String(el.textContent||'')+' '+String(el.innerHTML||'');for(const c of (el.children||[]))s+=' '+collect(c);return s;}
    const text=root.children.map(collect).join('\n');
    if(text.indexOf('继续轮输出 T0490')<0) throw new Error('202 排队结果未刷新到当前会话视图: '+text.slice(-500));
    T.stopQueuedPoll();
  },

  // 判据 3：max-steps 统计帧后点「继续」→ 直接发新请求，不进本地队列；老 finally 不关新流
  async maxStepsContinueDirect(){
    let streams=[];
    global.__lhSetFetcher((u,o)=>{
      const body=o&&o.body?JSON.parse(o.body):{};
      global.__lhRequests.push(body);
      const st=makeStream(); streams.push(st);
      return Promise.resolve({ok:true,status:200,body:st.body});
    });
    const p=T.sendMessage('第一轮');
    await sleep(20);
    const st=streams[0];
    st.push(sse({'种类':'统计','结束原因':'max-steps','步数上限':96}));
    await sleep(20);
    // 找到「继续」按钮并点击（流还没 [DONE]，服务端已空闲）
    let btn=null;
    for(const r of sysRows()){btn=findBtn(r,'continue-btn');if(btn)break;}
    if(!btn) throw new Error('max-steps 未出现继续按钮');
    btn.click();
    await sleep(30);
    if(T.state().queue!==0) throw new Error('继续被塞进本地队列（应直接发出）: queue='+T.state().queue);
    if(global.__lhRequests.length<2) throw new Error('继续未直接发新请求');
    const last=global.__lhRequests[global.__lhRequests.length-1];
    const lastMsg=last.messages&&last.messages.length?last.messages[last.messages.length-1].content:'';
    if(lastMsg!=='继续') throw new Error('发出的不是继续: '+JSON.stringify(last));
    // 老流的 [DONE]/finally 不能关掉新流
    st.push(global.__lhDONE); st.end();
    await sleep(20);
    if(T.state().streaming!==true) throw new Error('老轮收口关掉了新流（序列化竞态）');
    streams[1].push(global.__lhDONE); streams[1].end();
    await p;
  },

  // 判据 1（真链路）：sendMessage 收到 HTTP 202 → 自动轮询并刷新当前会话
  async queued202Direct(){
    global.__lhDetailCount=0;
    let detailCalls=0, queueCalls=0;
    global.__lhSetFetcher((u,o)=>{
      const url=String(u);
      if(url.indexOf('/api/sessions/')===0 && url.indexOf('/queue')>=0){
        queueCalls++;
        return Promise.resolve({ok:true,status:200,json:()=>Promise.resolve({深度:1,消息数:global.__lhDetailCount,忙:true})});
      }
      if(url.indexOf('/api/sessions/')===0){
        detailCalls++;
        return Promise.resolve({ok:true,status:200,json:()=>Promise.resolve({消息:[{角色:'user',内容:'继续'},{角色:'assistant',内容:'继续轮输出 T0490'}]})});
      }
      global.__lhRequests.push(o&&o.body?JSON.parse(o.body):{});
      return Promise.resolve({ok:true,status:202,json:()=>Promise.resolve({状态:'排队',位置:1,会话:'t0490-direct'})});
    });
    // 先用一个 200 流把 sessionId 绑定上（不经过 selectSession，避免它自带的轮询
    //   掩盖 202 分支接线；这是反跑能变红的关键）
    let firstStream=null;
    global.__lhSetFetcher((u,o)=>{
      const url=String(u);
      if(url.indexOf('/api/sessions/')===0) return Promise.resolve({ok:true,status:200,json:()=>Promise.resolve({消息:[]})});
      global.__lhRequests.push(o&&o.body?JSON.parse(o.body):{});
      if(!firstStream){firstStream=makeStream();return Promise.resolve({ok:true,status:200,body:firstStream.body});}
      return Promise.resolve({ok:true,status:202,json:()=>Promise.resolve({状态:'排队',位置:1,会话:'t0490-direct'})});
    });
    const first=T.sendMessage('建会话');
    await sleep(20);
    firstStream.push(sse({'种类':'会话','session_id':'t0490-direct'}));
    firstStream.push(global.__lhDONE); firstStream.end();
    await first;
    // 现在真正发「继续」→ 202
    global.__lhSetFetcher((u,o)=>{
      const url=String(u);
      if(url.indexOf('/api/sessions/')>=0 && url.indexOf('/queue')>=0){
        queueCalls++;
        const cnt=queueCalls>=2?1:0;
        return Promise.resolve({ok:true,status:200,json:()=>Promise.resolve({深度:1,消息数:cnt,忙:true})});
      }
      if(url.indexOf('/api/sessions/')===0){
        detailCalls++;
        return Promise.resolve({ok:true,status:200,json:()=>Promise.resolve({消息:[{角色:'user',内容:'继续'},{角色:'assistant',内容:'继续轮输出 T0490'}]})});
      }
      global.__lhRequests.push(o&&o.body?JSON.parse(o.body):{});
      return Promise.resolve({ok:true,status:202,json:()=>Promise.resolve({状态:'排队',位置:1,会话:'t0490-direct'})});
    });
    const p=T.sendMessage('继续');
    await p;
    await sleep(3300);
    if(queueCalls<1) throw new Error('202 后未轮询 /queue（调用次数 '+queueCalls+'）');
    if(detailCalls<1) throw new Error('202 后未刷新会话详情（调用次数 '+detailCalls+'）');
    T.stopQueuedPoll();
  },

  // 判据 4：切换到空会话 → 明确提示，不是空白
  async emptySessionHint(){
    global.__lhSetFetcher((u,o)=>Promise.resolve({ok:true,status:200,json:()=>Promise.resolve({消息:[]})}));
    // 先建一个会话（通过钩子 state 看 sessionId 变化）
    // 直接给 sessionId 赋值不可行，走 sendMessage 首帧绑定
    let st;
    global.__lhSetFetcher((u,o)=>{
      if(String(u).indexOf('/api/sessions/')===0) return Promise.resolve({ok:true,status:200,json:()=>Promise.resolve({消息:[]})});
      st=makeStream(); return Promise.resolve({ok:true,status:200,body:st.body});
    });
    const p=T.sendMessage('hi');
    await sleep(20);
    st.push(sse({'种类':'会话','session_id':'t0490-empty'}));
    st.push(global.__lhDONE); st.end();
    await p;
    if(T.state().sessionId!=='t0490-empty') throw new Error('会话绑定失败: '+JSON.stringify(T.state()));
    // 切走再切回（真实用户路径）：selectSession 空历史必须给明确提示
    T.selectSession('t0490-empty2');
    await sleep(30);
    T.selectSession('t0490-empty');
    await sleep(60);
    if(allText().indexOf('该会话暂无历史消息')<0) throw new Error('空会话无提示: '+allText());
  }
};

(async function(){
  const fn=CASES[caseName];
  if(!fn){console.error('未知场景 '+caseName);process.exit(2);}
  try { await fn(); console.log('CASE_OK '+caseName); process.exit(0); }
  catch(e){ console.error('CASE_FAIL '+caseName+': '+(e&&e.message?e.message:e)); process.exit(1); }
})();
'''


def _run_case(tmp_path, case, app_src=None):
    src = app_src if app_src is not None else open(APP_JS, 'r', encoding='utf-8').read()
    app_copy = tmp_path / 't0490_app.js'
    app_copy.write_text(src, encoding='utf-8')
    (tmp_path / 'messages.js').write_text(open(MESSAGES_JS, 'r', encoding='utf-8').read(), encoding='utf-8')
    harness = tmp_path / 't0490_harness.js'
    harness.write_text(_HARNESS, encoding='utf-8')
    proc = subprocess.run(['node', str(harness), str(app_copy), case],
                          capture_output=True, timeout=60)
    return proc.returncode, proc.stdout.decode('utf-8', errors='replace'), proc.stderr.decode('utf-8', errors='replace')


def test_前端_202排队结果自动刷新(tmp_path):
    rc, out, err = _run_case(tmp_path, 'queuedPollRefreshesView')
    assert rc == 0, ('排队结果未自动刷新', out[-800:], err[-800:])


def test_前端_202真链路自动轮询(tmp_path):
    rc, out, err = _run_case(tmp_path, 'queued202Direct')
    assert rc == 0, ('sendMessage 收到 202 后未自动轮询', out[-800:], err[-800:])


def test_前端_maxsteps继续直接发出(tmp_path):
    rc, out, err = _run_case(tmp_path, 'maxStepsContinueDirect')
    assert rc == 0, ('max-steps 继续未直接发出', out[-800:], err[-800:])


def test_前端_空会话明确提示(tmp_path):
    rc, out, err = _run_case(tmp_path, 'emptySessionHint')
    assert rc == 0, ('空会话无明确提示', out[-800:], err[-800:])


def test_反跑_删掉202轮询刷新_logic立红(tmp_path):
    original = open(APP_JS, 'r', encoding='utf-8').read()
    assert original.count(POLL_ANCHOR) == 1, '反跑锚点丢失或多处'
    mutated = original.replace(POLL_ANCHOR,
        '/* T-0490 反跑：202 后不轮询 */', 1)
    rc, out, err = _run_case(tmp_path, 'queued202Direct', app_src=mutated)
    assert rc != 0, (
        '反跑失败：删掉 202 轮询接线后真链路用例仍通过（判据假绿）', out[-800:], err[-800:])
    assert 'CASE_FAIL queued202Direct' in err or 'CASE_FAIL queued202Direct' in out, (out, err)
