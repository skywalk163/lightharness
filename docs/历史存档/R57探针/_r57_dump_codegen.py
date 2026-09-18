# -*- coding: utf-8 -*-
"""dump 断言工具.light 经 LightParser+PythonCodeGenerator 的编译产物，定位 错误 相关行。"""
import os
import sys

ROOT = r'G:\dswork\duan-light-merge\light-merge'
for p in (ROOT, os.path.join(ROOT, 'src'), os.path.join(ROOT, 'stdlib')):
    if p not in sys.path:
        sys.path.insert(0, p)

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator

light_path = os.path.join(ROOT, 'stdlib', '断言工具.light')
source = open(light_path, encoding='utf-8').read()
module_ast = LightParser().parse(source)
generated = PythonCodeGenerator().generate(module_ast)

lines = generated.splitlines()
print('产物总行数:', len(lines))
for i, l in enumerate(lines, 1):
    if '错误' in l or 'Exception' in l or 'class' in l.lower() or '断言失败异常' in l:
        print(i, l)
print('=== 277 行附近 ===')
for i in range(max(1, 277 - 6), min(len(lines), 277 + 4) + 1):
    print(i, lines[i - 1])
