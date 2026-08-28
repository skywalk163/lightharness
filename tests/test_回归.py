# -*- coding: utf-8 -*-
"""lightharness 回归门禁：全量 examples 用例 + 缺陷复现套件退出码断言。

用法：
    python -m pytest tests/ -q                # 全量
    python -m pytest tests/ -q -k 会话         # 按关键词过滤

判据约定（与 docs/功能对标/反跑判据.md 一致）：
    - 除「预期红」清单外，所有 examples/*.light 必须 rc==0；
    - 预期红用例（未修复缺陷判据）显式列出，断言 rc!=0；
    - 载体模块（_helper_*）跳过（被其他用例导入，非独立运行）。
"""
import glob
import os
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
EXAMPLES = os.path.join(ROOT, 'examples')

# 载体模块：被其它用例 import，不独立运行
SKIP = {'_helper_L004.light', '_helper_L007b.light'}

# 预期红（未修复缺陷判据 / 工程层演示）。key=文件名, value=说明
EXPECT_RED = {}

# 其余全部预期绿；如个别用例基线红且不属于本门禁范围，需在此显式登记
EXPECT_GREEN_EXCEPT = set()


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
    p = subprocess.run(
        ['python', RUNNER, f],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        timeout=300,
    )
    return p.returncode, (p.stdout or '') + (p.stderr or '')


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
