# -*- coding: utf-8 -*-
"""R30 探针：确认 位/应/除 等字的关键字属性 + 目标词在各形态下的 token 流（CCW 有/无）。"""
import sys
sys.path.insert(0, r'G:/dswork/duan-light-merge/light-merge/src')
import lexer as L

print('=== 单字关键字属性（_match_keyword 在 pos0）===')
for ch in ['位', '应', '除', '幂', '零', '当', '非', '与', '或', '异', '记', '录', '类', '型', '测', '试']:
    kw, ln = L.Lexer()._match_keyword(ch + '为1', 0)
    kw2, ln2 = L.Lexer()._match_keyword(ch + 'X', 0)
    print('  %s : match(字+为1)=%r/%d  match(字+X)=%r/%d' % (ch, kw, ln, kw2, ln2))

print()
print('=== 关键字集合成员检查 ===')
tables = {
    '_ALL_KEYWORDS_WITH_VERBS': None,
    '_OPERATOR_KEYWORDS': None,
    '_P0A_OP': None,
    '_P0A_SEP': None,
    '_P0A_NEVER_SPLIT': None,
    '_VALUE_LITERAL_KEYWORDS': None,
    '_AWAIT_KEYWORDS': None,
    '_P0A_HARD_STMT': None,
}
for name in tables:
    v = getattr(L, name, None)
    if v is None:
        v = getattr(L.Lexer, name, None)
    tables[name] = v
for ch in ['位', '应', '除', '幂', '零', '非', '与', '或', '当']:
    where = [n for n, v in tables.items() if v and ch in v]
    print('  %s : %s' % (ch, where or '(不在任何表)'))

print()
print('=== 目标词 token 流（CCW 有 / 无）===')


def toks(text, ccw=None):
    if ccw is not None:
        L.COMMON_COMPOUND_WORDS = frozenset(ccw)
    try:
        t = L.Lexer(text, deterministic=True).tokenize()
        return [(x.type.name, x.value) for x in t if x.type.name not in ('EOF', 'NEWLINE')]
    except Exception as e:
        return ['ERR:' + type(e).__name__ + ':' + str(e)[:40]]


base = sorted(L.COMMON_COMPOUND_WORDS)
FORMS = ['返回 %s(1)', '设 x 为 [ %s ]', '如果 %s 那么 返回 1', '设 %s 为 7', '段落 %s 接收 a:\n  返回 a']
for w in ['位与', '位异或', '位或', '位非', '应当', '除非', '零除错误', '幂次', '记录类型']:
    print('--- %s ---' % w)
    for f in FORMS:
        src = f % w
        a = toks(src, base)
        b = toks(src, [x for x in base if x != w])
        mark = 'SAME' if a == b else 'DIFF'
        print('  [%s] %-24s 有=%s' % (mark, src.replace('\n', '\\n')[:24], a))
        if mark == 'DIFF':
            print('  %-30s 无=%s' % ('', b))
L.COMMON_COMPOUND_WORDS = frozenset(base)
