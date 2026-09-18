# -*- coding: utf-8 -*-
"""R59 任务2 探针v3：剩余场景产物取证"""
import sys, os
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'src'))
from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator

def gen(code):
    return PythonCodeGenerator().generate(LightParser().parse(code))

def tail(tag, code, n=10, skip_prelude=True):
    py = gen(code)
    lines = [l for l in py.splitlines() if l.strip() and not l.strip().startswith('#')]
    print(f'===== {tag}')
    for l in lines[-n:]:
        print(repr(l))

tail('no_period_no_dot_ambiguity',
     '类 P:\n    令 x = 0\n    令 y = 0\n令 p = P()\np.x = 3\np.y = p.x + 1\n打印 p.y', 4)
tail('await_chained_member', '异步 函数 主():\n  等待 甲.乙.丙()', 2)
tail('普通标识符之成员赋值', '设 obj 为 1\nobj.字段 为 1', 2)
tail('点号成员赋值', '设 obj 为 1\nobj.字段 = 1', 2)
tail('为搭配函数调用', '遍 范围(1, 10) 为 i:\n  输出(i)', 3)
tail('async_03', '''类 计数器:
    设 值 为 0
    异步 段落 增加():
        己.值 为 己.值 加上 1
        返回 己.值
    异步 段落 取值():
        返回 己.值''', 8)
