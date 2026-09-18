# -*- coding: utf-8 -*-
from pathlib import Path
p = Path(r'G:\dswork\duan-light-merge\light-merge\stdlib\参数解析.light')
t = p.read_text(encoding='utf-8')
lines = t.splitlines()
print('总行数:', len(lines))
for i, l in enumerate(lines, 1):
    if '=' in l and ('查找' in l or '截取' in l or '等号' in l or '拆' in l):
        print(f'{i}: {l.strip()[:110]}')
print('--- 解析 主函数区 ---')
for i, l in enumerate(lines, 1):
    if '段落 解析' in l:
        for j in range(i-1, min(i+55, len(lines))):
            print(f'{j+1}: {lines[j][:110]}')
        break
