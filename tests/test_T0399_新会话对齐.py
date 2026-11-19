# -*- coding: utf-8 -*-
"""T-0399 对齐验收：新会话「五件事」整链 E2E（真起服务、真走 HTTP）。

T-0395（会话 cwd）、T-0396（新会话面板 + 只读目录校验）、T-0397（会话模式/权限）、
T-0398（附件暂存 / 用量+压缩入口）单卡 verify 各自的绿，只证明各自那一段；
本卡判的是**串起来**还能不能用：

  1. `POST /api/sessions{标题,工作目录,模式,权限预设}` → `GET current`/详情 cwd 与设置正确；
     `GET /api/cwd/check` 三态（目录 / 普通文件 / 不存在）+ 建会话的 400 拒绝；
  2. 首条 `/v1/chat/completions` 带 `preset` + `权限预设` + `attachments`
     → 会话记录四键（工作目录/模式/权限预设/模型）齐全，附件在场不打断首条落库；
     换一个新进程（同一持久化根）重读，四键仍在；
  3. 两个会话不同目录 + 不同权限**并发**（真并发 HTTP 请求）→ 目录/权限互不串，
     同一工具在「全放行」会话里执行、在「全拒绝」会话里被挡；
  4. `/compact` 走 HTTP 发完之后会话仍能继续发消息，历史可回看；
  5. 切回旧会话 → 模式/权限/目录按会话恢复，续聊不抹、另一个会话不受污染；
  6. 文档/对标登记自检（防止「只在 summary 里说登记了」而文件没动）。

## 与单卡判据的分工（本卡为什么不是「再测一遍 T-0395~T-0398」）

单卡走的是「`Web服务端` 处理器方法 + 假客户端」的进程内直调。那样测的是
路由函数本身，**从不碰 socket、不碰真实客户端对象、不碰持久化根**。本卡反过来：
真起 `examples/运行Web服务器.light` 子进程、从测试进程发 HTTP、用脚本化 mock LLM
（纯标准库 ThreadingHTTPServer，不引新依赖）驱动工具调用。

## 反证（中间态必红）

只合入 T-0395（`32fca17`）时跑本文件：第 1/2/3/5 组会因为「current/详情没有
模式、权限预设 两键」「创建期不收模式/权限」「会话级权限闸门不生效」而失败，
证明这些用例真的串了 T-0395~T-0397 的链路，而不是只测单卡。

## 已知边界（不改业务代码，已另开卡）

  - **会话索引写入在真并发下会互踩**：`会话存储.保存索引()` 的临时文件名是固定的
    `<索引>.tmp`，两个请求同时落盘时后到者 rename 到已被前者 rename 掉的文件
    → `No such file or directory` → 该轮 500「会话持久化失败」。因此本文件第 3 组
    的「并发」用**两个 HTTP 客户端同时发**（浏览器里两个标签页的真实形状），
    而不是在同一个进程里开两个线程直调 处理对话 —— 后者会稳定复现上述业务缺陷
    （已按卡面红线「发现 T-0395~T-0398 的 bug 开新卡」登记，不在本卡里修）。
  - 文件类工具仍按**进程根**取根（`HARNESS_ROOT`/服务进程 cwd），不按会话 cwd；
    故第 3 组断言的是「同一份进程根文件，全放行会话读得到、全拒绝会话被挡」，
    不是「工具读到了该会话目录下的文件」。
  - `/v1/chat/completions` 不消费 `attachments`（前端 best-effort 上送，协议既有面），
    故第 2 组只判「附件在场不打断首条消息落库」，不判附件进模型上下文。
  - Web 层没有独立的压缩端点：`/compact` 就是一条普通消息（T-0398 的入口即如此），
    故第 4 组判「发完 `/compact` 之后还能继续发、历史还在」，不判压缩摘要一定生成
    （摘要生成由服务端压缩阈值决定，属另一条链路）。
"""
import json
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
SERVER_SCRIPT = os.path.join(ROOT, 'examples', '运行Web服务器.light')
SERVER_TOKEN = 't0399-token'
BOOT_TIMEOUT_SEC = 180
_DEFAULT_TOKEN = object()   # 哨兵：区分「没传 → 用服务令牌」和「显式 None → 不带认证头」


