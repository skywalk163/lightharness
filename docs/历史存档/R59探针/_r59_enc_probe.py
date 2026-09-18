# -*- coding: utf-8 -*-
"""实测：光明编译 编码解码.URL编码("光") 与 .py 版对比。"""
import os, subprocess, sys, tempfile
from pathlib import Path

LM = Path(r'G:\dswork\duan-light-merge\light-merge')
os.chdir(LM)
sys.path.insert(0, str(LM / 'src'))
sys.path.insert(0, str(LM))

from llvm.compiler import compile_light_typed

code = (
    '从 编码解码 导入 URL编码 URL解码\n'
    '段落 主:\n'
    '  输出(URL编码("光"))\n'
    '  输出(URL编码("a b&c=1"))\n'
    '  输出(URL编码("path/to?q=光明"))\n'
)
with tempfile.TemporaryDirectory(prefix='_r59enc_') as d:
    src = os.path.join(d, '主.light')
    Path(src).write_text(code, encoding='utf-8')
    try:
        exe = compile_light_typed(src, os.path.join(d, '产物'), optimize_level=0)
        r = subprocess.run([exe], capture_output=True, timeout=60)
        print('[光明编译运行] rc=%d' % r.returncode)
        print('stdout:', repr(r.stdout.decode('utf-8', 'replace')))
        print('stderr:', r.stderr.decode('utf-8', 'replace')[:300])
    except Exception as e:
        print('[编译异常]', type(e).__name__, str(e)[:400])

# .py 版参考
sys.path.insert(0, str(LM / 'stdlib'))
import 编码解码 as E
print('\n[.py 版] URL编码("光") =', repr(E.URL编码('光')))
print('[.py 版] URL编码("a b&c=1") =', repr(E.URL编码('a b&c=1')))
print('[.py 版] URL编码("path/to?q=光明") =', repr(E.URL编码('path/to?q=光明')))

# 钩子加载 .light 版（模拟 _S 被劫持）
import _light_import_hook
_light_import_hook.install([str(LM / 'stdlib')])
import importlib
import 编码解码 as L2
print('\n[钩子] 编码解码 模块 =', getattr(L2, '__file__', '?'))
print('[钩子版] URL编码("光") =', repr(L2.URL编码('光')))
print('[钩子版] URL编码("path/to?q=光明") =', repr(L2.URL编码('path/to?q=光明')))
