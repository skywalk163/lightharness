# -*- coding: utf-8 -*-
"""T-0425 单轮最大步数可配（长任务不再被 25 步硬截断）。

背景：代理循环 的 属性 最大步数 原本写死 25，而选项层虽支持 "最大步数" 键，
却没有任何调用方传它 —— 于是长任务（读文件→改代码→跑测试→复盘→再改）
很容易在一轮里用光步数，表现为 max-steps 提前收尾、任务被截断成几段。
2026-11-21 的真实长任务里，连续两轮都恰好停在 25 步。

设计（与 /goal --max-rounds 的会话级选项同口径）：
  优先级 请求体「最大步数」> 环境变量 HARNESS_MAX_STEPS > 内置默认（T-0439 起 96）。
  非法值不中断对话，只回落并把理由带出来（部署不该因一个环境变量拼错就起不来）。

判据：
  1. 纯逻辑：缺省 / 请求 / 环境三层优先级；请求优先于环境；
  2. 纯逻辑：非法值（0、负数、超上限、非数字）一律回落且给出可读理由；
  3. 代理循环：选项里的 最大步数 真的改变步数上限（不是接了线却不生效）；
  4. 端到端：请求体 / 环境变量都能改掉实际生效的步数，统计帧回报生效值与来源。

反证（旧实现下必须红）：
  - 第 1 组：旧实现没有 步数上限 模块，导入即失败；
  - 第 3 组：旧代理把 最大步数 恒当 25，传 3 仍会跑 25 步；
  - 第 4 组：旧统计帧没有「步数上限」字段。
"""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 300


def _find_sibling(name):
    candidates = [
        os.environ.get(name, ''),
        os.path.join(ROOT, '..', 'lightplugin' if name == 'LIGHTPLUGIN' else 'light'),
        os.path.join(ROOT, '..', '..', 'lightplugin' if name == 'LIGHTPLUGIN' else 'light'),
        '/home/skywalk/dswork/' + ('lightplugin' if name == 'LIGHTPLUGIN' else 'light'),
    ]
    for c in candidates:
        if c and os.path.isdir(c):
            return os.path.normpath(c)
    return ''


def _run(src, tmp_path):
    f = tmp_path / 'driver.light'
    f.write_text(src, encoding='utf-8')
    env = {k: v for k, v in os.environ.items() if k not in ('HARNESS_ROOT', 'HARNESS_CWD')}
    for key in ('LIGHTPLUGIN', 'LIGHT_MERGE'):
        found = _find_sibling(key)
        if found:
            env[key] = found
        else:
            env.pop(key, None)
    p = subprocess.run(
        [sys.executable, RUNNER, str(f)],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        timeout=TIMEOUT_SEC, cwd=str(tmp_path), env=env,
    )
    kv = {}
    for line in p.stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    return p.returncode, p.stdout + p.stderr, kv


# --------------------------------------------------------------------------- #
# 1. 优先级：请求 > 环境 > 缺省
# --------------------------------------------------------------------------- #
def test_步数优先级请求优先于环境(tmp_path):
    src = '''
从 步数上限 导入 解析最大步数, 步数缺省, 步数上限

段落 主:
  设 甲 为 解析最大步数(空, "")
  设 乙 为 解析最大步数(80, "")
  设 丙 为 解析最大步数(空, "60")
  设 丁 为 解析最大步数(120, "50")
  打印 "缺省值=" + 转字符串(甲["值"])
  打印 "缺省来源=" + 转字符串(甲["来源"])
  打印 "请求值=" + 转字符串(乙["值"])
  打印 "请求来源=" + 转字符串(乙["来源"])
  打印 "环境值=" + 转字符串(丙["值"])
  打印 "环境来源=" + 转字符串(丙["来源"])
  打印 "双给值=" + 转字符串(丁["值"])
  打印 "双给来源=" + 转字符串(丁["来源"])
  打印 "缺省常量=" + 转字符串(步数缺省)
  打印 "上限常量=" + 转字符串(步数上限)
主()
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动失败 rc={rc}\n{out}'
    assert kv['缺省值'] == '96', f'缺省应为 96（T-0439 上调）\n{out}'
    assert kv['缺省来源'] == '缺省', out
    assert kv['请求值'] == '80' and kv['请求来源'] == '请求', out
    assert kv['环境值'] == '60' and kv['环境来源'] == '环境', out
    # 反证：若优先级写反（环境盖请求），这里会是 50
    assert kv['双给值'] == '120' and kv['双给来源'] == '请求', \
        f'请求必须优先于环境变量（实际 {kv["双给值"]}）\n{out}'


# --------------------------------------------------------------------------- #
# 2. 非法值回落且理由可读
# --------------------------------------------------------------------------- #
def test_非法步数回落且给理由(tmp_path):
    src = '''
