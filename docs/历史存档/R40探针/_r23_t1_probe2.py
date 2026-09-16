# -*- coding: utf-8 -*-
"""R23 任务1 细粒度探针：逐个片段单独 tokenize。"""
import sys

ROOT = r'G:/dswork/duan-light-merge'
sys.path.insert(0, ROOT + '/light-merge/src')
import lexer as L  # noqa
from keywords import ALL_KEYWORDS, VERB_ARITY  # noqa

FRAGS = ['己', '己任', '自己', '自己的', '错误己', '爱己', '知己', '己方', '己见']


def show(tag, src):
    try:
        toks = L.Lexer(src).tokenize()
    except Exception as e:  # noqa
        print(f'  {tag!r}: ERR {type(e).__name__}: {e}')
        return
    print(f'  {tag!r}: ' + ' | '.join(f'{t.type.name}={t.value!r}' for t in toks))


cur = frozenset(L._TRAILING_ALIAS_MERGE)
print('== 有表 ==')
for f in FRAGS:
    show(f, f)
print('== 无表 ==')
L._TRAILING_ALIAS_MERGE = frozenset()
try:
    for f in FRAGS:
        show(f, f)
finally:
    L._TRAILING_ALIAS_MERGE = cur

print('\n== 静态事实 ==')
print('己 in ALL_KEYWORDS      :', '己' in ALL_KEYWORDS)
print('己 in VERB_ARITY        :', '己' in VERB_ARITY)
print('己 in COMPOUND_SAFE     :', '己' in L._COMPOUND_SAFE_SINGLE_KEYWORDS)
print('己 in _P0A_NEVER_SPLIT  :', '己' in getattr(L.Lexer, '_P0A_NEVER_SPLIT', set()))
print('己 in _P0A_OP           :', '己' in getattr(L.Lexer, '_P0A_OP', set()))
print('己 in _OPERATOR_KEYWORDS:', '己' in L._OPERATOR_KEYWORDS)
print('TAM                     :', sorted(cur))
