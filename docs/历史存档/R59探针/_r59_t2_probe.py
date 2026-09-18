# -*- coding: utf-8 -*-
"""R59 任务2 探针：21 条断言更新前的产物形态取证（只读编译）"""
import sys, os
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'src'))
from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator

def gen(code):
    return PythonCodeGenerator().generate(LightParser().parse(code))

def show(tag, code, keys):
    py = gen(code)
    print(f'===== {tag}')
    for l in py.splitlines():
        if any(k in l for k in keys) and not l.strip().startswith('#'):
            print(repr(l))

show('dot_member_access', '类 P:\n    令 x = 0\n令 p = P()\n令 v = p.x', ['v ='])
show('mixed_period_and_dot', '类 P:\n    令 x = 0。\n令 p = P()。\n令 v = p.x\n打印 v。', ['v ='])
show('no_period_no_dot_ambiguity',
     '类 P:\n    令 x = 0\n    令 y = 0\n令 p = P()\np.x = 3\np.y = p.x + 1\n打印 p.y',
     ['p.', '打印'])
show('period_in_class_body', '类 A:\n    令 x = 10。\n    函数 get(self):\n        返回 self.x。', ['def ', 'return'])
show('dot_access_after_new_keyword', '类 A:\n    令 x = 0\n令 a = A()\n令 v = a.x', ['v ='])
show('two_level_attr_assign',
     '类 A:\n    令 x = 0\n类 B:\n    令 a = None\n令 b = B()\nb.a = A()\nb.a.x = 42', ['= 42', 'b.'])
show('self_chain_assign',
     '类 A:\n    令 val = 0\n类 B:\n    令 inner = None\n    函数 set_val(self, v):\n        self.inner.val = v\n令 b = B()\nb.inner = A()\nb.set_val(5)', ['def set_val', 'val ='])
show('three_level_attr_assign',
     '类 C:\n    令 val = 0\n类 B:\n    令 c = None\n类 A:\n    令 b = None\n令 a = A()\na.b = B()\na.b.c = C()\na.b.c.val = 99', ['= 99'])
show('attr_assign_with_expr', '类 A:\n    令 x = 0\n令 a = A()\na.x = 10 + 20', ['= 10'])
show('v34_self_attr_eq', '类 A:\n    函数 f(self):\n        self.x = 1', ['def ', 'x'])
show('v34_obj_attr_eq', '类 点:\n    令 x = 0\n令 p = 点()\np.x = 10', ['p.'])
show('v34_dot_access', '类 点:\n    令 x = 0\n令 p = 点()\n令 x = p.x', ['= p', 'x ='])
