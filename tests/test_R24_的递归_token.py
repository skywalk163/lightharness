# -*- coding: utf-8 -*-
"""test_R24_的递归_token.py —— 第24轮 任务1：`的` 递归契约 + 运算符/值字面量守卫 token 层验证

直接调用 light-merge Lexer.tokenize（P0-A 确定性模式，默认），把任务1 的四项
验证标准钉在 token 层（运行期自校验见 examples/test_R24_的递归修复.light）：

  1) `的` 递归路径契约（任务书怀疑的「吞分隔符」经审计不可复现，见交付报告 §1）；
  2) 成员/关系分隔符 `之` 的**语句起始 vs 表达式位置 token 流一致**（R24 P0 修复点）；
  3) 运算符单字（乘/加/减/除/余）守卫：运算符两侧切分、构词两侧并入；
  4) 值字面量单字（真/假/空）守卫：独立成词为 KEYWORD、成词时并入标识符；
  5) 100+ 自由名护栏（去除空格/10的幂/索引/种类/阶乘）不被吞；
  6) 保护表形态（R24 任务3 联动：_COMPOUND_SAFE_SINGLE_KEYWORDS 30 → 17）。
"""
import os
import sys

import pytest

LIGHT_MERGE = os.environ.get("LIGHT_MERGE", r"G:\dswork\duan-light-merge\light-merge")
sys.path.insert(0, os.path.join(LIGHT_MERGE, "src"))

from lexer import Lexer  # noqa: E402


def _pairs(src):
    return [(t.type.name, t.value) for t in Lexer(src).tokenize() if t.type.name != "EOF"]


def _kwfree(src):
    """去掉 NEWLINE（保留其它）便于比较同一语法形状的两处 token 流。"""
    return [(t.type.name, t.value) for t in Lexer(src).tokenize()
            if t.type.name not in ("EOF", "NEWLINE")]


# ── 1) `的` 递归路径契约 ────────────────────────────────────────────────
# 「`的` 递归吞分隔符」审计结论：不可复现。`的` 在 compound-safe 表内，
# 递归守卫(_match_keyword :1306)只对「后续命中 `之`」做 pos 对齐，其余原样返回，
# 不存在吞掉空白/标点/换行的分支。下面钉住其真实契约。

@pytest.mark.parametrize("src,expect", [
    # 词内：并入标识符（构词胶水）
    ("我的书", [("IDENTIFIER", "我的书")]),
    ("红色的花", [("IDENTIFIER", "红色的花")]),
    ("大的小的", [("IDENTIFIER", "大的小的")]),
    ("我的函数的参数", [("IDENTIFIER", "我的函数的参数")]),
    ("甲的", [("IDENTIFIER", "甲的")]),
    # 词首为多字关键字：关键字照切，余部含 的 仍并入
    ("函数的参数", [("KEYWORD", "函数"), ("IDENTIFIER", "的参数")]),
    # 独立成段：仍是 KEYWORD（`的` 不作变量名）
    ("的", [("KEYWORD", "的")]),
    # 空白分隔：的 是独立分隔词
    ("甲 的 书", [("IDENTIFIER", "甲"), ("KEYWORD", "的"), ("IDENTIFIER", "书")]),
    # 的 后随空白/标点：递归立即结束，不吞后续内容
    ("甲的 乙", [("IDENTIFIER", "甲的"), ("IDENTIFIER", "乙")]),
])
def test_de_recursion_contract(src, expect):
    assert _kwfree(src) == expect


def test_de_does_not_swallow_newline():
    """`的` 词尾后接换行：递归不得跨行吞入下一条语句。"""
    toks = _kwfree("甲的\n乙")
    assert toks == [("IDENTIFIER", "甲的"), ("IDENTIFIER", "乙")]


def test_de_does_not_swallow_punct():
    """`的` 词尾后接标点：递归不得吞入标点后的内容。"""
    toks = _kwfree("打印(甲的)")
    assert toks == [("KEYWORD", "打印"), ("LPAREN", "("),
                    ("IDENTIFIER", "甲的"), ("RPAREN", ")")]


