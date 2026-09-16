# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'G:/dswork/duan-light-merge/light-merge/src')
import lexer as L

EMBED = '_EMBED_MAX_MATCH_KEYWORDS'

def toks(src):
    return [(t.type.name, t.value) for t in L.Lexer(src).tokenize()]

tests = ['行为','末位行为','返回表','尝试记录','作为','成为','认为','为了',
         '设 甲 为 空','设 合并为 {}','断言为真(条件)','段落 断言为真 接收:']
for s in tests:
    cur = toks(s)
    saved = getattr(L, EMBED)
    setattr(L, EMBED, frozenset())
    try:
        emp = toks(s)
    finally:
        setattr(L, EMBED, saved)
    print('SRC:', repr(s))
    print('  WITH   :', cur)
    print('  WITHOUT:', emp)
    print()
