# -*- coding: utf-8 -*-
"""1) 验证「顶层引用（非调用）入口名 → 静默抑制入口块」
2) 度量收紧 gate3（只认 ParagraphCall）对全语料的影响面。"""
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LM = os.path.dirname(HERE)
PY = os.path.join(LM, '.venv', 'Scripts', 'python.exe')
sys.path.insert(0, os.path.join(LM, 'src'))
sys.path.insert(0, LM)

from light_parser_v3 import LightParser  # noqa: E402
from code_generator import PythonCodeGenerator, Paragraph, ParagraphCall  # noqa: E402

REF_CASE = '段落 主:\n  打印("MAIN-OK")\n\n设 回调 为 主\n'


def run_case():
    p = os.path.join(HERE, '_refcase.light')
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        f.write(REF_CASE)
    d = subprocess.run([PY, os.path.join(HERE, 'dump.py'), p], cwd=LM,
                       capture_output=True, text=True, encoding='utf-8')
    for ln in (d.stdout or '').split('\n'):
        s = ln.strip()
        if s.startswith(('entry =', 'arity =', 'module_invokes_entry', '_entry_call')):
            print('   ', s)
    r = subprocess.run([PY, '-m', 'cli.light', 'run', p], cwd=LM,
                       capture_output=True, text=True, encoding='utf-8', timeout=120)
    print(f'    rc={r.returncode}  输出={[x for x in (r.stdout or "").split(chr(10)) if x.strip()]}')
    print('    err=', (r.stderr or '').strip().split('\n')[0][:100])


ROOTS = [r'G:\dswork\duan-light-merge\lightharness\examples',
         r'G:\dswork\duan-light-merge\lightharness\src',
         r'G:\dswork\duan-light-merge\light-merge\examples']


def top_call_names(module):
    """顶层（非段落/类）语句中，作为 ParagraphCall 出现的名字集合。"""
    names = set()
    gen = PythonCodeGenerator()

    def walk(node, depth=0):
        if node is None or depth > 12:
            return
        if isinstance(node, ParagraphCall):
            names.add(getattr(node, 'name', None))
            return
        if isinstance(node, (str, int, float, bool, bytes)):
            return
        if isinstance(node, (list, tuple)):
            for x in node:
                walk(x, depth + 1)
            return
        if isinstance(node, (Paragraph,)):
            return
        for child in gen._iter_child_nodes(node):
            walk(child, depth + 1)

    for stmt in getattr(module, 'statements', None) or []:
        if isinstance(stmt, Paragraph):
            continue
        walk(stmt)
    return names


def main():
    print('=== 1) 顶层引用入口名（非调用）===')
    run_case()
    print()
    print('=== 2) 全语料影响面：invokes=True 但没有顶层 ParagraphCall 主 的文件 ===')
    refits = []
    for root in ROOTS:
        for p in sorted(glob.glob(os.path.join(root, '*.light'))):
            src = open(p, encoding='utf-8').read()
            if '主' not in src:
                continue
            try:
                module = LightParser().parse(src)
            except Exception:  # noqa: BLE001
                continue
            gen = PythonCodeGenerator()
            entry = gen._find_entry_paragraph(module)
            if entry is None or gen._paragraph_arity(entry) != 0:
                continue
            if gen._module_invokes_entry(module, entry):
                calls = top_call_names(module)
                if entry.name not in calls:
                    refits.append(os.path.relpath(p, r'G:\dswork\duan-light-merge'))
    print(f'受影响文件数（引用但未调用入口名）：{len(refits)}')
    for f in refits:
        print('   -', f)


if __name__ == '__main__':
    main()
