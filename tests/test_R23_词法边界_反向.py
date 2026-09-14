# -*- coding: utf-8 -*-
"""test_R23_词法边界_反向.py —— 第23轮 任务4：反向验证——合法语法不被上下文规则误并

token 层断言「关键字/运算符的合法切分形态」在白名单清表后一字不变：
  1) 语句起始与「关键字+名」结构（接收 参数/如果 条件/遍历 元素…）；
  2) 运算符关键字（与/或/非/等于/大于/小于/加/减/乘/除）；
  3) 硬语句头排除集契约（等于空那么 的 那么、除类型错误 的 类型、
     自定义表 的 定义——后缀位置规则的排除集 _P0A_SUFFIX_SPLIT_KW）；
  4) 控制流语句头（如果/否则/遍历/尝试/捕获/函数/段落）。
"""
import os
import sys

import pytest

LIGHT_MERGE = os.environ.get("LIGHT_MERGE", r"G:\dswork\duan-light-merge\light-merge")
sys.path.insert(0, os.path.join(LIGHT_MERGE, "src"))

from lexer import Lexer  # noqa: E402


def _pairs(src):
    return [(t.type.name, t.value) for t in Lexer(src).tokenize() if t.type.name != "EOF"]


# ---- 1) 「关键字+名」结构（带空格语句形态） ----

@pytest.mark.parametrize("src,kw", [
    ("接收 参数", "接收"),
    ("如果 条件", "如果"),
    ("遍历 元素", "遍历"),
    ("等待 结果", "等待"),
    ("捕获 异常", "捕获"),
    ("设 值 为 1", "设"),
])
def test_kw_name_structure_split(src, kw):
    """关键字与名字之间有空格 → 空格天然分词，关键字必须是 KEYWORD。"""
    toks = _pairs(src)
    assert toks[0] == ("KEYWORD", kw)
    assert all(t[0] != "ERR" for t in toks)


# ---- 2) 无空格「关键字头+名」：语句关键字必须切分 ----

@pytest.mark.parametrize("src,kw", [
    ("如果条件", "如果"),
    ("遍历元素", "遍历"),
    ("捕获异常", "捕获"),
])
def test_unspaced_kw_prefix_split(src, kw):
    """硬语句头在词首必须切分（支持 如果条件…/遍历元素… 等无空格写法）。"""
    toks = _pairs(src)
    assert toks[0] == ("KEYWORD", kw)


def test_unspaced_await_verb_compound_merged():
    """`等待结果` 整体成 IDENTIFIER：等待 是动词（await 语句用法恒带空格
    `等待 目标()`），词首后随汉字按复合名头并入；R21 的 NAMES 名单亦把
    等待结果 列为合法变量名。语料 A/B 实证零影响（765 文件）。"""
    assert _pairs("等待结果") == [("IDENTIFIER", "等待结果")]


# ---- 3) 运算符关键字照常切分 ----

@pytest.mark.parametrize("src,kw", [
    ("甲 与 乙", "与"),
    ("甲 或 乙", "或"),
    ("非 甲", "非"),
    ("甲 等于 乙", "等于"),
    ("甲 大于 乙", "大于"),
    ("甲 小于 乙", "小于"),
])
def test_operators_split(src, kw):
    assert ("KEYWORD", kw) in _pairs(src)


def test_unspaced_arithmetic_split():
    """无空格算术：甲加乙 必须切成 甲/加/乙（运算符在任何位置切分）。"""
    toks = _pairs("甲加乙")
    assert ("KEYWORD", "加") in toks
    assert ("IDENTIFIER", "甲") in toks and ("IDENTIFIER", "乙") in toks


# ---- 4) 硬语句头排除集契约（_P0A_SUFFIX_SPLIT_KW） ----

def test_name_connector_still_split():
    """`等于空那么`：那么 是连接词，词中不得被后缀规则吞掉。"""
    toks = _pairs("若 甲 等于空那么：")
    assert ("KEYWORD", "等于") in toks
    assert ("KEYWORD", "那么") in toks


def test_type_kw_still_split():
    """`除类型错误`：类型 是类型定义语句头，词中保持既有切分。"""
    toks = _pairs("除类型错误")
    assert ("KEYWORD", "类型") in toks
    assert ("IDENTIFIER", "除") in toks


def test_definition_kw_still_split():
    """`自定义表`：定义 是定义语句头，词中保持既有切分（权限.light 语料契约）。"""
    toks = _pairs("自定义表")
    assert ("KEYWORD", "定义") in toks
    assert ("IDENTIFIER", "自") in toks and ("IDENTIFIER", "表") in toks


# ---- 5) 控制流语句头（token 层） ----

@pytest.mark.parametrize("head", ["如果", "否则", "遍历", "尝试", "捕获", "函数", "段落", "类型"])
def test_control_flow_heads(head):
    """控制流/定义语句头单发出现时必须是 KEYWORD。"""
    toks = _pairs(head + " 探针:")
    assert toks[0] == ("KEYWORD", head), f"{head} 应为语句头 KEYWORD，实际 {toks[:2]}"


# ---- 6) 子序列守卫：token 字面必须是源文本子序列（防凭空造字） ----

@pytest.mark.parametrize("src", [
    "处理函数", "可打印", "我的标准库", "学生模块", "输出格式",
    "打印甲", "模块甲", "标准库甲", "自己", "错误己",
    "异步读取文件", "常量时间比较", "等于空那么", "除类型错误", "自定义表",
])
def test_tokens_are_subsequence(src):
    """每个 token 的字面必须能在源文本中按序找到（TestNoFabricatedCharacters 同口径）。"""
    toks = _pairs(src)
    it = iter(src)
    for _, value in toks:
        if value is None:
            continue
        for ch in str(value):
            for c in it:
                if c == ch:
                    break
            else:
                pytest.fail(f"{src!r} 的 token {value!r} 不是源文本子序列（凭空造字）")
