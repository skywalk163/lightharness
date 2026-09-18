# -*- coding: utf-8 -*-
"""64 红 ↔ 任务3/4 归因完整映射（规范化：去类名段 + unicode 解码）。"""
import json, re
from pathlib import Path

LH = Path(r'G:\dswork\duan-light-merge\lightharness')
base = json.loads((LH / 'reports' / '082_lightmerge基线_2026-09-18-133701.json').read_text(encoding='utf-8'))
reds = set()
for f in base['failed']:
    if isinstance(f, dict):
        reds.add((f.get('name') or f.get('id') or str(f)).encode().decode('unicode_escape'))
    else:
        reds.add(str(f).encode().decode('unicode_escape'))

def norm(iid):
    """file::Class::method -> file::method；file::method 保持。"""
    iid = iid.encode().decode('unicode_escape')
    parts = iid.split('::')
    if len(parts) >= 3:
        return '::'.join([parts[0], parts[-1]])
    return iid

t3 = json.loads((LH / '_task3_R58_代码生成语义债归因明细.json').read_text(encoding='utf-8'))
t4 = json.loads((LH / '_task4_R58_其余存量归因明细.json').read_text(encoding='utf-8'))

cov = {}
for gname in ['A', 'B', 'C']:
    for it in t3['groups'][gname]['items']:
        iid = norm(it['id'])
        cov.setdefault(iid, []).append('T3-' + gname)
        # 也按文件名+方法名记录原始
for it in t4['items']:
    iid = norm(it['id'])
    cov.setdefault(iid, []).append('T4-' + it.get('category', '')[:12])

red_hit = sorted(r for r in reds if r in cov)
print(f'=== 64 红中被任务3/4 归因覆盖: {len(red_hit)}/{len(reds)} ===')
for r in red_hit:
    print(f'   {r}  <- {cov[r]}')

uncov = sorted(r for r in reds if r not in cov)
print(f'\n=== 未覆盖: {len(uncov)} ===')
for r in uncov:
    print('   ', r)
