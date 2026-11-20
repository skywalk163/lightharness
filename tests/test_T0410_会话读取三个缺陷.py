# -*- coding: utf-8 -*-
"""T-0410 / T-0408 会话读取三个缺陷的正向判据（真起服务、真走 HTTP + 线程直调）。

T-0399 把验收从「直调 Web服务端 处理器方法」改成「真起服务进程 + 真走 HTTP」之后，
暴露出三个只有走真实链路才看得见的缺陷；T-0399 按红线只改测试与文档，用 strict xfail
把它们钉在 tests/test_T0399_新会话对齐.py（test_已知缺陷_*）。本文件是修复后的正向判据：

  1. `GET /api/sessions/current` 带认证令牌时**不再忽略** `?session=`：
     显式 session 优先，令牌→会话绑定只作「没写 session」时的兜底。
     （旧形状：令牌绑定的会话每次新建都被覆盖 → 带令牌问旧会话恒回最新那个。）
  2. 落库的 `tool-result` 消息 `内容` 里能解析出工具输出正文（判 `结果` 非空且含文件内容），
     并回填 `工具名` / `调用id`（与 生成SSE 同口径，下钻 content 子块）。
  3. `会话存储.保存索引()` 并发落盘不互踩：临时文件名带唯一后缀 + 进程内可重入锁，
     两个/四个线程同时 追加消息 → 零异常、`_index.json` 可解析、消息数累加正确。

## 三组的分工与写法

  - 第 1、2 组必须走真实链路（进程内直调处理器方法测不出「令牌绑定覆盖 session」
    的真实请求形状，也测不到落库那一层的正文提取），故照 T-0399 的 harness：
    起 `examples/运行Web服务器.light` 子进程 + 脚本化 mock LLM（纯标准库），
    从测试进程发 HTTP。
  - 第 3 组按卡面允许「用线程直调 会话存储，不必起 HTTP」：缺陷本体在存储层，
    起 HTTP 只会让失败原因隔了一层。线程数 × 轮数固定，便于复现。

## 反证（修复前必红）

在本卡 base（`f698095`）上跑本文件：第 1 组「带令牌 current?session=<旧会话>」
回的是新会话；第 2 组 `tool-result.内容` 解析出的 `结果` 是空串；第 3 组 4 线程
60 次追加稳定抛 `Permission denied / No such file`（实测 23 次失败）。
修复后在同样命令下全绿。
"""
import json
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
SERVER_SCRIPT = os.path.join(ROOT, 'examples', '运行Web服务器.light')
SERVER_TOKEN = 't0410-token'
BOOT_TIMEOUT_SEC = 180
TIMEOUT_SEC = 180


# --------------------------------------------------------------------------- #
# 环境定位：兄弟仓（光明编译器 / lightplugin）——口径同 运行.py / T-0399
# --------------------------------------------------------------------------- #
def _find_repo(env_name, dir_name):
    cands = []
    explicit = os.environ.get(env_name, '')
    if explicit:
        cands.append(explicit)
    here = ROOT
    for _ in range(6):
        here = os.path.dirname(here)
        if not here or here == os.path.dirname(here):
            break
        cands.append(os.path.join(here, dir_name))
        cands.append(os.path.join(here, 'duan-light-merge', dir_name))
    cands.append('/home/skywalk/dswork/' + dir_name)
    for c in cands:
        if c and os.path.isdir(c):
            return os.path.normpath(c)
    return ''


def _base_env():
    env = {k: v for k, v in os.environ.items()
           if k not in ('HARNESS_ROOT', 'HARNESS_CWD', 'HARNESS_PERMISSION_MODE',
                        'HARNESS_COMPACTION_THRESHOLD', 'HARNESS_COMPACTION_KEEP_ROUNDS',
                        'HARNESS_ENDPOINT', 'HARNESS_API_KEY', 'HARNESS_WEB_TOKEN')}
    for key, repo in (('LIGHTPLUGIN', 'lightplugin'), ('LIGHT_MERGE', 'light-merge')):
        found = _find_repo(key, repo)
        if found:
            env[key] = found
        else:
            env.pop(key, None)
    env['PYTHONIOENCODING'] = 'utf-8'
    return env


