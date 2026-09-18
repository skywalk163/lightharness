# -*- coding: utf-8 -*-
from pathlib import Path
p = Path(r'G:\dswork\duan-light-merge\light-merge\tests\test_pure_light_hook.py')
t = p.read_text(encoding='utf-8')
lines = t.splitlines()
for i in range(124, 170):
    print(f'{i}: {lines[i-1]}')
