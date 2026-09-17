# -*- coding: utf-8 -*-
"""L-172 关键判别：真实 R52 用例「去掉末尾显式 主()」后，
module_invokes_entry 是否仍为 True（=伪检测，即 L-172 根因）。"""
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
LM = os.path.dirname(HERE)
PY = os.path.join(LM, '.venv', 'Scripts', 'python.exe')
LH = r'G:\dswork\duan-light-merge\lightharness'
EX = os.path.join(LH, 'examples')

import sys
sys.path.insert(0, os.path.join(LM, 'src'))
sys.path.insert(0, LM)
from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator


def probe(label, src):
    parser = LightParser()
    module = parser.parse(src)
    gen = PythonCodeGenerator()
    entry = gen._find_entry_paragraph(module)
    arity = gen._paragraph_arity(entry) if entry else None
    invokes = gen._module_invokes_entry(module, entry) if entry else None
    code = gen.generate(module, is_main=True)
    print(f'{label:36s} entry={getattr(entry, "name", None)!r:6} arity={arity} '
          f'invokes={invokes} 追加入口块={"if __name__ == \'__main__\':" in code}')
    return module, gen, entry


def main():
    for fn in ['test_R52_ssh协议.light', 'test_R52_workflow_ptc.light']:
        src = open(os.path.join(EX, fn), encoding='utf-8').read()
        print('=' * 72)
        print('### ' + fn)
        probe('  原样(含末尾显式主())', src)
        # 去掉末尾显式 主()
        lines = src.rstrip('\n').split('\n')
        assert lines[-1].strip() == '主()', lines[-1]
        trimmed = '\n'.join(lines[:-1]) + '\n'
        module, gen, entry = probe('  去掉末尾显式主()', trimmed)
        # 逐条顶层语句归因：哪条顶层语句让 _node_calls_name 命中？
        for i, st in enumerate(module.statements):
            t = type(st).__name__
            n = getattr(st, 'name', None)
            hit = None
            if not isinstance(st, type(entry)) and t not in ('Paragraph', 'ClassDefinition'):
                hit = gen._node_calls_name(st, entry.name)
            print(f'     [{i}] {t:18s} name={n!r} 命中主={hit}')


if __name__ == '__main__':
    main()
