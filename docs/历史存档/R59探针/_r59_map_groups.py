# -*- coding: utf-8 -*-
"""读任务3/4 归因明细 id 清单，与 64 红映射（修正失败项取 id/name 兜底）。"""
import json
from pathlib import Path

LH = Path(r'G:\dswork\duan-light-merge\lightharness')
base = json.loads((LH / 'reports' / '082_lightmerge基线_2026-09-18-133701.json').read_text(encoding='utf-8'))
reds = set()
for f in base['failed']:
    if isinstance(f, dict):
        reds.add(f.get('name') or f.get('id') or str(f))
    else:
        reds.add(str(f))
print('红数:', len(reds))

t3 = json.loads((LH / '_task3_R58_代码生成语义债归因明细.json').read_text(encoding='utf-8'))
t4 = json.loads((LH / '_task4_R58_其余存量归因明细.json').read_text(encoding='utf-8'))

print('\n=== 任务3 groups 结构探查 ===')
for gname, g in t3['groups'].items():
    print(f'-- {gname}: keys={list(g.keys()) if isinstance(g,dict) else type(g)}')
    if isinstance(g, dict):
        for k, v in g.items():
            if k != 'items':
                print(f'    {k}: {str(v)[:100]}')
        its = g.get('items', [])
        print(f'    items({len(its)}) 样例: {str(its[0])[:200] if its else "空"}')

print('\n=== 任务4 items 样例 ===')
print(str(t4['items'][0])[:300])
