# -*- coding: utf-8 -*-
"""R59 任务1 探针2：用测试真实路径（LightCompiler().compile → UnifiedCodeGenerator）
复现 test_class_system::compile_and_run 的产物，确认：
  - unified 是否处理 SelfAssignment（构造写入位）
  - 己X 读取位产物
"""
import os
import sys

LM = r'G:\dswork\duan-light-merge\light-merge'
sys.path.insert(0, os.path.join(LM, 'src'))

from compiler import LightCompiler
from code_generator_unified import UnifiedCodeGenerator

SRC = '''类 人：
  属性 姓名
  属性 年龄
  构造 接收 姓名, 年龄：
    己姓名 为 姓名
    己年龄 为 年龄
  段落 介绍：
    打印 己姓名
    打印 己年龄

设 张三 为 新建 人("张三", 25)
张三.介绍()
'''

r = LightCompiler().compile(SRC)
ast = r['ast']
print('AST type:', type(ast).__name__)
print('compile errors:', getattr(r, 'errors', None) or r.get('errors'))
py = UnifiedCodeGenerator().generate(ast)
print('--- unified 产物（类定义段）---')
lines = py.splitlines()
inflag = False
for i, ln in enumerate(lines):
    if 'class 人' in ln:
        inflag = True
    if inflag:
        print('%4d| %s' % (i + 1, ln))
    if inflag and ln.strip().startswith('张三.介绍'):
        break
print('--- 全文是否含裸 己 ---')
for i, ln in enumerate(lines):
    if '己' in ln:
        print('  %4d| %s' % (i + 1, ln))
