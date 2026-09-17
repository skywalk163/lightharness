# -*- coding: utf-8 -*-
"""L-172 诊断工具：解析 .light 源，打印顶层语句结构 / 入口检测 / 产物末尾。

用法: python _l172probe/dump.py <file.light>
"""
import os
import sys

LM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(LM, 'src'))
sys.path.insert(0, LM)

from light_parser_v3 import LightParser  # noqa: E402
from code_generator import PythonCodeGenerator  # noqa: E402


def main():
    path = sys.argv[1]
    src = open(path, encoding='utf-8').read()
    parser = LightParser()
    module = parser.parse(src)
    print('--- 顶层语句 ---')
    for i, stmt in enumerate(getattr(module, 'statements', None) or []):
        name = getattr(stmt, 'name', None)
        n = len(getattr(stmt, 'body', None) or [])
        print(f'  [{i}] {type(stmt).__name__:24s} name={name!r} body={n}')
    gen = PythonCodeGenerator()
    code = gen.generate(module, is_main=True)
    print('--- 入口检测 ---')
    entry = gen._find_entry_paragraph(module)
    print('  entry =', getattr(entry, 'name', None) if entry else None)
    if entry is not None:
        print('  arity =', gen._paragraph_arity(entry))
        print('  module_invokes_entry =', gen._module_invokes_entry(module, entry))
    print('  _entry_call =', getattr(gen, '_entry_call', None))
    print('--- 产物末尾 12 行 ---')
    for line in code.split('\n')[-12:]:
        print('  |' + line)
    has_main = "if __name__ == '__main__':" in code
    print('--- 末尾是否含入口调用块:', has_main, '---')


if __name__ == '__main__':
    main()
