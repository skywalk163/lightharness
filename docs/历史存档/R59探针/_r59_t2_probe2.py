# -*- coding: utf-8 -*-
"""R59 任务2 探针v2：打印各场景产物尾部非注释行"""
import sys, os
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'src'))
from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator

def gen(code):
    return PythonCodeGenerator().generate(LightParser().parse(code))

def tail(tag, code, n=14):
    py = gen(code)
    lines = [l for l in py.splitlines() if l.strip() and not l.strip().startswith('#')]
    print(f'===== {tag}')
    for l in lines[-n:]:
        print(repr(l))

tail('two_level_attr_assign', '类 A:\n    令 x = 0\n类 B:\n    令 a = None\n令 b = B()\nb.a = A()\nb.a.x = 42')
tail('self_chain_assign', '类 A:\n    令 val = 0\n类 B:\n    令 inner = None\n    函数 set_val(self, v):\n        self.inner.val = v\n令 b = B()\nb.inner = A()\nb.set_val(5)', 8)
tail('three_level_attr_assign', '类 C:\n    令 val = 0\n类 B:\n    令 c = None\n类 A:\n    令 b = None\n令 a = A()\na.b = B()\na.b.c = C()\na.b.c.val = 99')
tail('attr_assign_with_expr', '类 A:\n    令 x = 0\n令 a = A()\na.x = 10 + 20', 5)
tail('v34_self_attr_eq', '类 A:\n    函数 f(self):\n        self.x = 1', 4)
tail('v34_self_attr_等于', '类 A:\n    函数 f(self):\n        self.x 等于 1', 4)
tail('v34_obj_attr_eq', '类 点:\n    令 x = 0\n令 p = 点()\np.x = 10', 3)
tail('v34_dot_access', '类 点:\n    令 x = 0\n令 p = 点()\n令 x = p.x', 3)
