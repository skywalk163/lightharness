# -*- coding: utf-8 -*-
"""T-0468 判据：lightharness 的 MCP 工具在生产装配路径上不再整批消失。

背景（2026-11-25 只读诊断）：
  mcp.json 配了 hive / lightmem 两个 HTTP MCP server，`mcp接线.挂载MCP服务器` 直接调用
  是好的（2 服务器 / 31 工具 / 0 失败），但生产路径三层断链：
    1) 配置发现靠 cwd —— Web 进程 cwd 不在仓库根时相对 "mcp.json" 找不到，静默 no-op；
    2) 预设过滤把 `mcp__*` 全注销 —— 装配挂载集里没有 MCP 的位置；
    3) 预设挂载集从没给 MCP 留入口（总入口旧注释「暂不挂载」）。

本卡判据（对应任务卡「验收」四条）：
  A. 设 HARNESS_MCP_CONFIG 指向临时 mcp.json（stdio 测试服务器）→ 组装注册表("standard","")
     名单里含 mcp__*（至少 1 个），且核心 bash 仍在（没把工具面换掉）。
  B. 不设环境变量，但配置放在「数据根」下 → 组装注册表("standard", 数据根) 也能发现。
  C. 配置缺失时日志明确打印「未找到 MCP 配置」+ 返回结构带 未找到=真（不是静默 no-op）。
  D. standard 预设下 MCP 工具不被 预设保留工具 注销；会话级开关 HARNESS_MCP_TOOLS=0 关掉后不再挂；
     收紧预设 minimal 仍按既有口径不挂（不给 minimal 塞宿主级工具）。

判据口径说明（写进 .hive/summary.md）：
  - 工具名到叶子 把 mcp__* 登记成「自身即叶子」，预设过滤的通配规则据此放行 —— 因此 D 用
    纯注册表（造工具定义 造假 MCP 工具）单测，不真起 MCP 服务器，避免判据被网络/宿主机配置污染。
  - A/B 用 examples/mcp_服务器.py（本仓既有 stdio fixture，echo/add 两个工具）真起一台服务器。
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
MCP_FIXTURE = os.path.join(ROOT, 'examples', 'mcp_服务器.py')
SERVER_NAME = 't0468'

# 这些环境变量会改变装配结果，判据必须自己控制（不能吃宿主机的真实配置）
_STRIP = (
    'HARNESS_ROOT', 'HARNESS_CWD', 'HARNESS_HOME', 'HARNESS_PRESET',
    'HARNESS_MCP_CONFIG', 'HARNESS_MCP_TOOLS', 'DSH_HOME',
    'HARNESS_PERMISSION_MODE', 'HARNESS_API_KEY', 'HARNESS_ENDPOINT',
    'HARNESS_MODEL', 'HARNESS_WEB_TOKEN', 'HARNESS_TOKEN', 'HARNESS_BIND',
)


def _env(extra=None):
    env = {k: v for k, v in os.environ.items() if k not in _STRIP}
    # 生产挂载（lightplugin）只在兄弟仓里；照抄 test_T0456 的兄弟仓探测
    here = ROOT
    for _ in range(6):
        here = os.path.dirname(here)
        if not here or here == os.path.dirname(here):
            break
        cand = os.path.join(here, 'lightplugin')
        if os.path.isdir(cand) and 'LIGHTPLUGIN' not in env:
            env['LIGHTPLUGIN'] = cand
    env['PYTHONIOENCODING'] = 'utf-8'
    if extra:
        env.update(extra)
    return env


def _run_light(source, work, name, cwd=None, extra_env=None):
    path = work / (name + '.light')
    path.write_text(source, encoding='utf-8')
    proc = subprocess.run([sys.executable, RUNNER, str(path)],
                          cwd=str(cwd or ROOT), capture_output=True, text=True,
                          timeout=240, env=_env(extra_env))
    kv = {}
    for line in (proc.stdout or '').splitlines():
        if '=' in line and not line.startswith('['):
            k, v = line.split('=', 1)
            kv.setdefault(k.strip(), v.strip())
    return proc.returncode, (proc.stdout or '') + (proc.stderr or ''), kv


def _missing_module(out):
    return ('生产挂载' in out) and ('No module named' in out or 'ModuleNotFound' in out or '导入失败' in out)


@pytest.fixture(scope='module')
def work():
    p = pathlib.Path(tempfile.mkdtemp(prefix='t0468'))
    try:
        yield p
    finally:
        shutil.rmtree(p, ignore_errors=True)


def _write_mcp_json(path):
    """本仓既有 stdio fixture：command 必须是绝对路径（解析MCP配置 形状校验）。"""
    cfg = {
        'mcpServers': [
            {'name': SERVER_NAME, 'command': sys.executable, 'args': [MCP_FIXTURE]}
        ]
    }
    path.write_text(json.dumps(cfg), encoding='utf-8')
    return path


_FAKE_HELPERS = '''
段落 假执行(_参):
  设 结果 为 {"content": [["type": "text", "text": "ok"]], "isError": 假}
  返回 结果

段落 造假表():
  设 形 为 {"type": "object", "properties": {}}
  设 表 为 新建 工具注册表()
  设 定甲 为 造工具定义("mcp__fake__a", "假 MCP 工具 A", 形, 假执行)
  表.注册(定甲)
  设 定乙 为 造工具定义("mcp__fake__b", "假 MCP 工具 B", 形, 假执行)
  表.注册(定乙)
  返回 表

段落 逗号连接(表):
  设 文本 为 ""
  设 序 为 0
  遍历 项 之 表:
    如果 序 > 0:
      设 文本 为 文本 + ","
    设 文本 为 文本 + 转字符串(项)
    设 序 为 序 + 1
  返回 文本
'''

# A + D：显式 HARNESS_MCP_CONFIG；真起一台 stdio 服务器；另用假注册表单测 预设保留工具
_DRIVER_EXPLICIT = '''
从 总入口 导入 组装注册表, 预设保留工具, 工具名到叶子
从 工具 导入 工具注册表, 造工具定义
从 内置核心转换 导入 转字符串
''' + _FAKE_HELPERS + '''
段落 主():
  设 标 为 组装注册表("standard")
  设 名表 为 标.名单()
  设 找到 为 []
  遍历 名 之 名表:
    如果 开头(名, "mcp__") == 真:
      找到.追加(名)
  打印 "STD_COUNT=" + 转字符串(长度(名表))
  打印 "STD_MCP_COUNT=" + 转字符串(长度(找到))
  打印 "STD_MCP=" + 逗号连接(找到)
  打印 "STD_HAS_BASH=" + 转字符串(名表.包含("bash"))
  打印 "MAP_MCP=" + 逗号连接(工具名到叶子("MAP_PROBE_NAME"))
  设 表 为 造假表()
  预设保留工具(表, "standard")
  打印 "KEEP_FAKE_STD=" + 转字符串(表.有无("mcp__fake__a")) + "/" + 转字符串(表.有无("mcp__fake__b"))
  设 小表 为 造假表()
  预设保留工具(小表, "minimal")
  打印 "KEEP_FAKE_MIN=" + 转字符串(小表.有无("mcp__fake__a"))

主()
'''

# B：不设 HARNESS_MCP_CONFIG，配置放在「数据根」下
_DRIVER_DATAROOT = '''
从 总入口 导入 组装注册表
从 内置核心转换 导入 转字符串

段落 主():
  设 根 为 环境变量("T0468_DATA_ROOT", "")
  设 标 为 组装注册表("standard", 根)
  设 找到 为 []
  遍历 名 之 标.名单():
    如果 开头(名, "mcp__") == 真:
      找到.追加(名)
  打印 "DATAROOT_MCP_COUNT=" + 转字符串(长度(找到))
  打印 "DATAROOT_MCP=" + 转字符串(找到)
  打印 "DATAROOT_HAS_BASH=" + 转字符串(标.名单().包含("bash"))

主()
'''

# C + D(开关)：隔离 cwd（空目录）下找不到任何 mcp.json；再把 HARNESS_MCP_TOOLS 关掉
_DRIVER_MISSING = '''
从 mcp接线 导入 挂载MCP服务器
从 总入口 导入 预设保留工具
从 工具 导入 工具注册表, 造工具定义
从 内置核心转换 导入 转字符串
''' + _FAKE_HELPERS + '''
段落 主():
  设 表 为 新建 工具注册表()
  设 结果 为 挂载MCP服务器(表)
  打印 "NO_CFG_REGISTERED=" + 转字符串(长度(结果["已注册"]))
  打印 "NO_CFG_SERVERS=" + 转字符串(结果["服务器数"])
  打印 "NO_CFG_NOT_FOUND=" + 转字符串(结果["未找到"])
  设置环境变量("HARNESS_MCP_TOOLS", "0")
  设 关表 为 造假表()
  预设保留工具(关表, "standard")
  打印 "OFF_KEEP=" + 转字符串(关表.有无("mcp__fake__a"))

主()
'''


@pytest.mark.timeout(240)
def test_standard预设下MCP工具有叶子且不被注销(work):
    cfg = _write_mcp_json(work / 'mcp_explicit.json')
    src = _DRIVER_EXPLICIT.replace('MAP_PROBE_NAME', 'mcp__' + SERVER_NAME + '__echo')
    rc, out, kv = _run_light(src, work, 'explicit', extra_env={'HARNESS_MCP_CONFIG': str(cfg)})
    if rc != 0 and _missing_module(out):
        pytest.skip('本机缺 lightplugin 兄弟仓：装配层用例请在 192.168.0.88 上跑')
    assert rc == 0, out
    # A：standard 下 MCP 工具必须活着（至少 1 个），且核心工具面没被换掉
    assert int(kv.get('STD_MCP_COUNT', '0')) >= 1, ('standard 下 MCP 工具全丢', kv, out)
    names = [x for x in kv.get('STD_MCP', '').split(',') if x]
    assert any(x.startswith('mcp__' + SERVER_NAME + '__') for x in names), (names, out)
    assert kv.get('STD_HAS_BASH') == 'True', out
    # D：预设保留工具 不再注销 MCP 工具（真实路径与假注册表两条）
    assert kv.get('KEEP_FAKE_STD') == 'True/True', ('standard 注销了 MCP 工具', kv, out)
    # 工具名到叶子 给 MCP 工具自持叶子（否则装配挂载集看不到它们）
    assert kv.get('MAP_MCP') == 'mcp__' + SERVER_NAME + '__echo', kv


@pytest.mark.timeout(240)
def test_数据根下mcp配置也能被发现(work):
    root = work / 'dataroot'
    root.mkdir(exist_ok=True)
    _write_mcp_json(root / 'mcp.json')
    rc, out, kv = _run_light(_DRIVER_DATAROOT, work, 'dataroot',
                             extra_env={'T0468_DATA_ROOT': str(root)})
    if rc != 0 and _missing_module(out):
        pytest.skip('本机缺 lightplugin 兄弟仓：装配层用例请在 192.168.0.88 上跑')
    assert rc == 0, out
    assert int(kv.get('DATAROOT_MCP_COUNT', '0')) >= 1, ('数据根 mcp.json 没被发现', kv, out)
    assert kv.get('DATAROOT_HAS_BASH') == 'True', out


@pytest.mark.timeout(240)
def test_用户持久化根下的mcp配置也能被发现(work):
    """不依赖 cwd：HARNESS_HOME（用户持久化根）下的 mcp.json 也必须被发现。"""
    home = work / 'home_lh'
    home.mkdir(exist_ok=True)
    _write_mcp_json(home / 'mcp.json')
    empty = work / 'empty_cwd2'
    empty.mkdir(exist_ok=True)
    rc, out, kv = _run_light(_DRIVER_DATAROOT, work, 'home_root',
                             cwd=empty, extra_env={'T0468_DATA_ROOT': '', 'HARNESS_HOME': str(home)})
    if rc != 0 and _missing_module(out):
        pytest.skip('本机缺 lightplugin 兄弟仓：装配层用例请在 192.168.0.88 上跑')
    assert rc == 0, out
    assert int(kv.get('DATAROOT_MCP_COUNT', '0')) >= 1, ('HARNESS_HOME 下 mcp.json 没被发现', kv, out)


@pytest.mark.timeout(180)
def test_配置缺失有明确日志且开关可关(work):
    empty = work / 'empty_cwd'
    empty.mkdir(exist_ok=True)
    rc, out, kv = _run_light(_DRIVER_MISSING, work, 'missing', cwd=empty)
    if rc != 0 and _missing_module(out):
        pytest.skip('本机缺 lightplugin 兄弟仓：装配层用例请在 192.168.0.88 上跑')
    assert rc == 0, out
    # C：不许静默 —— 日志里有明确提示，返回结构也带 未找到
    assert '未找到 MCP 配置' in out, ('配置缺失时没有明确日志', out)
    assert kv.get('NO_CFG_NOT_FOUND') == 'True', kv
    assert kv.get('NO_CFG_REGISTERED') == '0' and kv.get('NO_CFG_SERVERS') == '0', kv
    # D：会话级开关关掉后，MCP 工具不再挂（默认开已被上一条用例证明）
    assert kv.get('OFF_KEEP') == 'False', ('HARNESS_MCP_TOOLS=0 没生效', kv, out)


def test_预设挂载过滤有MCP通配规则(work):
    """反跑锚点（静态）：通配规则与装配接线都在，删掉任一处上面 D 的断言立红。"""
    src = (pathlib.Path(ROOT) / 'src' / '预设挂载过滤.light').read_text(encoding='utf-8')
    assert '段落 通配挂载(' in src and '开头(标识, "mcp__")' in src, '缺 MCP 通配规则'
    body = src.split('段落 按预设过滤(', 1)[1].split('段落 ', 1)[0]
    assert '通配挂载(标识, 预设标识)' in body, ('按预设过滤 没调用通配规则', body[:400])
    entry = (pathlib.Path(ROOT) / 'src' / '总入口.light').read_text(encoding='utf-8')
    leaf = entry.split('段落 工具名到叶子(名字):', 1)[1].split('段落 ', 1)[0]
    assert '开头(名字, "mcp__")' in leaf, ('工具名到叶子 没给 MCP 自持叶子', leaf[:400])
