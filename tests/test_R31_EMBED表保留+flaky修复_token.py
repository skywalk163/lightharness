"""
test_R31_EMBED表保留+flaky修复_token.py —— 第31轮 token层断言

覆盖：
1. _EMBED表维持3条（为/返回/尝试，全部保留为真护栏）
2. _EMBED表3条的保护语义（嵌入式扫描触发）
3. test_审批.light flaky修复验证（time.monotonic）
4. 联动保护表断言
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'light-merge', 'src'))
import lexer as _lx

L = _lx.Lexer()

def tok(src):
    return [t.value for t in L.tokenize(src)]

# === 1. _EMBED表维持3条断言 ===

def test_embed_table_still_3():
    """R31：_EMBED表维持3条（为/返回/尝试全部保留为真护栏）"""
    assert len(_lx._EMBED_MAX_MATCH_KEYWORDS) == 3

def test_embed_retained_entries():
    """R31：_EMBED保留3条清单"""
    assert set(_lx._EMBED_MAX_MATCH_KEYWORDS) == {'为', '返回', '尝试'}

# === 2. _EMBED表3条的保护语义 ===

def test_wei_embedded_scan_triggered():
    """为：嵌入式扫描触发，断言为真(1)整词成函数名"""
    t = tok('断言为真(1)')
    assert '断言为真' in t

def test_wei_assignment_tail_split():
    """为：赋值尾巴切分，设甲为空 → 甲+为+空"""
    t = tok('设 甲为空')
    assert '甲' in t
    assert '为' in t
    assert '空' in t

def test_wei_behavior_merged():
    """为：行为整词成IDENTIFIER"""
    t = tok('设 x 为 行为')
    assert '行为' in t

def test_fanhui_embedded_scan_triggered():
    """返回：嵌入式扫描触发，返回表整词成IDENTIFIER"""
    t = tok('设 x 为 返回表')
    assert '返回表' in t

def test_fanhui_return_value_merged():
    """返回：返回值整词成IDENTIFIER"""
    t = tok('设 x 为 返回值')
    assert '返回值' in t

def test_changshi_embedded_scan_triggered():
    """尝试：嵌入式扫描触发，尝试记录整词成IDENTIFIER"""
    t = tok('设 x 为 尝试记录')
    assert '尝试记录' in t

# === 3. test_审批.light flaky修复验证 ===

def test_test_approval_uses_monotonic():
    """test_审批.light使用time.monotonic()而非time.time()"""
    path = os.path.join(os.path.dirname(__file__), '..', 'examples', 'test_审批.light')
    src = open(path, encoding='utf-8').read()
    assert 'time.monotonic()' in src
    # 耗时计算不应使用time.time()
    lines = src.split('\n')
    for i, line in enumerate(lines, 1):
        if '耗时' in line and 'time.time()' in line:
            raise AssertionError(f'第{i}行仍使用time.time()计算耗时')

# === 4. 联动保护表断言 ===

def test_cs_table_still_zero():
    """CS表仍为0（R28清零）"""
    assert len(_lx._COMPOUND_SAFE_SINGLE_KEYWORDS) == 0

def test_ccw_table_still_zero():
    """CCW表仍为0（R30清零）"""
    assert len(_lx.COMMON_COMPOUND_WORDS) == 0

def test_dual_table_still_8():
    """DUAL表仍为8字"""
    assert len(_lx._P0A_HEAD_MERGE_DUAL) == 8

def test_tail_cut_table_still_1():
    """TAIL_CUT表仍为1字（列）"""
    assert _lx._P0A_TAIL_CUT_SINGLE == frozenset({'列'})

if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
