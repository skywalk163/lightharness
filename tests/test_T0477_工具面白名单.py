# -*- coding: utf-8 -*-
"""T-0477：工具面白名单收口（standard 168 → 20–30，MCP 不再硬塞叶子）。

判据全部走 .light 侧真实段落（子进程 `python 运行.py <driver>`）：
  A. 白名单规模：standard 20–30，18 个必须集逐个在册；基础白名单也 20–30。
  B. 方法维只删不增：ptc/topdown 与 standard 无差集；bottomup/lazy 少掉的工具
     全部落在 工作方法删减() 里，且预设侧没有 standard 之外的新增。
  C. 收紧预设：minimal 恰为 bash；brainstorm ≤ 27 且不含 bash/写文件/编辑文件/目标/todo_write。
  D. 装配日志：保留数与注册表一致、未映射(应=0)=0、白名单外注销 > 0、168 不再出现。
  E. MCP：工具名到叶子("mcp__*") == []；开关开时 MCP 工具在册、HARNESS_MCP_TOOLS=0 时注销。
  F. schema 体积：standard 描述表 JSON ≤ 15,000 字符（收口前 46,870）。
  G. 未知预设：白名单() 抛错（不静默返回空表）。

反跑锚点（写进交付说明，不放进断言）：
  ① 删掉必须集里的 todo_write → A 红；
  ② 把 未映射默认保留 兜底加回 预设保留工具 → D 的「未映射(应=0)」红；
  ③ 把 mcp__ 叶子改回自身名 → E 的无叶子判据红。
"""
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 240

# T-0540：T0477 的 xdist worker 崩溃根因是**超时预算**，不是断言。
# 本文件判据全部走真实 `.light` 子进程（`运行.py`），每次调用都要冷编译整仓
# 工具面（单跑 21–37s；`test_mcp工具无叶子且受开关控制` 连起两个子进程）。
# pytest.ini 的全局 `--timeout=60` 在 xdist 并跑（尤其全量负载、多 worker 同时
# 编译）时会被吃穿，pytest-timeout 直接把 worker kill，报「worker crashed」而非
# 断言红（T-0499/T-0521/T-0522 同源记录）。照 tests/test_T0456_收口接线.py /
# test_T0403_新模式预设.py 的既有先例放宽到 300s：判据一字不改，只给足真实编译
# 预算，xdist 并行下不再被误杀。
pytestmark = pytest.mark.timeout(300)

REQUIRED = [
    'bash', '读文件', '写文件', '编辑文件', '搜索文件',
    'job_start', 'job_output', 'job_kill',
    'skill', 'web_search', 'web_fetch', 'present', 'todo_write', '目标',
    '派发子任务', '收集子任务结果', '提问提交', '回答提交',
]

