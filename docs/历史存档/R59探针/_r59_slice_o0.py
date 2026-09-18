# -*- coding: utf-8 -*-
"""LLVM O0 实测 截取 语义 + 编码URL编码核心 输出。"""
import os, subprocess, sys, tempfile
from pathlib import Path

LM = Path(r'G:\dswork\duan-light-merge\light-merge')
os.chdir(LM)
sys.path.insert(0, str(LM / 'src'))
sys.path.insert(0, str(LM))
from llvm.compiler import compile_light_typed

code = (
    '从 内置核心字符串 导入 截取\n'
    '从 编码解码 导入 URL编码\n'
    '段落 主:\n'
    '  输出(截取("E58589", 0, 2))\n'
    '  输出(截取("E58589", 2, 2))\n'
    '  输出(截取("E58589", 4, 2))\n'
    '  输出(URL编码("光"))\n'
)
with tempfile.TemporaryDirectory(prefix='_r59sl_') as d:
    src = os.path.join(d, '主.light')
    Path(src).write_text(code, encoding='utf-8')
    try:
        exe = compile_light_typed(src, os.path.join(d, '产物'), optimize_level=0)
        r = subprocess.run([exe], capture_output=True, timeout=60)
        print('[LLVM O0] rc=%d' % r.returncode)
        print('stdout:', repr(r.stdout.decode('utf-8', 'replace')))
        print('stderr:', r.stderr.decode('utf-8', 'replace')[:400])
    except Exception as e:
        print('[编译异常]', type(e).__name__, str(e)[:500])
