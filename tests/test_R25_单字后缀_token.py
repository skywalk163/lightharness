# -*- coding: utf-8 -*-
"""test_R25_单字后缀_token.py —— 第25轮 任务3：单字后缀位置规则 token 层边界测试

把任务书「词尾并入 17 条 + 六类边界形态 + 混合场景」钉在 token 层（运行期自校验见
examples/test_R25_词尾并入正向.light 与 test_R25_词尾并入边界反向.light）。

覆盖范围：
  1) 17 条词尾并入（配/段 拆 2 字，逐字 18 个）正向：词尾单字并入后整词成 IDENTIFIER；
  2) 六类边界反向（值字面量 / 下标 / 控制流 / 范围 / 结构助词 / 运算符）：关键字不并入；
  3) 混合场景：同行多词尾并入、嵌套、列表元素、字典键；
  4) 保护表形态：F=43、CS=16（R26 任务3 三重判据删 14 字）、到/真 ∉ F 但 ⊆ CS。

与任务2 的关系：任务2 曾用「词首编译门 G2」证明 18 字在词首位置均不可删（CS=30 不变）；
R26 任务1+2 实现「词首并入正面规则」后，该 G2 空洞由位置规则覆盖，故任务3 把这批字移出 CS。
本文件在 token 层固化「词尾并入正确 + 边界形态不被破坏」两项不变量，作为回归护栏。
"""
import os
import sys

import pytest

LIGHT_MERGE = os.environ.get("LIGHT_MERGE", r"G:\dswork\duan-light-merge\light-merge")
sys.path.insert(0, os.path.join(LIGHT_MERGE, "src"))

from lexer import Lexer  # noqa: E402

# 18 个候选字（任务书 17 条 + 配/段 拆 2）
CANDS = "出列则到常引接断末的真类试跳过长配段"


def _tok(src):
    return [(t.type.name, t.value) for t in Lexer(src, deterministic=True).tokenize()
            if t.type.name not in ("EOF", "NEWLINE")]


def _is_single_id(src):
    toks = _tok(src)
    return len(toks) == 1 and toks[0][0] == "IDENTIFIER" and toks[0][1] == src


# ───────────────────────── 一、词尾并入正向（18 字） ─────────────────────────
@pytest.mark.parametrize("word", [
    "标准输出", "退出码输出",          # 出
    "日期列", "索引列",               # 列
    "规则", "正则",                    # 则
    "文件未找到", "收到",             # 到
    "首异常", "常数",                  # 常
    "最后索引", "引用",               # 引
    "符号链接", "连接",               # 接
    "截断", "中断",                    # 断
    "月末", "末尾",                    # 末
    "成绩的长度",                      # 的（的 在词中并入）
    "标准输出失真", "全真",            # 真
    "有界队列类", "字典类",            # 类
    "测试", "测试用例",               # 试
    "最后心跳跳过",                    # 跳（跳/过 均在词内并入）
    "通过", "过滤器",                  # 过
    "块长", "长度",                    # 长
    "配置项", "配额",                  # 配
    "代码段", "阶段",                  # 段
])
def test_tail_merge_forward(word):
    """每个候选字的代表词尾复合名必须整词成 IDENTIFIER。"""
    assert _is_single_id(word), "%s 应整词成 IDENTIFIER，实际 %s" % (word, _tok(word))


# ───────────────────────── 二、六类边界反向 ─────────────────────────
def test_boundary_value_literal():
    assert _tok("返回 真") == [("KEYWORD", "返回"), ("KEYWORD", "真")]
    assert _tok("设甲 为 真") == [("KEYWORD", "设"), ("IDENTIFIER", "甲"),
                                  ("KEYWORD", "为"), ("KEYWORD", "真")]
    assert _tok("设甲 为 空") == [("KEYWORD", "设"), ("IDENTIFIER", "甲"),
                                  ("KEYWORD", "为"), ("KEYWORD", "空")]


def test_boundary_subscript_alias():
    """L-119 单字别名下标访问：配/段 后随 [ 保持切分。"""
    assert _tok("配[0]") == [("IDENTIFIER", "配"), ("LBRACKET", "["),
                               ("NUMBER", 0), ("RBRACKET", "]")]
    assert _tok("段[1]") == [("IDENTIFIER", "段"), ("LBRACKET", "["),
                              ("NUMBER", 1), ("RBRACKET", "]")]
    assert _tok('配["键"]') == [("IDENTIFIER", "配"), ("LBRACKET", "["),
                                ("STRING", "键"), ("RBRACKET", "]")]


