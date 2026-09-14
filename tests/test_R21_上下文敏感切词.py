# -*- coding: utf-8 -*-
"""test_R21_上下文敏感切词.py —— 第21轮 任务2：词法上下文敏感切词（token 层验证）

验证「非语句起始位置的关键字前缀标识符整体成词」策略：
  1) A判据：**未注册**的关键字前缀标识符在表达式上下文中整体成 IDENTIFIER
     （这是任务2 相对第20轮的真增量——第20轮仅覆盖 `_scan_user_definitions` 已登记的名字）；
  2) B判据：语句起始位置的关键字优先切分**不变**（无空格写法 `如果条件:` 仍切出 `如果` 关键字）；
  3) C判据：运算符关键字在表达式中仍按 KEYWORD 切分（`甲加乙`/`甲 与 乙`）；
  4) 守卫：整串恰是关键字时仍作 KEYWORD（`打印(甲)`/`返回(甲)`/`如果(条件)`）；
  5) 语境：字典键 / 列表元素 / 调用参数等表达式语境整体成词。
"""
import os
import sys

import pytest

LIGHT_MERGE = os.environ.get("LIGHT_MERGE", r"G:\dswork\duan-light-merge\light-merge")
sys.path.insert(0, os.path.join(LIGHT_MERGE, "src"))

from lexer import Lexer  # noqa: E402

LEXER = Lexer()


def _tok(src):
    return [(t.type.name, t.value) for t in LEXER.tokenize(src)]


# ---------- A判据：未注册的关键字前缀标识符，在表达式中整体成 IDENTIFIER ----------
EXPR_UNREGISTERED = [
    ("设 结果 为 去重占位([1,1,2])", "去重占位"),
    ("设 结果 为 [排序函数, 筛选器]", "筛选器"),
    ("设 结果 为 {去重占位: 1}", "去重占位"),
    ("返回 作用域匹配(1)", "作用域匹配"),
    ("设 结果 为 去重占位(1) + 作用域匹配(2)", "作用域匹配"),
    ("去重占位(1)", "去重占位"),
    ("设 结果 为 断言为真(甲)", "断言为真"),
]


@pytest.mark.parametrize("src,ident", EXPR_UNREGISTERED)
def test_expr_context_unregistered_keeps_whole(src, ident):
    toks = _tok(src)
    assert ("IDENTIFIER", ident) in toks, \
        "表达式语境 %r 未整体成 IDENTIFIER %r（实际 %r）" % (src, ident, toks)


# ---------- B判据：语句起始位置关键字切分不变（含无空格写法） ----------
STMT_START = [
    ("如果条件:\n    打印 甲", "如果", "条件"),
    ("当条件:\n    打印 甲", "当", "条件"),
    ("遍历甲之列表:\n    打印 甲", "遍历", "甲"),
    ("否则若条件:\n    打印 甲", "否则若", "条件"),
]


@pytest.mark.parametrize("src,kw,nxt", STMT_START)
def test_statement_start_keyword_unchanged(src, kw, nxt):
    toks = _tok(src)
    assert ("KEYWORD", kw) in toks, \
        "语句起始 %r 的首关键字 %r 未保持 KEYWORD（实际 %r）" % (src, kw, toks)
    assert ("IDENTIFIER", nxt) in toks, \
        "语句起始 %r 的后续名字 %r 未成 IDENTIFIER（实际 %r）" % (src, nxt, toks)


def test_no_space_assign_and_print_split():
    """无空格写法：`设x为10` / `打印甲` 仍正确切分（本语言一等写法）。"""
    t1 = _tok("设x为10")
    assert ("KEYWORD", "设") in t1 and ("KEYWORD", "为") in t1, t1
    t2 = _tok("段落 主:\n    打印甲")
    assert ("KEYWORD", "打印") in t2 and ("IDENTIFIER", "甲") in t2, t2


# ---------- C判据：运算符关键字在表达式中仍按关键字切分 ----------
OPERATOR_CASES = [
    ("设 结果 为 甲 与 乙", "与"),
    ("设 结果 为 甲 或 乙", "或"),
    ("设 结果 为 甲加乙", "加"),
    ("设 结果 为 甲减乙", "减"),
    ("设 结果 为 甲 在 乙", "在"),
    ("设 结果 为 甲 大于 乙", "大于"),
]


@pytest.mark.parametrize("src,op", OPERATOR_CASES)
def test_operator_keyword_still_split(src, op):
    toks = _tok(src)
    assert ("KEYWORD", op) in toks, \
        "运算符 %r 未按 KEYWORD 切分（%r 实际 %r）" % (op, src, toks)


# ---------- 守卫：整串恰是关键字 → 仍作 KEYWORD（print/return/if 语句后接括号） ----------
KEYWORD_THEN_PAREN = [
    ("打印(甲)", "打印"),
    ("返回(甲)", "返回"),
    ("如果(条件)", "如果"),
]


@pytest.mark.parametrize("src,kw", KEYWORD_THEN_PAREN)
def test_keyword_itself_not_merged(src, kw):
    toks = _tok(src)
    assert ("KEYWORD", kw) in toks, \
        "关键字 %r 后接括号时被误并为标识符（%r → %r）" % (kw, src, toks)


# ---------- 语境：段落名/形参名含关键字前缀（含嵌套） ----------
def test_segment_name_and_param_keyword_prefix():
    src = ("段落 接收参数 接收 名单:\n"
           "    返回 名单\n"
           "段落 抛出异常 接收 甲:\n"
           "    返回 甲\n")
    toks = _tok(src)
    assert ("IDENTIFIER", "接收参数") in toks, toks
    assert ("IDENTIFIER", "抛出异常") in toks, toks


def test_nested_param_keyword_prefix_is_identifier():
    """L-152 家族：嵌套段落形参名（函数值）在定义处整体成 IDENTIFIER。"""
    src = ("段落 主:\n"
           "    段落 内层返回 接收 函数值:\n"
           "        返回 函数值(9)\n")
    toks = _tok(src)
    assert ("IDENTIFIER", "函数值") in toks, toks
    assert ("KEYWORD", "函数") not in toks, toks
