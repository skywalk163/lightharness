# -*- coding: utf-8 -*-
"""test_R23_词法边界_token.py —— 第23轮 任务4：上下文规则边界 token 层验证

直接调用 light-merge Lexer.tokenize，验证第23轮保护表通用化替代后的关键 token 形态：
  1) 己 词尾并入（_TRAILING_ALIAS_MERGE 家族）；
  2) IDENTIFIER_SAFE 后缀位置并入 + 词首切分（阶段B）；
  3) CCW 内建复合名整体成词（阶段C 前置契约）；
  4) 嵌入运算符守卫（合并逻辑不许吞词中真关键字）。
"""
import os
import sys

import pytest

LIGHT_MERGE = os.environ.get("LIGHT_MERGE", r"G:\dswork\duan-light-merge\light-merge")
sys.path.insert(0, os.path.join(LIGHT_MERGE, "src"))

from lexer import Lexer  # noqa: E402


def _pairs(src):
    return [(t.type.name, t.value) for t in Lexer(src).tokenize() if t.type.name != "EOF"]


# ---- 1) 己 词尾并入 ----

@pytest.mark.parametrize("src,whole", [
    ("自己", "自己"),
    ("错误己", "错误己"),
    ("本己录", "本己录"),
])
def test_ji_tail_merged(src, whole):
    """己 位于汉字词词尾 → 整体成 IDENTIFIER。"""
    assert _pairs(src) == [("IDENTIFIER", whole)]


def test_ji_word_start_not_merged():
    """己 位于词首仍是语句别名（不被并入前缀）。"""
    toks = _pairs("己任")
    assert toks[0][0] == "KEYWORD"


# ---- 2) IDENTIFIER_SAFE 后缀位置（阶段B 契约） ----

@pytest.mark.parametrize("src,whole", [
    ("处理函数", "处理函数"),
    ("可打印", "可打印"),
    ("可打印标志", "可打印标志"),
    ("是可打印", "是可打印"),
    ("我的标准库", "我的标准库"),
    ("学生模块", "学生模块"),
    ("输出格式", "输出格式"),
    ("输出结果", "输出结果"),
    ("输出甲", "输出甲"),
])
def test_suffix_position_merged(src, whole):
    """多字非运算符关键字位于词中/词尾 → 整体成 IDENTIFIER（后缀位置上下文规则）。"""
    assert _pairs(src) == [("IDENTIFIER", whole)]


@pytest.mark.parametrize("src,kw,rest", [
    ("打印甲", "打印", "甲"),
    ("打印结果", "打印", "结果"),
    ("打印甲乙丙", "打印", "甲乙丙"),
    ("模块甲", "模块", "甲"),
    ("标准库甲", "标准库", "甲"),
])
def test_word_start_statement_kw_split(src, kw, rest):
    """词首语句关键字（打印/模块/标准库）→ KEYWORD + 余部（无空格 print 一等写法）。"""
    assert _pairs(src) == [("KEYWORD", kw), ("IDENTIFIER", rest)]


# 【R35 修正】CCW 表已于 R30 清零（184→0）。本组原 6 例中 3 例不再整词：
#   异步读取文件 → KEYWORD(异步) + IDENTIFIER(读取文件)
#   并发等待     → KEYWORD(并) + IDENTIFIER(发) + KEYWORD(等待)
#   常量时间比较 → KEYWORD(常量) + IDENTIFIER(时间比较)
# 这是撤销逐词白名单的**已知语义代价**（全语料零命中 ⇒ R30 判零回归，但合成名
# 整词能力确实丧失）。详见 _task6_R35_质量审查报告.md 发现 F-3。
# 故拆为两组：仍整词的保留硬断言；已劈开的改为「记录现状」断言，使任何后续
# 变化都可感知（而不是让整词断言静默地一直红着）。

@pytest.mark.parametrize("src", ["低级关闭", "创建任务", "首个完成"])
def test_ccw_builtin_names_whole(src):
    """CCW 撤销后仍整体成 IDENTIFIER 的内建复合名（契约未变）。"""
    assert _pairs(src) == [("IDENTIFIER", src)]


@pytest.mark.parametrize("src,expected", [
    ("异步读取文件",
     [("KEYWORD", "异步"), ("IDENTIFIER", "读取文件")]),
    ("并发等待",
     [("KEYWORD", "并"), ("IDENTIFIER", "发"), ("KEYWORD", "等待")]),
    ("常量时间比较",
     [("KEYWORD", "常量"), ("IDENTIFIER", "时间比较")]),
])
def test_ccw_names_split_after_ccw_cleared(src, expected):
    """R30 CCW 清零后这 3 个合成名按关键字切分——钉住现状，防无声恶化。

    只钉"切成什么"，不钉"是否整词"；若将来某轮让它们重新整词，本断言会红，
    提示需同步更新本文件（即变更可感知）。"""
    assert _pairs(src) == expected


# ---- 3) 嵌入运算符守卫 ----

def test_embedded_ops_preserved():
    """合并逻辑只吃复合名成分，词中真关键字必须存活。"""
    assert _pairs("学生模块等于甲") == [
        ("IDENTIFIER", "学生模块"), ("KEYWORD", "等于"), ("IDENTIFIER", "甲")]
    assert _pairs("打印甲加1") == [
        ("KEYWORD", "打印"), ("IDENTIFIER", "甲"), ("KEYWORD", "加"), ("NUMBER", 1)]
    assert _pairs("甲加可打印") == [
        ("IDENTIFIER", "甲"), ("KEYWORD", "加"), ("IDENTIFIER", "可打印")]


def test_word_start_with_space():
    """带空格语句形态：打印/模块/标准库/输出 词首均为 KEYWORD。"""
    assert _pairs("打印 消息")[0] == ("KEYWORD", "打印")
    assert _pairs("模块 名")[0] == ("KEYWORD", "模块")
    assert _pairs("标准库 路径")[0] == ("KEYWORD", "标准库")
    assert _pairs("输出 内容")[0] == ("KEYWORD", "输出")
    assert _pairs("打印 学生模块") == [("KEYWORD", "打印"), ("IDENTIFIER", "学生模块")]


# ---- 4) ASCII/数字 混合边界 ----

def test_ascii_han_mixed():
    """ASCII 与中文混合、数字后缀的既有切分保持（非本轮目标，防回归）。"""
    toks = _pairs("函数1")
    assert toks[0] == ("KEYWORD", "函数")
    toks = _pairs("test函数")
    assert ("KEYWORD", "函数") in toks
