# -*- coding: utf-8 -*-
"""T-0453 P0：压缩之后还能不能继续（服务端）。

现场现象：长任务跑到上下文压缩，界面提示「已触发上下文压缩」后任务停住；
用户紧接着再发一条「继续」，界面毫无反应（像没发出去），会话也不再多任何消息。

本卡判的是「压缩之后这一条还能不能跑起来」，不是压缩质量：

  1. 第一轮 SSE 里必须真的出现「压缩」帧（场景成立，不是拿假压缩当证据）；
  2. 压缩提示出现的那一刻立刻发「继续」→ HTTP 200，且 30s 内真的多出一条
     assistant/message（旧行为：会话仍被占着 → 202 入队，而入队时那一轮的
     当 循环已经跳出 → 这条永远没人取）；
  3. 统计帧新增 结束原因，取值落在四值闭集内（completed/max-steps/max-tokens/aborted/error）；
  4. 压缩帧不能是最后一帧：顺序必须是 压缩 → 统计 → [DONE]；
  5. 压缩落盘后 增量保存（起始序号=压缩前最大序号）读回的消息条数 == 内存条数；
  6. 入队必有人取：释放占用的那一方必须把待办重新拉起来消费（本文件用闸门级
     不变量判：释放后待办被取走、占用被还回来）。

真起服务（同 T-0399/T-0407）：子进程跑 examples/运行Web服务器.light，
脚本化 mock LLM（纯标准库）驱动工具调用把上下文顶过压缩阈值。
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
TOKEN = 't0453-token'
BOOT_TIMEOUT = 180
结束原因闭集 = ('completed', 'max-steps', 'max-tokens', 'aborted', 'error')


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


_MOCK = r'''
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

计数 = {}
填充 = "填充数据" * 60


def 文本块(t):
    return [{"choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}]},
            {"choices": [{"index": 0, "delta": {"content": t}, "finish_reason": None}]},
            {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}]


def 工具块(i, 命令):
    return [{"choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}]},
            {"choices": [{"index": 0, "delta": {"tool_calls": [
                {"index": 0, "id": "c%d" % i, "type": "function",
                 "function": {"name": "bash", "arguments": json.dumps({"命令": 命令}, ensure_ascii=False)}}]},
                "finish_reason": None}]},
            {"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]}]


class 处理器(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == "/count":
            体 = json.dumps(计数).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(体)))
            self.end_headers()
            self.wfile.write(体)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        载荷 = json.loads(self.rfile.read(n) or b"{}")
        消息 = 载荷.get("messages") or []
        用户 = ""
        for m in reversed(消息):
            if m.get("role") == "user":
                内容 = m.get("content")
                if isinstance(内容, str):
                    用户 = 内容
                elif isinstance(内容, list):
                    用户 = "".join(b.get("text", "") for b in 内容 if isinstance(b, dict))
                break
        标签 = "继续" if ("继续" in 用户 and "T0453" not in 用户) else "长任务"
        计数[标签] = 计数.get(标签, 0) + 1
        if 标签 == "继续":
            块 = 文本块("继续往下做。")
        elif 计数[标签] <= 40:
            # 每一步都塞一块大工具输出：把上下文顶过压缩阈值，同时把轮次拖到步数上限
            块 = 工具块(计数[标签], "echo " + 填充 + " T0453")
        else:
            块 = 文本块("先到这里。")
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
            # 小窗口 + 小步数上限：一次长任务就会既压缩又撞步数上限（现场同款收口）
            'HARNESS_MODEL_CONTEXT_WINDOW': '200', 'HARNESS_MAX_STEPS': '8',
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

    def post(self, body, path='/v1/chat/completions', timeout=180):
        hs = {'Content-Type': 'application/json; charset=utf-8', 'X-Auth-Token': TOKEN}
        req = urllib.request.Request(f'http://127.0.0.1:{self.port}{path}',
                                     data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
                                     method='POST', headers=hs)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read().decode('utf-8', 'replace')
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode('utf-8', 'replace')

    def post_stream(self, body, on_frame=None, timeout=180):
        """POST 流式请求并**按行实时**读 SSE：每解析出一帧就回调 on_frame(帧)。

        返回 (状态码, 有序条目表, 原文)。条目表元素是 ("帧", dict) 或 ("DONE", 空)，
        用来判「压缩 → 统计 → [DONE]」的顺序；on_frame 用来在「看到压缩帧的那一刻」
        立刻发下一条请求（复现现场时序：提示一出现用户就按了发送）。
        """
        hs = {'Content-Type': 'application/json; charset=utf-8', 'X-Auth-Token': TOKEN}
        req = urllib.request.Request(f'http://127.0.0.1:{self.port}/v1/chat/completions',
                                     data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
                                     method='POST', headers=hs)
        try:
            resp = urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            return e.code, [], e.read().decode('utf-8', 'replace')
        条目 = []
        原文 = []
        with resp:
            状态 = resp.status
            while True:
                line = resp.readline()
                if not line:
                    break
                文本 = line.decode('utf-8', 'replace').rstrip('\r\n')
                if not 文本:
                    continue
                原文.append(文本)
                if not 文本.startswith('data: '):
                    continue
                体 = 文本[6:].strip()
                if 体 == '[DONE]':
                    条目.append(('DONE', 空))
                    continue
                try:
                    帧 = json.loads(体)
                except Exception:
                    continue
                if not isinstance(帧, dict):
                    continue
                条目.append(('帧', 帧))
                if on_frame:
                    on_frame(帧)
        return 状态, 条目, '\n'.join(原文)

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


空 = None


def _帧表(条目, 种类):
    return [j for 标, j in 条目 if 标 == '帧' and j.get('种类') == 种类]


def _统计(条目):
    表 = _帧表(条目, '统计')
    return 表[-1] if 表 else {}


def _文本(条目):
    out = []
    for 标, j in 条目:
        if 标 != '帧':
            continue
        for c in (j.get('choices') or []):
            d = c.get('delta') or {}
            if d.get('content'):
                out.append(d['content'])
    return ''.join(out)


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


def _用户文本(事件):
    数据 = 事件.get('data') or {}
    块表 = 数据.get('content') or []
    文本 = []
    for 块 in 块表:
        if isinstance(块, dict) and 块.get('type') == 'text':
            文本.append(块.get('text') or '')
    return ''.join(文本)


def _等继续轮收口(path, 秒=30):
    """等到「继续」这条用户消息之后真的出现 assistant/message 与 turn/end。"""
    截止 = time.time() + 秒
    while time.time() < 截止:
        事件 = _events(path)
        继续 = [e for e in 事件
                if e.get('type') == 'user/message' and _用户文本(e).strip() == '继续']
        if 继续:
            起号 = 继续[-1].get('seq') or 0
            助手 = [e for e in 事件
                    if e.get('type') == 'assistant/message' and (e.get('seq') or 0) > 起号]
            收口 = [e for e in 事件 if e.get('type') == 'turn/end' and (e.get('seq') or 0) > 起号]
            if 助手 and 收口:
                return 事件, 助手, 收口
        time.sleep(0.2)
    return _events(path), [], []


# --------------------------------------------------------------------------- #
@pytest.fixture(scope='module')
def work():
    p = pathlib.Path(tempfile.mkdtemp(prefix='t0453'))
    try:
        yield p
    finally:
        if os.environ.get('T0453_KEEP'):
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
# 1. 判据 1/2/4：压缩提示出现的那一刻发「继续」→ 必须 200 且真的跑起来
# --------------------------------------------------------------------------- #
def test_压缩提示后立刻继续必须200并跑出新消息(srv, work):
    sid = 't0453-continue'
    现场 = {}

    def 看到压缩帧(帧):
        # 复现现场时序：用户看到「已触发上下文压缩」提示，立刻按发送键。
        #   旧行为：此刻会话仍被推流协程占着 → 这条被判忙 202 入队 →
        #   而入队时后台那一轮的 当 循环已经跳出 → 永远没人取 → 界面毫无反应。
        if 帧.get('种类') != '压缩' or 现场.get('已发'):
            return
        现场['已发'] = True

        def 发继续():
            状态, 条目, 原文 = srv.post_stream(
                {'messages': [{'role': 'user', 'content': '继续'}], 'stream': True,
                 'session_id': sid}, timeout=120)
            现场['状态'] = 状态
            现场['条目'] = 条目
            现场['原文'] = 原文

        线程 = threading.Thread(target=发继续, daemon=True)
        线程.start()
        现场['线程'] = 线程

    状态1, 条目1, 原文1 = srv.post_stream(
        {'messages': [{'role': 'user', 'content': 'T0453 开始一次长任务'}], 'stream': True,
         'session_id': sid}, on_frame=看到压缩帧, timeout=300)
    assert 状态1 == 200, f'第一轮没起来：{状态1}\n{原文1[-2000:]}\n{srv.log()[-2000:]}'
    # 判据 1：场景成立 —— 第一轮 SSE 里真的出现了「压缩」帧
    assert _帧表(条目1, '压缩'), f'这个场景本该发生压缩却没有压缩帧（判据不成立）：{条目1[-6:]}'
    # 判据 4：压缩帧不能是最后一帧 —— 顺序 压缩 → 统计 → [DONE]
    位置 = {}
    for 下标, (标, j) in enumerate(条目1):
        if 标 == 'DONE':
            位置.setdefault('[DONE]', 下标)
        elif isinstance(j, dict) and j.get('种类') == '压缩':
            位置.setdefault('压缩', 下标)
        elif isinstance(j, dict) and j.get('种类') == '统计':
            位置.setdefault('统计', 下标)
    assert '[DONE]' in 位置, f'流里没有 [DONE]：{原文1[-800:]}'
    assert '统计' in 位置, f'流里没有统计帧：{原文1[-800:]}'
    assert 位置['压缩'] < 位置['统计'] < 位置['[DONE]'], \
        f'压缩帧之后必须还有统计帧与 [DONE]（实际顺序 {位置}）'

    # 判据 2：紧接着的「继续」必须 200（不是 202/409/空），且 30s 内真的多出 assistant 消息
    线程 = 现场.get('线程')
    assert 线程 is not None, '第一轮没有出现压缩帧，跑不到「继续」这一步'
    线程.join(timeout=120)
    assert 现场.get('状态') is not None, f'「继续」在 120s 内没有任何响应\n{srv.log()[-2000:]}'
    assert 现场['状态'] == 200, (
        f'压缩后「继续」拿到 {现场["状态"]}（不是 200）：'
        f'{str(现场.get("原文"))[-800:]}\n入队时那一轮已经跳出循环 → 这条永远没人取\n{srv.log()[-2000:]}')
    assert _帧表(现场['条目'], '统计'), f'「继续」的流里没有统计帧：{现场["条目"]}'
    assert '继续往下做' in _文本(现场['条目']), f'「继续」这一轮没有模型输出：{现场["条目"]}'

    路径 = _session_file(work, sid)
    事件, 助手, 收口 = _等继续轮收口(路径, 秒=30)
    assert 助手 and 收口, (
        '30s 内「继续」这条没有跑出 assistant/message 或 turn/end（压缩后这一条真的丢了）\n'
        + '\n'.join(f'{e.get("type")} {e.get("seq")}' for e in 事件[-12:]))
    继续轮 = [e for e in 事件
              if e.get('type') == 'user/message' and _用户文本(e).strip() == '继续']
    assert 继续轮, f'会话里没有「继续」这条用户消息：{[e.get("type") for e in 事件[-12:]]}'
    尾号 = max(e.get('seq') or 0 for e in 事件)
    assert 尾号 >= (收口[-1].get('seq') or 0), '事件序号倒退'


# --------------------------------------------------------------------------- #
# 2. 判据 3：统计帧新增 结束原因，取值落在四值闭集内
# --------------------------------------------------------------------------- #
def test_统计帧带结束原因且落在闭集(srv):
    sid = 't0453-reason'
    状态, 条目, 原文 = srv.post_stream(
        {'messages': [{'role': 'user', 'content': 'T0453 撞步数上限'}], 'stream': True,
         'session_id': sid}, timeout=300)
    assert 状态 == 200, 原文[-1500:]
    统计 = _统计(条目)
    assert 统计, f'没有统计帧：{原文[-800:]}'
    assert '结束原因' in 统计, (
        f'统计帧缺「结束原因」——前端拿不到「为什么停」的解释，只能看见空白：{统计}')
    assert 统计['结束原因'] in 结束原因闭集, f'结束原因越界：{统计["结束原因"]!r}'
    # 这个小窗口 + 8 步上限的场子里，本轮一定是撞步数停的（不是 completed）
    assert 统计['结束原因'] == 'max-steps', (
        f'撞步数上限的轮次必须报 max-steps，实际 {统计["结束原因"]!r}（旧实现根本没这个键）')

    # 正常跑完的一轮报 completed
    状态2, 条目2, 原文2 = srv.post_stream(
        {'messages': [{'role': 'user', 'content': '检查一下收尾'}], 'stream': False,
         'session_id': sid}, timeout=120)
    assert 状态2 == 200, 原文2[-800:]


# --------------------------------------------------------------------------- #
# 3. 判据 5：压缩落盘后「起始序号=压缩前最大序号」的增量保存必须不丢不乱
# --------------------------------------------------------------------------- #
_DRIVER = '''
从 会话 导入 新建会话
从 消息 导入 造用户消息, 造助手消息, 造文本块
从 压缩 导入 压缩到最近
从 总入口 导入 增量保存
从 持久化 导入 读入会话

段落 最大序号(会话对象):
  设 最大 为 0
  遍历 记录 之 会话对象.汇集全部事件():
    如果 记录["序号"] > 最大:
      设 最大 为 记录["序号"]
  返回 最大

段落 填对话(会话对象, 轮数, 字数):
  设 i 为 0
  当 i < 轮数:
    设 正文 为 "第" + 转字符串(i) + "轮："
    设 k 为 0
    当 k < 字数:
      设 正文 为 正文 + "填充内容"
      设 k 为  k + 1
    会话对象.记录事件("user/message", 造用户消息([造文本块(正文)]))
    会话对象.记录事件("assistant/message", ["消息": 造助手消息([造文本块("回答" + 正文)], "p", "m")])
    设 i 为 i + 1
  返回 真

段落 表内是否序号乱序(会话对象):
  设 表 为 会话对象.汇集全部事件()
  设 i 为 0
  当 i + 1 < 长度(表):
    如果 表[i]["序号"] > 表[i + 1]["序号"]:
      返回 真
    设 i 为 i + 1
  返回 假

段落 主:
  设 根 为 "."
  设 会话对象 为 新建会话("t0453save", 根)
  填对话(会话对象, 8, 3)
  设 忽略1 为 增量保存(根, 会话对象, 0)
  # 判据 5 口径：「增量保存(起始序号=压缩前长度)」，这里的长度就是 长(事件表)（= 下一序号）
  设 压缩前长度 为 长度(会话对象.汇集全部事件())
  设 忽略2 为 压缩到最近(会话对象, 2, 空, 20)
  # 增量保存 再走一遍：压缩替换 插了检查点（序号最大、位置居中）
  设 忽略3 为 增量保存(根, 会话对象, 压缩前长度)
  设 重载 为 读入会话(根, 根, "t0453save")
  打印 "内存条数=" + 转字符串(长度(会话对象.整理消息()))
  打印 "读回条数=" + 转字符串(长度(重载.整理消息()))
  打印 "压缩前水位=" + 转字符串(压缩前长度)
  打印 "压缩后最大序号=" + 转字符串(最大序号(会话对象))
  打印 "压缩后表长=" + 转字符串(长度(会话对象.汇集全部事件()))
  打印 "表内乱序=" + 转字符串(表内是否序号乱序(会话对象))
主()
'''


def _run_driver(src, tmp_path):
    f = tmp_path / 'driver.light'
    f.write_text(src, encoding='utf-8')
    env = {k: v for k, v in os.environ.items() if k not in ('HARNESS_ROOT', 'HARNESS_CWD')}
    env['PYTHONIOENCODING'] = 'utf-8'
    p = subprocess.run([sys.executable, RUNNER, str(f)], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=300, cwd=str(tmp_path), env=env)
    kv = {}
    for line in p.stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    return p.returncode, p.stdout + p.stderr, kv


def test_压缩后增量保存读回条数一致(tmp_path):
    rc, out, kv = _run_driver(_DRIVER, tmp_path)
    assert rc == 0, f'驱动失败 rc={rc}\n{out}'
    # 场景成立：压缩替换 真的插了一条检查点（表长比压缩前水位多 1）
    assert int(kv['压缩后表长']) > int(kv['压缩前水位']), (
        f'这个场景本该真的压缩（检查点多出一条事件）：{kv}\n{out}')
    print(f'压缩后 表长={kv["压缩后表长"]} 最大序号={kv["压缩后最大序号"]} '
          f'表内乱序={kv["表内乱序"]}（判据只认「读回==内存」条数）')
    assert kv['内存条数'] == kv['读回条数'], (
        f'压缩后 增量保存(起始序号=压缩前长度 {kv["压缩前水位"]}) 读回条数不一致：'
        f'内存 {kv["内存条数"]} vs 读回 {kv["读回条数"]}\n{out}')


# --------------------------------------------------------------------------- #
# 4. 判据 6：入队必有人取 —— 释放占用的一方必须把待办重新拉起来
# --------------------------------------------------------------------------- #
_GATE_DRIVER = '''
从 会话队列 导入 队建闸门, 队尝试占用, 队释放占用, 队是否忙, 队入队, 队排队深度
从 web服务器 导入 拉起待办消费, 后台消费待办

段落 假载具:
  返回 ["服务": 空, "会话": 空, "客户端": 空, "注册表": 空, "会话标识": "", "选项": 空, "闸门": 空]

段落 主:
  设 闸门 为 队建闸门()
  设 键 为 "t0453队列"
  # ① 有人持锁：拉起必须拒绝（待办由那一轮的轮末取，不能被第二个消费者抢走）
  设 入1 为 队入队(闸门, 键, ["文本": "持锁期待办", "流式": 假, "入队时刻": 时间戳()])
  打印 "入队ok=" + 转字符串(入1["ok"])
  设 占1 为 队尝试占用(闸门, 键)
  打印 "占用被持有=" + 转字符串(占1)
  设 拉起1 为 拉起待办消费(假载具(), 闸门, 键)
  打印 "持锁时拉起=" + 转字符串(拉起1)
  打印 "持锁时深度=" + 转字符串(队排队深度(闸门, 键))
  # ② 那一轮跑完（跳出循环）才释放 → 释放方必须重新拉起消费
  设 忽略释放 为 队释放占用(闸门, 键)
  设 拉起2 为 拉起待办消费(假载具(), 闸门, 键)
  打印 "释放后拉起=" + 转字符串(拉起2)
  # ③ 消费侧契约（同步判）：取走待办、跑完把占用还回来
  设 闸门2 为 队建闸门()
  设 键2 为 "t0453队列2"
  设 入2 为 队入队(闸门2, 键2, ["文本": "孤儿待办", "流式": 假, "入队时刻": 时间戳()])
  设 占2 为 队尝试占用(闸门2, 键2)
  打印 "占用二=" + 转字符串(占2)
  后台消费待办(假载具(), 闸门2, 键2)
  打印 "消费后深度=" + 转字符串(队排队深度(闸门2, 键2))
  打印 "消费后忙=" + 转字符串(队是否忙(闸门2, 键2))
主()
'''


def _布尔(out, 键):
    """从驱动输出里取一个布尔值。容忍并发线程把两行打印粘在一起（打印不保证行原子）。"""
    m = re.search(re.escape(键) + r'=(True|False)', out)
    return m.group(1) if m else None


def _整数(out, 键):
    m = re.search(re.escape(键) + r'=(\d+)', out)
    return m.group(1) if m else None


def test_释放占用的那一方必须把待办拉起来(tmp_path):
    rc, out, kv = _run_driver(_GATE_DRIVER, tmp_path)
    assert rc == 0, f'驱动失败 rc={rc}\n{out}'
    assert _布尔(out, '入队ok') == 'True', out
    assert _布尔(out, '占用被持有') == 'True', out
    # 有人持锁 → 拉起不能抢，待办还在（由那一轮的轮末取）
    assert _布尔(out, '持锁时拉起') == 'False', f'占用被持有时不该抢：{out}'
    assert _整数(out, '持锁时深度') == '1', f'待办不该在持锁期被吞掉：{out}'
    # 释放后 → 必须把待办拉起来（否则入队项永远没人取：现场「继续无反应」就是这个）
    assert _布尔(out, '释放后拉起') == 'True', (
        f'释放占用时待办非空却没重新拉起消费 → 入队项永远没人取\n{out}')
    # 兜底消费的契约：取走待办、跑完必须把占用还回来（否则下一轮又被判忙）
    assert _布尔(out, '占用二') == 'True', out
    assert _整数(out, '消费后深度') == '0', f'兜底消费没把待办取走：{out}'
    assert _布尔(out, '消费后忙') == 'False', f'兜底消费结束后占用没还回来：{out}'
