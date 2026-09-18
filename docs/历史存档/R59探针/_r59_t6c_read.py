# -*- coding: utf-8 -*-
from pathlib import Path
p = Path(r'G:\dswork\duan-light-merge\light-merge\tests\unit\test_原生腿_T6C_向量复数颜色参数编码.py')
t = p.read_text(encoding='utf-8')
lines = t.splitlines()
for i in range(320, 345):
    print(f'{i+1}: {lines[i]}')
print('...')
for i in range(430, 470):
    print(f'{i+1}: {lines[i]}')