# --------------------------------------------------------------------------- #
# 脚本化 mock LLM：第一轮吐一个「读文件」工具调用，第二轮收尾。
#   为什么要它：HARNESS_WEB_MOCK=1 的内置占位客户端只会吐文本，
#   而第 2 组必须让真实 agent 循环走到工具执行 + tool/result 落库那一步。
# --------------------------------------------------------------------------- #
_MOCK_LLM_SRC = r'''
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class 处理器(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            载荷 = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            载荷 = {}
        消息 = 载荷.get("messages") or []
        已调 = any(isinstance(m, dict) and "tool_calls" in m for m in 消息)
        if 已调:
            块 = [
                {"choices": [{"index": 0, "delta": {"content": "完成"}, "finish_reason": None}]},
                {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
            ]
        else:
            参数 = json.dumps({"路径": "own.txt"}, ensure_ascii=False)
            块 = [
                {"choices": [{"index": 0, "delta": {"tool_calls": [
                    {"index": 0, "id": "c1", "type": "function",
                     "function": {"name": "读文件", "arguments": 参数}}]},
                    "finish_reason": None}]},
                {"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]},
            ]
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


class _MockLlm:
    def __init__(self, work: pathlib.Path):
        self.script = work / 'mockllm.py'
        self.script.write_text(_MOCK_LLM_SRC, encoding='utf-8')
        self.proc = subprocess.Popen(
            [sys.executable, '-u', str(self.script)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding='utf-8', errors='replace', cwd=str(work),
        )
        self.port = self._wait_port()

    def _wait_port(self, timeout=60):
        deadline = time.time() + timeout
        while time.time() < deadline:
            line = self.proc.stdout.readline()
            if line and line.strip().isdigit():
                return int(line.strip())
            if self.proc.poll() is not None:
                err = (self.proc.stderr.read() or '')[-800:]
                raise RuntimeError(f'mock LLM 起不来：{err}')
        raise RuntimeError('mock LLM 端口超时')

    @property
    def endpoint(self):
        return f'http://127.0.0.1:{self.port}/chat/completions'

    def stop(self):
        try:
            self.proc.kill()
            self.proc.wait(timeout=10)
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# 真实服务：起 examples/运行Web服务器.light 子进程，等它把内核端口写进端口文件
# --------------------------------------------------------------------------- #
class _Server:
    def __init__(self, work: pathlib.Path, extra_env=None):
        self.work = work
        self.port_file = work / 'port.txt'
        self.log_path = work / 'server.log'
        self.token = SERVER_TOKEN
        env = _base_env()
        env.update({
            'HARNESS_WEB_TOKEN': SERVER_TOKEN,
            'HARNESS_WEB_NO_OPEN': '1',
            'HARNESS_PORT_FILE': str(self.port_file),
            'HARNESS_HOME': str(work),
            'HARNESS_WEB_LIFETIME': '900',
        })
        if extra_env:
            env.update(extra_env)
        self._log = open(self.log_path, 'w', encoding='utf-8')
        self.proc = subprocess.Popen(
            [sys.executable, RUNNER, SERVER_SCRIPT],
            stdout=self._log, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='replace',
            cwd=str(work), env=env,
        )
        self.port = self._wait_port()

    def _wait_port(self, timeout=BOOT_TIMEOUT_SEC):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(f'服务进程提前退出 rc={self.proc.returncode}\n{self.log()[-2000:]}')
            try:
                raw = self.port_file.read_text(encoding='utf-8').strip()
            except OSError:
                raw = ''
            if raw:
                port = int(raw)
                try:
                    with socket.create_connection(('127.0.0.1', port), timeout=1):
                        return port
                except OSError:
                    pass
            time.sleep(0.2)
        raise RuntimeError(f'服务 {timeout}s 内没起来\n{self.log()[-2000:]}')

    def log(self) -> str:
        try:
            self._log.flush()
            return self.log_path.read_text(encoding='utf-8', errors='replace')
        except OSError:
            return ''

    def request(self, method, path, body=None, timeout=120, token=SERVER_TOKEN):
        data = json.dumps(body, ensure_ascii=False).encode('utf-8') if body is not None else None
        headers = {'Content-Type': 'application/json; charset=utf-8'}
        if token:
            headers['X-Auth-Token'] = token
        req = urllib.request.Request(
            f'http://127.0.0.1:{self.port}{path}', data=data, method=method,
            headers=headers,
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode('utf-8', 'replace')
                return resp.status, _as_json(raw)
        except urllib.error.HTTPError as e:
            raw = e.read().decode('utf-8', 'replace')
            return e.code, _as_json(raw)

    def get(self, path, **kw):
        return self.request('GET', path, **kw)

    def post(self, path, body=None, **kw):
        return self.request('POST', path, body, **kw)

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


def _as_json(raw):
    try:
        return json.loads(raw)
    except Exception:
        return raw


def _q(**kv):
    return '&'.join(
        urllib.parse.quote(str(k)) + '=' + urllib.parse.quote(str(v)) for k, v in kv.items()
    )


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture(scope='module')
def work():
    p = pathlib.Path(tempfile.mkdtemp(prefix='t4100'))
    try:
        yield p
    finally:
        shutil.rmtree(p, ignore_errors=True)


@pytest.fixture(scope='module')
def llm(work):
    m = _MockLlm(work)
    try:
        yield m
    finally:
        m.stop()


@pytest.fixture(scope='module')
def server(work, llm):
    srv = _Server(work, extra_env={
        'HARNESS_WEB_MOCK': '0',
        'HARNESS_ENDPOINT': llm.endpoint,
        'HARNESS_API_KEY': 'mock-key',
        'HARNESS_MODEL': 'mock',
    })
    # 文件类工具按进程根取根（见 T-0399 的「已知边界」），故把被读文件放在服务 cwd
    (work / 'own.txt').write_text('OWN-CONTENT', encoding='utf-8')
    try:
        yield srv
    finally:
        srv.stop()


def _new_session(srv, title, **fields):
    body = {'标题': title}
    body.update(fields)
    status, data = srv.post('/api/sessions', body)
    assert status == 200, f'POST /api/sessions 失败 {status}: {data}\n{srv.log()[-1500:]}'
    return data


def _detail(srv, sid):
    status, data = srv.get('/api/sessions/' + urllib.parse.quote(sid))
    assert status == 200, f'GET /api/sessions/{sid} 失败 {status}: {data}'
    return data


# --------------------------------------------------------------------------- #
# 1. 带令牌的 current 必须尊重显式 ?session=（令牌绑定只作兜底）
# --------------------------------------------------------------------------- #
def test_带令牌_current优先用session参数(server):
    a = _new_session(server, '缺陷甲')
    b = _new_session(server, '缺陷乙')
    assert a['id'] != b['id'], f'两次建会话拿到同一个 id：{a}'

    # ① 带令牌问旧会话 A —— 必须回 A（旧代码回的是 B：令牌绑定被 B 覆盖）
    status, got = server.get('/api/sessions/current?' + _q(session=a['id']),
                             token=SERVER_TOKEN)
    assert status == 200, f'带令牌 current?session=<A> 失败 {status}: {got}\n{server.log()[-1200:]}'
    assert got['id'] == a['id'], (
        f'带令牌 current?session={a["id"]} 回的是 {got["id"]}（应为 {a["id"]}）；'
        f'令牌绑定的会话是 {b["id"]}')
    assert got['标题'] == '缺陷甲', f'带令牌取 A 的标题拿到了别的会话的：{got["标题"]!r}'

    # ② 反向也对：带令牌问 B 回 B（不是「恒回 A」的另一种坏法）
    status, got_b = server.get('/api/sessions/current?' + _q(session=b['id']),
                               token=SERVER_TOKEN)
    assert status == 200 and got_b['id'] == b['id'], f'带令牌 current?session=<B> 回错：{got_b}'

    # ③ 不带令牌读 A —— 修复前就正确，修复后不能退化
    status, anon = server.get('/api/sessions/current?' + _q(session=a['id']), token=None)
    assert status == 200 and anon['id'] == a['id'], f'无令牌 current?session=<A> 回错：{anon}'

    # ④ 兜底仍在：不写 session 时，令牌绑定（最近新建的 B）依然是答案 —— W2 契约不破
    status, bound = server.get('/api/sessions/current', token=SERVER_TOKEN)
    assert status == 200, f'带令牌 current（无 session）失败 {status}: {bound}'
    assert bound['id'] == b['id'], (
        f'不带 session 时应回令牌绑定的最新会话 {b["id"]}，实际 {bound["id"]}')

    # ⑤ 显式 session 优先 = 指向不存在的会话就 404，不再悄悄回落到令牌绑定
    status, gone = server.get('/api/sessions/current?' + _q(session='session_不存在_0410'),
                              token=SERVER_TOKEN)
    assert status == 404, f'显式 session 不存在应 404，实际 {status}: {gone}'


# --------------------------------------------------------------------------- #
# 2. 落库的 tool-result 正文不再丢（且有工具名/调用id）
# --------------------------------------------------------------------------- #
def test_工具结果正文落库且有工具名(server):
    sid = _new_session(server, '工具正文', 权限预设='全放行')['id']
    body = {'model': 'mock', 'messages': [{'role': 'user', 'content': '读文件'}], 'session_id': sid}
    status, resp = server.post('/v1/chat/completions', body)
    assert status == 200, f'对话失败 {status}: {resp}\n{server.log()[-1500:]}'

    detail = _detail(server, sid)
    results = [m for m in detail['消息'] if isinstance(m, dict) and m.get('角色') == 'tool-result']
    assert results, f'全放行会话没有 tool-result 落库：{detail["消息"]}'

    raw = results[-1]['内容']
    assert isinstance(raw, str), f'tool-result 的 内容 应是序列化字典：{type(raw)}'
    payload = json.loads(raw)
    # ① 正文非空且确实是工具输出的正文（文件内容），不是「{}」也不是空串
    assert payload.get('结果'), f'tool-result 的「结果」是空的：{payload}'
    assert 'OWN-CONTENT' in payload['结果'], (
        f'tool-result 正文丢了（实际={payload["结果"]!r}）；'
        f'落库路径应下钻 块["content"] 子块的 text')
    # ② 工具名 / 调用id 回填（与 生成SSE 同口径，经 源序号 关联 tool/call）
    assert payload.get('工具名') == '读文件', f'工具名没回填：{payload}'
    assert payload.get('调用id') == 'c1', f'调用id没回填：{payload}'
    assert payload.get('是否错误') is False, f'成功的工具被标成出错：{payload}'
    # ③ tool-call 那条仍在（别为了补正文把调用记录顶掉）
    calls = [m for m in detail['消息'] if isinstance(m, dict) and m.get('角色') == 'tool-call']
    assert calls, 'tool-call 记录丢了'
    assert '读文件' in calls[-1]['内容'], f'tool-call 记录内容不对：{calls[-1]}'


# --------------------------------------------------------------------------- #
# 3. 索引并发落盘：线程直调 会话存储，零异常 + 计数正确 + 格式不变
# --------------------------------------------------------------------------- #
_CONCURRENCY_DRIVER = '''从 会话存储 导入 会话存储
从 线程 导入 线程
从 JSON 导入 解析JSON
从 文件系统 导入 读取文件, 路径连接
设 根 为 "@ROOT@"
设 库 为 新建 会话存储(根)
设 元 为 库.新建会话("并发", "")
设 标识 为 元["id"]
设 错误表 为 []
段落 跑(前缀, 轮数):
  设 i 为 0
  当 i < 轮数:
    尝试:
      库.追加消息(标识, ["角色": "user", "内容": 前缀 + 转字符串(i)])
    捕获 异常 e:
      错误表.追加(前缀 + ":" + 转字符串(e))
    设 i 为 i + 1
