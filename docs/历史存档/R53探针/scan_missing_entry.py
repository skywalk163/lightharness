# -*- coding: utf-8 -*-
"""全库扫描：源文件含 `段落 主` 但产物缺入口调用块（=L-172 静默阻断可疑点）。"""
import glob
import os
import sys

LM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(LM, 'src'))
sys.path.insert(0, LM)

from light_parser_v3 import LightParser  # noqa: E402
from code_generator import PythonCodeGenerator  # noqa: E402
from code_generator import Paragraph  # noqa: E402

ROOTS = [r'G:\dswork\duan-light-merge\lightharness\examples',
         r'G:\dswork\duan-light-merge\light-merge\examples',
         r'G:\dswork\duan-light-merge\lightharness\src']


def main():
    bad = []
    total = 0
    for root in ROOTS:
        for p in sorted(glob.glob(os.path.join(root, '**', '*.light'), recursive=True)):
            try:
                src = open(p, encoding='utf-8').read()
            except Exception:
                continue
            total += 1
            if '主' not in src:
                continue
            try:
                module = LightParser().parse(src)
                gen = PythonCodeGenerator()
                code = gen.generate(module, is_main=True)
            except Exception as e:  # noqa: BLE001
                bad.append((p, 'EXC:' + type(e).__name__, str(e)[:60]))
                continue
            entry = gen._find_entry_paragraph(module)
            has_block = "if __name__ == '__main__':" in code
            if entry is not None and not has_block:
                arity = gen._paragraph_arity(entry)
                inv = gen._module_invokes_entry(module, entry)
                bad.append((p, f'arity={arity} invokes={inv}', ''))
    print(f'扫描 {total} 个 .light；可疑 {len(bad)} 个')
    for p, why, extra in bad:
        print('  -', os.path.relpath(p, r'G:\dswork\duan-light-merge'), '|', why, extra)


if __name__ == '__main__':
    main()
