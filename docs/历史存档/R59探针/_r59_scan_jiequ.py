# -*- coding: utf-8 -*-
"""搜 stdlib 所有 .light 中 截取( 三参调用，找 (start, len) 误用。"""
import re
from pathlib import Path
sd = Path(r'G:\dswork\duan-light-merge\light-merge\stdlib')
pat = re.compile(r'截取\(([^()]*)\)')
for f in sorted(sd.glob('*.light')):
    t = f.read_text(encoding='utf-8', errors='replace')
    lines = t.splitlines()
    for i, l in enumerate(lines, 1):
        for m in pat.finditer(l):
            args = [a.strip() for a in m.group(1).split(',')]
            if len(args) == 3:
                print(f'{f.name} L{i}: {l.strip()[:110]}')
