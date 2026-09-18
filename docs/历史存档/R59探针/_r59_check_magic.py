# -*- coding: utf-8 -*-
from pathlib import Path
p = Path(r'G:\dswork\duan-light-merge\light-merge\stdlib\编码解码.light')
t = p.read_text(encoding='utf-8')
lines = t.splitlines()
print('总行数:', len(lines))
for i, l in enumerate(lines[:8], 1):
    print(f'L{i}: {l[:90]}')
for i, l in enumerate(lines, 1):
    if '纯光明实现' in l:
        print(f'字样 L{i}: {l[:90]}')
