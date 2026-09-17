# -*- coding: utf-8 -*-
"""度量：语料中「入口存在但 arity>0（当前静默不调用）」的文件数。"""
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LM = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(LM, 'src'))
sys.path.insert(0, LM)

from light_parser_v3 import LightParser  # noqa: E402
from code_generator import PythonCodeGenerator  # noqa: E402

ROOTS = [r'G:\dswork\duan-light-merge\lightharness\examples',
         r'G:\dswork\duan-light-merge\lightharness\src',
         r'G:\dswork\duan-light-merge\light-merge\examples']


def main():
    n = 0
    hits = []
    for root in ROOTS:
        for p in sorted(glob.glob(os.path.join(root, '**', '*.light'), recursive=True)):
            src = open(p, encoding='utf-8').read()
            try:
                module = LightParser().parse(src)
            except Exception:  # noqa: BLE001
                continue
            gen = PythonCodeGenerator()
            entry = gen._find_entry_paragraph(module)
            if entry is None:
                continue
            n += 1
            a = gen._paragraph_arity(entry)
            if a > 0:
                hits.append((os.path.relpath(p, r'G:\dswork\duan-light-merge'), a))
    print(f'有入口段落的文件 {n} 个；其中 arity>0（当前静默不调用）{len(hits)} 个')
    for f, a in hits[:30]:
        print(f'   - {f}  arity={a}')


if __name__ == '__main__':
    main()
