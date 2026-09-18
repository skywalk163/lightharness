# -*- coding: utf-8 -*-
"""提取 133701 基线 failed 64 条红清单（精确，含护栏 1 条）。"""
import json
from pathlib import Path

LH = Path(r'G:\dswork\duan-light-merge\lightharness')
base = json.loads((LH / 'reports' / '082_lightmerge基线_2026-09-18-133701.json').read_text(encoding='utf-8'))
fails = base['failed']
names = []
for f in fails:
    if isinstance(f, dict):
        names.append(f.get('name') or f.get('id') or str(f))
    else:
        names.append(str(f))
print('=== 64 红（133701，含护栏 test_pure_light_hook）===')
for i, f in enumerate(sorted(names), 1):
    print(f'{i:3d}. {f}')
