"""
test_R33_NEVER_SPLIT精简_token.py —— 第33轮 token层断言

覆盖：
1. _P0A_NEVER_SPLIT从4→0条（清零）
2. 已删除4字的token序列不变（零回归验证）
3. 数字范围运算符识别不变（1至10/1到10步2）
4. 复合名整词不变（模型/模块/同步/乃至/遇到）
5. DUAL表中的"到"仍生效
6. 联动保护表断言
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'light-merge', 'src'))
import lexer as _lx

L = _lx.Lexer()

def tok(src):
    return [t.value for t in L.tokenize(src)]

# === 1. _P0A_NEVER_SPLIT从4→0条断言 ===

def test_never_split_now_zero():
    """R33：_P0A_NEVER_SPLIT从4→0条（清零）"""
    assert len(L._P0A_NEVER_SPLIT) == 0

def test_never_split_deleted_entries():
    """R33：_P0A_NEVER_SPLIT已删除4字"""
    deleted = {'模', '步', '至', '到'}
    for entry in deleted:
        assert entry not in L._P0A_NEVER_SPLIT

# === 2. 已删除4字的token序列不变（零回归验证） ===

def test_deleted_mo_compound_still_merged():
    """已删除：模-模型仍整词成IDENTIFIER（由OPERATOR_VERBS/DUAL兜底）"""
    t = tok('设 x 为 模型')
    assert '模型' in t

def test_deleted_mo_module_still_merged():
    """已删除：模-模块仍整词成IDENTIFIER"""
    t = tok('设 x 为 模块')
    assert '模块' in t

def test_deleted_mo_mode_still_merged():
    """已删除：模-模式仍整词成IDENTIFIER"""
    t = tok('设 x 为 模式')
    assert '模式' in t

def test_deleted_bu_sync_still_merged():
    """已删除：步-同步仍整词成IDENTIFIER"""
    t = tok('设 x 为 同步')
    assert '同步' in t

def test_deleted_zhi_even_still_merged():
    """已删除：至-乃至仍整词成IDENTIFIER"""
    t = tok('设 x 为 乃至')
    assert '乃至' in t

def test_deleted_dao_encounter_still_merged():
    """已删除：到-遇到仍整词成IDENTIFIER"""
    t = tok('设 x 为 遇到')
    assert '遇到' in t

# === 3. 数字范围运算符识别不变 ===

def test_range_1_to_10_still_recognized():
    """数字范围：1到10仍正确识别"""
    t = tok('从1到10')
    assert '到' in t
    assert 1 in t
    assert 10 in t

def test_range_1_zhi_10_still_recognized():
    """数字范围：1至10仍正确识别"""
    t = tok('从1至10')
    assert '至' in t
    assert 1 in t
    assert 10 in t

def test_range_1_dao_10_bu_2_still_recognized():
    """数字范围：1到10步2仍正确识别"""
    t = tok('从1到10步2')
    assert '到' in t
    assert '步' in t
    assert 1 in t
    assert 10 in t
    assert 2 in t

# === 4. 取模运算符识别不变 ===

def test_mod_operator_still_recognized():
    """取模运算符：甲 模 乙仍正确识别"""
    t = tok('甲 模 乙')
    assert '模' in t

# === 5. DUAL表中的"到"仍生效 ===

def test_dual_still_has_dao():
    """DUAL表仍含"到"（8字之一）"""
    assert '到' in _lx._P0A_HEAD_MERGE_DUAL

def test_dual_dao_head_merge_still_works():
    """DUAL"到"词首并入仍生效（到位）"""
    t = tok('设 x 为 到位')
    assert '到位' in t

# === 6. 联动保护表断言 ===

def test_cs_table_still_zero():
    """CS表仍为0（R28清零）"""
    assert len(_lx._COMPOUND_SAFE_SINGLE_KEYWORDS) == 0

def test_ccw_table_still_zero():
    """CCW表仍为0（R30清零）"""
    assert len(_lx.COMMON_COMPOUND_WORDS) == 0

def test_embed_table_still_3():
    """_EMBED表仍为3条（R31确认为真护栏）"""
    assert len(_lx._EMBED_MAX_MATCH_KEYWORDS) == 3

def test_operator_verbs_still_19():
    """OPERATOR_VERBS仍为19条（R32确认为真护栏）"""
    assert len(_lx.OPERATOR_VERBS) == 19

def test_merge_whole_now_2():
    """_P0A_MERGE_WHOLE：R32 精简为 3 条 → R35 精简为 2 条（移除 非空块）"""
    assert len(L._P0A_MERGE_WHOLE) == 2

def test_hm_now_25():
    """HM 词首并入类别：R26 设 22 字 → R33 清零 NEVER_SPLIT 后扩至 25 字
    （步/至/到 进入 F/HM；模 经 OPERATOR_VERBS 排除不进）"""
    assert len(_lx._P0A_HEAD_MERGE_SINGLE) == 25

def test_dual_table_still_8():
    """DUAL表仍为8字"""
    assert len(_lx._P0A_HEAD_MERGE_DUAL) == 8

def test_tail_cut_table_still_1():
    """TAIL_CUT表仍为1字（列）"""
    assert _lx._P0A_TAIL_CUT_SINGLE == frozenset({'列'})

if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
