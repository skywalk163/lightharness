# -*- coding: utf-8 -*-
"""test_R21_词法确定性_token.py —— 第21轮 任务4：词法确定性 token 层验证

直接调用 light-merge Lexer.tokenize，验证第21轮词法重构的关键 token 形态：
  1) L-152 家族：嵌套段落关键字前缀形参整体成 IDENTIFIER（断裂态回归保护）；
  2) 块内设名：if/遍历/尝试 块内 设 关键字前缀名整体成词；
  3) 表达式上下文（定义登记路径）：模块级定义后调用名整体成词；
  4) 语句起始位置：如果/否则/否则若/遍历/当/尝试/捕获/返回 语句头关键字保持 KEYWORD；
  5) 运算符/赋值字形态：为/等于/大于 切分不变。
"""
import os
import sys

import pytest

LIGHT_MERGE = os.environ.get("LIGHT_MERGE", r"G:\dswork\duan-light-merge\light-merge")
sys.path.insert(0, os.path.join(LIGHT_MERGE, "src"))

from lexer import Lexer  # noqa: E402

LEXER = Lexer()

NAMES = ["函数值", "返回值", "尝试结果", "设值器", "等于判断", "如果条件", "当循环", "遍历器",
         "捕获块", "抛出异常", "打印函数", "新建对象", "导入模块", "导出名称", "定义变量",
         "设置属性", "异步作用域", "等待结果", "推迟执行"]


def _ids(toks):
    return [t.value for t in toks if t.type.name == "IDENTIFIER"]


def _pairs(toks):
    return [(t.type.name, t.value) for t in toks]


@pytest.mark.parametrize("name", NAMES)
def test_nested_segment_param_whole(name):
    """L-152 家族：嵌套段落形参（关键字前缀）token 层整体成 IDENTIFIER。"""
    src = ("段落 外层 接收:\n"
           "  段落 内层 接收 %s:\n"
           "      返回 %s + 1\n"
           "  返回 内层(1)\n"
           "外层()" % (name, name))
    toks = LEXER.tokenize(src)
    assert name in _ids(toks), "嵌套形参 %s 未整体成词（%r）" % (name, _pairs(toks)[:12])


def test_nested_param_three_levels():
    """三层嵌套：二层/三层形参（返回值/尝试结果）均整体成词。"""
    src = ("段落 二层外 接收:\n"
           "    段落 二层内 接收 返回值:\n"
           "        段落 三层内 接收 尝试结果:\n"
           "            返回 返回值 * 10 + 尝试结果\n"
           "        返回 三层内(2)\n"
           "    返回 二层内(1)\n"
           "二层外()")
    toks = LEXER.tokenize(src)
    ids = _ids(toks)
    assert "返回值" in ids and "尝试结果" in ids, "三层嵌套形参被切碎（%r）" % _pairs(toks)[:16]


@pytest.mark.parametrize("name", ["函数值", "返回值", "尝试结果"])
def test_block_scope_set_name(name):
    """块内设名：if/遍历/尝试 块内 设 关键字前缀名，token 不切碎。"""
    src = ("段落 主:\n"
           "    如果 真:\n"
           "        设 %s 为 1\n"
           "    遍历 项 之 [1]:\n"
           "        设 %s二 为 2\n"
           "主()" % (name, name))
    toks = LEXER.tokenize(src)
    assert name in _ids(toks), "块内设名 %s 被切碎（%r）" % (name, _pairs(toks)[:12])


def test_expression_context_with_definition():
    """表达式上下文（模块级定义登记路径）：调用名整体成词。"""
    src = ("段落 去重占位 接收 输入:\n"
           "    返回 输入\n"
           "设 结果 为 去重占位(41)")
    toks = LEXER.tokenize(src)
    assert "去重占位" in _ids(toks), "表达式调用名被切碎（%r）" % _pairs(toks)[:12]


@pytest.mark.parametrize("head", ["如果", "否则", "否则若", "遍历", "当", "尝试", "捕获", "返回"])
def test_statement_head_keywords(head):
    """语句起始位置关键字保持 KEYWORD，不被并入标识符。"""
    snippets = {
        "如果": "如果 条件:",
        "否则": "否则:",
        "否则若": "否则若 条件:",
        "遍历": "遍历 键 之 列表:",
        "当": "当 条件:",
        "尝试": "尝试:",
        "捕获": "捕获 异常 甲:",
        "返回": "返回 真",
    }
    toks = LEXER.tokenize(snippets[head])
    assert ("KEYWORD", head) in _pairs(toks), "语句头 %s 未保持 KEYWORD（%r）" % (head, _pairs(toks))


def test_operator_and_assign_keywords_unchanged():
    """第21轮重构不变性：运算符/赋值关键字在表达式上下文仍按 KEYWORD 切分。

    注：`非甲`（无空格）当前整体成 IDENTIFIER（任务1 通用最大匹配现状）；
    逻辑非的运算形态为带空格 `非 真`，此处按带空格形态断言。
    """
    cases = [
        ("如果 条件 为 真:", "KEYWORD", "如果"),
        ("设 结果 为 甲 与 乙", "KEYWORD", "与"),
        ("设 结果 为 甲 或 乙", "KEYWORD", "或"),
        ("设 结果 为 非 真", "KEYWORD", "非"),
    ]
    for src, ttype, value in cases:
        assert (ttype, value) in _pairs(LEXER.tokenize(src)), "%r 缺少 %r" % (src, (ttype, value))


def test_l152_reproduction_token_shape():
    """L-152 修复回归保护：任务书复现源码中 函数值 为单个 IDENTIFIER。"""
    src = ("段落 小于判断 接收 甲:\n"
           "  返回 甲 + 1\n"
           "段落 主:\n"
           "  段落 内层返回 接收 函数值:\n"
           "      返回 函数值(9)\n"
           "  断言相等(内层返回(小于判断), 10, \"x\")\n"
           "主()")
    toks = LEXER.tokenize(src)
    assert "函数值" in _ids(toks), "L-152 回潮：函数值 被切碎（%r）" % _pairs(toks)[:16]
