# -*- coding: utf-8 -*-
"""R30 任务3 探针：零除错误 / 幂次 / 记录类型 的现状 token 行为。"""
import os
import sys

ROOT = r'G:/dswork/duan-light-merge'
sys.path.insert(0, os.path.join(ROOT, 'light-merge', 'src'))
import lexer  # noqa: E402
from keywords import ALL_KEYWORDS, VERB_ARITY, STDLIB_VERB_ARITY  # noqa: E402


def toks(text):
    try:
        return [(t.type.name, t.value) for t in lexer.Lexer(text, deterministic=True).tokenize()
                if t.type.name not in ('EOF', 'NEWLINE')]
    except Exception as e:
        return ['ERR:' + type(e).__name__]


print('=== 关键字身份 ===')
for w in ['零', '除', '错误', '幂', '次', '记录', '类型', '记录类型', '零除错误', '幂次']:
    print('  %-8s ALL=%-5s VERB=%-5s STDLIB=%-5s' % (
        w, w in ALL_KEYWORDS, w in VERB_ARITY, w in STDLIB_VERB_ARITY))

print('\n=== 保护表相关类别 ===')
print('  _P0A_OP          =', sorted(lexer.Lexer._P0A_OP))
print('  _P0A_SUFFIX_SPLIT_KW =', sorted(lexer.Lexer._P0A_SUFFIX_SPLIT_KW))
print('  _P0A_HARD_STMT   =', sorted(lexer.Lexer._P0A_HARD_STMT))
print('  _P0A_SEP         =', sorted(lexer.Lexer._P0A_SEP))
print('  _OPERATOR_KEYWORDS 含 除/非/记录/类型:',
      [w for w in ('除', '非', '记录', '类型') if w in lexer._OPERATOR_KEYWORDS])
print('  _P0A_MERGE_WHOLE   =', sorted(lexer.Lexer._P0A_MERGE_WHOLE))
print('  _P0A_HEAD_MERGE_SINGLE 含 幂/记:',
      [w for w in ('幂', '次', '记', '录', '零', '错', '误', '类', '型')
       if w in lexer._P0A_HEAD_MERGE_SINGLE])
print('  _P0A_HEAD_MERGE_DUAL =', sorted(lexer._P0A_HEAD_MERGE_DUAL))
print('  _TRAILING_ALIAS_CLASS 含 幂/次/零:',
      [w for w in ('幂', '次', '零', '记', '录', '类', '型', '错', '误', '错')
       if w in lexer.Lexer._TRAILING_ALIAS_CLASS])
print('  OPERATOR_VERBS 含 幂/除:',
      [w for w in ('幂', '除', '错') if w in lexer.OPERATOR_VERBS])

print('\n=== 三条目标的现状 token（CCW 有登记） ===')
CASES = [
    '捕获 零除错误:',
    '设 x 为 幂次(2, 10)',
    '设 x 为 记录类型(用户)',
    '零除错误',
    '幂次',
    '记录类型',
    '零 个',
    '幂 x',
    '类型 用户:',
    '记录 事件:',
]
for c in CASES:
    print('  %-24s -> %s' % (repr(c), toks(c)))