DRIVER = r'''
从 总入口 导入 组装注册表, 工具名到叶子
从 工具面装配 导入 基础白名单, 只读白名单, 最小白名单, 工作方法删减
从 JSON 导入 序列化JSON

段落 逗号连接(表):
  设 结果串 为 ""
  设 序号 为 0
  遍历 项 之 表:
    如果 序号 > 0:
      设 结果串 为 结果串 + ","
    设 结果串 为 结果串 + 转字符串(项)
    设 序号 为 序号 + 1
  返回 结果串

段落 差集(甲, 乙):
  设 结果 为 []
  遍历 项 之 甲:
    如果 乙.包含(项) == 假:
      结果.追加(项)
  返回 结果

段落 主程():
  设 表一 为 组装注册表("standard")
  设 标名 为 表一.名单()
  打印("STD_COUNT=" + 转字符串(长度(标名)))
  打印("STD_NAMES=" + 逗号连接(标名))
  打印("BASE_COUNT=" + 转字符串(长度(基础白名单())))
  打印("BASE_NAMES=" + 逗号连接(基础白名单()))
  打印("BRAIN_COUNT=" + 转字符串(长度(只读白名单())))
  打印("BRAIN_NAMES=" + 逗号连接(只读白名单()))
  打印("MIN_COUNT=" + 转字符串(长度(最小白名单())))
  打印("MIN_NAMES=" + 逗号连接(最小白名单()))
  打印("DEL_BOTTOMUP=" + 逗号连接(工作方法删减("bottomup")))
  打印("DEL_LAZY=" + 逗号连接(工作方法删减("lazy")))
  打印("DEL_TOPDOWN=" + 逗号连接(工作方法删减("topdown")))
  设 表二 为 组装注册表("ptc")
  设 表三 为 组装注册表("topdown")
  设 表四 为 组装注册表("bottomup")
  设 表五 为 组装注册表("lazy")
  设 表六 为 组装注册表("brainstorm")
  设 表七 为 组装注册表("minimal")
  打印("PTC_COUNT=" + 转字符串(长度(表二.名单())))
  打印("PTC_DIFF=" + 逗号连接(差集(表二.名单(), 标名)))
  打印("PTC_ADD=" + 逗号连接(差集(标名, 表二.名单())))
  打印("TOP_COUNT=" + 转字符串(长度(表三.名单())))
  打印("TOP_DIFF=" + 逗号连接(差集(表三.名单(), 标名)))
  打印("TOP_ADD=" + 逗号连接(差集(标名, 表三.名单())))
  打印("BOT_COUNT=" + 转字符串(长度(表四.名单())))
  打印("BOT_DIFF=" + 逗号连接(差集(表四.名单(), 标名)))
  打印("BOT_ADD=" + 逗号连接(差集(标名, 表四.名单())))
  打印("LAZY_COUNT=" + 转字符串(长度(表五.名单())))
  打印("LAZY_DIFF=" + 逗号连接(差集(表五.名单(), 标名)))
  打印("LAZY_ADD=" + 逗号连接(差集(标名, 表五.名单())))
  打印("BRAIN_COUNT2=" + 转字符串(长度(表六.名单())))
  打印("BRAIN_NAMES2=" + 逗号连接(表六.名单()))
  打印("MIN_COUNT2=" + 转字符串(长度(表七.名单())))
  打印("MIN_NAMES2=" + 逗号连接(表七.名单()))
  设 描述集 为 表一.描述表()
  设 序列 为 序列化JSON(描述集)
  打印("SCHEMA_LEN=" + 转字符串(长度(序列)))
  打印("MAP_MCP=" + 转字符串(长度(工具名到叶子("mcp__echo"))))
  打印("MAP_TODO=" + 逗号连接(工具名到叶子("todo_write")))
主程()
'''

MCP_DRIVER = r'''
从 总入口 导入 组装注册表, 预设保留工具, 工具名到叶子
从 工具 导入 造工具定义

段落 假执行(参数):
  返回 ["ok": 真]

段落 主程():
  设 表 为 组装注册表()
  设 定义 为 造工具定义("mcp__demo__echo", "假 MCP 工具（echo）", ["type": "object", "properties": {}], 假执行)
  表.内部表.注册(定义)
  设 定义二 为 造工具定义("mcp__demo__add", "假 MCP 工具（add）", ["type": "object", "properties": {}], 假执行)
  表.内部表.注册(定义二)
  预设保留工具(表.内部表, "standard")
  设 后 为 表.内部表.名单()
  打印("MCP_后=" + 转字符串(长度(后)))
  打印("MCP_ECHO=" + 转字符串(后.包含("mcp__demo__echo")))
  打印("MCP_ADD=" + 转字符串(后.包含("mcp__demo__add")))
  打印("MCP_无叶子=" + 转字符串(长度(工具名到叶子("mcp__demo__echo"))))
主程()
'''

UNKNOWN_DRIVER = r'''
从 工具面装配 导入 白名单

段落 主程():
  设 表 为 白名单("不存在的预设")
  打印("SHOULD_NOT=" + 转字符串(长度(表)))
主程()
'''


