# -*- coding: utf-8 -*-
"""T-0481 判据：MCP 资源服务器系统提示段（服务器清单 + 已挂 mcp__ 工具）。

验收口径（任务卡）：
  - (["fs","git"], ["bash","mcp__fs__read"]) → 含 `## MCP resource servers`、
    服务器名 `["fs","git"]` 升序、且含 `mcp__fs__read`；
  - 服务器表空 → ""；服务器表非空但资源工具全缺 → ""；
  - 只有 read_mcp_resource 在场 → 仍渲染服务器段（三个资源工具是「或」关系）；
  - 13 个 mcp__ 工具 → 只列 12 个 + 「共 13 个」；
  - 服务器名 60 字 → 40 + `…`；总长 ≤ 800。

反跑锚点（见 .hive/summary.md 记录）：
  ①资源工具全缺分支改成照样渲染 → test_资源工具全缺返回空串 立红；
  ②服务器名不排序 → test_服务器名升序 立红；
  ③删掉 mcp__ 工具行 → test_mcp工具行 立红。

判据全部走 .light 侧真实段落：子进程 `python 运行.py <driver>`，
driver 导入 src/提示_MCP段.light 的 MCP段文本/MCP段 并把结果打印出来。
"""
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')

# driver 只依赖本仓 src/ 下的模块，不需要任何环境开关；固定 UTF-8 输出。
_DRIVER = r'''
从 提示_MCP段 导入 MCP段文本, MCP段
从 内置核心转换 导入 转字符串

段落 压平(文本):
  设 r 为 替换字符串(文本, "\r", "<CR>")
  设 r 为 替换字符串(r, "\n", "<NL>")
  设 r 为 替换字符串(r, "=", "<EQ>")
  返回 r

段落 长度(文本):
  返回 字符串长度(文本)

段落 主():
  设 资源 为 "list_mcp_resources"
  设 读资源 为 "read_mcp_resource"
  设 模板 为 "list_mcp_resource_templates"

  # 基准：服务器升序 + mcp__ 工具行
  打印("P1=" + 压平(MCP段文本(["git", "fs"], ["bash", "mcp__fs__read", 资源])))
  # 空服务器表
  打印("P2=" + 压平(MCP段文本([], [资源])))
  # 非空服务器但资源工具全缺
  打印("P3=" + 压平(MCP段文本(["fs"], ["bash", "写文件"])))
  # 只有 read_mcp_resource 在场
  打印("P4=" + 压平(MCP段文本(["fs"], [读资源])))
  # 只有 list_mcp_resource_templates 在场
  打印("P5=" + 压平(MCP段文本(["fs"], [模板])))
  # 非列表服务器名表
  打印("P6=" + 压平(MCP段文本("not-a-list", [资源])))
  # 别名 MCP段
  打印("P7=" + 压平(MCP段(["a"], [资源])))

  # 13 个 mcp__ 工具 + 1 个 bash → 只列 12 个，总数 13
  设 多工具 为 ["bash"]
  设 i 为 0
  当 i < 13:
    列表追加(多工具, "mcp__s" + 转字符串(i) + "__tool")
    设 i 为 i + 1
  打印("P8=" + 压平(MCP段文本(["fs"], 多工具 + [资源])))

  # 超长服务器名 60 字 → 40 字 + 省略号
  设 长名 为 "abcdefghij" + "abcdefghij" + "abcdefghij" + "abcdefghij" + "abcdefghij" + "abcdefghij"
  打印("P9=" + 压平(MCP段文本([长名], [资源])))

  # 总长 ≤ 800：30 个服务器 + 20 个 mcp__ 工具，全部展开远超 800
  设 多服务器 为 []
  设 k 为 0
  当 k < 30:
    列表追加(多服务器, "server-" + 转字符串(k))
    设 k 为 k + 1
  设 超多工具 为 [资源]
  设 j 为 0
  当 j < 20:
    列表追加(超多工具, "mcp__server" + 转字符串(j) + "__tool_" + "xxxxxxxxxxxxxxxxxxxxxxxx")
    设 j 为 j + 1
  设 超长文本 为 MCP段文本(多服务器, 超多工具)
  打印("P10_LEN=" + 转字符串(长度(超长文本)))

主()
'''


