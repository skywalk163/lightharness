# -*- coding: utf-8 -*-
from pathlib import Path
sd = Path(r'G:\dswork\duan-light-merge\light-merge\stdlib')
for f in sorted(sd.glob('编码解码*')):
    t = f.read_text(encoding='utf-8', errors='replace')
    lines = t.splitlines()
    magic = any('纯光明实现' in h for h in lines[:2])
    print(f'{f.name}: {len(lines)} 行 | 魔数={magic} | 首行 {lines[0][:60]}')
    for i, l in enumerate(lines, 1):
        if 'URL编码' in l and ('段落' in l or 'def' in l or '返回' in l):
            print(f'   L{i}: {l.strip()[:110]}')
            # 打印实现体附近
            for j in range(i, min(i+12, len(lines)+1)):
                print(f'     L{j}: {lines[j-1].strip()[:110]}')
            print('   ---')