从 步数上限 导入 解析最大步数, 校验步数

段落 主:
  设 零 为 校验步数(0)
  设 负 为 校验步数(-5)
  设 超 为 校验步数(99999)
  设 好 为 校验步数(50)
  设 环境乱 为 解析最大步数(空, "abc")
  设 环境负 为 解析最大步数(空, "-3")
  打印 "零合法=" + 转字符串(零["ok"])
  打印 "零理由=" + 转字符串(零["错误"])
  打印 "负合法=" + 转字符串(负["ok"])
  打印 "超合法=" + 转字符串(超["ok"])
  打印 "好合法=" + 转字符串(好["ok"])
  打印 "环境乱值=" + 转字符串(环境乱["值"])
  打印 "环境乱理由=" + 转字符串(环境乱["错误"])
  打印 "环境负值=" + 转字符串(环境负["值"])
  打印 "环境负理由=" + 转字符串(环境负["错误"])
主()
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动失败 rc={rc}\n{out}'
    assert kv['零合法'] == 'False', f'0 步不该被接受（会退化成一步都不跑）\n{out}'
    assert '大于 0' in kv['零理由'], f'理由要能读懂：{kv["零理由"]}\n{out}'
    assert kv['负合法'] == 'False', out
    assert kv['超合法'] == 'False', out
    assert kv['好合法'] == 'True', out
    # 非法环境值必须回落缺省，并保留可读理由（不是静默吞掉）
    assert kv['环境乱值'] == '96', f'非法环境值应回落缺省，实际 {kv["环境乱值"]}\n{out}'
    assert '纯数字' in kv['环境乱理由'], f'环境值非法要给理由：{kv["环境乱理由"]}\n{out}'
    assert kv['环境负值'] == '96', out
    # 负号不是数字，所以在「纯数字」这一关就被挡住了——理由必须非空且点名变量
    assert kv['环境负理由'] != '', f'非法环境值必须给理由，不能静默回落\n{out}'
    assert 'HARNESS_MAX_STEPS' in kv['环境负理由'], out


