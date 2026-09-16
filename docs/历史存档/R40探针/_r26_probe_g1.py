# -*- coding: utf-8 -*-
"""R26 设计探针 · G1：逐字从 CS 表移除后的全语料 token 变化（内存态 monkeypatch）。

只读探针，不改磁盘。用于在任务1/2 设计前摸清 CS 30 字中哪些是「语料载重字」。
输出：_r26_probe_g1.json + 控制台摘要。
"""
import os
import sys
import json
import glob
import time

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
sys.path.insert(0, os.path.join(LIGHTP, 'src'))

PATTERNS = [HARNESS + '/examples/**/*.light', HARNESS + '/src/**/*.light',
            HARNESS + '/tests/**/*.light', LIGHTP + '/examples/**/*.light',
            LIGHTP + '/stdlib/**/*.light', LIGHTP + '/bootstrap/**/*.light',
            LIGHTP + '/src/**/*.light', LIGHTP + '/tests/**/*.light']
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))


def read(f):
    return open(f, encoding='utf-8', errors='replace').read()


def toks(mod, text):
    try:
        return repr([(t.type.name, t.value)
                     for t in mod.Lexer(text, deterministic=True).tokenize()
                     if t.type.name not in ('EOF', 'NEWLINE')])
    except Exception as e:  # noqa
        return 'ERR:' + type(e).__name__


def main():
    import lexer as L
    t0 = time.time()
    CS = L._COMPOUND_SAFE_SINGLE_KEYWORDS
    print('CS(%d): %s' % (len(CS), ''.join(sorted(CS))))
    # 预读语料
    SRC = {f: read(f) for f in CORPUS}
    print('语料 %d 文件' % len(CORPUS))

    base = {f: toks(L, SRC[f]) for f in CORPUS}

    result = {}
    for c in sorted(CS):
        newcs = frozenset(CS - {c})
        L._COMPOUND_SAFE_SINGLE_KEYWORDS = newcs
        L.Lexer.compound_safe_single_keywords = newcs
        changed = []
        for f in CORPUS:
            if c not in SRC[f]:
                continue
            if toks(L, SRC[f]) != base[f]:
                changed.append(os.path.relpath(f, ROOT).replace('\\', '/'))
        # 还原
        L._COMPOUND_SAFE_SINGLE_KEYWORDS = CS
        L.Lexer.compound_safe_single_keywords = CS
        result[c] = {'changed_count': len(changed), 'files': changed[:8]}
        print('  撤 %s -> 变化 %d 文件 %s' % (c, len(changed), changed[:3]))

    json.dump({'corpus': len(CORPUS), 'cs': ''.join(sorted(CS)), 'result': result},
              open(HARNESS + '/_r26_probe_g1.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('\n耗时 %.1fs -> _r26_probe_g1.json' % (time.time() - t0))
    zero = [c for c in result if result[c]['changed_count'] == 0]
    print('语料零变化(可删候选) %d 字: %s' % (len(zero), ''.join(zero)))


if __name__ == '__main__':
    main()
