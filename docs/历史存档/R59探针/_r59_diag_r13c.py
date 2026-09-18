# -*- coding: utf-8 -*-
"""R13C 诊断 v2：钩子 vs 无钩子环境下 字符串工具.URL编码 行为 + .light 编译输出。"""
import os, subprocess, sys, tempfile
from pathlib import Path

LM = Path(r'G:\dswork\duan-light-merge\light-merge')
os.chdir(LM)
SD = str(LM / 'stdlib')
ROOT = str(LM)

def run_py(hook: bool, code: str):
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONPATH=SD)
    if hook:
        code = 'import sys; sys.path.insert(0, %r); import _light_import_hook; _light_import_hook.install([%r])\n' % (ROOT, SD) + code
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, encoding='utf-8', errors='replace', env=env, cwd=str(LM), timeout=120)
    return r.returncode, r.stdout.strip(), r.stderr.strip()

rc, out, err = run_py(False, 'import 字符串工具 as S\nprint(repr(S.URL编码("path/to?q=光明")))\nprint(repr(S.URL解码("a%20b%26c%3D1")))\nprint("MOD:", getattr(S,"__file__","?"))')
print('[无钩子] rc=%d\n%s\n%s' % (rc, out, err[:300]))

rc, out, err = run_py(True, 'import 字符串工具 as S\nprint(repr(S.URL编码("path/to?q=光明")))\nprint(repr(S.URL解码("a%20b%26c%3D1")))\nprint("MOD:", getattr(S,"__file__","?"))')
print('\n[钩子] rc=%d\n%s\n%s' % (rc, out, err[:300]))

# .light 编译运行（O0）
code = ('从 字符串工具 导入 URL编码 URL解码\n'
        '段落 主:\n'
        '  输出(URL编码("a b&c=1"))\n'
        '  输出(URL解码("a%20b%26c%3D1"))\n'
        '  输出(URL解码(URL编码("path/to?q=光明")))\n')
try:
    with tempfile.TemporaryDirectory(prefix='_r59diag_') as d:
        src = os.path.join(d, '主.light')
        Path(src).write_text(code, encoding='utf-8')
        env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONPATH=ROOT)
        sys.path.insert(0, ROOT)
        from llvm.compiler import compile_light_typed
        exe = compile_light_typed(src, os.path.join(d, '产物'), optimize_level=0)
        r = subprocess.run([exe], capture_output=True, timeout=60)
        print('\n[.light O0 编译运行] rc=%d\nstdout=%r' % (r.returncode, r.stdout.decode('utf-8', 'replace').rstrip()))
except Exception as e:
    print('\n[.light 编译异常]', e)
