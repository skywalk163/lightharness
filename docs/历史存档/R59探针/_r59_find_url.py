# -*- coding: utf-8 -*-
from pathlib import Path
t = Path(r'G:\dswork\duan-light-merge\light-merge\stdlib\字符串工具.light').read_text(encoding='utf-8')
lines = t.splitlines()
print('总行数:', len(lines))
hits = [(i, l) for i, l in enumerate(lines, 1) if ('URL编码' in l or 'URL解码' in l or '百分号' in l or 'quote' in l.lower())]
print('命中行数:', len(hits))
for i, l in hits[:15]:
    print(f'L{i}: {l[:110]}')
