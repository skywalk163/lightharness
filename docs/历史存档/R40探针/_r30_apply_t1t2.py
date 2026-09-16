# -*- coding: utf-8 -*-
"""R30 任务1+2 落盘：新增词首前缀类通用规则 + 从 CCW 删除 6 条。

护栏：导入当前 lexer 断言 CCW==预期10条；两处编辑锚点各唯一；写临时文件
py_compile + 正则复核 CCW==4 后再 os.replace 原子落盘。
"""
import os
import re
import sys
import py_compile

ROOT = r'G:/dswork/duan-light-merge'
LP = ROOT + r'/light-merge/src/lexer.py'
sys.path.insert(0, ROOT + r'/light-merge/src')
import lexer  # noqa: E402

DELETE = {'位与', '位异或', '位或', '位非', '应当', '除非'}
KEEP = {'幂次', '测试_生成问候语', '记录类型', '零除错误'}
cur = set(lexer.COMMON_COMPOUND_WORDS)
assert cur == (DELETE | KEEP), (
    'CCW 现状不符（疑似并发改动）：缺=%s 多=%s' % (sorted(KEEP - cur), sorted(cur - KEEP)))

text = open(LP, encoding='utf-8').read()

# ── 编辑1：新增前缀类 ──
ANCHOR_CLASS = ("assert _P0A_HEAD_MERGE_DUAL == frozenset(\n"
                "    {'乘', '减', '加', '除', '模', '真', '空', '到'}), (\n"
                "    'R27 DUAL 类别漂移：应恒为 8 字（乘减加除模真空到）')")
CLASS_ADD = ANCHOR_CLASS + """

# ── R30 任务1/2：词首【前缀类】——非关键字(位/应)/被DUAL抑制(除)开头的复合名 ──
# 位与/位异或/位或/位非（首字 位，非关键字）、应当（首字 应，非关键字）、
# 除非（首字 除，DUAL 抑制后成标识符）在**非语句起始/调用语境**下需整词并入；
# 其后随关键字（与/或/非/当/异）会把复合名劈开，且无既有通用规则覆盖
# （HM/DUAL 仅对「词首关键字」生效，位/应 非关键字故不适用）。
# 本类别以**首字**为键，命中即整体并入（见 _tokenize_chinese_sequence 主循环）。
_P0A_HEAD_MERGE_PREFIX = frozenset({'位', '应', '除'})
assert _P0A_HEAD_MERGE_PREFIX == frozenset({'位', '应', '除'}), (
    'R30 词首前缀类漂移：应恒为 3 字（位应除）')"""
assert text.count(ANCHOR_CLASS) == 1, 'anchor class 不唯一'
text = text.replace(ANCHOR_CLASS, CLASS_ADD, 1)

# ── 编辑2：主循环分支 ──
ANCHOR_BRANCH = ("                if _ctx_call or not self._at_statement_start(source, pos):\n"
                 "                    _lead_kw, _lead_len = _match_kw(source, pos)")
BRANCH_ADD = ("                if _ctx_call or not self._at_statement_start(source, pos):\n"
              "                    # ── R30 任务1/2：词首前缀类（位/应/除）→ 整体并入标识符 ──\n"
              "                    # 位/应 非关键字、除 被 DUAL 抑制后成标识符；其后随关键字\n"
              "                    # （与/或/非/当）在词中会劈开复合名。命中前缀类即整体并入。\n"
              "                    if full_identifier[0] in _P0A_HEAD_MERGE_PREFIX:\n"
              "                        _tokens_append(_Token(_TokenType.IDENTIFIER, full_identifier, line, current_col))\n"
              "                        consumed += len(full_identifier)\n"
              "                        current_col += len(full_identifier)\n"
              "                        continue\n"
              "                    _lead_kw, _lead_len = _match_kw(source, pos)")
assert text.count(ANCHOR_BRANCH) == 1, 'anchor branch 不唯一'
text = text.replace(ANCHOR_BRANCH, BRANCH_ADD, 1)

# ── 编辑3：删 6 条 CCW ──
for e in DELETE:
    pat = re.compile(r"^    '%s',[^\n]*\n" % re.escape(e), re.M)
    assert pat.search(text), '未找到条目行: ' + e
    text = pat.sub('', text, count=1)

# ── 编辑4：R30 注释 ──
note = ("    # 【R30 任务1/2 精简】删除 6 条（位与/位异或/位或/位非/应当/除非）：\n"
        "    #   新增词首前缀类 `_P0A_HEAD_MERGE_PREFIX`（位/应/除）通用规则，\n"
        "    #   非语句起始/调用语境整词并入。三重判据全通过\n"
        "    #   （证据 lightharness/_task1t2_R30_证据.json）。原标注作废。\n")
anchor2 = "    # ===== 保留 A：真护栏"
assert anchor2 in text
text = text.replace(anchor2, note + anchor2, 1)

# ── 原子写 + 校验 ──
tmp = LP + '.tmp'
open(tmp, 'w', encoding='utf-8').write(text)
py_compile.compile(tmp, doraise=True)
m = re.search(r"COMMON_COMPOUND_WORDS = frozenset\(\{(.*?)\}\)\n", text, re.S)
entries = set(re.findall(r"'([^']*)'", m.group(1)))
assert entries == KEEP, '写回后 CCW 不符: 实=%s 期=%s' % (sorted(entries), sorted(KEEP))
assert '_P0A_HEAD_MERGE_PREFIX' in text
os.replace(tmp, LP)
print('OK: 新增前缀类规则 + CCW %d -> %d（删 %d 条）' % (len(cur), len(entries), len(DELETE)))
print('保留: %s' % '、'.join(sorted(entries)))
