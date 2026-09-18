# -*- coding: utf-8 -*-
"""双后端 URL解码 中文验证（LLVM O0 vs Python 后端钩子）。"""
import os, subprocess, sys, tempfile, json
from pathlib import Path

LM = Path(r'G:\dswork\duan-light-merge\light-merge')
os.chdir(LM)
sys.path.insert(0, str(LM / 'src'))
sys.path.insert(0, str(LM))

# LLVM O0
code = (
    '从 编码解码 导入 URL编码 URL解码\n'
    '段落 主:\n'
    '  输出(URL解码("%E5%85%89"))\n'
    '  输出(URL解码(URL编码("光")))\n'
    '  输出(URL解码(URL编码("path/to?q=光明")))\n'
)
with tempfile.TemporaryDirectory(prefix='_r59ud_') as d:
    src = os.path.join(d, '主.light')
    Path(src).write_text(code, encoding='utf-8')
    from llvm.compiler import compile_light_typed
    exe = compile_light_typed(src, os.path.join(d, '产物'), optimize_level=0)
    r = subprocess.run([exe], capture_output=True, timeout=60)
    print('[LLVM O0] rc=%d' % r.returncode)
    print('stdout:', repr(r.stdout.decode('utf-8', 'replace')))
    print('stderr:', r.stderr.decode('utf-8', 'replace')[:200])

# Python 后端（钩子干净子进程）
SD = str(LM / 'stdlib')
ROOT = str(LM)
code2 = (
    'import sys\n'
    'sys.path.insert(0, ROOT)\n'
    'import _light_import_hook\n'
    '_light_import_hook.install([SD])\n'
    'import 编码解码 as E\n'
    'print("URL解码(%E5%85%89):", repr(E.URL解码("%E5%85%89")))\n'
    'print("URL解码(URL编码(光)):", repr(E.URL解码(E.URL编码("光"))))\n'
    'print("URL解码(URL编码(光明)):", repr(E.URL解码(E.URL编码("path/to?q=光明"))))\n'
).replace('ROOT', json.dumps(ROOT)).replace('SD', json.dumps(SD))
env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONPATH=SD)
r = subprocess.run([sys.executable, '-c', code2], capture_output=True, text=True, encoding='utf-8', errors='replace', env=env, cwd=str(LM), timeout=120)
print('\n[Python 后端钩子] rc=%d' % r.returncode)
print(r.stdout)
print(r.stderr[:300])
