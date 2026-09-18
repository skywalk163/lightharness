# -*- coding: utf-8 -*-
"""dump 任务3 A/B/C 组 + 任务4 完整 items（id/红因/根因/建议），供任务书引用。"""
import json
from pathlib import Path

LH = Path(r'G:\dswork\duan-light-merge\lightharness')
t3 = json.loads((LH / '_task3_R58_代码生成语义债归因明细.json').read_text(encoding='utf-8'))
t4 = json.loads((LH / '_task4_R58_其余存量归因明细.json').read_text(encoding='utf-8'))

print('=== 任务3 汇总 ===')
print(json.dumps(t3['汇总'], ensure_ascii=False, indent=1))

for gname in ['A', 'B', 'C']:
    g = t3['groups'][gname]
    print(f'\n=== 任务3 {gname} 组（{len(g["items"])} 条）===')
    print('meta:', g.get('meta', '')[:160])
    if '汇总' in g:
        print('汇总:', json.dumps(g['汇总'], ensure_ascii=False))
    for it in g['items']:
        print(f"- {it['id']}")
        for k in ['category', '红因', '根因', '修复建议', '预期']:
            if k in it and it[k]:
                print(f"    {k}: {str(it[k])[:240]}")