def _run_driver(tmp_path):
    """把 driver 落成 .light 并跑起来，返回 stdout/stderr 全文。"""
    driver = tmp_path / 'driver481.light'
    driver.write_text(_DRIVER, encoding='utf-8')
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    proc = subprocess.run([sys.executable, RUNNER, str(driver)],
                          cwd=ROOT, capture_output=True, text=True,
                          timeout=240, env=env)
    out = (proc.stdout or '') + (proc.stderr or '')
    assert proc.returncode == 0, ('driver 运行失败', proc.returncode, out)
    return out


def _kv(out):
    kv = {}
    for line in out.splitlines():
        if '=' in line and not line.startswith('['):
            k, v = line.split('=', 1)
            kv.setdefault(k.strip(), v.strip())
    return kv


@pytest.fixture(scope='module')
def out(tmp_path_factory):
    return _run_driver(tmp_path_factory.mktemp('t0481'))


def test_基准含资源服务器段与MCP工具(out):
    kv = _kv(out)
    text = kv.get('P1', '')
    assert '## MCP resource servers' in text, ('缺资源服务器段', text)
    assert 'list_mcp_resources' in text, ('缺资源工具文案', text)
    assert 'mcp__fs__read' in text, ('缺已挂 MCP 工具行', text)


def test_服务器名升序(out):
    kv = _kv(out)
    text = kv.get('P1', '')
    # 压平后 `["fs","git"]`（git 在前、fs 在后 → 升序应变成 fs 先）
    assert '["fs","git"]' in text, ('服务器名未升序', text)
    assert text.find('fs') < text.find('git'), ('fs 应在 git 之前', text)


def test_服务器表空返回空串(out):
    kv = _kv(out)
    assert kv.get('P2') == '', ('空服务器表应返回空串', kv.get('P2'))


def test_资源工具全缺返回空串(out):
    kv = _kv(out)
    assert kv.get('P3') == '', ('资源工具全缺应返回空串，不渲染用不了的工具名', kv.get('P3'))


@pytest.mark.parametrize('key', ['P4', 'P5'])
def test_单个资源工具在场仍渲染(out, key):
    kv = _kv(out)
    text = kv.get(key, '')
    assert '## MCP resource servers' in text, ('单个资源工具在场应仍渲染服务器段', key, text)


def test_非列表服务器名表返回空串(out):
    kv = _kv(out)
    assert kv.get('P6') == '', ('非列表服务器名表应返回空串', kv.get('P6'))


def test_别名MCP段等价(out):
    kv = _kv(out)
    assert '## MCP resource servers' in kv.get('P7', ''), ('别名 MCP段 不工作', kv.get('P7'))


def test_mcp工具行只列12个并报总数(out):
    kv = _kv(out)
    text = kv.get('P8', '')
    assert '（共 13 个）' in text, ('未报总数 13', text)
    # 12 个工具名 mcp__s0__tool ... mcp__s12__tool 中只列前 12（升序：s0,s1,s10,s11,s12,s2...）
    # 只需确认「列了 12 个」：数逗号分隔符 = 11 个（工具行内）
    line = next((seg for seg in text.split('<NL>') if '已挂 MCP 工具' in seg), '')
    count = line.count('mcp__')
    assert count == 12, ('mcp__ 工具行应只列 12 个', count, line)
    assert '共 13 个' in line, ('总数应为 13', line)


def test_服务器名超40截断(out):
    kv = _kv(out)
    text = kv.get('P9', '')
    # 40 个 a/b 交替 + 省略号；不能出现完整 60 字
    assert '…' in text, ('超长名未截断加省略号', text)
    assert 'abcdefghijabcdefghijabcdefghijabcdefghijabcdefghijabcdefghij' not in text, '未截断'


def test_总长不超800(out):
    kv = _kv(out)
    n = int(kv.get('P10_LEN', '99999'))
    assert n <= 800, ('总长超过 800', n)
