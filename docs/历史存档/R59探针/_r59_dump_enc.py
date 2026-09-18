# -*- coding: utf-8 -*-
from pathlib import Path
t = Path(r'G:\dswork\duan-light-merge\light-merge\stdlib\编码解码.light').read_text(encoding='utf-8')
lines = t.splitlines()
for i in range(263, 333):
    print(f'{i+1}: {lines[i]}')
