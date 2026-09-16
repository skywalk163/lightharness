# -*- coding: utf-8 -*-
"""R24 任务2/3 取证：每个「真护栏」单字的保护场景 diff（真实口径 V2）。

对每个真护栏单字 c：撤掉 c（CS−{c}）并重算 `_TRAILING_ALIAS_CLASS`，
对含 c 的语料文件 dump token，打印首个差异窗口，用于归纳保护场景类型
（词首并入 / 词中并入 / 词尾并入 / 运算符-值字面量守卫）。
"""
import os
import sys
import glob
import importlib.util

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
LEXER = os.path.join(LIGHTP, 'src', 'lexer.py')
sys.path.insert(0, os.path.join(LIGHTP, 'src'))

PATTERNS = [
    HARNESS + '/examples/**/*.light', HARNESS + '/src/**/*.light',
    LIGHTP + '/examples/**/*.light', LIGHTP + '/stdlib/**/*.light',
    LIGHTP + '/bootstrap/**/*.light', LIGHTP + '/src/**/*.light',
    LIGHTP + '/tests/**/*.light',
]
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))
GUARDS = list('列到对断模段的类自配') + list('乘加真')

spec = importlib.util.spec_from_file_location('_lx_scn', LEXER)
mod = importlib.util.module_from_spec(spec)
sys.modules['_lx_scn'] = mod
spec.loader.exec_module(mod)
CS = frozenset(mod._COMPOUND_SAFE_SINGLE_KEYWORDS)
TR0 = frozenset(mod.Lexer._TRAILING_ALIAS_CLASS)
TEXTS = {f: open(f, encoding='utf-8', errors='replace').read() for f in CORPUS}


def derive(cs):
    return frozenset(
        k for k in (mod._ALL_KEYWORDS_WITH_VERBS - mod.Lexer._P0A_OP
                    - mod._OPERATOR_KEYWORDS - mod.Lexer._P0A_NEVER_SPLIT
                    - mod._AWAIT_KEYWORDS - cs - mod._VALUE_LITERAL_KEYWORDS)
        if len(k) == 1)


def setcfg(cs, tr):
    mod._COMPOUND_SAFE_SINGLE_KEYWORDS = cs
    mod.Lexer.compound_safe_single_keywords = cs
    mod.Lexer._TRAILING_ALIAS_CLASS = tr


def toks(t):
    try:
        return [(x.type.name, x.value) for x in mod.Lexer(t).tokenize()]
    except Exception as e:  # noqa
        return [('ERR', type(e).__name__)]


setcfg(CS, TR0)
BASE = {f: toks(t) for f, t in TEXTS.items()}

out = []
for c in GUARDS:
    setcfg(CS - {c}, derive(CS - {c}))
    ch = []
    for f in CORPUS:
        if c not in TEXTS[f]:
            continue
        d = toks(TEXTS[f])
        if d != BASE[f]:
            ch.append((f, d))
    setcfg(CS, TR0)
    out.append('===== %s  变化 %d 文件 =====' % (c, len(ch)))
    for f, d in ch[:5]:
        a = BASE[f]
        i = next((k for k in range(min(len(a), len(d))) if a[k] != d[k]),
                 min(len(a), len(d)))
        lo = max(0, i - 4)
        out.append('  %s' % os.path.relpath(f, ROOT))
        out.append('    BASE %s' % (a[lo:i + 6],))
        out.append('    NEW  %s' % (d[lo:i + 6],))
    print('\n'.join(out[-1 - 3 * min(len(ch), 5):]))

open(HARNESS + '/_r24_t3_guard_scenarios.txt', 'w', encoding='utf-8').write('\n'.join(out))
print('\n写入 _r24_t3_guard_scenarios.txt')
