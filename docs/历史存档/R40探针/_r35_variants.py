# -*- coding: utf-8 -*-
"""R35 变体定义：源文本补丁列表。被 _r35_g1_engine.py 导入。

通用规则候选：
  GR-1  嵌入扫描运算符分支口径统一到 _P0A_OP
        （OPERATOR_VERBS 中已被 _P0A_OP 剔除的「非真运算符」字 —— 模/步/至/到 ——
         不参与词中运算符切分，落到 P0-A 单字并入判据）→ 覆盖 整理模型消息
  GR-2  R21 闸门3 对「一元前缀运算符」开例外（非）→ 覆盖 非空块
  GR-3  R21 分支补「词尾多字硬语句关键字」接受路径 → 覆盖 记录类型
"""

MW_BODY = "        '整理模型消息', '非空块',\n        '记录类型',\n"
MW_EMPTY = ("        # R35: 三条全撤\n",)

# ---- GR-1：三处 `sub_len == 1 and sub_kw in OPERATOR_VERBS` 收窄为
#            OPERATOR_VERBS ∩ _P0A_OP（剔除 模/步/至/到 四个非真运算符）----
GR1 = [
    ("                        if sub_len == 1 and sub_kw in OPERATOR_VERBS:",
     "                        if (sub_len == 1 and sub_kw in OPERATOR_VERBS\n"
     "                                and sub_kw in self._P0A_OP):"),
    ("                            elif sub_len == 1 and sub_kw in OPERATOR_VERBS:",
     "                            elif (sub_len == 1 and sub_kw in OPERATOR_VERBS\n"
     "                                  and sub_kw in self._P0A_OP):"),
    ("                                elif sub_len == 1 and sub_kw in OPERATOR_VERBS:",
     "                                elif (sub_len == 1 and sub_kw in OPERATOR_VERBS\n"
     "                                      and sub_kw in self._P0A_OP):"),
]

# ---- GR-2：新增一元前缀运算符类别 + R21 闸门3 例外 ----
GR2 = [
    ("    _P0A_HARD_STMT = frozenset({'如果', '那么', '否则', '否则如果', '段落', "
     "'函数', '类型', '捕获', '等待'})",
     "    _P0A_HARD_STMT = frozenset({'如果', '那么', '否则', '否则如果', '段落', "
     "'函数', '类型', '捕获', '等待'})\n"
     "    # R35：一元前缀运算符（无空格 `非X` 恒为复合名，非 `not X` 表达式）\n"
     "    _P0A_UNARY_PREFIX_KW = frozenset({'非'})"),
    ("                            and _lead_kw not in _OPERATOR_KEYWORDS\n",
     "                            and _lead_kw not in (_OPERATOR_KEYWORDS\n"
     "                                                 - self._P0A_UNARY_PREFIX_KW)\n"),
]

# GR-2b = GR-2 + 收窄：一元前缀 `非` 的余部若是**已声明名字**则仍是操作数
#        （`非甲` = not 甲），保持运算符切分，不得并入复合名。
GR2B = [
    GR2[0],
    ("                            and _lead_kw not in _OPERATOR_KEYWORDS\n",
     "                            and _lead_kw not in (_OPERATOR_KEYWORDS\n"
     "                                                 - self._P0A_UNARY_PREFIX_KW)\n"
     "                            and (_lead_kw not in self._P0A_UNARY_PREFIX_KW\n"
     "                                 or full_identifier[_lead_len:] not in user_definitions)\n"),
]

# ---- GR-3：R21 分支补「词尾多字硬语句关键字」接受路径 ----
GR3_OLD = """                    _lead_kw, _lead_len = _match_kw(source, pos)
"""
GR3_NEW = """                    _lead_kw, _lead_len = _match_kw(source, pos)
                    # R35 通用化：切分点也可能落在**词尾多字硬语句关键字**
                    # （_P0A_SUFFIX_SPLIT_KW，如 记录类型 的 类型）。词首非关键字时
                    # 「词首关键字」三道闸门无从生效，故补一条词尾接受路径：
                    # 整串非关键字、词尾恰为硬语句关键字、词首非关键字 ⇒ 整体并入。
                    _tail_kw = None
                    if not _lead_kw:
                        for _tl in range(min(4, len(full_identifier) - 1), 1, -1):
                            _cand = full_identifier[len(full_identifier) - _tl:]
                            if _cand in self._P0A_SUFFIX_SPLIT_KW:
                                _tail_kw = _cand
                                break
"""
GR3_COND_OLD = """                    if (_lead_kw and 0 < _lead_len < len(full_identifier)
                            and _lead_kw not in _OPERATOR_KEYWORDS
                            and not (any(_c in _op_hints for _c in full_identifier)
                                     and self._p0a_contains_sep(source, pos, len(full_identifier)))):"""
