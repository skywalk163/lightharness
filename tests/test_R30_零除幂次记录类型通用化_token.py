"""
test_R30_零除幂次记录类型通用化_token.py —— R30 任务3 token层断言

三条 CCW 登记（零除错误 / 幂次 / 记录类型）通用化并从 CCW 移除后，逐条验证：
1. CCW 已清空这 3 条（10→1）
2. 三条整词仍成 IDENTIFIER（正向，含语句起始 / 调用 / 返回 三种语境）
3. 三条通用规则**非逐词登记**（同构未登记词形同被覆盖：零除法/一加一/一真一）
4. 规则收窄不越界（幂次 无括号形态、X类型 其他复合词、二字串数字+关键字）
5. 「零」作为数字使用完全不受影响（反向硬门槛：CHINESE_NUM 语义零漂移）
6. 联动保护表断言（HM 仍 22、DUAL 仍 8、MERGE_WHOLE 现为 7 条——R86-A 对齐 R58 口径）

全语料 token 零变化证据：lightharness/_antirun_r30_t3_全量反跑.py
  HEAD(pre-R30, CCW=10) ←→ t12(任务1/2, CCW=4) ←→ 当前(+任务3, CCW=1)
  三口径 854 个 .light 文件 token 序列 sha256 全等，token 总数差 +0。
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'light-merge', 'src'))
import lexer as _lx

L = _lx.Lexer()

def tok(src):
    return [t.value for t in L.tokenize(src)]

def toks(src):
    return [(t.type.name, t.value) for t in L.tokenize(src)
            if t.type.name not in ('EOF', 'NEWLINE')]

# === 1. CCW 已移除 3 条 ===

def test_r30_removed_three():
    """R30 任务3：零除错误/幂次/记录类型 已移出 CCW"""
    assert not ({'零除错误', '幂次', '记录类型'} & _lx.COMMON_COMPOUND_WORDS)

def test_r30_ccw_left_at_most_one():
    """CCW 10→1（任务4 负责剩余的 测试_生成问候语）"""
    assert _lx.COMMON_COMPOUND_WORDS <= {'测试_生成问候语'}

# === 2. 正向：零除错误 整词成 IDENTIFIER ===

def test_zc_error_stmt_head():
    """语句起始：`捕获 零除错误:` → 零除错误 整词（不被 零=CHINESE_NUM 劈开）"""
    t = toks('捕获 零除错误:')
    assert ('KEYWORD', '捕获') in t
    assert ('IDENTIFIER', '零除错误') in t
    assert not any(k == 'CHINESE_NUM' for k, v in t), t

def test_zc_error_call():
    """调用语境：`返回 零除错误(1)` → 整词"""
    assert '零除错误' in tok('返回 零除错误(1)')

def test_zc_error_in_identifier():
    """嵌入更长短串：仍整体成标识符（不与 除 的 DUAL 词首并入冲突）"""
    t = tok('设 x 为 零除错误x')
    assert '零除错误x' in t

# === 3. 正向：幂次 整词成 IDENTIFIER ===

def test_mici_call_form():
    """调用语境（整串后紧跟 '('）：`设 r6 为 幂次(2, 10)` → 整词"""
    t = toks('设 r6 为 幂次(2, 10)')
    assert ('IDENTIFIER', '幂次') in t
    assert ('KEYWORD', '幂') not in t

def test_mici_call_return():
    """返回语句调用点：`返回 幂次(1)` → 整词（递归调用点同形态）"""
    assert '幂次' in tok('返回 幂次(1)')

# === 4. 正向：记录类型 整词成 IDENTIFIER ===

def test_record_type_call():
    """调用语境：`设 r7 为 记录类型(用户)` → 整词（不被关键字 类型 劈开）"""
    t = toks('设 r7 为 记录类型(用户)')
    assert ('IDENTIFIER', '记录类型') in t
    assert ('KEYWORD', '类型') not in t

def test_record_type_bare():
    """非调用语境同样整词：`返回 记录类型(1)` / `设 x 为 记录类型`"""
    assert '记录类型' in tok('返回 记录类型(1)')
    assert '记录类型' in tok('设 x 为 记录类型')

# === 5. 规则非逐词登记：同构未登记词形同被覆盖 ===

def test_num_head_merge_generalizes():
    """_r30_cn_num_head_merge 是类别推导，不认词：3 字整串且第二字 ∈ HM∪DUAL
    ⇒ 整词成标识符（语料 0 登记的 零除法 同被覆盖）。

    R58 任务1 收窄（light-merge 5d097a4c）：第三字是中文数字且整串闭合
    （len==3 或其后非汉字）⇒ 「数字+运算符+数字」算术三元式，词首数字
    独立成 CHINESE_NUM——一加一（三字闭合）→ 数字+加+数字；
    一真一（三字闭合）→ 数字+真一。零除法 第三字 非 数 字 ， 不 触 发 收 窄 ， 仍 整 词 。"""
    # 非闭合三元式：仍整体并入（类别推导不认词）
    t = toks('设 x 为 零除法')
    assert ('IDENTIFIER', '零除法') in t
    assert not any(k == 'CHINESE_NUM' for k, _ in t)
    # R58 收窄：闭合算术三元式不再吞成标识符
    t = toks('设 x 为 一加一')
    assert ('CHINESE_NUM', 1) in t and ('KEYWORD', '加') in t, t
    assert not any(v == '一加一' for _, v in t), t
    t = toks('设 x 为 一真一')
    assert any(k == 'CHINESE_NUM' for k, _ in t), t
    assert not any(v == '一真一' for _, v in t), t

# === 6. 收窄不越界：无括号形态保持既有切分 ===

def test_mici_no_paren_keeps_split():
    """幂次 无括号形态（语料 幂集/幂结果/幂值/幂运算/幂等）保持 幂=KEYWORD 切分"""
    for w in ('幂集', '幂结果', '幂值', '幂运算', '幂等'):
        t = toks('设 x 为 ' + w)
        assert ('KEYWORD', '幂') in t, w
        assert not any(k == 'IDENTIFIER' and v == w for k, v in t), w

def test_mici_bare_not_merged():
    """裸 `设 x 为 幂次`（无 '('）不触发 skip_verb，仍切成 幂 + 次"""
    t = toks('设 x 为 幂次')
    assert ('KEYWORD', '幂') in t and ('IDENTIFIER', '次') in t

# === 7. 收窄不越界：X类型 其他复合词不受 MERGE_WHOLE 影响 ===

def test_other_x_lx_types_keeps_split():
    """_P0A_MERGE_WHOLE 是精确整串口径：数类型/内容类型/分类内容类型/注册事件类型
    的 类型 仍按后缀切分关键字行为落出 KEYWORD"""
    for head, w in (('数', '数类型'), ('内容', '内容类型'),
                    ('分类内容', '分类内容类型'), ('注册事件', '注册事件类型')):
        t = toks('设 x 为 ' + w)
        assert ('KEYWORD', '类型') in t, w
        assert not any(k == 'IDENTIFIER' and v == w for k, v in t), w

# === 8. 反向硬门槛：「零」作数字使用不受影响 ===

def test_zero_still_chinese_num():
    """`设 x 为 零` → CHINESE_NUM(0)（词首并入规则不得吞掉数字语义）"""
    assert any(k == 'CHINESE_NUM' and v == 0 for k, v in toks('设 x 为 零'))

def test_zero_in_arithmetic():
    """`零 + 1` → CHINESE_NUM(0) + PLUS（数字参与运算）"""
    t = toks('设 x 为 零 + 1')
    assert ('CHINESE_NUM', 0) in t and ('PLUS', '+') in t

def test_zero_decimal_and_composite():
    """中文数字解析不受影响：零点一 → 0.1，一百零一 → 101，一千零一 → 1001"""
    for src, val in (('设 x 为 零点一', 0.1),
                     ('设 x 为 一百零一', 101),
                     ('设 x 为 一千零一', 1001)):
        t = toks(src)
        assert ('CHINESE_NUM', val) in t, src

def test_two_char_num_plus_keyword_keeps_split():
    """二字串（数字 + 关键字）语料钉住形态全部保持 CHINESE_NUM + KEYWORD"""
    for w, kw in (('零导入', '导入'), ('零匹配', '匹配'), ('零非', '非'),
                  ('零列', '列'), ('零除', '除'), ('零真', '真'), ('一加', '加'),
                  ('三段', '段'), ('三类', '类'),
                  ('一并', '并'), ('一真', '真'), ('一等', '等'), ('一假', '假')):
        t = toks('设 x 为 ' + w)
        assert any(k == 'CHINESE_NUM' for k, _ in t), w
        assert ('KEYWORD', kw) in t, w
        assert not any(k == 'IDENTIFIER' and v == w for k, v in t), w

# === 9. 联动保护表断言 ===

def test_hm_now_25():
    """HM 表：R26 设 22 字 → R33 清零 _P0A_NEVER_SPLIT 后扩至 25 字

    R33 移除 NEVER_SPLIT 的 步/至/到 三字，它们随之进入 F(_TRAILING_ALIAS_CLASS)
    与 HM(_P0A_HEAD_MERGE_SINGLE)；模 因已在 OPERATOR_VERBS 被排除，不进 HM。
    全语料 857 文件 token 零变化（见 _antirun_r33_final_zeroregress.json）。"""
    assert len(_lx._P0A_HEAD_MERGE_SINGLE) == 25

def test_dual_still_8():
    """DUAL 表仍为 8 字（乘减加除模真空到，R27 设定，任务3 未增删）"""
    assert _lx._P0A_HEAD_MERGE_DUAL == frozenset(
        {'乘', '减', '加', '除', '模', '真', '空', '到'})

def test_merge_whole_has_record_type():
    """R58 更新：MERGE_WHOLE 当前 7 条（R32 保留 2 + R58 恢复 5）。

    R32 任务3/4：10→3，移除 7 条（导出事件表/退出码/接收参数/外部命令/排序依据/
    输出块表/返回码），整串语义由设名预扫描、函数调用语境整串合并、成员访问规则接住。
    R35：3→2，非空块 由一元前缀运算符通用规则接住后移除。
    R58（light-merge 5d097a4c）：2→7，恢复 导出事件表/返回码/接收参数/非空块/
    外部命令 —— R32/R35 撤条只证了语料语境可逆，§8.4 要求的裸串语句起始位
    仍需精确整串口径承接；退出码/排序依据/输出块表 三条裸串已由通用规则接住，
    维持删除态。"""
    mw = _lx.Lexer._P0A_MERGE_WHOLE
    assert mw == frozenset({
        '整理模型消息', '记录类型',
        '导出事件表', '返回码', '接收参数', '非空块', '外部命令'})
    assert '退出码' not in mw and '排序依据' not in mw and '输出块表' not in mw

def test_num_head_class_is_derived():
    """数字词首并入类别由 HM ∪ DUAL 推导，不独立登记"""
    assert _lx._R30_NUM_HEAD_MERGE_CLASS == (_lx._P0A_HEAD_MERGE_SINGLE
                                             | _lx._P0A_HEAD_MERGE_DUAL)

def test_predicates():
    """判据函数自洽：整串 ≥3 字 ∧ 词首数字 ∧ 第二字 ∈ HM∪DUAL
    （R58 收窄：第三字为数字且整串闭合 ⇒ False，算术三元式不吞词）"""
    f = _lx._r30_cn_num_head_merge
    assert f('零除错误') and f('零除法')
    assert not f('零个') and not f('零除') and not f('零真') and not f('一加')
    assert not f('三段') and not f('零导入') and not f('零匹配')
    assert not f('零点一') and not f('一千零一')   # 第二字为数字 → 不触发
    assert not f('一加一') and not f('一真一')     # R58 收窄：三字闭合三元式
    assert not f('') and not f('零') and not f('除错误')


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
