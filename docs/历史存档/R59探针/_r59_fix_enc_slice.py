# -*- coding: utf-8 -*-
"""R59 路M 预修：编码解码.light L306 截取语义修正（[start:end] vs (start,len) 误用）。"""
from pathlib import Path

p = Path(r'G:\dswork\duan-light-merge\light-merge\stdlib\编码解码.light')
t = p.read_text(encoding='utf-8')
old = '设 结果 为 结果 加上 "%" 加上 截取(hx, k * 2, 2)'
new = '设 结果 为 结果 加上 "%" 加上 截取(hx, k * 2, k * 2 + 2)'
if old not in t:
    print('ALREADY: 未找到旧调用（可能已修）')
else:
    t = t.replace(old, new, 1)
    # 护栏口径：首两行含魔数即安全（test_magic_number_in_first_two_lines 只判这个）
    assert '纯光明实现' in '\n'.join(t.splitlines()[:2]), '首两行魔数丢失'
    p.write_text(t, encoding='utf-8')
    print('PATCHED')
t2 = p.read_text(encoding='utf-8')
for i, l in enumerate(t2.splitlines(), 1):
    if '截取(hx' in l:
        print(f'L{i}: {l.strip()}')
