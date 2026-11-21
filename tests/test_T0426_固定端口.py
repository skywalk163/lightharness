# -*- coding: utf-8 -*-
"""T-0426 固定端口（HARNESS_WEB_PORT）：给常驻 Web GUI 一个稳定地址。

背景：Web 服务端一直用 bind(("127.0.0.1", 0)) 由内核分配端口（协作规程 §3：
不写死端口），好处是 600+ 个 example 并行起临时服务互不冲突，代价是**每次重启
地址都会变** —— 给人长期用的 GUI 场景下，书签和深链每重启一次就失效。

取舍：默认仍是内核分配（不能改默认，否则并行门禁互踩），新增 HARNESS_WEB_PORT
显式固定；指定端口不可用时**不放弃启动**，回退内核分配并在启动日志说明原因。

判据：
  1. HARNESS_WEB_PORT=N → 真的绑到 N，启动日志明示「固定端口」；
  2. 端口被占用 → 回退内核分配，服务照常起来，日志写明占用原因；
  3. 非法值（非数字/超范围）→ 回退内核分配，日志写明原因；
  4. 不设该变量 → 仍为内核分配（旧行为不变，红灯即改坏默认）。

反证（旧实现下必须红）：旧 HTTP服务端 构造只收 3 参、恒 bind(port=0)，
第 1 条永远拿不到 7788，第 2/3 条也没有「回退」这回事。
"""
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
SERVER = os.path.join(ROOT, 'examples', '运行Web服务器.light')
BOOT_TIMEOUT = 90


def _free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _env(work, extra):
    env = dict(os.environ)
    env.update({
        'HARNESS_HOME': str(work), 'HARNESS_WEB_NO_OPEN': '1',
        'HARNESS_WEB_LIFETIME': '30', 'HARNESS_PORT_FILE': str(work / 'port'),
        'HARNESS_WEB_TOKEN': 'tok-test',
    })
    # 起步别让本机的真实配置渗进来：显式 mock，且清掉可能干扰端口判断的变量
    env['HARNESS_WEB_MOCK'] = '1'
    env.pop('HARNESS_PORT', None)
    env.update(extra)
    return env


def _start(work, extra):
    log = work / 'server.log'
    fh = open(log, 'w', encoding='utf-8')
    proc = subprocess.Popen([sys.executable, RUNNER, SERVER], cwd=str(work),
                            env=_env(work, extra), stdout=fh, stderr=subprocess.STDOUT)
    return proc, log, fh


def _wait_port(work):
    end = time.time() + BOOT_TIMEOUT
    while time.time() < end:
        try:
            raw = (work / 'port').read_text(encoding='utf-8').strip()
            if raw:
                return int(raw)
        except OSError:
            pass
        time.sleep(0.2)
    return None


def _stop(proc, fh):
    proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
    fh.close()


# --------------------------------------------------------------------------- #
# 1. 固定端口真的生效
# --------------------------------------------------------------------------- #
def test_指定端口真的绑到该端口():
    work = Path(tempfile.mkdtemp(prefix='lh_port_'))
    want = _free_port()
    proc, log, fh = _start(work, {'HARNESS_WEB_PORT': str(want)})
    try:
        actual = _wait_port(work)
        assert actual == want, \
            f'HARNESS_WEB_PORT={want} 应绑到 {want}，实际 {actual}\n{log.read_text(encoding="utf-8", errors="replace")[-2000:]}'
        text = log.read_text(encoding='utf-8', errors='replace')
        assert '固定端口' in text, f'启动日志应明示固定端口\n{text[-1500:]}'
        assert '端口回退' not in text, f'端口可用时不该出现回退提示\n{text[-1500:]}'
        # 真的能连上（不是只写了个端口文件）
        s = socket.create_connection(('127.0.0.1', want), timeout=5)
        s.close()
    finally:
        _stop(proc, fh)


# --------------------------------------------------------------------------- #
# 2. 端口被占用 → 回退，但服务必须照常起来
# --------------------------------------------------------------------------- #
def test_端口被占用时回退且服务可用():
    work = Path(tempfile.mkdtemp(prefix='lh_port_busy_'))
    want = _free_port()
    # 先占住
    holder = socket.socket()
    holder.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    holder.bind(('127.0.0.1', want))
    holder.listen(1)
    proc, log, fh = _start(work, {'HARNESS_WEB_PORT': str(want)})
    try:
        actual = _wait_port(work)
        assert actual is not None, '端口被占用时服务仍必须启动（回退内核分配）'
        assert actual != want, f'端口 {want} 已被占用，不该拿到同一个端口'
        text = log.read_text(encoding='utf-8', errors='replace')
        assert '端口回退' in text, f'回退必须在日志里说清原因，否则用户只看到地址变了\n{text[-1500:]}'
        assert str(want) in text, f'回退说明应点名是哪个端口占用\n{text[-1500:]}'
    finally:
        _stop(proc, fh)
        holder.close()


# --------------------------------------------------------------------------- #
# 3. 非法值 → 回退，不阻断启动
# --------------------------------------------------------------------------- #
def test_非法端口值回退不阻断启动():
    work = Path(tempfile.mkdtemp(prefix='lh_port_bad_'))
    proc, log, fh = _start(work, {'HARNESS_WEB_PORT': 'not-a-port'})
    try:
        actual = _wait_port(work)
        assert actual is not None, '非法 HARNESS_WEB_PORT 不该让服务起不来'
        text = log.read_text(encoding='utf-8', errors='replace')
        assert '端口回退' in text, f'非法值要给出可读原因\n{text[-1500:]}'
    finally:
        _stop(proc, fh)


# --------------------------------------------------------------------------- #
# 4. 不设变量 → 仍是内核分配（旧行为，改坏默认这里会红）
# --------------------------------------------------------------------------- #
def test_未设变量仍走内核分配():
    work = Path(tempfile.mkdtemp(prefix='lh_port_default_'))
    proc, log, fh = _start(work, {})
    try:
        actual = _wait_port(work)
        assert actual is not None and actual > 0, '默认启动应仍由内核分配端口'
        text = log.read_text(encoding='utf-8', errors='replace')
        assert '固定端口' not in text, f'未设 HARNESS_WEB_PORT 时不该声称固定端口\n{text[-1500:]}'
    finally:
        _stop(proc, fh)


# --------------------------------------------------------------------------- #
# 5. 源码契约：默认参数必须保持 0（防止有人把默认改成写死端口）
# --------------------------------------------------------------------------- #
def test_源码默认端口仍为内核分配():
    with open(os.path.join(ROOT, 'stdlib', 'HTTP服务端.light'), encoding='utf-8') as fh:
        text = fh.read()
    # 直接找带 端口 形参的那个构造（文件里可能有别的 构造）
    m = None
    for cand in re.finditer(r'段落 构造\(([^)]*)\)', text):
        if '端口' in cand.group(1):
            m = cand
            break
    assert m, '找不到带 端口 形参的 HTTP服务端 构造'
    params = [p.strip() for p in m.group(1).split(',') if p.strip()]
    assert any('端口=0' in p.replace(' ', '') for p in params), \
        f'构造 必须保留 端口=0 默认（并行门禁靠内核分配避让），实际 {params}'