# -*- coding: utf-8 -*-
import json
from pathlib import Path
p = Path(r'G:\dswork\duan-light-merge\lightharness\docs\功能对标\对标清单.json')
d = json.loads(p.read_text(encoding='utf-8'))
print('top type:', type(d).__name__)
if isinstance(d, dict):
    for k, v in d.items():
        if isinstance(v, list):
            print('list key:', k, 'len=', len(v), 'last=', (v[-1].get('id') if isinstance(v[-1], dict) else type(v[-1]).__name__))
