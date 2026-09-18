# -*- coding: utf-8 -*-
"""R59 任务书数据准备：读 133701 基线 64 红 + 任务3/4 归因明细，映射分组。"""
import json
from pathlib import Path

LH = Path(r'G:\dswork\duan-light-merge\lightharness')

# 1. 133701 基线（64 红 = 63 存量 + 1 护栏）
base = json.loads((LH / 'reports' / '082_lightmerge基线_2026-09-18-133701.json').read_text(encoding='utf-8'))
reds = base['红'] if isinstance(base, dict) and '红' in base else base
if isinstance(reds, dict):
    reds = list(reds.keys())
print('=== 基线红数:', len(reds))
for i, r in enumerate(sorted(reds), 1):
    print(f'{i:3d}. {r}')

# 2. 任务3 归因（35 条）
t3 = json.loads((LH / '_task3_R58_代码生成语义债归因明细.json').read_text(encoding='utf-8'))
print('\n=== 任务3 归因结构 ===')
if isinstance(t3, dict):
    print('keys:', list(t3.keys())[:10])
    for k, v in list(t3.items())[:3]:
        print(k, '->', str(v)[:200])
elif isinstance(t3, list):
    print('list len', len(t3), 'first:', str(t3[0])[:300])

# 3. 任务4 归因（30 条）
t4 = json.loads((LH / '_task4_R58_其余存量归因明细.json').read_text(encoding='utf-8'))
print('\n=== 任务4 归因结构 ===')
if isinstance(t4, dict):
    print('keys:', list(t4.keys())[:10])
    for k, v in list(t4.items())[:3]:
        print(k, '->', str(v)[:200])
elif isinstance(t4, list):
    print('list len', len(t4), 'first:', str(t4[0])[:300])
