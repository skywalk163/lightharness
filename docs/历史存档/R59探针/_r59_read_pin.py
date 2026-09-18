# -*- coding: utf-8 -*-
from pathlib import Path
p = Path(r'G:\dswork\duan-light-merge\light-merge\tests\test_R40_语言支撑配套.py')
t = p.read_text(encoding='utf-8')
lines = t.splitlines()
for i in range(175, 215):
    print(f'{i+1}: {lines[i]}')
