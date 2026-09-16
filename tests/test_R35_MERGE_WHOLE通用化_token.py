# -*- coding: utf-8 -*-
"""
test_R35_MERGE_WHOLE通用化_token.py —— 第35轮 token 层断言

本轮结果：_P0A_MERGE_WHOLE 3 → 2
  · 非空块     —— 通用化**成功**，由新的一元前缀运算符规则接住后移除
  · 整理模型消息 —— 通用化失败（模 是真取模运算符，甲模乙 实证），保留为真护栏
  · 记录类型   —— 通用化失败（与 期望类型/参数类型 结构不可分），保留为真护栏

覆盖：
 1. MERGE_WHOLE 现状（2 条：整理模型消息 / 记录类型）
 2. 新通用规则 _P0A_UNARY_PREFIX_KW（= {'非'}）存在且生效
 3. 非空块 五种边界形态（设名/函数名/成员访问/段落名/传参位）均整词
 4. 反向形态：带空格 `非 X` 仍是 not 表达式；余部是已声明名字时 `非X` 仍切分
 5. 保留 2 条真护栏的保护语义（甲模乙 / 数类型 等仍切分）
 6. 联动保护表断言（HM=25 / F=46 / NEVER_SPLIT=0 / CS=0 / DUAL=8 …）
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'light-merge', 'src'))
import lexer as _lx  # noqa: E402

L = _lx.Lexer()


def toks(src):
    return [(t.type.name, t.value) for t in L.tokenize(src)
            if t.type.name not in ('EOF', 'NEWLINE')]


def vals(src):
    return [v for _, v in toks(src)]


# === 1. MERGE_WHOLE 现状：3 → 2 ===

def test_merge_whole_is_2():
    """R35：_P0A_MERGE_WHOLE 3→2（非空块 通用化后移除）"""
    assert len(L._P0A_MERGE_WHOLE) == 2


def test_merge_whole_exact_contents():
    """R35：保留 2 条 = 整理模型消息 / 记录类型"""
    assert set(L._P0A_MERGE_WHOLE) == {'整理模型消息', '记录类型'}


def test_non_empty_block_removed():
    """R35：非空块 已不在 MERGE_WHOLE（由通用规则接住，非删除语义）"""
    assert '非空块' not in L._P0A_MERGE_WHOLE


# === 2. 新通用规则：一元前缀运算符类别 ===

def test_unary_prefix_class_exists():
    """R35 新增 Lexer._P0A_UNARY_PREFIX_KW = {'非'}"""
    assert _lx.Lexer._P0A_UNARY_PREFIX_KW == frozenset({'非'})


def test_unary_prefix_is_subset_of_operator_keywords():
    """一元前缀字必须原本属于运算符关键字集合（否则本规则无意义）"""
    assert _lx.Lexer._P0A_UNARY_PREFIX_KW <= set(_lx._OPERATOR_KEYWORDS)


def test_binary_operators_not_in_unary_prefix():
    """二元中缀运算符（加/减/乘/除/等于/包含）不得进入一元前缀类别"""
    binary = {'加', '减', '乘', '除', '等于', '包含', '大于', '小于'}
    assert not (binary & set(_lx.Lexer._P0A_UNARY_PREFIX_KW))


# === 3. 非空块 五种边界形态（G3 契约，均由通用规则接住） ===

def test_f1_set_name():
    """F1 设名位：`设 x 为 非空块` → 整词 IDENTIFIER"""
    assert ('IDENTIFIER', '非空块') in toks('设 x 为 非空块')


def test_f2_function_name():
    """F2 函数名位：`段落 非空块:` → 整词 IDENTIFIER"""
    t = toks('段落 非空块:\n  返回 1')
    assert ('IDENTIFIER', '非空块') in t
    assert ('KEYWORD', '非') not in t


def test_f3_member_access():
    """F3 成员访问位：`甲.非空块` → 非空块 整词"""
    assert ('IDENTIFIER', '非空块') in toks('设 x 为 甲.非空块')


def test_f4_call_position():
    """F4 调用位：`非空块()` → 整词 IDENTIFIER + 括号"""
    t = toks('设 x 为 非空块()')
    assert ('IDENTIFIER', '非空块') in t
    assert ('LPAREN', '(') in t


def test_f5_argument_position():
    """F5 传参位：`取(非空块)` → 整词 IDENTIFIER（不被劈成 非 + 空块）"""
    t = toks('设 x 为 取(非空块)')
    assert ('IDENTIFIER', '非空块') in t
    assert not any(v == '空块' for _, v in t)


# === 4. 反向形态（防过度并入） ===

def test_spaced_not_is_still_operator():
    """带空格 `非 X` 仍是 not 表达式：KEYWORD(非) + IDENTIFIER(甲)"""
    t = toks('设 y 为 非 甲')
    assert ('KEYWORD', '非') in t
    assert ('IDENTIFIER', '甲') in t


def test_not_true_value_literal_unaffected():
    """`非 是真` 正常用法不受影响（真 为值字面量）"""
    t = toks('设 y 为 非 是真')
    assert ('KEYWORD', '非') in t
    assert ('IDENTIFIER', '是真') in t


def test_narrowing_declared_name_still_splits():
    """收窄判据：余部是**已声明名字**时 `非甲` 仍是 `not 甲`（不并成复合名）

    这是 R35 通用规则的关键护栏 —— 若无此收窄，`非甲` 会被静默并成标识符，
    把 `not 甲` 表达式变成 NameError。"""
    t = toks('设 甲 为 1\n设 y 为 非甲')
    assert ('KEYWORD', '非') in t, t
    assert ('IDENTIFIER', '甲') in t, t
    assert not any(v == '非甲' for _, v in t), t


def test_undeclared_tail_still_merges():
    """余部**未**声明时 `非X` 恒为复合名（非空/非法/非零… 语料惯例）"""
    for w in ('非空', '非法', '非零', '非值', '非空块'):
        assert ('IDENTIFIER', w) in toks('设 x 为 ' + w), w


# === 5. 保留 2 条真护栏的保护语义 ===

def test_mo_is_real_modulo_operator():
    """保留理由①：`模` 是真取模运算符 —— `甲模乙` 必须切出 模"""
    t = toks('甲模乙')
    assert ('KEYWORD', '模') in t
    assert ('IDENTIFIER', '甲') in t and ('IDENTIFIER', '乙') in t


def test_spaced_mo_operator_unaffected():
    """`甲 模 乙`（带空格）取模运算不受影响"""
    assert ('KEYWORD', '模') in toks('设 x 为 甲 模 乙')


def test_merge_whole_zhengli_whole():
    """整理模型消息 整词（MERGE_WHOLE 兜底生效）"""
    assert ('IDENTIFIER', '整理模型消息') in toks('设 x 为 整理模型消息')
    assert ('IDENTIFIER', '整理模型消息') in toks('设 x 为 取(整理模型消息)')


def test_merge_whole_record_type_whole():
    """记录类型 整词（MERGE_WHOLE 兜底生效）"""
    assert ('IDENTIFIER', '记录类型') in toks('设 x 为 记录类型')


def test_other_x_type_still_split():
    """保留理由②：`X类型` 与 记录类型 结构不可分，故其余 X类型 仍按类型切分"""
    for w in ('数类型', '内容类型', '分类内容类型', '注册事件类型'):
        t = toks('设 x 为 ' + w)
        assert ('KEYWORD', '类型') in t, w
        assert not any(v == w for _, v in t), w


# === 6. 联动保护表断言 ===

def test_never_split_still_zero():
    """_P0A_NEVER_SPLIT 仍为 0（R33 清零）"""
    assert len(_lx.Lexer._P0A_NEVER_SPLIT) == 0


def test_cs_table_still_zero():
    """CS 表仍为 0（R28 清零）"""
    assert len(_lx._COMPOUND_SAFE_SINGLE_KEYWORDS) == 0


def test_ccw_table_still_zero():
    """CCW 表仍为 0（R30 清零）。COMMON_COMPOUND_WORDS 是**模块级**常量。"""
    assert len(_lx.COMMON_COMPOUND_WORDS) == 0


def test_hm_now_25():
    """HM：R26 设 22 → R33 后 25（步/至/到 进入）"""
    assert len(_lx._P0A_HEAD_MERGE_SINGLE) == 25


def test_trailing_class_F_now_46():
    """F（_TRAILING_ALIAS_CLASS）：R25 设 43 → R33 后 46"""
    assert len(_lx.Lexer._TRAILING_ALIAS_CLASS) == 46


def test_head_split_single_now_39():
    """词首切分排除集：R26 设 42 → R33 后 39（步/至/到 移出）"""
    assert len(_lx._P0A_HEAD_SPLIT_SINGLE) == 39


def test_dual_still_8():
    """DUAL 表仍为 8 字"""
    assert len(_lx._P0A_HEAD_MERGE_DUAL) == 8


def test_embed_still_3():
    """_EMBED 仍为 3 条（R31 确认为真护栏）"""
    assert len(_lx._EMBED_MAX_MATCH_KEYWORDS) == 3


def test_operator_verbs_still_19():
    """OPERATOR_VERBS 仍为 19 条（R32 确认为真护栏）"""
    assert len(_lx.OPERATOR_VERBS) == 19


def test_hard_stmt_unchanged():
    """_P0A_HARD_STMT 未因 R35 改变（仍含 类型/等待/捕获）"""
    assert _lx.Lexer._P0A_HARD_STMT == frozenset(
        {'如果', '那么', '否则', '否则如果', '段落', '函数', '类型', '捕获', '等待'})


def test_head_merge_subset_of_F():
    """不变量：HM ⊆ F（词首并入类别 ⊆ 词尾并入类别）"""
    assert _lx._P0A_HEAD_MERGE_SINGLE <= set(_lx.Lexer._TRAILING_ALIAS_CLASS)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
