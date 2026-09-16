# -*- coding: utf-8 -*-
"""R24 探索 v2：候选「通用化配置」对全语料 token 流的影响（内存态，不改源码）。

修正 v1 的建模错误：撤掉 CS 条目后 `_TRAILING_ALIAS_CLASS` 必须**按推导式重算**
（撤掉的字会落进「词尾并入类别」），v1 把 trailing 冻结成 21 字 ⇒ 假回归。

配置（CS 指 `_COMPOUND_SAFE_SINGLE_KEYWORDS` 的**显式**成员；
「有效构词保护集合」= CS ∪ _VALUE_LITERAL_KEYWORDS，模拟值字面量按类别参与）：
  C0 基线：CS=30, trailing=21
  C1 值字面量类别：显式 CS 保持 30、有效集合 = CS ∪ 假（行为等价 CS∪{假}），trailing=21
  C3 删①冗余13条：CS=17, trailing=derive(CS)=34
  C4 目标配置：删①冗余13条 + 真/空改由值字面量类别承担：CS=15, trailing=34，
      有效集合 = 17
  C5 激进：CS=∅（整表删除，仅留值字面量类别），trailing=derive(∅)
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
    HARNESS + '/examples/**/*.light',
    HARNESS + '/src/**/*.light',
    LIGHTP + '/examples/**/*.light',
    LIGHTP + '/stdlib/**/*.light',
    LIGHTP + '/bootstrap/**/*.light',
    LIGHTP + '/src/**/*.light',
    LIGHTP + '/tests/**/*.light',
]
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))

REDUNDANT13 = set('例出则常引接是末试跳过长首')
VALUE = frozenset({'真', '假', '空'})


def load_module():
    spec = importlib.util.spec_from_file_location('_lexer_explore', LEXER)
    mod = importlib.util.module_from_spec(spec)
    sys.modules['_lexer_explore'] = mod
    spec.loader.exec_module(mod)
    return mod


def main():
    mod = load_module()
    CS0 = frozenset(mod._COMPOUND_SAFE_SINGLE_KEYWORDS)
    TR0 = frozenset(mod.Lexer._TRAILING_ALIAS_CLASS)
    TEXTS = {f: open(f, encoding='utf-8', errors='replace').read() for f in CORPUS}
    print('语料 %d 文件 | CS %d | trailing %d' % (len(CORPUS), len(CS0), len(TR0)))

    def derive(explicit_cs):
        return frozenset(
            k for k in (mod._ALL_KEYWORDS_WITH_VERBS - mod.Lexer._P0A_OP
                        - mod._OPERATOR_KEYWORDS - mod.Lexer._P0A_NEVER_SPLIT
                        - mod._AWAIT_KEYWORDS - explicit_cs - mod._VALUE_LITERAL_KEYWORDS)
            if len(k) == 1)

    def dump(explicit_cs, effect_extra, tr):
        eff = frozenset(explicit_cs) | frozenset(effect_extra)
        mod._COMPOUND_SAFE_SINGLE_KEYWORDS = eff
        mod.Lexer.compound_safe_single_keywords = eff
        mod.Lexer._TRAILING_ALIAS_CLASS = tr
        out = {}
        for f, t in TEXTS.items():
            try:
                out[f] = [(x.type.name, x.value) for x in mod.Lexer(t).tokenize()]
            except Exception as e:  # noqa
                out[f] = [('ERR', type(e).__name__)]
        return out

    base = dump(CS0, set(), TR0)
    assert dump(CS0, set(), TR0) == base, '[A] 自检失败'

    C3 = CS0 - REDUNDANT13
    C4 = C3 - {'真', '空'}
    configs = [
        ('C1 值字面量类别(=CS+假)', CS0, VALUE, TR0),
        ('C3 删①冗余13条', C3, set(), derive(C3)),
        ('C4 目标(删13+真空改类别)', C4, VALUE, derive(C4)),
        ('C5 整表清空(仅值字面量类别)', frozenset(), VALUE, derive(frozenset())),
    ]
    for name, cs, extra, tr in configs:
        d = dump(cs, extra, tr)
        ch = sorted(f for f in CORPUS if base[f] != d[f])
        print('\n### %s | 显式CS=%d 有效=%d trailing=%d | 变化 %d 文件'
              % (name, len(cs), len(frozenset(cs) | frozenset(extra)), len(tr), len(ch)))
        print('    trailing:', ''.join(sorted(tr)))
        for f in ch[:8]:
            a, b = base[f], d[f]
            i = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]),
                     min(len(a), len(b)))
            lo = max(0, i - 3)
            print('   ', os.path.relpath(f, ROOT))
            print('       BASE', a[lo:i + 5])
            print('       NEW ', b[lo:i + 5])
    dump(CS0, set(), TR0)
    return 0


if __name__ == '__main__':
    sys.exit(main())
