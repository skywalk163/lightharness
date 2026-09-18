# -*- coding: utf-8 -*-
"""R59 任务1 探针3：unified 后端嵌套类/多泛型类的产物结构 + 己X 泄漏点。"""
import os
import sys

LM = r'G:\dswork\duan-light-merge\light-merge'
sys.path.insert(0, os.path.join(LM, 'src'))
from compiler import LightCompiler
from code_generator_unified import UnifiedCodeGenerator

SRC_A25 = (
    '类 工具：\n'
    '  类 参数：\n'
    '    属性 名。\n'
    '    构造 接收 名：\n'
    '      己名 为 名。\n'
    '  类 结果：\n'
    '    属性 值。\n'
    '    构造 接收 值：\n'
    '      己值 为 值。\n'
    '  属性 号。\n'
    '  构造：\n'
    '    己号 为 1。\n'
    '  段落 描述()：\n'
    '    返回 己号。\n'
    '\n'
    '设 甲 为 工具()。\n'
    '打印 甲.描述()。\n'
)

SRC_A24 = (
    '类 对[T, U]：\n'
    '  属性 左。\n'
    '  属性 右。\n'
    '  构造 接收 左, 右：\n'
    '    己左 为 左。\n'
    '    己右 为 右。\n'
    '  段落 取左()：\n'
    '    返回 己左。\n'
    '\n'
    '设 甲 为 对(3, "四")。\n'
)


def show(tag, src):
    print('=' * 70)
    print('###', tag)
    r = LightCompiler().compile(src)
    py = UnifiedCodeGenerator().generate(r['ast'])
    lines = py.splitlines()
    # 只打印类相关段（从第一个 class 到最后一个含 打印/甲. 的行）
    start = next((i for i, l in enumerate(lines) if l.strip().startswith('class ')), 0)
    for i in range(start, len(lines)):
        print('%4d| %s' % (i + 1, lines[i]))
    print('--- 裸己行 ---')
    for i, l in enumerate(lines):
        if '己' in l:
            print('  %4d| %s' % (i + 1, l))


show('A25 嵌套类', SRC_A25)
show('A24 多参数泛型', SRC_A24)
