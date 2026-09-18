# -*- coding: utf-8 -*-
from pathlib import Path
t = Path(r'G:\dswork\duan-light-merge\light-merge\stdlib\编码解码.light').read_text(encoding='utf-8')
lines = t.splitlines()
for i, l in enumerate(lines[:40], 1):
    print(f'{i}: {l[:110]}')
print('--- 全部 import 行 ---')
for i, l in enumerate(lines, 1):
    if ('从 ' in l and ' 导入 ' in l) or l.startswith('导入') or ('导入 ' in l and ' 从 ' in l):
        print(f'L{i}: {l.strip()[:110]}')
print('--- 调用截取的函数上下文 ---')
for i, l in enumerate(lines, 1):
    if '截取(' in l:
        print(f'L{i}: {l.strip()[:110]}')
