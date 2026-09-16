# -*- coding: utf-8 -*-
"""R35 根因探针：MERGE_WHOLE 剩余 3 条，撤除后在 5 种边界形态下的实际 token 流。

目的：定位每条被「哪个关键字 / 哪条规则」劈开，为通用规则设计提供依据。
用法：python _r35_probe_根因.py
"""
import glob
import os
import sys

ROOT = r'G:/dswork/duan-light-merge'
sys.path.insert(0, os.path.join(ROOT, 'light-merge', 'src'))
import lexer  # noqa: E402

ENTRIES = ['整理模型消息', '非空块', '记录类型']

FORMS = lambda X: [
    ('F1 变量名',   '设 X 为 1'.replace('X', X)),
    ('F2 函数名',   '返回 X(1)'.replace('X', X)),
    ('F3 成员访问', '设 r 为 结果.X'.replace('X', X)),
    ('F4 段落名',   '段落 X:\n    返回 1\n'.replace('X', X)),
    ('F5 传参',     '断言相等(X, 1, "t")'.replace('X', X)),
]


def tk(src, mw=None):
    orig = lexer.Lexer._P0A_MERGE_WHOLE
    if mw is not None:
        lexer.Lexer._P0A_MERGE_WHOLE = frozenset(mw)
    try:
        return [(t.type.name, t.value) for t in
                lexer.Lexer(src, deterministic=True).tokenize()
                if t.type.name not in ('EOF', 'NEWLINE')]
    except Exception as e:
        return ['ERR:' + type(e).__name__ + ':' + str(e)[:40]]
    finally:
        lexer.Lexer._P0A_MERGE_WHOLE = orig


def fmt(toks):
    return ' | '.join('%s(%s)' % (k, v) for k, v in toks)


def main():
    print('=== 关键字资格检查（_match_keyword(text,pos) 于整串起点）===')
    _lx = lexer.Lexer('', deterministic=True)
    for w in ['模', '非', '类型', '空', '记录', '整理', '模型', '块', '消息',
              '模型消息', '空块']:
        kw = _lx._match_keyword(w, 0)
        print('  %-6s _match_keyword=%r' % (w, kw))

    print()
    print('=== 集合归属 ===')
    L = lexer.Lexer
    for w in ['模', '非', '类型']:
        ins = []
        for name in ['_P0A_OP', '_P0A_SEP', '_P0A_HEAD_SPLIT_SINGLE',
                     '_P0A_HEAD_MERGE_SINGLE', '_P0A_NEVER_SPLIT',
                     '_TRAILING_ALIAS_CLASS', '_P0A_SUFFIX_SPLIT_SINGLE',
                     '_P0A_HARD_STMT']:
            s = getattr(L, name, None)
            if s is not None and w in s:
                ins.append(name)
        print('  %-4s ∈ %s' % (w, ins if ins else '（无）'))
    print('  OPERATOR_VERBS 含 模? %s  含 非? %s' % (
        '模' in lexer.OPERATOR_VERBS, '非' in lexer.OPERATOR_VERBS))
    print('  _EMBED_MAX_MATCH_KEYWORDS = %s' % sorted(
        lexer._EMBED_MAX_MATCH_KEYWORDS))

    print()
    print('=== 逐条：基线(含条目) vs 撤除(空集合) ===')
    for e in ENTRIES:
        print('--- %s ---' % e)
        for tag, src in FORMS(e):
            a = tk(src, mw=lexer.Lexer._P0A_MERGE_WHOLE)   # 基线（全 3 条）
            b = tk(src, mw=set())                           # 撤除全部
            same = a == b
            print('  %s %s' % (tag, '一致' if same else '★变化'))
            if not same:
                print('    基线: %s' % fmt(a))
                print('    撤除: %s' % fmt(b))

    print()
    print('=== 语料真实形态扫描 ===')
    pats = [ROOT + p for p in (
        '/lightharness/examples/**/*.light', '/lightharness/src/**/*.light',
        '/lightharness/tests/**/*.light', '/light-merge/examples/**/*.light',
        '/light-merge/stdlib/**/*.light', '/light-merge/bootstrap/**/*.light',
        '/light-merge/src/**/*.light', '/light-merge/tests/**/*.light')]
    corpus = sorted(set(sum((glob.glob(g, recursive=True) for g in pats), [])))
    print('  语料文件数 = %d' % len(corpus))
    for e in ENTRIES:
        hits = []
        for f in corpus:
            s = open(f, encoding='utf-8', errors='replace').read()
            n = s.count(e)
            if n:
                hits.append((os.path.relpath(f, ROOT).replace('\\', '/'), n))
        print('  %-8s 命中 %d 处 / %d 文件' % (
            e, sum(n for _, n in hits), len(hits)))
        for p, n in hits[:8]:
            print('      %s (%d)' % (p, n))


if __name__ == '__main__':
    main()
