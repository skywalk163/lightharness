# -*- coding: utf-8 -*-
"""T-0420：plan 模式闭环判据。

判据分三层：
  1. 纯逻辑：exit_plan_mode 的参数校验 + 折叠计划状态（事件 → 投影）；
  2. 命令面：/plan、/plan off 不调模型、不走轮次，直接落事件并回 plan 帧；
     GET /api/sessions/current 的「计划」键随命令即时翻转；
  3. 接线静态：提示注入、exit 工具只在 active 时注册、前端角标/面板在位。

真起服务复用 T-0407 的 mock LLM / 服务器夹具（同 T-0399 姿势）。
反证：把 /plan 当普通消息发给模型，计数会从 0 变 1，test_plan命令不调模型 立红。
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import shutil
import urllib.request
from pathlib import Path

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
EXAMPLE = os.path.join(ROOT, 'examples', 'test_计划模式.light')
TESTS = os.path.dirname(os.path.abspath(__file__))


def _load_harness():
    spec = importlib.util.spec_from_file_location(
        't0407harness', os.path.join(TESTS, 'test_T0407_收口接线.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


H = _load_harness()


@pytest.fixture
def work():
    # Windows 路径长度限制：短临时目录（中文用例名不进路径）
    d = Path(tempfile.mkdtemp(prefix='lh420-'))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _run_example():
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    return subprocess.run([sys.executable, RUNNER, EXAMPLE], cwd=ROOT, env=env,
                          capture_output=True, text=True, encoding='utf-8', timeout=180)


def test_纯逻辑_投影与出口工具():
    proc = _run_example()
    assert proc.returncode == 0, (proc.stdout or '')[-1500:] + (proc.stderr or '')[-1500:]
    assert '计划模式纯逻辑核心子系统（模块39）测试通过' in proc.stdout


def _latest_sid(work):
    hits = [p.parent.name for p in work.rglob('session.jsonl')]
    assert hits, '找不到会话目录（/plan 应已建会话）'
    return sorted(hits)[-1]


def _get_json(port, path):
    req = urllib.request.Request(f'http://127.0.0.1:{port}{path}',
                                 headers={'X-Auth-Token': H.TOKEN})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode('utf-8'))


def test_plan命令不调模型且计划键翻转(work):
    llm = H._Mock(work)
    srv = H._Server(work, llm)
    try:
        body = {'model': 'mock', 'stream': False,
                'messages': [{'role': 'user', 'content': '/plan'}]}
        code, raw = srv.post(body)
        assert code == 200, raw[-800:]
        载荷 = json.loads(raw)
        assert 载荷['状态'] == 'ok' and 载荷['plan']['active'] is True, raw[-800:]
        assert llm.count()['n'] == 0, '/plan 被当消息发给模型了'

        sid = 载荷['会话']
        元数据 = _get_json(srv.port, '/api/sessions/current?session=' + sid)
        assert 元数据['计划']['active'] is True, 元数据
        assert 元数据['计划']['pending'] is False

        # 非法参数：400 用法，不落事件（带同一 session，避免新建会话）
        code2, raw2 = srv.post({'model': 'mock', 'stream': False, 'session_id': sid,
                                'messages': [{'role': 'user', 'content': '/plan maybe'}]})
        assert code2 == 400 and '用法：/plan 或 /plan off' in raw2, raw2[-500:]
        assert llm.count()['n'] == 0

        code3, raw3 = srv.post({'model': 'mock', 'stream': False, 'session_id': sid,
                                'messages': [{'role': 'user', 'content': '/plan off'}]})
        assert code3 == 200, raw3[-500:]
        assert json.loads(raw3)['plan']['active'] is False, raw3[-500:]
        assert _get_json(srv.port, '/api/sessions/current?session=' + sid)['计划']['active'] is False
        assert llm.count()['n'] == 0
    finally:
        srv.stop()
        llm.stop()


def test_plan流式回执先发计划帧(work):
    llm = H._Mock(work)
    srv = H._Server(work, llm)
    try:
        code, raw = srv.post({'model': 'mock', 'stream': True,
                              'messages': [{'role': 'user', 'content': '/plan'}]})
        assert code == 200, raw[-500:]
        frames = H._frames(raw)
        assert frames and frames[0].get('种类') == '计划', frames
        assert frames[0]['plan']['active'] is True
        assert '"计划"' in raw or '计划' in raw
        assert llm.count()['n'] == 0
    finally:
        srv.stop()
        llm.stop()


def test_接线与前端在位():
    web = open(os.path.join(ROOT, 'src', 'web服务器.light'), encoding='utf-8').read()
    proxy = open(os.path.join(ROOT, 'src', '代理.light'), encoding='utf-8').read()
    entry = open(os.path.join(ROOT, 'src', '总入口.light'), encoding='utf-8').read()
    plan_tool = open(os.path.join(ROOT, 'src', '计划工具.light'), encoding='utf-8').read()
    preset = open(os.path.join(ROOT, 'src', '预设组合.light'), encoding='utf-8').read()
    assert 'exit_plan_mode' in plan_tool and '计划工具处理为结果' in plan_tool
    # 出口工具只在 active 时注册，且复用本会话 commandId 落三类事件
    assert '如果 会话计划["active"] == 真' in web
    assert 'plan/submitted' in web and 'plan/mode' in web and '取计划命令编号' in web
    # 执行闸门对出口放行
    assert 'exit_plan_mode' in proxy
    # 提示来自规划组的 plan-mode section，并在系统提示前注入
    assert '计划提示文本' in preset and '计划模式提示' in entry
    # 前端：角标 + 面板 + SSE 帧 + sessions 计划键
    js = open(os.path.join(ROOT, 'webui', 'app.js'), encoding='utf-8').read()
    html = open(os.path.join(ROOT, 'webui', 'index.html'), encoding='utf-8').read()
    css = open(os.path.join(ROOT, 'webui', 'style.css'), encoding='utf-8').read()
    assert 'function applyPlanState' in js and 'json.种类 === "计划"' in js
    assert 'applyPlanState(data && data["计划"]' in js
    assert 'plan-chip' in html and 'plan-panel' in html
    assert '.plan-chip' in css and '.plan-panel' in css
