"""
test_R29_CCW表分批精简_token.py —— 第29轮 CCW 37→10精简 token层断言

覆盖：
1. CCW表最终条数断言（10条）
2. 保留10条真护栏的保护语义（撤后token变化，保留后整词）
3. 删除27条的token序列不变（撤后仍整词成IDENTIFIER）
4. 联动保护表断言（CS表仍为0、HM仍为22、DUAL仍为8）
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'light-merge', 'src'))
import lexer as _lx

L = _lx.Lexer()

def tok(src):
    return [t.value for t in L.tokenize(src)]

# === 1. CCW表最终条数断言 ===

def test_ccw_table_is_10():
    """R29：CCW 37→10（删27条，保留10条真护栏）

    R30 更新（任务1/2/3）：CCW 10→1。R29 保留的 10 条中已有 9 条通用化移出：
      · 任务1/2：位与/位异或/位或/位非/应当/除非 → `_P0A_HEAD_MERGE_PREFIX`
      · 任务3  ：零除错误/幂次/记录类型 → `_r30_cn_num_head_merge` / skip_verb /
                 `_P0A_MERGE_WHOLE`
    现仅可能剩 `测试_生成问候语`（R30 任务4 负责），故上界判定。"""
    assert _lx.COMMON_COMPOUND_WORDS <= {'测试_生成问候语'}
    assert len(_lx.COMMON_COMPOUND_WORDS) <= 1

def test_ccw_retained_entries():
    """R29：保留10条真护栏清单

    R30 更新（任务1/2/3）：上述 10 条中 9 条已从 CCW 移除，但整词语义由通用规则
    接住 —— 逐条 token 断言见本文件下方 `*_retained()` 用例（未随表删而放宽）
    与 test_R30_零除幂次记录类型通用化_token.py。此处断言「9 条已清空」。"""
    gone = {'位与', '位异或', '位或', '位非', '应当', '除非',
            '零除错误', '幂次', '记录类型'}
    assert not (gone & _lx.COMMON_COMPOUND_WORDS)

# === 2. 保留10条真护栏的保护语义 ===

def test_bitwise_and_retained():
    """位与：保留后整词成IDENTIFIER"""
    t = tok('返回 位与(1)')
    assert '位与' in t

def test_bitwise_xor_retained():
    """位异或：保留后整词成IDENTIFIER"""
    t = tok('返回 位异或(1)')
    assert '位异或' in t

def test_bitwise_or_retained():
    """位或：保留后整词成IDENTIFIER"""
    t = tok('返回 位或(1)')
    assert '位或' in t

def test_bitwise_not_retained():
    """位非：保留后整词成IDENTIFIER"""
    t = tok('返回 位非(1)')
    assert '位非' in t

def test_zero_division_error_retained():
    """零除错误：保留后整词成IDENTIFIER"""
    t = tok('返回 零除错误(1)')
    assert '零除错误' in t

def test_yingdang_retained():
    """应当：保留后整词成IDENTIFIER（"当"关键字在词首劈开）"""
    t = tok('如果 应当 那么:')
    assert '应当' in t

def test_chufei_retained():
    """除非：保留后整词成IDENTIFIER（双侧关键字夹击）"""
    t = tok('返回 除非(1)')
    assert '除非' in t

def test_test_generate_greeting_retained():
    """测试_生成问候语：保留后整词成IDENTIFIER（ASCII下划线+Han粘连）"""
    t = tok('返回 测试_生成问候语(1)')
    assert '测试_生成问候语' in t

def test_mici_retained():
    """幂次：保留后整词成IDENTIFIER（被关键字"幂"劈开）"""
    t = tok('返回 幂次(1)')
    assert '幂次' in t

def test_jiluleixing_retained():
    """记录类型：保留后整词成IDENTIFIER（语料0命中但边界形态G3失败）"""
    t = tok('返回 记录类型(1)')
    assert '记录类型' in t

# === 3. 删除27条的token序列不变（撤后仍整词成IDENTIFIER）===

# A批删除5条
def test_async_write_file_deleted():
    """异步写入文件：已删，仍整词成IDENTIFIER（词法通用机制覆盖）"""
    t = tok('设 异步写入文件 为 真')
    assert '异步写入文件' in t

def test_async_sleep_deleted():
    """异步睡眠：已删，仍整词成IDENTIFIER"""
    t = tok('设 异步睡眠 为 真')
    assert '异步睡眠' in t

def test_async_read_file_deleted():
    """异步读取文件：已删，仍整词成IDENTIFIER"""
    t = tok('设 异步读取文件 为 真')
    assert '异步读取文件' in t

def test_async_append_file_deleted():
    """异步追加文件：已删，仍整词成IDENTIFIER"""
    t = tok('设 异步追加文件 为 真')
    assert '异步追加文件' in t

def test_concurrent_wait_deleted():
    """并发等待：已删，仍整词成IDENTIFIER"""
    t = tok('设 并发等待 为 真')
    assert '并发等待' in t

# B批删除9条（抽样5条）
def test_import_error_deleted():
    """导入错误：已删，仍整词成IDENTIFIER"""
    t = tok('设 导入错误 为 真')
    assert '导入错误' in t

def test_type_error_deleted():
    """类型错误：已删，仍整词成IDENTIFIER"""
    t = tok('设 类型错误 为 真')
    assert '类型错误' in t

def test_shezhizhen_deleted():
    """设指针：已删，仍整词成IDENTIFIER"""
    t = tok('设 设指针 为 真')
    assert '设指针' in t

def test_shezhi_deleted():
    """设置：已删，仍整词成IDENTIFIER"""
    t = tok('设 设置 为 真')
    assert '设置' in t

def test_dijiguanbi_deleted():
    """低级关闭：已删，仍整词成IDENTIFIER"""
    t = tok('设 低级关闭 为 真')
    assert '低级关闭' in t

# C批删除7条（抽样5条）
def test_shengchengfenxi_deleted():
    """生成分析：已删，仍整词成IDENTIFIER"""
    t = tok('设 生成分析 为 真')
    assert '生成分析' in t

def test_zuizhongdaan_deleted():
    """最终答案：已删，仍整词成IDENTIFIER"""
    t = tok('设 最终答案 为 真')
    assert '最终答案' in t

def test_dangran_deleted():
    """当然：已删，仍整词成IDENTIFIER（"当"关键字上下文规则覆盖）"""
    t = tok('设 当然 为 真')
    assert '当然' in t

def test_dangqian_deleted():
    """当前：已删，仍整词成IDENTIFIER"""
    t = tok('设 当前 为 真')
    assert '当前' in t

def test_kaiqitiaoshi_deleted():
    """开启调试：已删，仍整词成IDENTIFIER"""
    t = tok('设 开启调试 为 真')
    assert '开启调试' in t

# D批删除6条（抽样4条）
def test_hanshuduixiang_deleted():
    """函数对象：已删，仍整词成IDENTIFIER"""
    t = tok('设 函数对象 为 真')
    assert '函数对象' in t

def test_changliangshijianbijiao_deleted():
    """常量时间比较：已删，仍整词成IDENTIFIER"""
    t = tok('设 常量时间比较 为 真')
    assert '常量时间比较' in t

def test_zhengzepipei_deleted():
    """正则匹配：已删，仍整词成IDENTIFIER"""
    t = tok('设 正则匹配 为 真')
    assert '正则匹配' in t

def test_huanjingmeiju_deleted():
    """环境枚举：已删，仍整词成IDENTIFIER"""
    t = tok('设 环境枚举 为 真')
    assert '环境枚举' in t

# === 4. 联动保护表断言 ===

def test_cs_table_still_zero():
    """CS表仍为0（R28清零，R29不受影响）"""
    assert len(_lx._COMPOUND_SAFE_SINGLE_KEYWORDS) == 0

def test_hm_table_still_22():
    """HM表仍为22字（R26设定，R29不受影响）"""
    assert len(_lx._P0A_HEAD_MERGE_SINGLE) == 22

def test_dual_table_still_8():
    """DUAL表仍为8字（R27设定，R29不受影响）"""
    assert len(_lx._P0A_HEAD_MERGE_DUAL) == 8

def test_tail_cut_table_still_1():
    """TAIL_CUT表仍为1字（列，R28设定，R29不受影响）"""
    assert _lx._P0A_TAIL_CUT_SINGLE == frozenset({'列'})

if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
