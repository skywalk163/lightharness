# -*- coding: utf-8 -*-
"""R30 任务3 探针3：零+关键字 语料实形态的现状 token。"""
import os
import sys

ROOT = r'G:/dswork/duan-light-merge'
sys.path.insert(0, os.path.join(ROOT, 'light-merge', 'src'))
import lexer  # noqa: E402

CASES = ['零导入', '零匹配', '零使用', '零引', '零非', '零列', '零假', '零除',
         '零导入 为 真', '设 零匹配 为 0', '零导入 是 真',
         '三段', '三类', '一并', '一等', '一加', '一假', '一真', '零除错误']
for c in CASES:
    try:
        seq = [(t.type.name, t.value) for t in lexer.Lexer(c, deterministic=True).tokenize()
               if t.type.name not in ('EOF', 'NEWLINE')]
    except Exception as e:
        seq = ['ERR:' + type(e).__name__]
    print('%-16s -> %s' % (repr(c), seq))

print('\n--- 集合.light:360-375 ---')
p = os.path.join(ROOT, 'light-merge', 'stdlib', '集合.light')
for n, ln in enumerate(open(p, encoding='utf-8', errors='replace'), 1):
    if 360 <= n <= 375:
        print('%4d| %s' % (n, ln.rstrip()))
