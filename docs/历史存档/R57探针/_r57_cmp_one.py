# -*- coding: utf-8 -*-
"""对单个 .light 文件比较 base/patched lexer 的 token 流差异。"""
import sys, os, io, difflib, importlib.util

ROOT = r'G:\dswork\duan-light-merge'
LM = os.path.join(ROOT, 'light-merge')
sys.path.insert(0, os.path.join(LM, 'src'))
sys.path.insert(0, LM)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.Lexer


Base = load('lexer_base_cmp', sys.argv[1])
Patched = load('lexer_patched_cmp', sys.argv[2])
target = sys.argv[3]
src = io.open(target, encoding='utf-8').read()


def toks(L):
    try:
        return [(t.type.name, t.value) for t in L().tokenize(src)]
    except Exception as e:  # noqa: BLE001
        return [('<EXC>', f'{type(e).__name__}: {e}')]


tb, tp = toks(Base), toks(Patched)
print(f'target={target}')
print(f'base tokens={len(tb)}  patched tokens={len(tp)}')
sm = difflib.SequenceMatcher(a=[str(x) for x in tb], b=[str(x) for x in tp], autojunk=False)
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == 'equal':
        continue
    print(f'  {tag}: base[{i1}:{i2}]={tb[i1:i2]}')
    print(f'  {" "*len(tag)}  patched[{j1}:{j2}]={tp[j1:j2]}')
