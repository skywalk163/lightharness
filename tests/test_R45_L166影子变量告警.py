# -*- coding: utf-8 -*-
"""第45轮：L-166「影子变量」编译告警验收。

背景（L-165 实证）
------------------
`mock大模型服务器.light` 的 `新建Mock服务` 给模块级的 `当前实例` 赋值却漏了
`全局` 声明 → 按作用域语义只写了**局部**变量 → 模块级恒为空 → 真实 HTTP 服务
永远 500 MOCK_NOT_READY。全程零报错零警告，症状离现场极远。

本测试守住三件事：
1. 检查器能抓到这个模式（**正向**）；
2. 声明了 `全局` 的同名赋值**不误报**（**反向**）；
3. 告警经 `light run` 真正浮出到 stderr、rc 不变，且可用环境变量关掉（**端到端**）。
"""
import os
import subprocess
import sys

import pytest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(BASE)
LIGHT_MERGE = os.environ.get("LIGHT_MERGE", os.path.join(ROOT, "light-merge"))
sys.path.insert(0, os.path.join(LIGHT_MERGE, "src"))
sys.path.insert(0, LIGHT_MERGE)

# 影子变量原型：模块级 X，函数内未声明 全局 就给 X 赋值
SRC_BAD = '''设 当前值 为 0

段落 坏_写不回:
  设 当前值 为 1
  返回 当前值
'''

# 同一段源码，补上 全局 声明 → 不应再告警
SRC_GOOD = '''设 当前值 为 0

段落 好_写回:
  全局 当前值
  设 当前值 为 1
  返回 当前值
'''


def _warns(src):
    from light_parser_v3 import LightParser
    from scope_shadow_check import check_global_shadow
    return check_global_shadow(LightParser().parse(src), 't')


def test_影子变量_必报警():
    ws = _warns(SRC_BAD)
    assert ws, "L-166：函数内写模块级同名变量且未声明 全局，必须告警"
    assert '当前值' in ws[0] and 'L-166' in ws[0]


def test_声明全局后_不误报():
    assert _warns(SRC_GOOD) == [], "已声明『全局 当前值』的同名赋值不得告警（否则噪音淹没真实问题）"


def test_形参同名_不误报():
    src = '设 值 为 0\n\n段落 处理 接收 值:\n  返回 值\n'
    assert _warns(src) == [], "形参遮蔽模块级变量是正常写法，不得告警"


def _run_example(env_extra=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    p = subprocess.run(
        [sys.executable, os.path.join(BASE, '运行.py'),
         os.path.join(BASE, 'examples', 'test_R45_影子变量告警.light')],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        timeout=300, cwd=BASE, env=env,
    )
    return p


def test_端到端_告警浮出且rc不变():
    p = _run_example()
    assert p.returncode == 0, f"用例应绿，实际 rc={p.returncode}\n{p.stderr[-800:]}"
    assert 'L-166' in p.stderr, f"告警必须浮出到 stderr（否则等于没做）\n--- stderr ---\n{p.stderr}"
    # stdout 是程序输出，绝不能被告警污染
    assert 'PASS' in p.stdout and 'L-166' not in p.stdout


def test_端到端_环境变量可关闭():
    p = _run_example({'LIGHT_WARN_GLOBAL_SHADOW': '0'})
    assert p.returncode == 0
    assert 'L-166' not in p.stderr, "LIGHT_WARN_GLOBAL_SHADOW=0 时必须静默"
