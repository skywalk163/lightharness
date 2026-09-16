# -*- coding: utf-8 -*-
"""R28 任务3：CS表残部2字（列/类）逐字隔离验证（三重判据 G1/G2/G3）。

验证方式：monkeypatch lexer 模块级 CS 常量 + 类属性，逐字移除后与基线比对。
  G1 语料判据：全语料 844 文件 token 序列零变化
  G2 词首编译门：{字}+复合名 词首裸名 `X名 为 7` 撤掉态与基线一致
  G3 边界形态门：词尾切出/词尾并入/词首并入/独立关键字/类声明/继承 token 流不变

输出：_task3_R28_CS表2字逐条验证_证据.json + 控制台摘要
"""
import os
import sys
import json
import glob
import hashlib

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
sys.path.insert(0, os.path.join(LIGHTP, 'src'))

PATTERNS = [HARNESS + '/examples/**/*.light', HARNESS + '/src/**/*.light',
            HARNESS + '/tests/**/*.light', LIGHTP + '/examples/**/*.light',
            LIGHTP + '/stdlib/**/*.light', LIGHTP + '/bootstrap/**/*.light',
            LIGHTP + '/src/**/*.light', LIGHTP + '/tests/**/*.light']
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))

CS2 = ['列', '类']

G2_WORDS = {
    '列': ['列数', '列表'], '类': ['类别', '分类'],
}

G3_FORMS = {
    '列': ['设 列数 为 3',                      # 词首并入
           '设 序列 为 [1, 2]',                 # 词尾并入（非冒号）
           '对于 元素 在 序列: 1',               # 词尾切出（无空格，打红形态）
           '对于 元素 在 序列 : 1'],             # 词尾切出（带空格变体）
    '类': ['设 类别 为 7',                      # 词首并入
           '类 名称:',                          # 独立关键字
           '类 独立类:',                        # 类声明词尾并入（打红形态）
           '类 子类 继承 基类:'],                # 继承
}


def read(f):
    return open(f, encoding='utf-8', errors='replace').read()


def sha_text(t):
    return hashlib.sha256(t.encode('utf-8')).hexdigest()


def token_seq(text):
    import lexer
    try:
        toks = lexer.Lexer(text, deterministic=True).tokenize()
        return [(x.type.name, x.value) for x in toks
                if x.type.name not in ('EOF', 'NEWLINE')]
    except Exception as e:
        return ['ERR:' + type(e).__name__]


def set_cs(words):
    import lexer
    fs = frozenset(words)
    lexer._COMPOUND_SAFE_SINGLE_KEYWORDS = fs
    lexer.Lexer.compound_safe_single_keywords = fs


def diff_seq(a, b, limit=3):
    out = []
    for i in range(max(len(a), len(b))):
        ta = a[i] if i < len(a) else ('<END>', '')
        tb = b[i] if i < len(b) else ('<END>', '')
        if ta != tb:
            out.append('@%d %r -> %r' % (i, ta, tb))
            if len(out) >= limit:
                break
    return out


def main():
    import lexer
    base_cs = sorted(lexer._COMPOUND_SAFE_SINGLE_KEYWORDS)
    assert sorted(CS2) == base_cs, 'CS 表漂移: %s' % base_cs

    print('语料 %d 文件，构建基线 token 序列...' % len(CORPUS))
    texts, base_tokens, base_errs = {}, {}, []
    for f in CORPUS:
        rel = os.path.relpath(f, ROOT).replace('\\', '/')
        texts[rel] = read(f)
        seq = token_seq(texts[rel])
        base_tokens[rel] = seq
        if len(seq) == 1 and seq[0].startswith('ERR:'):
            base_errs.append(rel)
    print('基线完成：成功 %d | 既有失败 %d'
          % (len(base_tokens) - len(base_errs), len(base_errs)))

    g2_src = {c: ['段落 主:\n  设 %s 为 7\n  返回 %s\n' % (w, w) for w in ws]
              for c, ws in G2_WORDS.items()}
    g3_src = {c: ['段落 主:\n  %s\n  返回 0\n' % line for line in lines]
              for c, lines in G3_FORMS.items()}
    g2_base = {c: [token_seq(s) for s in ss] for c, ss in g2_src.items()}
    g3_base = {c: [token_seq(s) for s in ss] for c, ss in g3_src.items()}

    evidence = {}
    print('\n%-4s %-6s %-6s %-6s %s' % ('字', 'G1', 'G2', 'G3', '结论'))
    print('-' * 60)
    for c in CS2:
        reduced = [w for w in base_cs if w != c]
        set_cs(reduced)
        changed = {}
        for rel, t in texts.items():
            seq = token_seq(t)
            if seq != base_tokens[rel]:
                changed[rel] = diff_seq(base_tokens[rel], seq)
        g2_bad = []
        for i, w in enumerate(G2_WORDS[c]):
            cur = token_seq(g2_src[c][i])
            if cur != g2_base[c][i]:
                g2_bad.append({'word': w, 'diff': diff_seq(g2_base[c][i], cur)})
        g3_bad = []
        for i, line in enumerate(G3_FORMS[c]):
            cur = token_seq(g3_src[c][i])
            if cur != g3_base[c][i]:
                g3_bad.append({'form': line, 'diff': diff_seq(g3_base[c][i], cur)})
        set_cs(base_cs)

        ok = (not changed) and (not g2_bad) and (not g3_bad)
        evidence[c] = {
            'g1_changed_files': changed, 'g1_changed_count': len(changed),
            'g2_fail': g2_bad, 'g3_fail': g3_bad,
            'g1_pass': not changed, 'g2_pass': not g2_bad, 'g3_pass': not g3_bad,
            'verdict': '可删' if ok else '保留',
        }
        print('%-4s %-6s %-6s %-6s %s' % (
            c, 'PASS' if not changed else 'FAIL(%d)' % len(changed),
            'PASS' if not g2_bad else 'FAIL', 'PASS' if not g3_bad else 'FAIL',
            evidence[c]['verdict']))
        for rel, d in list(changed.items())[:5]:
            print('     G1 %s: %s' % (rel, d[:2]))
        for bad in g3_bad:
            print('     G3 %s: %s' % (bad['form'], bad['diff'][:2]))

    out = os.path.join(HARNESS, '_task3_R28_CS表2字逐条验证_证据.json')
    json.dump({'cs2': CS2, 'corpus_files': len(CORPUS),
               'base_err_files': base_errs, 'evidence': evidence},
              open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    deletable = [c for c in CS2 if evidence[c]['verdict'] == '可删']
    print('-' * 60)
    print('可删 %d 字: %s' % (len(deletable), ''.join(deletable)))
    print('保留 %d 字: %s' % (2 - len(deletable),
                              ''.join(c for c in CS2 if c not in deletable)))
    print('证据文件: %s' % out)


if __name__ == '__main__':
    main()