# ── 2) 成员/关系分隔符 `之`：两处位置 token 流必须一致（R24 P0 修复点）────
# 修复前：`自之姓名` 在语句起始 = 自+之+姓名，在表达式位置（返回/实参/运算）
# 却并成一个 IDENTIFIER → `name '自之姓名' is not defined`。

_ZI_TAIL = [("KEYWORD", "自"), ("KEYWORD", "之"), ("IDENTIFIER", "姓名")]


@pytest.mark.parametrize("src,head", [
    ("自之姓名", []),                                    # 语句起始
    ("印 自之姓名", [("IDENTIFIER", "印")]),              # 实参位置
    ("返回 自之姓名", [("KEYWORD", "返回")]),             # 表达式位置
])
def test_zi_member_access_consistent(src, head):
    """`自之姓名` 无论出现在哪个位置，都必须是 自 + 之 + 姓名。"""
    assert _kwfree(src) == head + _ZI_TAIL


def test_zi_member_access_dotted_chain():
    assert _kwfree("对象之属性") == [("IDENTIFIER", "对象"), ("KEYWORD", "之"),
                                 ("IDENTIFIER", "属性")]
    assert _kwfree("打印 对象之方法") == [("KEYWORD", "打印"), ("IDENTIFIER", "对象"),
                                     ("KEYWORD", "之"), ("IDENTIFIER", "方法")]
    assert _kwfree("甲之乙") == [("IDENTIFIER", "甲"), ("KEYWORD", "之"),
                             ("IDENTIFIER", "乙")]

def test_zi_not_merged_into_single_identifier():
    """回归护栏：任何含 `之` 的汉字段都不许整体并成单个 IDENTIFIER。"""
    for src in ("自之姓名", "对象之属性", "甲之乙", "数列之长度"):
        vals = [v for (t, v) in _kwfree(src) if t == "IDENTIFIER"]
        assert not any("之" in v for v in vals), src


# ── 3) 运算符单字守卫（乘/加/减/除/余）────────────────────────────────
@pytest.mark.parametrize("src,expect", [
    # 无空格表达式：运算符切分
    ("甲加乙", [("IDENTIFIER", "甲"), ("KEYWORD", "加"), ("IDENTIFIER", "乙")]),
    ("甲减乙", [("IDENTIFIER", "甲"), ("KEYWORD", "减"), ("IDENTIFIER", "乙")]),
    ("甲乘乙", [("IDENTIFIER", "甲"), ("KEYWORD", "乘"), ("IDENTIFIER", "乙")]),
    ("甲除乙", [("IDENTIFIER", "甲"), ("KEYWORD", "除"), ("IDENTIFIER", "乙")]),
    # 有空格表达式：运算符切分
    ("甲 加 乙", [("IDENTIFIER", "甲"), ("KEYWORD", "加"), ("IDENTIFIER", "乙")]),
    ("甲 余 乙", [("IDENTIFIER", "甲"), ("KEYWORD", "余"), ("IDENTIFIER", "乙")]),
    # 构词：整体成 IDENTIFIER
    ("加法", [("IDENTIFIER", "加法")]),
    ("减法", [("IDENTIFIER", "减法")]),
    ("乘法表", [("IDENTIFIER", "乘法表")]),
    ("余数", [("IDENTIFIER", "余数")]),
    # 无空格 甲余乙 归构词一侧：余 是 compound-safe 构词胶水（单测钉住），非此处运算符
    ("甲余乙", [("IDENTIFIER", "甲余乙")]),
])
def test_operator_single_guard(src, expect):
    assert _kwfree(src) == expect


def test_operator_run_not_split_by_sep_gate():
    """闸门只排除成员/关系分隔符，**不**波及算术/幂粘连语义：调用语境下
    `自加乙(...)` / `定义幂(...)` 保持整串粘连（与 HEAD 一致，避免误伤生成树）。"""
    assert _kwfree("自加乙(甲)")[0] == ("IDENTIFIER", "自加乙")
    assert _kwfree("定义幂(甲)")[0] == ("IDENTIFIER", "定义幂")