def _env(extra=None):
    env = {k: v for k, v in os.environ.items()
           if k not in ('HARNESS_ROOT', 'HARNESS_CWD', 'HARNESS_PERMISSION_MODE',
                        'HARNESS_WEB_TOKEN', 'HARNESS_ENDPOINT', 'HARNESS_API_KEY',
                        'HARNESS_MODEL', 'HARNESS_MODEL_CONTEXT_WINDOW', 'HARNESS_HOME',
                        'DSH_HOME', 'AGENTS_HOME', 'HARNESS_PRESET', 'HARNESS_MCP_CONFIG',
                        'HARNESS_MCP_TOOLS')}
    env['PYTHONIOENCODING'] = 'utf-8'
    if extra:
        env.update(extra)
    return env


def _run(source, tmp_path, name, extra=None):
    path = tmp_path / (name + '.light')
    path.write_text(source, encoding='utf-8')
    proc = subprocess.run([sys.executable, RUNNER, str(path)],
                          cwd=ROOT, capture_output=True, text=True,
                          encoding='utf-8', errors='replace',
                          timeout=TIMEOUT_SEC, env=_env(extra))
    kv = {}
    for line in (proc.stdout or '').splitlines():
        if '=' in line and not line.startswith('['):
            k, v = line.split('=', 1)
            kv.setdefault(k.strip(), v.strip())
    return proc.returncode, (proc.stdout or '') + (proc.stderr or ''), kv


def _missing_module(out):
    return ('lightplugin' in out) and (
        'ModuleNotFound' in out or '导入失败' in out or 'No module' in out)


def _names(kv, key):
    return [x for x in kv.get(key, '').split(',') if x]


@pytest.fixture(scope='module')
def 探针(tmp_path_factory):
    tmp = tmp_path_factory.mktemp('t0477')
    rc, out, kv = _run(DRIVER, tmp, 'whitelist_probe')
    assert rc == 0, 'T-0477 白名单探针应 rc=0，实际 %s\n--- 输出 ---\n%s' % (rc, out[-4000:])
    return kv, out


# ---------------------------------------------------------------------------
# A. 规模与必须集
# ---------------------------------------------------------------------------

def test_standard工具面20到30且必须集逐个在册(探针):
    kv, out = 探针
    std = _names(kv, 'STD_NAMES')
    assert 20 <= int(kv['STD_COUNT']) <= 30, ('standard 工具面应 20–30', kv['STD_COUNT'], std)
    assert len(std) == int(kv['STD_COUNT'])
    missing = [x for x in REQUIRED if x not in std]
    assert not missing, ('standard 缺必须集工具', missing, out[-2000:])
    assert 20 <= int(kv['BASE_COUNT']) <= 30, ('基础白名单应 20–30', kv['BASE_COUNT'])


# ---------------------------------------------------------------------------
# B. 方法维只删不增
# ---------------------------------------------------------------------------

def test_ptc与topdown对standard无差集(探针):
    kv, out = 探针
    assert kv['PTC_DIFF'] == '' and kv['PTC_ADD'] == '', ('ptc 与 standard 应同口径', kv, out[-2000:])
    assert kv['TOP_DIFF'] == '' and kv['TOP_ADD'] == '', ('topdown 与 standard 应同口径', kv, out[-2000:])


def test_bottomup与lazy只删白名单内工具(探针):
    kv, out = 探针
    del_bot = set(_names(kv, 'DEL_BOTTOMUP'))
    del_lazy = set(_names(kv, 'DEL_LAZY'))
    assert set(_names(kv, 'BOT_DIFF')) == set(), ('bottomup 出现了 standard 之外的新增', kv['BOT_DIFF'])
    assert set(_names(kv, 'LAZY_DIFF')) == set(), ('lazy 出现了 standard 之外的新增', kv['LAZY_DIFF'])
    removed_bot = set(_names(kv, 'BOT_ADD'))
    removed_lazy = set(_names(kv, 'LAZY_ADD'))
    assert removed_bot and removed_bot <= del_bot, ('bottomup 的删减越界', removed_bot, del_bot)
    assert removed_lazy and removed_lazy <= del_lazy, ('lazy 的删减越界', removed_lazy, del_lazy)
    # bottomup 必须真删掉 goal 与 ask-user 族（沿用 预设组合.方法删减 的权威表）
    assert '目标' in removed_bot and {'提问提交', '回答提交'} <= removed_bot, removed_bot


