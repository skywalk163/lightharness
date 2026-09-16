# -*- coding: utf-8 -*-
"""R36 任务3：性能优化（预计算 `_OPERATOR_KEYWORDS_NO_UNARY_PREFIX`）语义等价 pytest。

验证点：
  1) 模块常量 `_OPERATOR_KEYWORDS_NO_UNARY_PREFIX` 必须 == `_OPERATOR_KEYWORDS - _P0A_UNARY_PREFIX_KW`
     （与 src/lexer.py 文末 import 自校验④ 双重兜底，防止未来 `_P0A_UNARY_PREFIX_KW` 增删成员时
     忘记同步预计算常量）。
  2) 预计算后，R21 词首闸门3 的 `非` 一元前缀行为不变：
       · 非语句起始位置（如 `设 X 为 非空` / `打印 非空块`）`非X` 仍整体并入 IDENTIFIER（复合名）；
       · 词尾 `非`（`长度非0`）仍切出为独立 KEYWORD（逻辑非运算符）；
       · 语句起始的 `非甲` 仍是 `非`(KW) + `甲`(ID)（not 表达式，R21 闸门不在语句起始生效）。
  3) 全语料零回归由 _antirun_r36 反跑保证（见 _task3_R36_性能优化.md）。
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, '..', 'light-merge', 'src'))
import lexer  # noqa: E402


def _tokens(text):
    return [(t.type.name, t.value) for t in
            lexer.Lexer(text, deterministic=True).tokenize()
            if t.type.name not in ('EOF', 'NEWLINE')]


def test_precomputed_constant_equals_inline_difference():
    """预计算常量必须与「_OPERATOR_KEYWORDS - _P0A_UNARY_PREFIX_KW」严格相等。"""
    expected = lexer._OPERATOR_KEYWORDS - lexer.Lexer._P0A_UNARY_PREFIX_KW
    assert lexer._OPERATOR_KEYWORDS_NO_UNARY_PREFIX == expected
    # 差集语义：排除一元前缀关键字 非，但保留其余运算符关键字
    assert '非' not in lexer._OPERATOR_KEYWORDS_NO_UNARY_PREFIX
    assert '与' in lexer._OPERATOR_KEYWORDS_NO_UNARY_PREFIX
    assert '或' in lexer._OPERATOR_KEYWORDS_NO_UNARY_PREFIX
    assert '为' in lexer._OPERATOR_KEYWORDS_NO_UNARY_PREFIX


def test_非_prefix_merged_in_non_statement_start():
    """非语句起始位置，`非X` 仍整体成 IDENTIFIER（R21 闸门3 一元前缀例外）。"""
    # 设 X 为 非空  ->  非空 作为赋值右值（非语句起始）整体并入
    toks = _tokens('设 X 为 非空')
    assert ('IDENTIFIER', '非空') in toks, f'非空 应整体并入，实际 {toks}'
    # 打印 非空块  ->  非空块 作为调用实参（非语句起始）整体并入
    toks = _tokens('打印 非空块')
    assert ('IDENTIFIER', '非空块') in toks, f'非空块 应整体并入，实际 {toks}'


def test_非_operator_split_at_tail():
    """词尾 `非`（`长度非0`）仍切出为独立 KEYWORD（逻辑非），不被并入。"""
    toks = _tokens('长度非0')
    assert ('IDENTIFIER', '长度') in toks
    assert ('KEYWORD', '非') in toks
    assert ('NUMBER', 0) in toks
    joined = ''.join(str(v) for _, v in toks)
    assert joined == '长度非0'


def test_非_at_statement_start_is_not_operator():
    """语句起始的 `非甲` 仍是 `非`(KW) + `甲`(ID)（not 表达式，R21 闸门不在语句起始生效）。"""
    toks = _tokens('非甲')
    assert toks == [('KEYWORD', '非'), ('IDENTIFIER', '甲')], f'实际 {toks}'


def test_非_mid_word_merges_when_prefix_merged():
    """非语句起始且非在词中（甲非乙），整体并入 IDENTIFIER（非 不强制切分）。"""
    toks = _tokens('甲非乙')
    assert ('IDENTIFIER', '甲非乙') in toks, f'甲非乙 应整体并入，实际 {toks}'
