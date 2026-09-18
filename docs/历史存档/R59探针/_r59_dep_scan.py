# -*- coding: utf-8 -*-
from pathlib import Path
sd = Path(r'G:\dswork\duan-light-merge\light-merge\stdlib')
for name in ['内置核心字符串.light', '内置核心字符串.py']:
    p = sd / name
    if not p.exists():
        continue
    t = p.read_text(encoding='utf-8', errors='replace')
    print(f'=== {name} ({len(t.splitlines())} 行) ===')
    for i, l in enumerate(t.splitlines()[:40], 1):
        if '导入' in l or '从 ' in l:
            print(f'  L{i}: {l.strip()[:100]}')
# 全 stdlib：哪些 .light import 了 编码解码 或 内置核心字符串
print('\n=== 依赖扫描（编码解码 ↔ 内置核心字符串）===')
for f in sorted(sd.glob('*.light')):
    t = f.read_text(encoding='utf-8', errors='replace')
    refs = []
    if '内置核心字符串' in t:
        refs.append('引用内置核心字符串')
    if '编码解码' in t:
        refs.append('引用编码解码')
    if refs:
        print(f'{f.name}: {", ".join(refs)}')
