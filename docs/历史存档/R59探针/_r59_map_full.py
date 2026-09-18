# -*- coding: utf-8 -*-
"""64 红 ↔ 任务3/4 归因完整映射 + 未覆盖清单。"""
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

t3 = json.loads((LH / '_task3_R58_代码生成语义债归因明细.json').read_text(encoding='utf-8'))
t4 = json.loads((LH / '_task4_R58_其余存量归因明细.json').read_text(encoding='utf-8'))

cov = {}
print('=== 任务3 A 组（13 条）===')
for it in t3['groups']['A']['items']:
    iid = it['id']
    cov[iid] = 'T3-A 测试期望更新'
    print(f"   {iid}  ★红" if iid in reds else f"   {iid}  (非当前红)")

print('\n=== 任务3 B 组（11 条）===')
for it in t3['groups']['B']['items']:
    iid = it['id']
    cov[iid] = 'T3-B'
    print(f"   {iid}  ★红" if iid in reds else f"   {iid}  (非当前红)")

print('\n=== 任务3 C 组（11 条）===')
for it in t3['groups']['C']['items']:
    iid = it['id']
    cov[iid] = 'T3-C'
    print(f"   {iid}  ★红" if iid in reds else f"   {iid}  (非当前红)")

print('\n=== 任务4（30 条）===')
for it in t4['items']:
    iid = it['id']
    cov[iid] = 'T4-' + it.get('category', '')
    print(f"   {iid}  ★红" if iid in reds else f"   {iid}  (非当前红)")

uncov = sorted(r for r in reds if r not in cov)
print(f'\n=== 64 红未覆盖: {len(uncov)} ===')
for r in uncov:
    print('   ', r)
