# -*- coding: utf-8 -*-
"""R57 任务3：R22/R26/R27 词法缺陷复现用例挂 tests/（G7 覆盖缺口收口）。

背景（R56 任务2 归因 + R57 任务1a 修复）：
  R56 实测 4 例 example 红（test_R22_嵌入关键字冗余验证 / test_R26_词首并入反向 /
  test_R26_词首并入混合 / test_R27_词首并入反向），根因为 light-merge 词法器
  `src/lexer.py` 两处缺陷（R57 任务1a 修复，diff ±21 行）：
    1. 无空格回退路径把段名内嵌的 `返回` 当分隔符 → 段名被腰斩
       （`段落 测试返回语句:` → 段名注册成 `测试`）；
    2. 名字首字符处的 `为` 被当赋值分隔符 → `设 为了 为 "为了值"` 报
       「期望'为'或'等于'，但得到「了」」。
  R54 的教训（G7）：缺陷复现用例只放 `examples/` 不会进全量 pytest 门
  （light-merge 的 examples/*.light 不被收集），必须同时挂 `tests/`。

本文件两层钉桩（铁律：修一遍、钉一层）：
  · token 层——直接断言 Lexer 切词结果，秒级、环境无关、定位精准；
  · 运行层——按 `tests/test_回归.py` 既有机制真跑 4 个 example 文件断 rc==0，
    与 examples 内的运行期自校验互为印证。

铁律对表（不许被本文件无意破坏，红即报警）：
  · R26 的坑：21 个单字语句关键字（含 `返回`/`设`）词首必须切分；
  · L-155 语义：`_EMBED_MAX_MATCH_KEYWORDS={为,返回,尝试}` 嵌入块吞并整行保持。

前置：LIGHT_MERGE 环境变量可覆盖编译器源码根（0.82 上由运行器注入）。
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

LIGHT_MERGE_PATH = os.environ.get(
    'LIGHT_MERGE', r'G:\dswork\duan-light-merge\light-merge')
ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / '运行.py'
EXAMPLES = ROOT / 'examples'

sys.path.insert(0, os.path.join(LIGHT_MERGE_PATH, 'src'))
from lexer import Lexer  # noqa: E402


def stream(text):
    """返回去除 EOF/NEWLINE 的可见 token 流 [(type_name, value)]。"""
    toks = Lexer(text, deterministic=True).tokenize()
    return [(t.type.name, t.value) for t in toks
            if t.type.name not in ('EOF', 'NEWLINE')]


# ──────────────────────────────────────────────────────────────
# token 层：R57 任务1a 的两个修复点 × 4 个场景
# ──────────────────────────────────────────────────────────────

def test_r22_为了_嵌入关键字整词成标识符():
    """修复点2：名字首字符的 `为` 不再被当赋值分隔符。

    修复前：`设 为了 为 "为了值"` → `为`(KEYWORD)+`了`(IDENTIFIER)，
    解析报「期望'为'或'等于'，但得到「了」」。
    """
    got = stream('设 为了 为 "为了值"')
    assert got == [
        ('KEYWORD', '设'),
        ('IDENTIFIER', '为了'),
        ('KEYWORD', '为'),
        ('STRING', '为了值'),
    ], f'`为了` 未整词成 IDENTIFIER：{got}'


def test_r26_段名_测试返回语句_不被返回腰斩():
    """修复点1：段名内嵌 `返回` 不再被当无空格回退路径的分隔符。"""
    got = stream('段落 测试返回语句:\n  返回 斐波那契(5)')
    head = got[:3]
    assert head == [
        ('KEYWORD', '段落'),
        ('IDENTIFIER', '测试返回语句'),
        ('COLON', ':'),
    ], f'段名被切开：{got}'
    # 段名不应以「测试 + 独立的 语句」形态出现
    assert ('IDENTIFIER', '语句') not in got, f'`语句` 被切出：{got}'


def test_r26_段名_测试真的与返回_整词成标识符():
    got = stream('段落 测试真的与返回:\n  返回 真')
    head = got[:3]
    assert head == [
        ('KEYWORD', '段落'),
        ('IDENTIFIER', '测试真的与返回'),
        ('COLON', ':'),
    ], f'段名被切开：{got}'
    assert ('IDENTIFIER', '的') not in got and ('KEYWORD', '的') not in got[:3], (
        f'段名含独立 `的`：{got}')


def test_r27_段名_测试_返回真_真不被切出成裸名():
    """修复前：段名 `测试_返回真` 被切成 `测试_`+`返回`+`真`，
    `真` 沦为未定义变量名（name '真' is not defined）。"""
    got = stream('段落 测试_返回真:\n  返回 真')
    head = got[:3]
    assert head == [
        ('KEYWORD', '段落'),
        ('IDENTIFIER', '测试_返回真'),
        ('COLON', ':'),
    ], f'段名被切开：{got}'
    assert ('IDENTIFIER', '真') not in got, f'`真` 被切成裸标识符：{got}'
    assert ('KEYWORD', '真') in got, f'行尾 `返回 真` 的 真 应为值字面量：{got}'


# ──────────────────────────────────────────────────────────────
# 铁律守卫：修复不许破坏的既有语义（R26 坑 / L-155）
# ──────────────────────────────────────────────────────────────

def test_guard_硬语句关键字词首仍切分():
    """R26 的坑：`返回`/`设`/`如果` 词首必须切分（后随空白时）。"""
    got = stream('返回 真')
    assert got[0] == ('KEYWORD', '返回'), f'词首 `返回` 被并入：{got}'
    got2 = stream('如果 真:')
    assert got2[0] == ('KEYWORD', '如果'), f'词首 `如果` 被并入：{got2}'


def test_guard_L155_嵌入块吞并语义保持():
    """L-155：`_EMBED_MAX_MATCH_KEYWORDS={为,返回,尝试}`——
    `返回表`/`行为` 等嵌入复合词仍整词成 IDENTIFIER（R22 要保护的特性）。"""
    for word in ('返回表', '行为', '尝试记录'):
        got = stream('设 %s 为 1' % word)
        assert ('IDENTIFIER', word) in got, f'`{word}` 未整词成 IDENTIFIER：{got}'


def test_guard_普通赋值不受修复影响():
    got = stream('设 甲 为 1')
    assert got == [('KEYWORD', '设'), ('IDENTIFIER', '甲'),
                   ('KEYWORD', '为'), ('NUMBER', 1)], got


# ──────────────────────────────────────────────────────────────
# 运行层：4 个 example 文件真跑断 rc==0（test_回归.py 同机制）
# ──────────────────────────────────────────────────────────────

R57_EXAMPLES = [
    'test_R22_嵌入关键字冗余验证.light',
    'test_R26_词首并入反向.light',
    'test_R26_词首并入混合.light',
    'test_R27_词首并入反向.light',
]


def _run_example(name: str):
    """独立临时目录里真跑单个 example，返回 (rc, 输出尾)。"""
    workdir = tempfile.mkdtemp(prefix='r57_case_')
    try:
        env = dict(os.environ)
        env.setdefault('PYTHONIOENCODING', 'utf-8')
        env['PYTHONUTF8'] = '1'
        p = subprocess.run(
            [sys.executable, str(RUNNER), str(EXAMPLES / name)],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=300, cwd=workdir, env=env,
        )
        return p.returncode, ((p.stdout or '') + (p.stderr or ''))[-600:]
    finally:
        import shutil
        shutil.rmtree(workdir, ignore_errors=True)


@pytest.mark.parametrize('name', R57_EXAMPLES)
def test_r57_复现example真跑绿(name):
    assert os.path.isfile(EXAMPLES / name), f'example 文件缺失: {name}'
    rc, tail = _run_example(name)
    assert rc == 0, f'{name} 应绿，实际 rc={rc}\n--- 输出尾 ---\n{tail}'
