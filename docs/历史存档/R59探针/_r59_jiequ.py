# -*- coding: utf-8 -*-
"""钩子环境 截取 行为 + 定义位置。"""
import os, subprocess, sys, json
from pathlib import Path

LM = Path(r'G:\dswork\duan-light-merge\light-merge')
SD = str(LM / 'stdlib')
ROOT = str(LM)

code = (
    'import sys\n'
    'sys.path.insert(0, ROOT)\n'
    'import _light_import_hook\n'
    '_light_import_hook.install([SD])\n'
    'import 内置核心字符串 as S\n'
    'import builtins as B\n'
    'print("内置核心字符串 截取:", hasattr(S, "截取"))\n'
    'print("builtins 截取:", hasattr(B, "截取"))\n'
    'print("S.截取(E58589,0,2):", repr(S.截取("E58589", 0, 2)) if hasattr(S, "截取") else "无")\n'
    'print("S.截取(E58589,2,2):", repr(S.截取("E58589", 2, 2)) if hasattr(S, "截取") else "无")\n'
    'print("S.截取(E58589,4,2):", repr(S.截取("E58589", 4, 2)) if hasattr(S, "截取") else "无")\n'
    'print("S.截取(E58589,0,3):", repr(S.截取("E58589", 0, 3)) if hasattr(S, "截取") else "无")\n'
).replace('ROOT', json.dumps(ROOT)).replace('SD', json.dumps(SD))
env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONPATH=SD)
r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, encoding='utf-8', errors='replace', env=env, cwd=str(LM), timeout=120)
print('rc=%d' % r.returncode)
print(r.stdout)
print(r.stderr[:400])

# 定义位置（源码层）
import re
for name in ['内置核心字符串.light', '内置核心字符串.py']:
    p = Path(SD) / name
    if p.exists():
        t = p.read_text(encoding='utf-8', errors='replace')
        for i, l in enumerate(t.splitlines(), 1):
            if '截取' in l and ('段落' in l or 'def' in l):
                print(f'{name} L{i}: {l.strip()[:90]}')
                for j in range(i, min(i+10, len(t.splitlines())+1)):
                    print(f'    {name} L{j}: {t.splitlines()[j-1].strip()[:100]}')
                break
