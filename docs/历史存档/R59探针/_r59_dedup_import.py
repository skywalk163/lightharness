# -*- coding: utf-8 -*-
"""幂等清理：编码解码.light 中重复的 import 截取行。"""
from pathlib import Path
p = Path(r'G:\dswork\duan-light-merge\light-merge\stdlib\编码解码.light')
t = p.read_text(encoding='utf-8')
lines = t.splitlines()
# 去重：只保留第一个 import 截取
seen = False
out = []
for l in lines:
    if l.strip() == '从 内置核心字符串 导入 截取。':
        if seen:
            continue
        seen = True
    out.append(l)
t2 = '\n'.join(out)
p.write_text(t2, encoding='utf-8')
print('剩余 import 行:', t2.count('从 内置核心字符串 导入 截取'))
for i, l in enumerate(t2.splitlines(), 1):
    if '内置核心字符串' in l:
        print(f'L{i}: {l.strip()[:90]}')
