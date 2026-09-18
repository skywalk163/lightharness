# -*- coding: utf-8 -*-
from pathlib import Path
p = Path(r'G:\dswork\duan-light-merge\light-merge\stdlib\编码解码.light')
t = p.read_text(encoding='utf-8')
lines = t.splitlines()
print('总行数:', len(lines))
for i, l in enumerate(lines, 1):
    if '截取(hx' in l:
        print(f'L{i}: {l.strip()}')
for i, l in enumerate(lines[:30], 1):
    if '内置核心字符串' in l:
        print(f'L{i}: {l.strip()}')
# URL查询串解码 实现（L335-355）
print('--- URL查询区 ---')
for i in range(334, 356):
    print(f'{i+1}: {lines[i]}')
