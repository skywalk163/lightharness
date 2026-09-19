# -*- coding: utf-8 -*-
"""L-177 复核锁定测试：括号式参数注解「递归死循环」判据不成立。

背景
----
R73 任务B 交付记录「已知限制①」声称：

    段落 名(a: 整数, b: 整数) 括号式参数注解在解析期触发递归死循环
    （独立 parser bug，本轮测试规避、另记）

R71-R73 收口总报告 §五 据此把它登记为「三轮遗留里唯一会崩溃的项」。

复核结论（2026-09-19，见 语言缺陷账.md L-177）
----------------------------------------------
**判据不成立**：任务书原文形式实测可用（rc=0），`_parse_type_annotation` /
`_parse_type_union` / `_parse_type_atom` 的函数体在 R70 基线（5c12fb8a）与 HEAD
之间逐字节相同，三轮开发未触碰该路径。

本测试的作用是**把「括号式注解正常可用」这件事钉死在门禁里**：
1. 正向：各形态括号式注解必须 rc==0（带硬超时，任何挂死立即失败）；
2. 反向：`递归错误` 只应出现在「真自递归」用例上，且必须带诊断而非挂死。

若未来有人重新引入解析期递归，`test_括号式注解不挂死` 会因超时而失败。
"""
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')

# 硬超时：远小于回归门禁的 300s——挂死/死循环必须被立即抓住
TIMEOUT_SEC = 25


def _run(src: str, tmp_path) -> tuple:
    """在独立子进程里编译运行一段光明源码，返回 (rc, 合并输出)。"""
    f = tmp_path / 'case.light'
    f.write_text(src, encoding='utf-8')
    try:
        p = subprocess.run(
            [sys.executable, RUNNER, str(f)],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=TIMEOUT_SEC, cwd=str(tmp_path),
        )
    except subprocess.TimeoutExpired:
        pytest.fail(
            f'括号式注解用例超过 {TIMEOUT_SEC}s 未返回——疑似挂死/死循环（L-177 复核判据被破坏）\n'
            f'--- 源码 ---\n{src}'
        )
    return p.returncode, (p.stdout or '') + (p.stderr or '')


# 括号式参数注解的各形态：全部必须 rc==0
POSITIVE_CASES = {
    '双参+返回注解': '段落 加法(a: 整数, b: 整数) -> 整数:\n    返回 a 加 b\n\n打印(加法(1, 2))\n',
    '单参': '段落 加一(a: 整数) -> 整数:\n    返回 a 加 1\n\n打印(加一(1))\n',
    '三参无返回注解': '段落 f(a: 整数, b: 整数, c: 整数):\n    返回 a 加 b 加 c\n\n打印(f(1, 2, 3))\n',
    '泛型注解': '段落 f(a: 列表<整数>) -> 整数:\n    返回 a[0]\n\n打印(f([7]))\n',
    '字典泛型注解': '段落 f(a: 字典<字符串, 整数>):\n    返回 1\n\n打印(f({}))\n',
    '嵌套泛型注解': '段落 f(a: 列表<字典<字符串, 整数>>):\n    返回 1\n\n打印(f([]))\n',
    '联合注解': '段落 f(a: 整数|字符串):\n    返回 1\n\n打印(f(1))\n',
    '可空注解': '段落 f(a: 可空 字符串) -> 整数:\n    若 a == 空:\n        返回 0\n    返回 1\n\n打印(f(空))\n',
    '多行括号注解': '段落 f(\n    a: 整数,\n    b: 整数\n) -> 整数:\n    返回 a 乘 b\n\n打印(f(3, 4))\n',
    '混合注解与无注解': '段落 f(a: 整数, b, c: 字符串):\n    返回 a\n\n打印(f(1, 2, "x"))\n',
    '方法括号注解': '类 C:\n    段落 方法(己, a: 整数) -> 整数:\n        返回 a 加 100\n\n打印(C().方法(1))\n',
    '与接收式共存': '段落 f 接收 a: 整数 -> 整数:\n    返回 a 减 1\n\n段落 g(a: 整数) -> 整数:\n    返回 f(a)\n\n打印(g(10))\n',
}


@pytest.mark.parametrize('name', list(POSITIVE_CASES), ids=list(POSITIVE_CASES))
def test_括号式注解正常可用(name, tmp_path):
    """L-177 正向：括号式参数注解各形态必须编译运行成功（rc==0）。"""
    rc, out = _run(POSITIVE_CASES[name], tmp_path)
    assert rc == 0, f'{name} 应 rc=0，实际 rc={rc}\n--- 输出尾 ---\n{out[-800:]}'


def test_任务书原文形式不挂死(tmp_path):
    """L-177 核心：任务书原文声称崩溃的那一行，必须 rc==0。"""
    src = '段落 名(a: 整数, b: 整数) -> 整数:\n    返回 a 加 b\n\n打印(名(1, 2))\n'
    rc, out = _run(src, tmp_path)
    assert rc == 0, f'任务书原文形式应 rc=0，实际 rc={rc}\n--- 输出尾 ---\n{out[-800:]}'


def test_真自递归报诊断而非挂死(tmp_path):
    """L-177 反向：无终止条件的自递归应报「递归错误」rc!=0，且带诊断、不挂死。

    R73-B 记录的「② 长度(<裸参数>) 解析期递归」实为这一形态的**运行期真自递归**，
    正确行为就是抛 RecursionError（Python 同口径），而非解析期死循环。
    """
    src = '段落 长度 接收 可能:\n    返回 长度(可能)\n\n打印(长度("hi"))\n'
    rc, out = _run(src, tmp_path)
    assert rc != 0, '无终止条件的自递归应 rc!=0'
    assert '递归' in out, f'应报递归相关诊断，实际输出：\n{out[-800:]}'


def test_合法深递归正常(tmp_path):
    """L-177 边界：有终止条件的深递归（900 层）应正常返回，证明递归本身可用。"""
    src = ('段落 求和到(n):\n    若 n <= 0: 返回 0\n'
           '    返回 n 加 求和到(n 减 1)\n\n打印(求和到(900))\n')
    rc, out = _run(src, tmp_path)
    assert rc == 0, f'合法深递归应 rc=0，实际 rc={rc}\n--- 输出尾 ---\n{out[-800:]}'
    assert '405450' in out, f'求和到(900) 应为 405450，实际输出：\n{out[-400:]}'
