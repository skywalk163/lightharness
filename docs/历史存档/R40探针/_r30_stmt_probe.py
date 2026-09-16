# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, r'G:/dswork/duan-light-merge/light-merge/src')
import lexer
def seq(t):
    try:
        return [(x.type.name, x.value) for x in lexer.Lexer(t, deterministic=True).tokenize()
                if x.type.name not in ('EOF','NEWLINE')]
    except Exception as e:
        return ['ERR:'+type(e).__name__]
cases = [
    '位与(1, 2)',
    '位异或(1, 2)',
    '位非(1)',
    '应当(1)',
    '除非(1)',
    '设 位与 为 1',
    '如果 应当 那么:\n  返回 1',
    '除非 条件:\n  返回 1',
    '返回 位与(1, 2)',
]
for c in cases:
    print(repr(c), '->', seq(c))
