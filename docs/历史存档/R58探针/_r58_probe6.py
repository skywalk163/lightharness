# -*- coding: utf-8 -*-
"""R58 探针6：对 A/B 变化文件做 base vs new 的逐 token 差异（含行号/上下文）。只读。"""
import io, os, sys, difflib, importlib.util

ROOT = r'G:\dswork\duan-light-merge'
LM = os.path.join(ROOT, 'light-merge')
sys.path.insert(0, os.path.join(LM, 'src'))
sys.path.insert(0, LM)


def load(p, n):
    spec = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


b = load(os.path.join(LM, '_r58_lexer_base.py'), 'lexB')
n = load(os.path.join(LM, 'src', 'lexer.py'), 'lexN')

FILES = ['light-merge/bootstrap/release/stdlib/字符串常量.light',
         'light-merge/examples/modules/main.light',
         'lightharness/examples/test_R24_运算符单字守卫.light']

out = []


def sig(mod, src):
    return ['%s %r' % (t.type.name, t.value) for t in mod.Lexer(src).tokenize()
            if t.type.name not in ('EOF',)]


for f in FILES:
    p = os.path.join(ROOT, f)
    src = io.open(p, encoding='utf-8').read()
    sb, sn = sig(b, src), sig(n, src)
    out.append('=' * 78)
    out.append('### %s   (token %d -> %d)' % (f, len(sb), len(sn)))
    sm = difflib.SequenceMatcher(a=sb, b=sn, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        out.append('  [%s] base[%d:%d] new[%d:%d]' % (tag, i1, i2, j1, j2))
        out.append('      base: %s' % (sb[max(0, i1 - 3):i2 + 3],))
        out.append('      new : %s' % (sn[max(0, j1 - 3):j2 + 3],))
    out.append('')

txt = '\n'.join(out)
io.open(os.path.join(ROOT, 'lightharness', '_r58_probe6.txt'), 'w', encoding='utf-8').write(txt)
print(txt)
