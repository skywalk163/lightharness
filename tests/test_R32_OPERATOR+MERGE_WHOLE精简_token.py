"""
test_R32_OPERATOR+MERGE_WHOLE精简_token.py —— 第32轮 token层断言

覆盖：
1. OPERATOR_VERBS维持19条（全部保留为真护栏）
2. _P0A_MERGE_WHOLE从10→3条（删除7条，保留3条）
3. 已删除条目的token序列不变（零回归验证）
4. 保留条目的保护语义
5. 联动保护表断言
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'light-merge', 'src'))
import lexer as _lx

L = _lx.Lexer()

def tok(src):
    return [t.value for t in L.tokenize(src)]

# === 1. OPERATOR_VERBS维持19条断言 ===

def test_operator_verbs_still_19():
    """R32：OPERATOR_VERBS维持19条（全部保留为真护栏）"""
    assert len(_lx.OPERATOR_VERBS) == 19

def test_operator_verbs_retained_entries():
    """R32：OPERATOR_VERBS保留19条清单"""
    expected = {'不大于', '不小于', '不等于', '乘', '乘以', '减', '减去',
                '加', '加上', '包含', '大于', '大于等于', '小于', '小于等于',
                '幂', '模', '等于', '除', '除以'}
    assert set(_lx.OPERATOR_VERBS) == expected

# === 2. _P0A_MERGE_WHOLE从10→3→2条断言 ===

def test_merge_whole_now_2():
    """R32：10→3；R35：3→2（非空块 由通用规则 _P0A_UNARY_PREFIX_KW 接住后移除）"""
    assert len(L._P0A_MERGE_WHOLE) == 2

def test_merge_whole_retained_entries():
    """R35 更新：保留 2 条清单（整理模型消息 / 记录类型）

    R35 移除 非空块 —— 一元前缀运算符通用规则（无空格 `非X` 恒为复合名，
    仅当余部是已声明名字时才是 `not X` 表达式）三重判据全通过后接住。
    保留的 2 条经实证为**真护栏、不可通用化**（详见 _task1/_task3_R35_*.md）。"""
    assert set(L._P0A_MERGE_WHOLE) == {'整理模型消息', '记录类型'}

def test_merge_whole_r35_removed_entry():
    """R35：非空块 已移除（由通用规则接住，非删除语义）"""
    assert '非空块' not in L._P0A_MERGE_WHOLE
    # 且通用规则确实生效：无空格 `非空块` 整词成 IDENTIFIER
    assert '非空块' in tok('设 x 为 非空块')

def test_merge_whole_deleted_entries():
    """R32：_P0A_MERGE_WHOLE已删除7条"""
    deleted = {'导出事件表', '退出码', '接收参数', '外部命令', '排序依据', '输出块表', '返回码'}
    for entry in deleted:
        assert entry not in L._P0A_MERGE_WHOLE

# === 3. 已删除条目的token序列不变（零回归验证） ===

def test_deleted_export_event_table_still_merged():
    """已删除：导出事件表仍整词成IDENTIFIER（由其他规则覆盖）"""
    t = tok('设 x 为 导出事件表')
    assert '导出事件表' in t

def test_deleted_exit_code_still_merged():
    """已删除：退出码仍整词成IDENTIFIER"""
    t = tok('设 x 为 退出码')
    assert '退出码' in t

def test_deleted_receive_params_still_merged():
    """已删除：接收参数仍整词成IDENTIFIER"""
    t = tok('设 x 为 接收参数')
    assert '接收参数' in t

def test_deleted_external_command_still_merged():
    """已删除：外部命令仍整词成IDENTIFIER"""
    t = tok('设 x 为 外部命令')
    assert '外部命令' in t

def test_deleted_sort_key_still_merged():
    """已删除：排序依据仍整词成IDENTIFIER"""
    t = tok('设 x 为 排序依据')
    assert '排序依据' in t

def test_deleted_output_block_table_still_merged():
    """已删除：输出块表仍整词成IDENTIFIER"""
    t = tok('设 x 为 输出块表')
    assert '输出块表' in t

def test_deleted_return_code_still_merged():
    """已删除：返回码仍整词成IDENTIFIER"""
    t = tok('设 x 为 返回码')
    assert '返回码' in t

# === 4. 保留条目的保护语义 ===

def test_retained_sort_model_messages_merged():
    """保留：整理模型消息整词成IDENTIFIER"""
    t = tok('设 x 为 整理模型消息')
    assert '整理模型消息' in t

def test_retained_record_type_merged():
    """保留：记录类型整词成IDENTIFIER（类型是硬语句关键字）"""
    t = tok('设 x 为 记录类型')
    assert '记录类型' in t

def test_retained_non_empty_block_merged():
    """保留：非空块整词成IDENTIFIER"""
    t = tok('设 x 为 非空块')
    assert '非空块' in t

# === 5. 联动保护表断言 ===

def test_cs_table_still_zero():
    """CS表仍为0（R28清零）"""
    assert len(_lx._COMPOUND_SAFE_SINGLE_KEYWORDS) == 0

def test_ccw_table_still_zero():
    """CCW表仍为0（R30清零）"""
    assert len(_lx.COMMON_COMPOUND_WORDS) == 0

def test_embed_table_still_3():
    """_EMBED表仍为3条（R31确认为真护栏）"""
    assert len(_lx._EMBED_MAX_MATCH_KEYWORDS) == 3

def test_dual_table_still_8():
    """DUAL表仍为8字"""
    assert len(_lx._P0A_HEAD_MERGE_DUAL) == 8

def test_tail_cut_table_still_1():
    """TAIL_CUT表仍为1字（列）"""
    assert _lx._P0A_TAIL_CUT_SINGLE == frozenset({'列'})

if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
