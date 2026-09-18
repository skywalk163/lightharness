# -*- coding: utf-8 -*-
"""干净子进程：钩子加载 编码解码.light 的真实产物 + URL编码 输出。"""
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
    'print("MOD:", getattr(E, "__file__", "?"))\n'
    'print("URL编码(光):", repr(E.URL编码("光")))\n'
    'print("URL编码(a b&c=1):", repr(E.URL编码("a b&c=1")))\n'
    'print("URL编码(path/to?q=光明):", repr(E.URL编码("path/to?q=光明")))\n'
    'print("URL解码(a%20b%26c%3D1):", repr(E.URL解码("a%20b%26c%3D1")))\n'
).replace('ROOT', json.dumps(ROOT)).replace('SD', json.dumps(SD))
env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONPATH=SD)
r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, encoding='utf-8', errors='replace', env=env, cwd=str(LM), timeout=120)
print('[干净子进程·钩子加载] rc=%d' % r.returncode)
print(r.stdout)
print(r.stderr[:500])
