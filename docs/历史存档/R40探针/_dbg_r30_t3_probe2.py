# -*- coding: utf-8 -*-
"""R30 任务3 探针2：撤掉 CCW 三条后的 token 行为（模拟移除）。"""
import os
import sys

ROOT = r'G:/dswork/duan-light-merge'
sys.path.insert(0, os.path.join(ROOT, 'light-merge', 'src'))
import lexer  # noqa: E402

FULL = set(lexer.COMMON_COMPOUND_WORDS)
TARGETS = ['零除错误', '幂次', '记录类型']
REDUCED = frozenset(FULL - set(TARGETS))

CASES = [
    '捕获 零除错误:',
    '设 x 为 幂次(2, 10)',
    '设 x 为 记录类型(用户)',
    '零除错误',
    '幂次',
    '记录类型',
    # 反向（独立关键字/数字使用不受影响）
    '零 个',
    '幂 二',
    '类型 用户:',
    '记录 事件:',
    '外部 调试 { 开启, 记录类型, 追踪内存 }',
]


def toks(text):
    try:
        return [(t.type.name, t.value) for t in lexer.Lexer(text, deterministic=True).tokenize()
                if t.type.name not in ('EOF', 'NEWLINE')]
    except Exception as e:
        return ['ERR:' + type(e).__name__]


print('CCW 全表 %d 条，撤三条后 %d 条' % (len(FULL), len(REDUCED)))
for c in CASES:
    a = toks(c)
    lexer.COMMON_COMPOUND_WORDS = REDUCED
    b = toks(c)
    lexer.COMMON_COMPOUND_WORDS = FULL
    flag = 'SAME ' if a == b else 'DIFF '
    print(flag + repr(c))
    print('      CCW有: %s' % (a,))
    if a != b:
        print('      CCW撤: %s' % (b,))
