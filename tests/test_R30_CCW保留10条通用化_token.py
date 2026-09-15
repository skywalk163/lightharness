"""
test_R30_CCW保留10条通用化_token.py —— 第30轮 CCW 10→0清零 token层断言

覆盖：
1. CCW表最终条数断言（0条，清零）
2. 原10条CCW条目通用化后的保护语义（整词成IDENTIFIER）
3. 关键字独立使用不受影响
4. 联动保护表断言（CS=0、HM扩展、DUAL=8等）
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'light-merge', 'src'))
import lexer as _lx

L = _lx.Lexer()

def tok(src):
    return [t.value for t in L.tokenize(src)]

# === 1. CCW表最终条数断言（清零）===

def test_ccw_table_is_zero():
    """R30：CCW 10→0清零（保留10条全部通用化）"""
    assert len(_lx.COMMON_COMPOUND_WORDS) == 0

# === 2. 原10条CCW条目通用化后的保护语义 ===

# 位运算符4条
def test_bitwise_and_generalized():
    """位与：通用化后整词成IDENTIFIER"""
    t = tok('设 r1 为 位与(3, 1)')
    assert '位与' in t

def test_bitwise_xor_generalized():
    """位异或：通用化后整词成IDENTIFIER"""
    t = tok('设 r2 为 位异或(3, 1)')
    assert '位异或' in t

def test_bitwise_or_generalized():
    """位或：通用化后整词成IDENTIFIER"""
    t = tok('设 r3 为 位或(3, 1)')
    assert '位或' in t

def test_bitwise_not_generalized():
    """位非：通用化后整词成IDENTIFIER"""
    t = tok('设 r4 为 位非(3)')
    assert '位非' in t

# 应当/除非
def test_yingdang_generalized():
    """应当：通用化后整词成IDENTIFIER"""
    t = tok('如果 应当 那么:')
    assert '应当' in t

def test_chufei_generalized():
    """除非：通用化后整词成IDENTIFIER"""
    t = tok('设 r5 为 除非(条件)')
    assert '除非' in t

# 零除错误/幂次/记录类型
def test_zero_division_error_generalized():
    """零除错误：通用化后整词成IDENTIFIER"""
    t = tok('捕获 零除错误:')
    assert '零除错误' in t

def test_mici_generalized():
    """幂次：通用化后整词成IDENTIFIER"""
    t = tok('设 r6 为 幂次(2, 10)')
    assert '幂次' in t

def test_jiluleixing_generalized():
    """记录类型：通用化后整词成IDENTIFIER"""
    t = tok('设 r7 为 记录类型(用户)')
    assert '记录类型' in t

# 测试_生成问候语
def test_test_generate_greeting_generalized():
    """测试_生成问候语：ASCII下划线+Han粘连通用化后整词成IDENTIFIER"""
    t = tok('返回 测试_生成问候语(1)')
    assert '测试_生成问候语' in t

# === 3. 关键字独立使用不受影响 ===

def test_dang_keyword_independent():
    """当：作为循环关键字独立使用不受影响"""
    t = tok('当 x > 0:')
    assert '当' in t

def test_fei_keyword_independent():
    """非：作为逻辑关键字独立使用不受影响"""
    t = tok('非 真')
    assert '非' in t

def test_wei_keyword_independent():
    """位：作为关键字独立使用不受影响"""
    t = tok('位 为 1')
    assert '位' in t

def test_ling_number_independent():
    """零：作为数字独立使用不受影响"""
    t = tok('零 个')
    assert 0 in t or '零' in t

# === 4. 联动保护表断言 ===

def test_cs_table_still_zero():
    """CS表仍为0（R28清零，R30不受影响）"""
    assert len(_lx._COMPOUND_SAFE_SINGLE_KEYWORDS) == 0

def test_dual_table_still_8():
    """DUAL表仍为8字（R27设定，R30不受影响）"""
    assert len(_lx._P0A_HEAD_MERGE_DUAL) == 8

def test_tail_cut_table_still_1():
    """TAIL_CUT表仍为1字（列，R28设定，R30不受影响）"""
    assert _lx._P0A_TAIL_CUT_SINGLE == frozenset({'列'})

def test_trailing_alias_class_still_43():
    """F表仍为43字（R25设定，R30不受影响）"""
    assert len(_lx.Lexer._TRAILING_ALIAS_CLASS) == 43

if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
