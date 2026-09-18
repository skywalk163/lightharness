# -*- coding: utf-8 -*-
"""LLVM O0：dump URL编码("光") 的码位序列 + URL解码 直接处理该结果。"""
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
    '  设 x 为 URL编码("光")\n'
    '  输出(x)\n'
    '  设 n 为 长(x)\n'
    '  设 i 为 0\n'
    '  当 i < n:\n'
    '    输出(码位(x[i]))\n'
    '    设 i 为 i + 1\n'
    '  输出(URL解码(x))\n'
)
with tempfile.TemporaryDirectory(prefix='_r59uc_') as d:
    src = os.path.join(d, '主.light')
    Path(src).write_text(code, encoding='utf-8')
    exe = compile_light_typed(src, os.path.join(d, '产物'), optimize_level=0)
    r = subprocess.run([exe], capture_output=True, timeout=60)
    print('rc=%d' % r.returncode)
    print('stdout:', repr(r.stdout.decode('utf-8', 'replace')))
    print('stderr:', r.stderr.decode('utf-8', 'replace')[:300])
