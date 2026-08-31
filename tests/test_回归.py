# -*- coding: utf-8 -*-
"""lightharness 回归门禁：全量 examples 用例 + 缺陷复现套件退出码断言。

用法：
    python -m pytest tests/ -q                # 全量
    python -m pytest tests/ -q -k 会话         # 按关键词过滤

判据约定（与 docs/功能对标/反跑判据.md 一致）：
    - 除「预期红」清单外，所有 examples/*.light 必须 rc==0；
    - 预期红用例（未修复缺陷判据）显式列出，断言 rc!=0；
    - 载体模块（_helper_*）跳过（被其他用例导入，非独立运行）；
    - 平台可移植性欠账（PLATFORM_ENV_DEBT）仅在其不适用的平台上登记为预期红，
      见下方注释——它不是缺陷，是环境能力差异，且登记是自清理的。
"""
import glob
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
EXAMPLES = os.path.join(ROOT, 'examples')


# 载体模块：被其它用例 import，不独立运行
SKIP = {'_helper_L004.light', '_helper_L007b.light'}

# 预期红（未修复缺陷判据 / 工程层演示）。key=文件名, value=说明
# 注：test_L026.light / test_L032.light 是「修复后绿」确认套件（验证语言缺陷
# L-026/L-032 已修好：排序列表 现为返回新列表的内置、父 可作局部变量），它们
# 设计为 rc==0，故不在 EXPECT_RED 之列。历史上曾误把它们登记为预期红导致门禁
# 假红，已于 2026-08-31 修正（详见 docs/功能对标/语言缺陷账.md L-026/L-032）。
EXPECT_RED = {}

# ── 平台可移植性欠账 ────────────────────────────────────────────────────
# 以下用例依赖 OS 级能力，在 Windows 开发机全绿，但在 FreeBSD CI runner 上红。
# 曾登记 3 条（2026-08-29 CI run 307 实测），已全部修好并清空：
#   test_子进程码.light  exit(3) 被读成 2
#       根因：运行进程走 shell=True，命令串 "python -c exit(3)" 未加引号，
#             POSIX sh 把 ( ) 当元字符 → Syntax error → sh 返回 2，而非 python 的 3。
#             cmd.exe 不把 ( 当元字符，故 Windows 不受影响。
#       修复：给 -c 的参数加引号 → "python -c \"exit(3)\""，两种 shell 都正确。
#   test_沙箱.light      「读根外路径拒绝」护栏未生效
#       根因：用例写死 "C:\\Windows" 当「根外路径」。POSIX 下反斜杠不是分隔符，
#             它只是根下的普通文件名 → 归一化后仍在根内 → 检查读返回真。
#       修复：改用 <根>/..（父目录），归一化后必然在根外，两平台语义一致。
#   test_终端PTY.light   PTY 读到「退出」而非数据
#       根因：用例写死 cmd.exe（FreeBSD 上根本 spawn 不起来），且用 cmd 专有的
#             set /a 1+2，行尾还是 Windows 的 CRLF（sh 会把它读成 "exit\r"）。
#       修复：按平台挑外壳/行尾/算式命令。⚠️ 判定必须用「是否Windows 的否定」——
#             FreeBSD 上 是否Linux() 返回 假（实测），用它会把 FreeBSD 误判成 Windows。
# 三条现均在 Windows 与 FreeBSD 上 rc=0 全绿，故清空本表。
#
# 保留机制本身：日后若再出现平台能力差异，直接往这里登记即可。
# 它仍是「自清理」的——平台上修好后 rc 变 0，「断言 rc != 0」即失败，逼你删登记。
PLATFORM_ENV_DEBT = {}

if not sys.platform.startswith('win'):
    EXPECT_RED.update(PLATFORM_ENV_DEBT)
    # 历史：test_终端PTY.light 曾因 FreeBSD PTY 计时脆弱在 runner 上偶发红，
    # 登记为预期红作临时挡板。2026-08-30 已将测试改为「轮询+累积读取」消除
    # 计时脆弱（见 examples/test_终端PTY.light 的 读至包含 助手），FreeBSD 上
    # 稳定绿，故删除本登记，门禁全量硬判绿（EXPECT_RED 归零，符合
    # 「EXPECT_RED 应保持为空」的验收口径）。详见 docs/问题档案.md。

# 其余全部预期绿；如个别用例基线红且不属于本门禁范围，需在此显式登记
EXPECT_GREEN_EXCEPT = set(EXPECT_RED)


def _collect():
    cases = []
    for f in sorted(glob.glob(os.path.join(EXAMPLES, '*.light'))):
        name = os.path.basename(f)
        if name in SKIP:
            continue
        cases.append((name, f))
    return cases


CASES = _collect()


def _run(f):
    """在「独立的系统临时目录」里运行单个用例。

    背景（2026-08-31 实测）：若干用例把工作根目录取成 当前目录() 或相对路径，
    例如 tmp_文件测试 / .test_persist_incr / .test_cli_v2 / _taskT10_02_resume。
    默认 cwd 是仓库目录（G: 盘），于是这些目录落在工作区内；而沙箱对「工作区内
    的删除」做 safe-delete 拦截（要求先进回收站），G: 盘没有 $Recycle.Bin，于是
    safe-delete fail-closed 抛错 → 用例 rc!=0，门禁假红 5 条：
        [safe-delete][SAFE_DELETE_FAIL_CLOSED] ... "reason":
        "windows-sandbox-recycle-bin-unavailable"
    把 cwd 换成系统临时目录（C: 盘，有回收站）即可消除假红；副作用全是正面的：
    用例之间互不干扰，且不再往仓库里掉 tmp_文件测试 等残留目录。
    """
    workdir = tempfile.mkdtemp(prefix='lightharness_case_')
    try:
        # 少数用例以「相对路径」引用仓库内的脚本（如 examples/mcp_服务器.py），
        # 因此在隔离 cwd 里补一个 examples/ 目录，把这些 .py 助手脚本拷过去，
        # 保证相对引用照旧可用（这些脚本仅依赖标准库，拷贝即可独立运行）。
        _ex = os.path.join(workdir, 'examples')
        os.makedirs(_ex, exist_ok=True)
        for _py in glob.glob(os.path.join(EXAMPLES, '*.py')):
            shutil.copy2(_py, _ex)
        p = subprocess.run(
            ['python', RUNNER, f],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=300, cwd=workdir,
        )
        return p.returncode, (p.stdout or '') + (p.stderr or '')
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@pytest.mark.parametrize('name,fpath', CASES, ids=[c[0] for c in CASES])
def test_example_exit_code(name, fpath):
    rc, out = _run(fpath)
    if name in EXPECT_RED:
        assert rc != 0, f'{name} 应为红（{EXPECT_RED[name]}），实际 rc=0'
    else:
        assert rc == 0, f'{name} 应绿，实际 rc={rc}\n--- 输出尾 ---\n{out[-800:]}'


def test_expected_red_registered():
    """预期红清单必须都有对应文件，防止登记了不存在的用例。"""
    for name in EXPECT_RED:
        assert os.path.isfile(os.path.join(EXAMPLES, name)), f'预期红登记无文件: {name}'


def test_green_exception_consistent():
    """EXPECT_RED 与 EXPECT_GREEN_EXCEPT 保持一致。"""
    assert set(EXPECT_RED) == EXPECT_GREEN_EXCEPT
