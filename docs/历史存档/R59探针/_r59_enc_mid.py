# -*- coding: utf-8 -*-
"""钩子环境 dump 编码编UTF8/截取/整除 中间量（Python 后端生成产物行为）。"""
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
    'import 编码解码 as E\n'
    'for fn in ["编码编UTF8", "编码hex值", "编码hex2", "编码解UTF8"]:\n'
    '    print(fn, "存在:", hasattr(E, fn))\n'
    'print("编码编UTF8(光):", repr(E.编码编UTF8("光")))\n'
    'hx = E.编码编UTF8("光")\n'
    'print("长(hx):", len(hx))\n'
    'print("截取 E58589 0,2:", repr(E.截取("E58589", 0, 2)) if hasattr(E, "截取") else "无截取")\n'
    'print("整除(长(hx),2):", repr(E.整除(len(hx), 2)) if hasattr(E, "整除") else "无整除")\n'
    'print("调用核心: URL编码(光) =", repr(E.URL编码("光")))\n'
).replace('ROOT', json.dumps(ROOT)).replace('SD', json.dumps(SD))
env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONPATH=SD)
r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, encoding='utf-8', errors='replace', env=env, cwd=str(LM), timeout=120)
print('rc=%d' % r.returncode)
print(r.stdout)
print(r.stderr[:400])
