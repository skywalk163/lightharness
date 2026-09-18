# -*- coding: utf-8 -*-
"""dump 任务4 完整 items（id/分类/root_cause/建议）。"""
import json
from pathlib import Path

LH = Path(r'G:\dswork\duan-light-merge\lightharness')
t4 = json.loads((LH / '_task4_R58_其余存量归因明细.json').read_text(encoding='utf-8'))
print('=== 任务4 items（30 条）===')
for it in t4['items']:
    print(f"- {it['id']}")
    for k in ['category', 'root_cause', 'red_reason', '修复建议', '建议']:
        if k in it and it[k]:
            print(f"    {k}: {str(it[k])[:260]}")
