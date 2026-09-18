# -*- coding: utf-8 -*-
"""dump 133701 基线 JSON 完整结构 + 从 xml 提取失败清单。"""
import json, re
from pathlib import Path

LH = Path(r'G:\dswork\duan-light-merge\lightharness')
base = json.loads((LH / 'reports' / '082_lightmerge基线_2026-09-18-133701.json').read_text(encoding='utf-8'))
print('=== 基线 JSON 顶层键 ===')
for k, v in base.items():
    if isinstance(v, (dict, list)):
        print(f'  {k}: {type(v).__name__} len={len(v)}')
    else:
        print(f'  {k}: {str(v)[:80]}')
# 找含红名的字段
for k, v in base.items():
    if isinstance(v, list) and v and isinstance(v[0], str):
        print(f'--- {k} 前5条:')
        for x in v[:5]:
            print('   ', x)
# xml 提取失败
xmlp = LH / 'reports' / '_082_lm_results_2026-09-18-133700.xml'
xml = xmlp.read_text(encoding='utf-8', errors='replace')
fails = re.findall(r'<testcase[^>]*classname="([^"]+)"[^>]*name="([^"]+)"[^>]*>\s*<(failure|error)', xml)
print(f'\n=== xml 失败/错误数: {len(fails)} ===')
seen = set()
for cn, nm, kind in fails:
    key = f'{cn}::{nm}'
    if key not in seen:
        seen.add(key)
print('唯一失败名数:', len(seen))
for cn, nm, kind in sorted(seen):
    print(f'{cn}::{nm}  [{kind}]')