# ---------------------------------------------------------------------------
# C. 收紧预设
# ---------------------------------------------------------------------------

def test_minimal恰为bash(探针):
    kv, out = 探针
    assert _names(kv, 'MIN_NAMES2') == ['bash'], ('minimal 必须恰为 bash', kv['MIN_NAMES2'])
    assert int(kv['MIN_COUNT']) == 1, kv


def test_brainstorm只读且不超27(探针):
    kv, out = 探针
    brain = _names(kv, 'BRAIN_NAMES2')
    assert 0 < len(brain) <= 27, ('brainstorm 白名单应 ≤ 27', brain)
    for bad in ('bash', '写文件', '编辑文件', '目标', 'todo_write'):
        assert bad not in brain, ('brainstorm 不该有执行/写类工具 ' + bad, brain, out[-2000:])
    assert '读文件' in brain and '搜索文件' in brain, ('brainstorm 必须有读/搜', brain)


# ---------------------------------------------------------------------------
# D. 装配日志
# ---------------------------------------------------------------------------

def test_装配日志未映射为零且不再出现168(探针):
    kv, out = 探针
    lines = [ln for ln in out.splitlines() if ln.startswith('[装配] 预设=standard ')]
    assert lines, '没有打出 standard 装配日志'
    line = lines[0]
    kept = int(re.search(r'保留=(\d+)', line).group(1))
    dropped = int(re.search(r'白名单外注销=(\d+)', line).group(1))
    unmapped = int(re.search(r'未映射\(应=0\)=(\d+)', line).group(1))
    assert kept == int(kv['STD_COUNT']), ('日志保留数与注册表不一致', line, kv['STD_COUNT'])
    assert unmapped == 0, ('白名单收口后不该还有未映射工具', line)
    assert dropped > 0, ('白名单外注销必须真的发生', line)
    assert kept != 168, ('168 个工具的老口径又回来了', line)


# ---------------------------------------------------------------------------
# E. MCP：不再硬塞叶子 + 开关
# ---------------------------------------------------------------------------

def test_mcp工具无叶子且受开关控制(tmp_path):
    rc, out, kv = _run(MCP_DRIVER, tmp_path, 'mcp_on')
    if rc != 0 and _missing_module(out):
        pytest.skip('本机缺 lightplugin 兄弟仓：装配层用例请在 192.168.0.88 上跑')
    assert rc == 0, out
    assert int(kv['MCP_无叶子']) == 0, ('mcp__* 不该再返回自身名当叶子', out)
    assert kv['MCP_ECHO'] in ('True', '真'), ('开关开时 MCP 工具必须保留', out)
    assert kv['MCP_ADD'] in ('True', '真'), ('开关开时 MCP 工具必须保留', out)

    rc2, out2, kv2 = _run(MCP_DRIVER, tmp_path, 'mcp_off', {'HARNESS_MCP_TOOLS': '0'})
    assert rc2 == 0, out2
    assert kv2['MCP_ECHO'] in ('False', '假'), ('HARNESS_MCP_TOOLS=0 时 MCP 工具必须注销', out2)
    assert kv2['MCP_ADD'] in ('False', '假'), ('HARNESS_MCP_TOOLS=0 时 MCP 工具必须注销', out2)
    assert int(kv['MCP_后']) - int(kv2['MCP_后']) == 2, (kv['MCP_后'], kv2['MCP_后'])


# ---------------------------------------------------------------------------
# F. schema 体积
# ---------------------------------------------------------------------------

def test_白名单schema不超过15000字符(探针):
    kv, out = 探针
    assert int(kv['SCHEMA_LEN']) <= 15000, ('工具面 schema 仍过大', kv['SCHEMA_LEN'])


# ---------------------------------------------------------------------------
# G. 未知预设抛错
# ---------------------------------------------------------------------------

def test_未知预设白名单抛错(tmp_path):
    rc, out, kv = _run(UNKNOWN_DRIVER, tmp_path, 'unknown')
    assert rc != 0, ('未知预设不应静默返回空表', out)
    assert '未知 agent preset' in out, ('未知预设的错误文案丢了', out[-2000:])