def test_sep_gate_blocks_merge_but_not_arithmetic():
    """成员/关系分隔符在串内 → 整串不得并入；算术运算符在串内 → 不受影响。"""
    for s in ("印 自之姓名", "返回 自之姓名", "打印 对象之方法"):
        vals = [v for (t, v) in _kwfree(s) if t == "IDENTIFIER"]
        assert not any(("之" in v) for v in vals), s


# ── 4) 值字面量单字守卫（真/假/空）────────────────────────────────────
@pytest.mark.parametrize("src,expect", [
    ("设 甲 为 真", [("KEYWORD", "设"), ("IDENTIFIER", "甲"),
                     ("KEYWORD", "为"), ("KEYWORD", "真")]),
    ("设 甲 为 空", [("KEYWORD", "设"), ("IDENTIFIER", "甲"),
                     ("KEYWORD", "为"), ("KEYWORD", "空")]),
    ("设 甲 为 假", [("KEYWORD", "设"), ("IDENTIFIER", "甲"),
                     ("KEYWORD", "为"), ("KEYWORD", "假")]),
])
def test_value_literal_standalone_is_keyword(src, expect):
    assert _kwfree(src) == expect


@pytest.mark.parametrize("whole", ["真实", "空白", "空值", "真空", "真假标志"])
def test_value_literal_compound_merged(whole):
    assert _kwfree(whole) == [("IDENTIFIER", whole)]


def test_value_literal_false_prefixed_name_merged_in_call():
    """`假` 打头的名字在**调用语境**整体成词（值字面量守卫不误切）。"""
    assert _kwfree("假名(甲)")[0] == ("IDENTIFIER", "假名")


# ── 5) 100+ 自由名护栏（任务书通用约束 4）────────────────────────────
@pytest.mark.parametrize("src,expect", [
    ("去除空格", [("IDENTIFIER", "去除空格")]),
    ("索引", [("IDENTIFIER", "索引")]),
    ("种类", [("IDENTIFIER", "种类")]),
    ("阶乘", [("IDENTIFIER", "阶乘")]),
    ("10的幂", [("NUMBER", 10), ("IDENTIFIER", "的幂")]),
])
def test_free_names_not_split(src, expect):
    assert _kwfree(src) == expect


# ── 6) 保护表形态与「13 条保留」审计结论（R24 任务3 联动）────────────────
_RETAINED_13 = list("例出则常引接是末试跳过长首")


def test_compound_safe_table_is_30():
    """R24 任务3 审计结论：任务2 判为①冗余可删的 13 条**保留**（语料冗余但语义非冗余）。"""
    import lexer as _lx
    assert len(_lx._COMPOUND_SAFE_SINGLE_KEYWORDS) == 30


@pytest.mark.parametrize("ch", _RETAINED_13)
def test_retained_single_chars_present(ch):
    import lexer as _lx
    assert ch in _lx._COMPOUND_SAFE_SINGLE_KEYWORDS


@pytest.mark.parametrize("ch", _RETAINED_13)
def test_retained_chars_member_name_whole(ch):
    """空洞A（成员访问段首）：`甲之<字>顶` 成员名整体成词 —— 由 CR1 通用规则覆盖。"""
    toks = _kwfree("甲之" + ch + "顶")
    assert toks == [("IDENTIFIER", "甲"), ("KEYWORD", "之"), ("IDENTIFIER", ch + "顶")]


@pytest.mark.parametrize("ch", _RETAINED_13)
def test_retained_chars_statement_initial_whole(ch):
    """空洞B（语句起始裸名）：`<字>顶 = 1` 的赋值目标必须整体成词 —— 这是 13 条
    **不能被位置规则替代**的直接理由（语句起始位置关键字优先，无法并入）。"""
    toks = _kwfree(ch + "顶 = 1")
    assert toks == [("IDENTIFIER", ch + "顶"), ("EQUALS", "="), ("NUMBER", 1)]


def test_dead_constant_removed():
    """R24 任务3 死代码清理：_P0A_COMPOUND_SAFE 零引用，已删除。"""
    import lexer as _lx
    assert not hasattr(_lx.Lexer, "_P0A_COMPOUND_SAFE")
