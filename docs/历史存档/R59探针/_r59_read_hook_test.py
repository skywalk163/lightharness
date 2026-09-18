# -*- coding: utf-8 -*-
from pathlib import Path
p = Path(r'G:\dswork\duan-light-merge\light-merge\tests\test_pure_light_hook.py')
t = p.read_text(encoding='utf-8')
lines = t.splitlines()
for i, l in enumerate(lines, 1):
    if '纯光明实现' in l or 'first_two' in l or '前两行' in l or 'def test' in l:
        print(f'{i}: {l.strip()[:120]}')
