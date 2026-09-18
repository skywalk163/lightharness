# -*- coding: utf-8 -*-
"""R59 任务1 探针：己X 读取位不展开（codegen 粘连）。

确认：
  1. UnifiedCodeGenerator 与 src CodeGenerator 对 `打印 己姓名` / `返回 己初始值 加 数值`
     的产物是否漏出裸 `己X`（NameError 根因）。
  2. 类的属性名来源：declared fields vs SelfAssignment(attr_name)。
"""
import os
import sys

LM = r'G:\dswork\duan-light-merge\light-merge'
sys.path.insert(0, os.path.join(LM, 'src'))

SRC_A = '''类 人：
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

SRC_B = '''类 计算器：
  属性 初始值。
  构造 接收 初始值：
    己初始值 为 初始值。
  结束。
  段落 加 接收 数值：
    返回 己初始值 加 数值。
  结束。
结束。
'''


def gen_unified(src):
    from code_generator_unified import UnifiedCodeGenerator
    from light_parser_v3 import LightParser
    module = LightParser().parse(src)
    return UnifiedCodeGenerator().generate(module)


def gen_src(src):
    from compiler import LightCompiler
    from code_generator import CodeGenerator
    r = LightCompiler().compile(src)
    return CodeGenerator().generate(r['ast'])


def dump_ast_names(src):
    from light_parser_v3 import LightParser
    from ast_nodes_v3 import SelfAssignment
    module = LightParser().parse(src)
    out = []

    def walk(node, depth=0):
        if node is None:
            return
        tn = type(node).__name__
        if tn in ('ClassDefinition', 'Class'):
            fields = getattr(node, 'fields', None) or []
            fnames = [getattr(f, 'name', '?') for f in fields]
            out.append(('CLASS', getattr(node, 'name', '?'), 'fields=' + repr(fnames)))
        if tn == 'SelfAssignment':
            out.append(('SELF_ASSIGN', getattr(node, 'attr_name', '?'), ''))
        # 遍历常见容器属性
        for attr in ('body', 'methods', 'fields', 'constructor', 'nested_classes'):
            v = getattr(node, attr, None)
            if isinstance(v, list):
                for c in v:
                    walk(c, depth + 1)
            elif hasattr(v, '__class__') and type(v).__name__ not in ('str', 'int', 'NoneType'):
                if hasattr(v, '__slots__') or hasattr(v, 'body'):
                    walk(v, depth + 1)

    walk(module)
    return out


for tag, src in (('A(类人/属性声明)', SRC_A), ('B(计算器/属性+结束)', SRC_B)):
    print('=' * 70)
    print('###', tag)
    print('--- AST attrs ---')
    for row in dump_ast_names(src):
        print('   ', row)
    print('--- unified 产物 ---')
    print(gen_unified(src))
    try:
        print('--- src 产物 ---')
        print(gen_src(src))
    except Exception as e:
        print('   src backend ERROR:', type(e).__name__, e)