# --------------------------------------------------------------------------- #
# 3. 代理循环真的按选项改上限（不是接了线却不生效）
# --------------------------------------------------------------------------- #
def test_代理按选项改变步数上限(tmp_path):
    src = '''
从 代理 导入 代理循环
从 会话 导入 新建会话
从 工具 导入 工具注册表, 造工具定义

类 死循环客户端:
  属性 模型名 等于 "mock"
  段落 构造:
    设 己.占位 为 0
  段落 对话响应(网络消息, 选项, 工具模式表, 增量回调 = 空):
    返回 [
      ["type": "block-start", "index": 0, "blockType": "tool-call"],
      ["type": "tool-call-delta", "index": 0, "id": "c1", "name": "echo1", "argumentsDelta": "{}"],
      ["type": "block-end", "index": 0, "block": ["type": "tool-call", "id": "c1", "name": "echo1", "arguments": "{}"]],
      ["type": "finish", "reason": ["种类": "tool-calls"]]
    ]

段落 假执行(参数):
  返回 ["content": [["type": "text", "text": "ok"]], "isError": 假]

段落 跑(上限):
  设 会话对象 为 新建会话("t0425", 当前目录())
  设 注册表 为 新建 工具注册表()
  注册表.注册(造工具定义("echo1", "回声", ["type": "object", "properties": {}], 假执行))
  设 代理对象 为 新建 代理循环(会话对象, 新建 死循环客户端(), 注册表, ["最大步数": 上限])
  设 结果 为 代理对象.驱动("跑")
  返回 结果

段落 主:
  设 三 为 跑(3)
  设 八 为 跑(8)
  打印 "三步种类=" + 转字符串(三["种类"])
  打印 "三步数=" + 转字符串(三["步骤数"])
  打印 "八步数=" + 转字符串(八["步骤数"])
主()
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动失败 rc={rc}\n{out}'
    # 反证：旧代理恒按 25 步跑，传 3 也会得到 25
    assert kv['三步种类'] == 'max-steps', out
    assert kv['三步数'] == '3', f'传 3 就该在第 3 步停下（旧实现固定 25），实际 {kv["三步数"]}\n{out}'
    assert kv['八步数'] == '8', f'传 8 就该跑 8 步，实际 {kv["八步数"]}\n{out}'


# --------------------------------------------------------------------------- #
# 4. 端到端：请求体 / 环境变量都能改掉实际生效步数，统计帧回报来源
# --------------------------------------------------------------------------- #
@pytest.mark.timeout(240)
def test_端到端步数上限生效且统计帧回报(tmp_path):
    import http.server
    import socketserver
    import threading
    import time
    import urllib.request

    class LLM(http.server.BaseHTTPRequestHandler):
        calls = 0

        def do_POST(self):
            n = int(self.headers.get('content-length', '0'))
            self.rfile.read(n)
            LLM.calls += 1
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.end_headers()

            def emit(d):
                self.wfile.write(('data: ' + json.dumps(d, ensure_ascii=False) + '\n\n').encode())
                self.wfile.flush()

            emit({"choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}]})
            emit({"choices": [{"index": 0, "delta": {"tool_calls": [{
                "index": 0, "id": f"c{LLM.calls}", "type": "function",
                "function": {"name": "bash", "arguments": '{"命令": "echo x"}'}}]}, "finish_reason": None}]})
            emit({"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]})
            self.wfile.write(b'data: [DONE]\n\n')
            self.wfile.flush()

        def log_message(self, *a):
            pass

    srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), LLM)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    llm_port = srv.server_address[1]

    def chat(env_extra, body_extra):
        work = tmp_path / ('w%d' % abs(hash((str(env_extra), str(body_extra)))))
        work.mkdir(exist_ok=True)
        env = dict(os.environ)
        env.update({
            'HARNESS_HOME': str(work), 'HARNESS_WEB_NO_OPEN': '1', 'HARNESS_WEB_MOCK': '0',
            'HARNESS_ENDPOINT': f'http://127.0.0.1:{llm_port}', 'HARNESS_API_KEY': 'k',
            'HARNESS_MODEL': 'mock', 'HARNESS_PORT_FILE': str(work / 'port'),
            'HARNESS_WEB_LIFETIME': '120', 'HARNESS_WEB_TOKEN': 'tok',
        })
        env.update(env_extra)
        LLM.calls = 0
        proc = subprocess.Popen(
            [sys.executable, RUNNER, os.path.join(ROOT, 'examples', '运行Web服务器.light')],
            cwd=str(work), env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            port = None
            for _ in range(240):
                try:
                    port = int((work / 'port').read_text().strip())
                    break
                except Exception:
                    time.sleep(0.25)
            assert port, '服务没起来'
            body = {'messages': [{'role': 'user', 'content': '一直跑别停'}], 'stream': True}
            body.update(body_extra)
            req = urllib.request.Request(
                f'http://127.0.0.1:{port}/v1/chat/completions',
                data=json.dumps(body).encode(),
                headers={'Content-Type': 'application/json', 'X-Auth-Token': 'tok'})
            with urllib.request.urlopen(req, timeout=180) as resp:
                raw = resp.read().decode('utf-8', 'replace')
        finally:
            proc.terminate()
        stat = None
        for line in raw.splitlines():
            if not line.startswith('data:'):
                continue
            payload = line[5:].strip()
            if payload == '[DONE]':
                continue
            try:
                j = json.loads(payload)
            except Exception:
                continue
            if isinstance(j, dict) and j.get('种类') == '统计':
                stat = j
        # 同时回报「模型实际被调用了几次」= 这一轮真正跑了几步。
        #   只看统计帧的 步数上限 字段是假判据：那个字段由服务端读出，
        #   即使选项没传给代理，它照样显示正确值（反跑实测确实漏过）。
        stat = dict(stat or {})
        stat['_实际步数'] = LLM.calls
        return stat

    srv_shutdown = srv.shutdown
    try:
        s1 = chat({}, {'最大步数': 3})
        assert s1 is not None, '缺统计帧'
        assert s1.get('步数上限') == 3, f'请求体 最大步数 应生效，统计帧={s1}'
        assert s1.get('步数上限来源') == '请求', s1
        # 真正钉住行为：模型只能被调 3 次（旧实现会一路跑到 25）
        assert s1['_实际步数'] == 3, (
            f'请求体 最大步数=3 应真的只跑 3 步，实际模型被调 {s1["_实际步数"]} 次（旧实现固定 25）')

        s2 = chat({'HARNESS_MAX_STEPS': '4'}, {})
        assert s2 is not None, '缺统计帧'
        assert s2.get('步数上限') == 4, f'环境变量应生效，统计帧={s2}'
        assert s2.get('步数上限来源') == '环境', s2
        assert s2['_实际步数'] == 4, (
            f'环境变量=4 应真的只跑 4 步，实际 {s2["_实际步数"]} 次')

        s3 = chat({}, {})
        assert s3 is not None and s3.get('步数上限') == 96, f'缺省应仍为 96，统计帧={s3}'
        assert s3.get('步数上限来源') == '缺省', s3
        assert s3['_实际步数'] == 96, f'缺省应跑 96 步，实际 {s3["_实际步数"]} 次' 
    finally:
        srv_shutdown()