设 t1 为 新建 线程(跑, "A", @轮数@)
设 t2 为 新建 线程(跑, "B", @轮数@)
设 t3 为 新建 线程(跑, "C", @轮数@)
设 t4 为 新建 线程(跑, "D", @轮数@)
t1.开始()
t2.开始()
t3.开始()
t4.开始()
t1.等待()
t2.等待()
t3.等待()
t4.等待()
设 库2 为 新建 会话存储(根)
设 元2 为 库2.取元数据(标识)
设 行数 为 -1
尝试:
  设 行数 为 长(库2.获取会话(标识))
捕获 异常 e:
  设 行数 为 -1
设 索引可解 为 假
尝试:
  设 解 为 解析JSON(读取文件(路径连接(根, "sessions/_index.json")))
  如果 type(解) == dict:
    设 索引可解 为 真
捕获 异常 e:
  设 索引可解 为 假
打印("错误数=" + 转字符串(长(错误表)))
如果 长(错误表) > 0:
  打印("首错=" + 转字符串(错误表[0]))
打印("消息数=" + 转字符串(元2["消息数"]))
打印("行数=" + 转字符串(行数))
打印("索引可解=" + 转字符串(索引可解))
'''


def _lp(p) -> str:
    return str(p).replace('\\', '/')


def _run_driver(src: str, tmp_path):
    f = tmp_path / 'driver.light'
    f.write_text(src, encoding='utf-8')
    p = subprocess.run(
        [sys.executable, RUNNER, str(f)],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        timeout=TIMEOUT_SEC, cwd=str(tmp_path), env=_base_env(),
    )
    kv = {}
    for line in p.stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    return p.returncode, p.stdout + p.stderr, kv


def test_索引并发落盘零异常且计数正确(tmp_path):
    rounds = 15           # 4 线程 × 15 轮 = 60 次追加
    total = rounds * 4
    src = (_CONCURRENCY_DRIVER
           .replace('@ROOT@', _lp(tmp_path))
           .replace('@轮数@', str(rounds)))
    rc, out, kv = _run_driver(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    assert kv.get('错误数') == '0', (
        f'并发追加抛了异常（旧缺陷：固定 tmp 名互踩）：{kv.get("首错", "")}\n{out}')
    assert kv.get('消息数') == str(total), (
        f'索引消息数没累加对（丢计数=读改写被插队）：{kv.get("消息数")} != {total}\n{out}')
    assert kv.get('行数') == str(total), f'JSONL 行数不对：{kv.get("行数")} != {total}\n{out}'
    # 布尔经 转字符串 出来是 Python 口径的 True/False（不是「真/假」），两种都认
    assert kv.get('索引可解') in ('真', 'True'), f'_index.json 无法解析（被写坏）：\n{out}'

    # 索引落盘格式不变（键与结构一个不改，旧数据不迁移）
    index = json.loads((tmp_path / 'sessions' / '_index.json').read_text(encoding='utf-8'))
    assert list(index.keys()) == ['会话'], f'索引顶层键被改了：{list(index.keys())}'
    assert len(index['会话']) == 1, f'索引会话条数不对：{index["会话"]}'
    meta = index['会话'][0]
    assert set(meta.keys()) == {'id', '标题', '创建时间', '最后更新', '消息数', '文件'}, \
        f'索引条目键被改了：{sorted(meta.keys())}'
    assert meta['消息数'] == total, f'落盘的 消息数 不对：{meta["消息数"]} != {total}'

    # 临时文件不残留（原子写的清洁性）：唯一后缀也不能留垃圾
    leftovers = sorted(p.name for p in (tmp_path / 'sessions').glob('*.tmp'))
    assert leftovers == [], f'索引临时文件残留：{leftovers}'
