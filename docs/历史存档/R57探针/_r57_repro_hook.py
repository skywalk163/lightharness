# -*- coding: utf-8 -*-
"""本机复现：安装 _light_import_hook 后 import 断言工具，验证 NameError 错误 是否出现。"""
import os
import sys
import traceback

ROOT = r'G:\dswork\duan-light-merge\light-merge'
STDLIB = os.path.join(ROOT, 'stdlib')
for p in (ROOT, os.path.join(ROOT, 'src'), STDLIB):
    if p not in sys.path:
        sys.path.insert(0, p)

import _light_import_hook
_light_import_hook.install([STDLIB])

print('[1] 钩子已安装')
try:
    import 断言工具
    print('[2] import 断言工具 成功')
    print('    模块文件:', getattr(断言工具, '__file__', '?'))
    print('    __light_source__:', getattr(断言工具, '__light_source__', '无(用.py)'))
    print('    有 断言失败异常:', hasattr(断言工具, '断言失败异常'))
    if hasattr(断言工具, '断言失败异常'):
        exc = 断言工具.断言失败异常
        print('    断言失败异常 MRO:', [c.__name__ for c in exc.__mro__])
except Exception as e:
    print('[2] import 断言工具 失败:', type(e).__name__, e)
    traceback.print_exc()

print()
print('[3] 对照：不装钩子直接 import（清 sys.modules 后）')
sys.modules.pop('断言工具', None)
try:
    import importlib
    m = importlib.import_module('断言工具')
    print('    成功，模块文件:', getattr(m, '__file__', '?'))
    if hasattr(m, '断言失败异常'):
        print('    断言失败异常 MRO:', [c.__name__ for c in m.断言失败异常.__mro__])
except Exception as e:
    print('    失败:', type(e).__name__, e)