GR3_COND_NEW = """                    if (((_lead_kw and 0 < _lead_len < len(full_identifier)
                           and _lead_kw not in _OPERATOR_KEYWORDS)
                          or _tail_kw is not None)
                            and not (any(_c in _op_hints for _c in full_identifier)
                                     and self._p0a_contains_sep(source, pos, len(full_identifier)))):"""
GR3 = [(GR3_OLD, GR3_NEW), (GR3_COND_OLD, GR3_COND_NEW)]

# ---- GR-1c（收窄）：单字运算符动词两侧汉字段长度均 ≥2 ⇒ 构词成分，不按运算符切分。
#      依据：运算符表达式形态恒为「单字操作数 + 运算符 + 单字操作数」（甲加乙/甲模乙），
#      两侧均为 ≥2 字复合词段时该字是构词成分（整理+模+型消息）。 ----
_GR1C_PROBE = """                            # R35 GR-1c：两侧汉字段均 >=2 字 ⇒ 构词成分，不按运算符切分
                            if (not skip_kw
                                    and scan_pos >= 2
                                    and len(full_identifier) - (scan_pos + sub_len) >= 2
                                    and full_identifier.isalpha()):
                                skip_kw = True
"""
_GR1C_OUT = """                                # R35 GR-1c：两侧汉字段均 >=2 字 ⇒ 构词成分，不按运算符切分
                                if (not skip_kw
                                        and scan_pos >= 2
                                        and len(full_identifier) - (scan_pos + sub_len) >= 2
                                        and full_identifier.isalpha()):
                                    skip_kw = True
"""
GR1C = [
    ("""                            # 否则作为运算符识别（不跳过）
                            # 例如：甲加乙 -> [甲] [加] [乙]""",
     _GR1C_PROBE + """                            # 否则作为运算符识别（不跳过）
                            # 例如：甲加乙 -> [甲] [加] [乙]"""),
    ("""                                # 注意：在词中时（如"甲加乙"），运算符应作为关键字分隔符""",
     _GR1C_OUT + """                                # 注意：在词中时（如"甲加乙"），运算符应作为关键字分隔符"""),
]

VARIANTS = {
    # ---- GR-1c 收窄版 ----
    'gr1c_only': GR1C,
    'gr1c_mw_empty': GR1C + [(MW_BODY, "        # R35: 三条全撤\n")],
    'gr2b_only': GR2B,
    'gr2b_mw_empty': GR2B + [(MW_BODY, "        # R35: 三条全撤\n")],
    'gr2b_mw_no2': GR2B + [("'整理模型消息', '非空块',", "'整理模型消息',")],
    # GR-3c：词尾硬语句关键字路径**仅**在函数调用语境（`X(`）生效
    'gr3c_only': [(GR3_OLD, GR3_NEW),
                  (GR3_COND_OLD, GR3_COND_NEW.replace(
                      'or _tail_kw is not None)',
                      'or (_tail_kw is not None and _ctx_call))'))],
    'gr3c_mw_no3': [(GR3_OLD, GR3_NEW),
                    (GR3_COND_OLD, GR3_COND_NEW.replace(
                        'or _tail_kw is not None)',
                        'or (_tail_kw is not None and _ctx_call))')),
                    ("        '记录类型',\n", "")],
    # ---- 基线对照：撤除条目（无通用规则） ----
    'mw_empty': [(MW_BODY, "        # R35: 三条全撤\n")],
    'mw_no1': [("'整理模型消息', '非空块',", "'非空块',")],
    'mw_no2': [("'整理模型消息', '非空块',", "'整理模型消息',")],
    'mw_no3': [("        '记录类型',\n", "")],
    # ---- 通用规则单独评估（**不撤条目**，仅看规则自身是否零变化）----
    'gr1_only': GR1,
    'gr2_only': GR2,
    'gr3_only': GR3,
    # ---- 通用规则 + 撤除全部条目 ----
    'gr1_mw_empty': GR1 + [(MW_BODY, "        # R35: 三条全撤\n")],
    'gr2_mw_empty': GR2 + [(MW_BODY, "        # R35: 三条全撤\n")],
    'gr3_mw_empty': GR3 + [(MW_BODY, "        # R35: 三条全撤\n")],
    'gr12_mw_empty': GR1 + GR2 + [(MW_BODY, "        # R35: 三条全撤\n")],
    'gr123_mw_empty': GR1 + GR2 + GR3 + [(MW_BODY, "        # R35: 三条全撤\n")],
}
