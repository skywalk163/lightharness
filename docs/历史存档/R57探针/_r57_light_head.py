# -*- coding: utf-8 -*-
from pathlib import Path
p = Path(r'G:\dswork\duan-light-merge\light-merge\stdlib\断言工具.light')
lines = p.read_text(encoding='utf-8').splitlines()
print('总行数:', len(lines))
print('=== 头部 15 行 ===')
for i, l in enumerate(lines[:15], 1):
    print(i, l)
print('=== 含 错误 的行 ===')
for i, l in enumerate(lines, 1):
    if '错误' in l:
        print(i, l)
print('=== 含 继承 的行 ===')
for i, l in enumerate(lines, 1):
    if '继承' in l:
        print(i, l)