# --------------------------------------------------------------------------- #
# 环境定位：兄弟仓（光明编译器 / lightplugin）——口径同 运行.py
# --------------------------------------------------------------------------- #
def _find_repo(env_name, dir_name):
    """沿祖先逐级探测兄弟仓（worktree 深度不固定，口径同 运行.py / T-0396）。"""
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
    """子进程环境：清掉会改变默认值的宿主变量，按需补兄弟仓路径。"""
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
# 脚本化 mock LLM（纯标准库；只在需要「模型开口调工具」的用例里启用）
#
# 为什么要它：`HARNESS_WEB_MOCK=1` 的内置占位客户端只会吐文本，
# 而第 3 组必须让真实 agent 循环走到工具执行/权限闸门那一步。
# 不做成 pytest fixture 的 autouse，避免给纯文本用例拖慢启动。
# --------------------------------------------------------------------------- #
_MOCK_LLM_SRC = r'''
import json, sys
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
    """起一个只听 127.0.0.1:0 的 mock LLM，端口由内核分配。"""

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
# 真实服务：起 `examples/运行Web服务器.light` 子进程，等它把内核端口写进端口文件
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
            # 持久化根：会话 JSONL/索引/session-modes.json 都落在这里，
            # 重启恢复用例要指着同一个根再起一次。
            'HARNESS_HOME': str(work),
            # 常驻用例的「寿命」：远大于本文件耗时，测试结束显式 kill。
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
                # 端口文件已写 ≠ 已在 accept；用一次 TCP 连接确认真的起来了
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

    # ---- HTTP 客户端（只走公开 HTTP 面，不 import 被测模块）----
    def request(self, method, path, body=None, timeout=120, token=_DEFAULT_TOKEN):
        data = json.dumps(body, ensure_ascii=False).encode('utf-8') if body is not None else None
        headers = {'Content-Type': 'application/json; charset=utf-8'}
        # token=None 显式表示「这条请求不带认证头」（用来验证令牌与会话参数的关系）
        use = self.token if token is _DEFAULT_TOKEN else token
        if use:
            headers['X-Auth-Token'] = use
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
    """把中文键也安全塞进查询串（urllib 不接受非 ASCII 的 URL）。"""
    return '&'.join(
        urllib.parse.quote(str(k)) + '=' + urllib.parse.quote(str(v)) for k, v in kv.items()
    )


def _norm(s) -> str:
    return os.path.normcase(os.path.normpath(str(s).strip()))


def _same(a, b) -> bool:
    return _norm(a) == _norm(b)


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture(scope='module')
def work():
    """模块级短基准目录：服务要起一次（编译 ~10s），五个用例共用。"""
    p = pathlib.Path(tempfile.mkdtemp(prefix='t3999'))
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
    """主服务：走脚本化 mock LLM（真实客户端对象，能触发工具调用）。"""
    srv = _Server(work, extra_env={
        'HARNESS_WEB_MOCK': '0',
        'HARNESS_ENDPOINT': llm.endpoint,
        'HARNESS_API_KEY': 'mock-key',
        'HARNESS_MODEL': 'mock',
    })
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


def _current(srv, sid, token=None):
    """GET /api/sessions/current?session=<id>。

    ⚠️ 这里**故意不带认证令牌**：带令牌时服务端按「令牌→会话」绑定优先解析，
    会忽略 `?session=`，返回该令牌最后创建的那个会话（见下方
    `test_已知缺陷_current忽略session参数` 与另开的新卡）。本卡不动业务代码，
    故正链用例走不带令牌的读法把链路本身验干净，缺陷单独钉在一条用例里。
    """
    status, data = srv.get('/api/sessions/current?' + _q(session=sid), token=token)
    assert status == 200, f'GET /api/sessions/current 失败 {status}: {data}'
    return data


def _chat(srv, sid, text, **extra):
    body = {'model': 'mock', 'messages': [{'role': 'user', 'content': text}], 'session_id': sid}
    body.update(extra)
    status, data = srv.post('/v1/chat/completions', body)
    return status, data


def _roles(detail):
    return [m.get('角色') for m in detail.get('消息') or [] if isinstance(m, dict)]


def _count_role(detail, role):
    return sum(1 for r in _roles(detail) if r == role)


# --------------------------------------------------------------------------- #
# 1. 建会话带目录 → current/详情 cwd 正确 + cwd/check 三态 + 非法目录 400
# --------------------------------------------------------------------------- #
def test_建会话带目录_current与详情cwd一致(server, work):
    target = work / '对齐目录'
    target.mkdir(exist_ok=True)

    meta = _new_session(server, '对齐', 工作目录=str(target))
    sid = meta['id']
    assert _same(meta.get('工作目录', ''), str(target)), f'创建回显的 cwd 不对：{meta}'

    cur = _current(server, sid)
    assert _same(cur.get('工作目录', ''), str(target)), f'GET current 的 cwd 不对：{cur}'
    assert _same(_detail(server, sid).get('工作目录', ''), str(target)), '会话详情 cwd 不对'

    # 面板 chip 的只读校验：目录 / 普通文件 / 不存在 三态
    status, ok = server.get('/api/cwd/check?' + _q(工作目录=str(target)))
    assert status == 200, f'cwd/check 失败 {status}: {ok}'
    assert ok['存在'] is True and ok['是目录'] is True and ok['可读'] is True, ok
    assert _same(ok['绝对路径'], str(target)), f'绝对路径回显不对：{ok}'
    assert ok['错误'] == '', ok

    a_file = work / 'own.txt'
    status, file_res = server.get('/api/cwd/check?' + _q(工作目录=str(a_file)))
    assert status == 200, file_res
    assert file_res['存在'] is True and file_res['是目录'] is False, f'普通文件被判成目录：{file_res}'
    assert file_res['错误'] != '', '指向普通文件时必须给中文理由'

    missing = work / '不存在的目录'
    status, miss_res = server.get('/api/cwd/check?' + _q(工作目录=str(missing)))
    assert status == 200, miss_res
    assert miss_res['存在'] is False and miss_res['可读'] is False and miss_res['错误'] != '', miss_res

    # 建会话的 400：相对路径 / 不存在 都必须拒绝，且不落索引
    status, rel = server.post('/api/sessions', {'标题': 'rel', '工作目录': 'rel/dir'})
    assert status == 400, f'相对路径应 400，实际 {status}: {rel}'
    status, gone = server.post('/api/sessions', {'标题': 'gone', '工作目录': str(missing)})
    assert status == 400, f'不存在的目录应 400，实际 {status}: {gone}'

    # 空体 / 坏 JSON 仍是旧行为（不因多读一个可选键变成 500）
    status, _ = server.post('/api/sessions', {})
    assert status == 200, '空对象体应仍按旧行为建会话'
    status, _ = server.request('POST', '/api/sessions', None)
    assert status == 200, '空体应仍按旧行为建会话'


# --------------------------------------------------------------------------- #
# 2. 首条消息带 preset/权限/附件 → 四键齐全 + 重启后仍能读回
# --------------------------------------------------------------------------- #
def test_首条消息带preset权限附件_四键齐全且重启可恢复(server, work):
    target = work / '首条目录'
    target.mkdir(exist_ok=True)
    meta = _new_session(server, '首条', 工作目录=str(target))
    sid = meta['id']

    attachments = [{'name': 'a.txt', 'type': 'text/plain',
                    'dataUrl': 'data:text/plain;base64,QQ=='}]
    status, resp = _chat(server, sid, '你好带附件', preset='ptc', 权限预设='全放行',
                         attachments=attachments)
    assert status == 200, f'首条消息（preset+权限+附件）失败 {status}: {resp}\n{server.log()[-1500:]}'

    detail = _detail(server, sid)
    # 四键齐全：工作目录 / 模式 / 权限预设 / 模型
    assert _same(detail['工作目录'], str(target)), f'详情 cwd 丢了：{detail["工作目录"]}'
    assert detail['模式'] == 'ptc', f'preset 没写进会话：{detail["模式"]}'
    assert detail['权限预设'] == '全放行', f'权限预设没写进会话：{detail["权限预设"]}'
    assert detail['模型'] == 'mock', f'模型没写进会话：{detail["模型"]}'
    # 附件在场不能把首条消息顶掉
    assert len(detail['消息']) >= 2, f'首条消息没落库（附件字段打断了？）：{detail["消息"]}'
    assert any('你好带附件' in json.dumps(m, ensure_ascii=False) for m in detail['消息']), \
        '用户正文丢了'

    cur = _current(server, sid)
    assert cur['模式'] == 'ptc' and cur['权限预设'] == '全放行', f'current 没回两键：{cur}'

    # 换一个新进程（同一持久化根，不同端口）重读：只增不改的键必须落盘
    srv2 = _Server(server.work, extra_env={
        'HARNESS_WEB_MOCK': '1', 'HARNESS_MODEL': 'mock',
    })
    try:
        again = _detail(srv2, sid)
        assert _same(again['工作目录'], str(target)), '重启后 cwd 丢了'
        assert again['模式'] == 'ptc', '重启后模式丢了'
        assert again['权限预设'] == '全放行', '重启后权限预设丢了'
        assert again['模型'] == 'mock', '重启后会话模型丢了'
        assert len(again['消息']) >= 2, '重启后消息丢了'
    finally:
        srv2.stop()


# --------------------------------------------------------------------------- #
# 3. 两会话不同目录 + 不同权限并发：目录/权限互不串，工具放行/拒绝各按会话
# --------------------------------------------------------------------------- #
def test_两会话不同目录不同权限并发隔离(server, work):
    a_dir = work / '甲项目'
    b_dir = work / '乙项目'
    a_dir.mkdir(exist_ok=True)
    b_dir.mkdir(exist_ok=True)

    a = _new_session(server, '甲', 工作目录=str(a_dir), 权限预设='全放行')
    b = _new_session(server, '乙', 工作目录=str(b_dir), 权限预设='全拒绝')

    results, errors = {}, {}

    def fire(name, sid, text):
        try:
            results[name] = _chat(server, sid, text)
        except Exception as e:  # 线程里抛不出去，收进 errors 供断言打印
            errors[name] = f'{type(e).__name__}: {e}'

    # 真并发：两个客户端线程同时打同一个服务进程（浏览器两个标签页的形状）
    threads = [threading.Thread(target=fire, args=('甲', a['id'], '读甲的目录')),
               threading.Thread(target=fire, args=('乙', b['id'], '读乙的目录'))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f'并发请求抛异常：{errors}'
    assert results['甲'][0] == 200, f'甲会话对话失败：{results["甲"]}\n{server.log()[-1500:]}'
    assert results['乙'][0] == 200, f'乙会话对话失败：{results["乙"]}\n{server.log()[-1500:]}'

    da = _detail(server, a['id'])
    db = _detail(server, b['id'])

    # 目录/权限互不串
    assert _same(da['工作目录'], str(a_dir)), f'甲 cwd 被串了：{da["工作目录"]}'
    assert _same(db['工作目录'], str(b_dir)), f'乙 cwd 被串了：{db["工作目录"]}'
    assert da['权限预设'] == '全放行' and db['权限预设'] == '全拒绝', \
        f'两会话权限串了：甲={da["权限预设"]} 乙={db["权限预设"]}'

    # 全放行：工具真的执行了（有 tool-call 也有 tool-result）
    # 注：这里只判「执行了没有」，不判结果文本 —— 落库的 tool-result 正文当前恒为空
    # （见 test_已知缺陷_tool_result消息正文丢失 与另开的新卡），属既有业务缺陷。
    assert _count_role(da, 'tool-call') >= 1, '全放行会话连工具调用都没发起（工具表没接上？）'
    assert _count_role(da, 'tool-result') >= 1, '全放行会话的工具没执行'

    # 全拒绝：只有调用记录，没有结果记录（被会话级闸门挡在工具执行之前）
    assert _count_role(db, 'tool-call') >= 1, '全拒绝会话连调用记录都没有（闸门没接上？）'
    assert _count_role(db, 'tool-result') == 0, '全拒绝会话的工具被执行了（会话级权限没生效）'


# --------------------------------------------------------------------------- #
# 4. /compact 走 HTTP 之后，会话仍能继续发消息
# --------------------------------------------------------------------------- #
def test_压缩后会话仍可继续发消息(server, work):
    target = work / '压缩目录'
    target.mkdir(exist_ok=True)
    sid = _new_session(server, '压缩', 工作目录=str(target))['id']

    for i in range(3):
        status, resp = _chat(server, sid, f'第{i}句')
        assert status == 200, f'第 {i} 轮对话失败 {status}: {resp}'

    before = len(_detail(server, sid)['消息'])

    # T-0398 的「压缩」入口 = 发一条 /compact（前端 requestCompaction 就是这么做的）
    status, compact = _chat(server, sid, '/compact')
    assert status == 200, f'/compact 失败 {status}: {compact}\n{server.log()[-1500:]}'

    # 压缩之后仍能继续发，且不是 500
    status, resp = _chat(server, sid, '压缩后继续')
    assert status == 200, f'压缩后继续发消息失败 {status}: {resp}\n{server.log()[-1500:]}'
    assert resp.get('choices'), f'压缩后续轮没有拿到模型回复：{resp}'

    detail = _detail(server, sid)
    assert len(detail['消息']) > before, '压缩后消息没继续落库（落库断档？）'
    # 压缩不该动会话属性：cwd 还在、模式键还在（值可以是空=跟随全局）
    assert _same(detail.get('工作目录', ''), str(target)), '压缩把会话 cwd 弄丢了'
    assert '模式' in detail, '压缩后会话详情丢了「模式」键'


# --------------------------------------------------------------------------- #
# 5. 切回旧会话：模式/权限/目录按会话恢复，续聊不吃默认值
# --------------------------------------------------------------------------- #
def test_切回旧会话恢复模式权限目录(server, work):
    a_dir = work / '旧会话目录'
    b_dir = work / '新会话目录'
    a_dir.mkdir(exist_ok=True)
    b_dir.mkdir(exist_ok=True)

    old = _new_session(server, '旧', 工作目录=str(a_dir), 模式='minimal', 权限预设='全拒绝')
    new = _new_session(server, '新', 工作目录=str(b_dir), 模式='cordis', 权限预设='全放行')

    assert _chat(server, old['id'], '甲一')[0] == 200
    assert _chat(server, new['id'], '乙一')[0] == 200

    # 切回旧会话：前端 selectSession 走 GET /api/sessions/<id>，用它回填
    # cwd（bindSessionCwd）、模式/权限（applySessionMode）与历史；这是「切回恢复」
    # 真正的那条数据通路，必须在 HTTP 层断言。
    back = _detail(server, old['id'])
    assert _same(back['工作目录'], str(a_dir)), f'切回后 cwd 没恢复：{back["工作目录"]}'
    assert back['模式'] == 'minimal' and back['权限预设'] == '全拒绝', \
        f'切回后模式/权限没恢复：{back["模式"]}/{back["权限预设"]}'
    assert back['消息'], '切回后历史是空的'

    # current 是另一条读法（前端 refreshSessionTitle 用它取标题）；
    # 不带认证令牌时也按 ?session= 还原，两条读法口径一致。
    back_cur = _current(server, old['id'])
    assert back_cur['id'] == old['id'], f'current 回的不是这个会话：{back_cur["id"]}'
    assert _same(back_cur['工作目录'], str(a_dir)), 'current 的 cwd 与详情不一致'
    assert back_cur['模式'] == 'minimal' and back_cur['权限预设'] == '全拒绝', \
        'current 的模式/权限与详情不一致'

    # 续聊只带消息、不再带 preset/权限：旧会话必须保住自己的设置
    assert _chat(server, old['id'], '甲二')[0] == 200
    detail = _detail(server, old['id'])
    assert detail['模式'] == 'minimal' and detail['权限预设'] == '全拒绝', \
        f'续聊把旧会话设置抹了：{detail["模式"]}/{detail["权限预设"]}'
    assert _same(detail['工作目录'], str(a_dir)), '续聊把旧会话 cwd 抹了'

    # 另一个会话不受影响
    other = _detail(server, new['id'])
    assert other['模式'] == 'cordis' and other['权限预设'] == '全放行', \
        f'乙会话被旧会话的切回污染：{other["模式"]}/{other["权限预设"]}'
    assert _same(other['工作目录'], str(b_dir)), '乙会话 cwd 被改'

    # 会话内切换只改本会话（不动另一个，也不动全局默认）
    status, switched = server.post(
        '/api/sessions/' + urllib.parse.quote(old['id']) + '/' + urllib.parse.quote('模式权限'),
        {'模式': 'ptc'},
    )
    assert status == 200, f'会话内切换失败 {status}: {switched}'
    old_after = _detail(server, old['id'])
    assert old_after['模式'] == 'ptc', old_after['模式']
    assert old_after['权限预设'] == '全拒绝', '只传模式时权限被连带抹掉'
    assert _detail(server, new['id'])['模式'] == 'cordis', '会话内切换污染了另一个会话'


# --------------------------------------------------------------------------- #
# 5.5 已知缺陷钉桩（本卡不动业务代码，缺陷另开卡；修好后这里的 strict xfail 会变红，
#     提醒把钉桩改成正向断言）
# --------------------------------------------------------------------------- #
@pytest.mark.xfail(strict=True, reason=(
    '已知缺陷（另开卡）：GET /api/sessions/current 带认证令牌时忽略 ?session=，'
    '返回该令牌最后创建的那个会话。前端 refreshSessionTitle(id) 正是带令牌取标题，'
    '多会话下会拿到别的会话的标题。修好后请把本条改成正向断言。'))
def test_已知缺陷_current忽略session参数(server, work):
    a = _new_session(server, '缺陷甲')
    b = _new_session(server, '缺陷乙')
    assert a['id'] != b['id']

    # 带令牌问 A，应当回 A
    got = _current(server, a['id'], token=SERVER_TOKEN)
    assert got['id'] == a['id'], (
        f'带令牌 current?session={a["id"]} 回的是 {got["id"]}（应为 {a["id"]}）；'
        f'令牌绑定的会话是 {b["id"]}'
    )


@pytest.mark.xfail(strict=True, reason=(
    '已知缺陷（另开卡）：处理对话 落库的 tool-result 消息正文恒为空。'
    '事件层 tool/result 的 content 是嵌套块（{type:tool-result, content:[{type:text,...}]}），'
    '而落库路径只扫顶层 type=="text"，于是「结果」被写成空串，会话重放看不到工具输出。'
    '修好后请把本条改成正向断言。'))
def test_已知缺陷_tool_result消息正文丢失(server, work):
    sid = _new_session(server, '缺陷工具', 权限预设='全放行')['id']
    status, resp = _chat(server, sid, '读文件')
    assert status == 200, resp
    detail = _detail(server, sid)
    results = [m for m in detail['消息'] if m.get('角色') == 'tool-result']
    assert results, '全放行会话没有 tool-result 落库'
    body = results[-1]['内容']
    assert 'OWN-CONTENT' in body, f'tool-result 正文丢了（实际={body!r}）'


# --------------------------------------------------------------------------- #
# 6. 文档/对标登记的自检（防止「只在 summary 里说登记了」而文件没动）
# --------------------------------------------------------------------------- #
def test_文档与对标登记到位():
    quick = open(os.path.join(ROOT, 'docs', '快速开始.md'), encoding='utf-8').read()
    api = open(os.path.join(ROOT, 'docs', 'API参考.md'), encoding='utf-8').read()
    change = open(os.path.join(ROOT, 'CHANGELOG.md'), encoding='utf-8').read()

    # 快速开始：五件事 checklist（目录/模式/权限/附件/压缩）+ 失败时怎么排查
    for word in ('新建会话', '/api/cwd/check', '模式', '权限', '附件', '压缩'):
        assert word in quick, f'docs/快速开始.md 缺「{word}」（冒烟 checklist 不完整）'
    assert '排查' in quick, 'docs/快速开始.md 的 checklist 必须给「失败时怎么排查」'

    # API 参考：接口与新键
    for word in ('POST /api/sessions', 'GET /api/cwd/check', 'GET /api/sessions/current',
                 '工作目录', '权限预设', 'attachments'):
        assert word in api, f'docs/API参考.md 缺「{word}」'

    # CHANGELOG 有一条本卡的记录
    assert 'T-0399' in change, 'CHANGELOG.md 没有 T-0399 条目'

    # 对标清单：只在末尾追加（编号升序、无重复、旧编号一个不删）
    path = os.path.join(ROOT, 'docs', '功能对标', '对标清单.json')
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    entries = data['条目']
    nums = [e['编号'] for e in entries]
    assert nums == sorted(nums), '对标清单编号乱序（旧条目被重排）'
    assert len(nums) == len(set(nums)), '对标清单编号重复'
    # 本卡新增的是尾部连续 5 条（#366~#370，对应 T-0395~T-0399），
    # 用「尾部连续 5 个递增整数」判，避免把编号写死成某次运行的快照。
    tail = nums[-5:]
    assert tail == list(range(tail[0], tail[0] + 5)), f'尾部 5 条编号不连续：{tail}'
    assert tail[0] >= 366, f'本卡应在旧末号之后追加，实际尾部：{tail}'
    assert 365 in nums, '旧末号 365 被删了（只增不改）'
    tail_text = json.dumps(entries[-5:], ensure_ascii=False)
    for num in ('T-0395', 'T-0396', 'T-0397', 'T-0398', 'T-0399'):
        assert num in tail_text, f'对标清单新增条目没登记 {num}'