def test_boundary_control_flow():
    """控制流连词保持 KEYWORD（spaced 则 不并入甲/乙）；无空格则 在词内并入（不浮出）。"""
    # spaced 形式：则 作连词 KEYWORD（light 真实写法 `如果 甲 则 乙`）
    assert _tok("如果 甲 则 乙") == [("KEYWORD", "如果"), ("IDENTIFIER", "甲"),
                                     ("KEYWORD", "则"), ("IDENTIFIER", "乙")]
    # 否则 独立成连词 KEYWORD
    assert _tok("否则") == [("KEYWORD", "否则")]
    # 无空格 `甲则乙`：则 在词内并入 → 整词成 IDENTIFIER（则 不浮出为独立 KEYWORD），
    # 这正是 F 正面规则的预期行为（则∈F，词内并入）；带空格 `甲 则 乙` 才作连词。
    assert _is_single_id("甲则乙")


def test_boundary_range_operator():
    """范围运算符从…到… 保持 KEYWORD。"""
    assert _tok("从 1 到 10") == [("KEYWORD", "从"), ("NUMBER", 1),
                                  ("KEYWORD", "到"), ("NUMBER", 10)]
    assert _tok("从甲 到 乙") == [("KEYWORD", "从"), ("IDENTIFIER", "甲"),
                                  ("KEYWORD", "到"), ("IDENTIFIER", "乙")]


def test_boundary_structure_particle():
    """结构助词：的 后随空白分词；无空格整词（类字在 CS，词首并入成立）。"""
    assert _tok("我的 书") == [("IDENTIFIER", "我的"), ("IDENTIFIER", "书")]
    assert _tok("类的 参数") == [("IDENTIFIER", "类的"), ("IDENTIFIER", "参数")]


def test_boundary_arithmetic_operator():
    """算术运算符单字：加/减 保持 KEYWORD，不并入。"""
    assert _tok("甲加乙") == [("IDENTIFIER", "甲"), ("KEYWORD", "加"),
                              ("IDENTIFIER", "乙")]
    assert _tok("甲减乙") == [("IDENTIFIER", "甲"), ("KEYWORD", "减"),
                              ("IDENTIFIER", "乙")]


# ───────────────────────── 三、混合场景 ─────────────────────────
def test_mixed_same_line_multiple_tail():
    """同一行多个词尾并入：日期列 + 块长 + 最后索引（变量名均整词）。"""
    assert _is_single_id("日期列")
    assert _is_single_id("块长")
    assert _is_single_id("最后索引")


def test_mixed_nested_and_list_and_dict():
    """嵌套调用名（有界队列类）、列表元素（标准输出/配置项）、字典键（字符串不受词法影响）。"""
    assert _is_single_id("有界队列类")
    assert _is_single_id("标准输出")
    assert _is_single_id("配置项")
    # 字典键为字符串，无需词法并入，但键名本身若含词尾单字须合法
    assert _tok('{"输出列": 1}')[0] == ("LBRACE", "{")
    assert _is_single_id("块长")


# ───────────────────────── 四、保护表形态（与任务2 证据一致） ─────────────────────────
def test_protection_table_shape():
    """任务1 后：词尾并入正面类别 F=43；【R26 任务3】CS 30→16；
    【R27 任务3】CS 16→2；【R28 任务3】CS 2→0（列/类移出，CS 表清零）；
    【R33】_P0A_NEVER_SPLIT 清零 ⇒ 步/至/到 进入 F，F 43→46。

    【R35 修正】旧断言引用 `Lexer.compound_safe_single_keywords`（小写、无下划线
    前缀的旧名），CS 表清零重构后该属性已不存在 ⇒ AttributeError 假红。
    现统一走模块级 `_COMPOUND_SAFE_SINGLE_KEYWORDS`。"""
    import lexer as _lx
    assert len(_lx._COMPOUND_SAFE_SINGLE_KEYWORDS) == 0
    assert len(Lexer._TRAILING_ALIAS_CLASS) == 46
    # R26/R27：18 候选字若已移出 CS，必须由词首并入正面类别或 DUAL 类别覆盖
    for c in CANDS:
        assert (c in _lx._COMPOUND_SAFE_SINGLE_KEYWORDS
                or c in _lx._P0A_HEAD_MERGE_SINGLE
                or c in _lx._P0A_HEAD_MERGE_DUAL), \
            "%s 既不在 CS 也不在词首并入正面类别/DUAL" % c
    # 到/真 不在 F（范围运算符 / 值字面量），R27 后由 DUAL 类别覆盖（不在 CS）
    # 【R35 修正】R33 清零 _P0A_NEVER_SPLIT 后，`到` **已并入 F**（词尾并入类），
    # 与 `真` 不同（真 仍在 F 外、仅属 DUAL）。二者同属 DUAL 这一点未变。
    # 另：`Lexer.compound_safe_single_keywords` 旧名已不存在，改用模块级名。
    assert "到" in Lexer._TRAILING_ALIAS_CLASS      # R33 后改判：在 F 内
    assert "真" not in Lexer._TRAILING_ALIAS_CLASS
    assert "到" in _lx._P0A_HEAD_MERGE_DUAL
    assert "真" in _lx._P0A_HEAD_MERGE_DUAL
    assert "到" not in _lx._COMPOUND_SAFE_SINGLE_KEYWORDS
    assert "真" not in _lx._COMPOUND_SAFE_SINGLE_KEYWORDS
