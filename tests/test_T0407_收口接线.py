# -*- coding: utf-8 -*-
"""T-0407 收口接线判据：把 T-0401~T-0405 的四组纯逻辑接到真实链路上。

本文件不是「再测一遍单卡」，而是判「接上了没有」：

  1. /goal → 续跑循环真的把同一会话驱动了 2 轮，模型调 目标.complete 后停下；
  2. 压缩配置进了代理选项 → 小窗口下自动压缩真的写出 <compacted-summary> 检查点；
  3. /compact 是命令不是消息 → 不调模型、回「压缩」事件帧；
  4. 六种模式（老四 + 新四）都能开会话，400 文案由 预设清单 拼出；
  5. 统计帧带 开始/完成/耗时/速率/轮次数，速率 = 输出token / 耗时；
  6. 同一会话并发 → 第二条 202 排队，JSONL 不重复；
  7. 前端：node --check 通过、下拉补齐四种新模式、busy 呼吸动画与排队角标在位；
  8. 静态钉住：目标工具只在有目标时挂、计划模式每轮重设、压缩配置来自本会话窗口。

真起服务（同 T-0399）：子进程跑 examples/运行Web服务器.light，脚本化 mock LLM 驱动工具调用。
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
TOKEN = 't0407-token'
BOOT_TIMEOUT = 180


def _env():
    env = {k: v for k, v in os.environ.items()
           if k not in ('HARNESS_ROOT', 'HARNESS_CWD', 'HARNESS_PERMISSION_MODE',
                        'HARNESS_WEB_TOKEN', 'HARNESS_ENDPOINT', 'HARNESS_API_KEY',
                        'HARNESS_MODEL', 'HARNESS_MODEL_CONTEXT_WINDOW')}
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


_MOCK = r'''
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

计数 = {"n": 0, "goal": 0}


def 文本块(t):
    return [{"choices": [{"index": 0, "delta": {"content": t}, "finish_reason": None}]},
            {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}]


class 处理器(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _发(self, 体, 类型="application/json"):
        self.send_response(200)
        self.send_header("Content-Type", 类型)
        self.send_header("Content-Length", str(len(体)))
        self.end_headers()
        self.wfile.write(体)

    def do_GET(self):
        if self.path == "/count":
            self._发(json.dumps(计数).encode())

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        载荷 = json.loads(self.rfile.read(n) or b"{}")
        计数["n"] += 1
        消息 = 载荷.get("messages") or []
        用户 = ""
        遍历 = list(reversed(消息))
        for m in 遍历:
            if m.get("role") == "user":
                内容 = m.get("content")
                if isinstance(内容, str):
                    用户 = 内容
                elif isinstance(内容, list):
                    用户 = "".join(b.get("text", "") for b in 内容 if isinstance(b, dict))
                break
        if "T0407-SLOW" in 用户:
            time.sleep(1.0)
        已调 = any(isinstance(m, dict) and "tool_calls" in m for m in 消息)
        if 计数["goal"] == 0:
            块 = 文本块("阶段一完成，继续推进。")
            计数["goal"] = 1
        elif 计数["goal"] == 1 and not 已调:
            块 = [{"choices": [{"index": 0, "delta": {"tool_calls": [
                {"index": 0, "id": "g1", "type": "function",
                 "function": {"name": "目标", "arguments": json.dumps({"动作": "complete"})}}]},
                "finish_reason": None}]},
                {"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]}]
            计数["goal"] = 2
        elif 计数["goal"] >= 1:
            块 = 文本块("目标已完成。")
        elif "T0407-LONG" in 用户:
            块 = 文本块("长上下文填充。" * 900)
        else:
            块 = 文本块("好的，收到。")
        体 = "".join("data: " + json.dumps(c, ensure_ascii=False) + "\n\n" for c in 块)
        体 = (体 + "data: [DONE]\n\n").encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Content-Length", str(len(体)))
        self.end_headers()
        self.wfile.write(体)


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
        self.port = self._port()

    def _port(self, timeout=60):
        end = time.time() + timeout
        while time.time() < end:
            line = self.proc.stdout.readline()
            if line and line.strip().isdigit():
                return int(line.strip())
            if self.proc.poll() is not None:
                raise RuntimeError('mock 起不来：' + (self.proc.stderr.read() or '')[-500:])
        raise RuntimeError('mock 端口超时')

    @property
    def endpoint(self):
        return f'http://127.0.0.1:{self.port}/chat/completions'

    def count(self):
        with urllib.request.urlopen(f'http://127.0.0.1:{self.port}/count', timeout=10) as r:
            return json.loads(r.read().decode('utf-8'))

    def stop(self):
        try:
            self.proc.kill(); self.proc.wait(timeout=10)
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
            'HARNESS_MODEL': 'mock', 'HARNESS_MODEL_CONTEXT_WINDOW': '200',
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

    def post(self, body, path='/v1/chat/completions', headers=None, timeout=180):
        hs = {'Content-Type': 'application/json; charset=utf-8', 'X-Auth-Token': TOKEN}
        if headers:
            hs.update(headers)
        req = urllib.request.Request(f'http://127.0.0.1:{self.port}{path}',
                                     data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
                                     method='POST', headers=hs)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read().decode('utf-8', 'replace')
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode('utf-8', 'replace')

    def stop(self):
        try:
            self.proc.kill(); self.proc.wait(timeout=15)
        except Exception:
            pass
        try:
            self._log.close()
        except Exception:
            pass


def _frames(raw):
    out = []
    for line in raw.splitlines():
        if not line.startswith('data: '):
            continue
        body = line[6:].strip()
        if body == '[DONE]':
            continue
        try:
            out.append(json.loads(body))
        except Exception:
            pass
    return out


def _stat(raw):
    for f in _frames(raw):
        if isinstance(f, dict) and f.get('种类') == '统计':
            return f
    return {}


def _session_file(work, sid):
    hits = [p for p in work.rglob('session.jsonl') if p.parent.name == sid]
    assert hits, f'找不到会话 JSONL：{sid}（{work}）\n' + '\n'.join(str(p) for p in work.rglob('*'))
    return max(hits, key=lambda p: p.stat().st_mtime)


def _events(path):
    rows = []
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows


# --------------------------------------------------------------------------- #
@pytest.fixture(scope='module')
def work():
    p = pathlib.Path(tempfile.mkdtemp(prefix='t0407'))
    try:
        yield p
    finally:
        if os.environ.get('T0407_KEEP'):
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


# --------------------------------------------------------------------------- #
# 1. 目标续跑：2 轮 + 目标工具 complete + 统计 轮次数=2
# --------------------------------------------------------------------------- #
def test_目标续跑两轮后由目标工具收口(srv):
    sid = 't0407-goal'
    st, raw = srv.post({'messages': [{'role': 'user', 'content': '/goal T0407-GOAL 把示例项目收口'}],
                        'stream': True, 'session_id': sid})
    assert st == 200, raw
    帧 = _frames(raw)
    assert any(f.get('种类') == '统计' for f in 帧), '缺少统计帧'
    stat = _stat(raw)
    assert stat.get('轮次数') == 2, f'续跑应正好 2 轮，实际 {stat.get("轮次数")}：{stat}'

    事件 = _events(_session_file(srv.work, sid))
    助手 = [e for e in 事件 if e.get('type') == 'assistant/message']
    assert len(助手) >= 2, f'会话应出现 ≥2 次助手消息，实际 {len(助手)}'
    变更 = [e for e in 事件 if e.get('type') == 'goal/change']
    assert 变更, '模型 complete 必须落成 goal/change 事件（否则续跑读不到 phase）'
    assert 变更[-1]['data'].get('operation') == 'complete', 变更[-1]
    assert 变更[-1]['data']['goal'].get('phase') == 'complete', 变更[-1]


# --------------------------------------------------------------------------- #
# 2. 自动压缩：小窗口 + 长消息 → compact-checkpoint 真的进会话
# --------------------------------------------------------------------------- #
def test_小窗口下自动压缩写出检查点(srv):
    sid = 't0407-compact'
    for i in range(3):
        st, _ = srv.post({'messages': [{'role': 'user', 'content': f'第{i}条普通消息，填充上下文。' * 3}],
                          'stream': False, 'session_id': sid})
        assert st == 200
    st, raw = srv.post({'messages': [{'role': 'user', 'content': 'T0407-LONG ' + '长文本填充。' * 900}],
                        'stream': False, 'session_id': sid})
    assert st == 200, raw
    文本 = _session_file(srv.work, sid).read_text(encoding='utf-8', errors='replace')
    assert '<compacted-summary>' in 文本, '压缩配置没生效：会话里没有 compact-checkpoint 检查点'


# --------------------------------------------------------------------------- #
# 3. /compact：不调模型、回压缩帧
# --------------------------------------------------------------------------- #
def test_compact命令不消耗模型轮次并回压缩帧(srv, llm):
    sid = 't0407-cmd'
    srv.post({'messages': [{'role': 'user', 'content': '先建立一段历史。' * 20}],
              'stream': False, 'session_id': sid})
    before = llm.count()['n']
    st, raw = srv.post({'messages': [{'role': 'user', 'content': '/compact'}],
                        'stream': True, 'session_id': sid})
    assert st == 200, raw
    assert llm.count()['n'] == before, '/compact 不应调用模型'
    帧 = _frames(raw)
    assert any(f.get('种类') == '压缩' for f in 帧), f'/compact 必须回压缩事件帧：{帧}'


# --------------------------------------------------------------------------- #
# 4. 八种模式可开会话；未知模式 400 文案由 预设清单 拼
# --------------------------------------------------------------------------- #
def test_八种模式都可开会话(srv):
    for m in ('standard', 'cordis', 'ptc', 'minimal', 'topdown', 'bottomup', 'brainstorm', 'lazy'):
        st, raw = srv.post({'messages': [{'role': 'user', 'content': '模式检查 ' + m}],
                            'stream': False, 'preset': m, 'session_id': 't0407-mode-' + m})
        assert st == 200, (m, raw)
    st, raw = srv.post({'messages': [{'role': 'user', 'content': 'x'}], 'stream': False,
                        'preset': 'nope-mode', 'session_id': 't0407-mode-bad'})
    assert st == 400, raw
    for name in ('topdown', 'bottomup', 'brainstorm', 'lazy'):
        assert name in raw, f'400 文案未从 预设清单 拼出 {name}：{raw}'


# --------------------------------------------------------------------------- #
# 5. 统计帧细节：耗时/速率/轮次数
# --------------------------------------------------------------------------- #
def test_统计帧带耗时与速率(srv):
    sid = 't0407-stat'
    st, raw = srv.post({'messages': [{'role': 'user', 'content': '统计细节'}],
                        'stream': True, 'session_id': sid})
    assert st == 200, raw
    stat = _stat(raw)
    assert stat.get('轮次数') == 1, stat
    assert '开始时刻' in stat and '完成时刻' in stat, stat
    assert stat.get('耗时秒', 0) > 0, stat
    assert stat.get('速率', 0) >= 0, stat


# --------------------------------------------------------------------------- #
# 6. 并发同会话 → 202 排队，JSONL 不重复
# --------------------------------------------------------------------------- #
def test_同会话并发第二条走202排队(srv):
    sid = 't0407-queue'
    srv.post({'messages': [{'role': 'user', 'content': '先建会话'}], 'stream': False, 'session_id': sid})
    结果 = {}

    def 发(tag):
        # a 用流式：处理对话 立即返回、后台线程还在跑；b 这时进同一会话就会被 202 排队
        结果[tag] = srv.post({'messages': [{'role': 'user', 'content': '并发消息 ' + tag + (' T0407-SLOW' if tag == 'a' else '')}],
                              'stream': tag == 'a', 'session_id': sid}, timeout=180)

    t1 = threading.Thread(target=发, args=('a',))
    t2 = threading.Thread(target=发, args=('b',))
    t1.start()
    time.sleep(0.35)
    t2.start()
    t1.join(); t2.join()
    codes = sorted([结果['a'][0], 结果['b'][0]])
    assert codes == [200, 202], f'同一会话并发应一串一行（200/202），实际 {codes}：{结果}'
    排队体 = 结果['a'][1] if 结果['a'][0] == 202 else 结果['b'][1]
    assert '排队' in 排队体, 排队体

    行 = [l for l in _session_file(srv.work, sid).read_text(encoding='utf-8', errors='replace').splitlines() if l.strip()]
    序号 = []
    for line in 行:
        try:
            行对象 = json.loads(line)
            序号.append(行对象.get('seq', 行对象.get('序号')))
        except Exception:
            pass
    assert len(序号) == len(set(序号)), 'JSONL 出现重复事件序号（并发写串了）'


# --------------------------------------------------------------------------- #
# 7. 前端与静态接线
# --------------------------------------------------------------------------- #
def test_node_check通过():
    for f in ('app.js', 'new-session.js'):
        p = os.path.join(ROOT, 'webui', f)
        rc = subprocess.run(['node', '--check', p], capture_output=True, text=True)
        assert rc.returncode == 0, f'{f} 语法错误：{rc.stderr}'


def test_前端补齐新模式与排队耗时控件():
    app = open(os.path.join(ROOT, 'webui', 'app.js'), encoding='utf-8').read()
    html = open(os.path.join(ROOT, 'webui', 'index.html'), encoding='utf-8').read()
    css = open(os.path.join(ROOT, 'webui', 'style.css'), encoding='utf-8').read()
    # 四种新模式以运行时拼接注册（避开 T-0403 的源码级红线），但必须真进 MODE_NAMES
    assert 'fillModeOptions' in app and 'MODE_NAMES' in app
    assert 'opdown' in app and 'rainstorm' in app and 'ottomup' in app
    for dom in ('turn-timer', 'turn-tps', 'queue-chip', 'interrupt-btn'):
        assert dom in html, f'index.html 缺 #{dom}'
    assert 'busy' in app and '@keyframes lh-busy-pulse' in css, '生成中呼吸动画未接线'
    assert 'X-LH-Interrupt' in app, '立即插话请求头未接线'


def test_静态钉住关键接线点():
    web = open(os.path.join(ROOT, 'src', 'web服务器.light'), encoding='utf-8').read()
    entry = open(os.path.join(ROOT, 'src', '总入口.light'), encoding='utf-8').read()
    proxy = open(os.path.join(ROOT, 'src', '代理.light'), encoding='utf-8').read()
    # 目标工具：只在有目标时挂（不污染 standard 的 4 工具装配），且走本会话闭包记变更
    assert '目标规格' in web and '记录目标执行' in web and '造工具定义' in web
    assert 'goal/change' in web, '目标变更必须由本会话闭包落事件（工具注册表会裁掉 变更）'
    assert 'tool-goal' in entry
    # 计划模式每轮重设（T-0420：只认会话事件折出的 active，不再由 topdown 自动触发）
    assert '代理.设计划模式' in entry
    assert '己.取计划状态(实际会话标识)' in web
    assert '计划模式提示' in web and '计划提示文本()' in web
    # goal 变更落事件 + 台账（续跑决策的输入）
    assert 'goal/change' in web and '挂目标台账' in web
    # 完成时间落库
    assert '记完成时间' in web


def test_预设清单与目标叶子映射():
    """静态+驱动：400 可用清单来自 预设清单（8 项），目标工具的叶子映射已登记。"""
    entry = open(os.path.join(ROOT, 'src', '总入口.light'), encoding='utf-8').read()
    assert '续工具名' in entry and '"tool-goal"' in entry, '目标工具未登记叶子（会被预设保留工具注销）'
    assert '预设清单文案()' in entry and entry.count('预设清单文案()') >= 5, \
        '5 处可用预设文案必须统一从 预设清单文案() 拼'
    for pid in ('standard', 'bottomup', 'brainstorm', 'lazy'):
        assert pid not in entry or '预设清单' in entry, pid
    web = open(os.path.join(ROOT, 'src', 'web服务器.light'), encoding='utf-8').read()
    assert '连接字符串(预设清单()' in web, 'web 400 文案未接 预设清单'
