# -*- coding: utf-8 -*-
"""R30 任务4 前置扫描：全语料中「IDENTIFIER 以 _ 结尾且后继为汉字」的形态清单。

目的：设计方案A 判据前，先精确掌握真实语料所有 `xxx_` + 汉字的 token 上下文，
确认哪些形态必须保持劈开（如 R27 反向的 测试_返回真/测试_捕获到），
哪些形态在 CCW=OFF 下会劈开需要方案A 救回（测试_生成问候语调用）。
"""
import glob
import importlib
import json
import os
import sys

ROOT = r'G:/dswork/duan-light-merge'
sys.path.insert(0, os.path.join(ROOT, 'light-merge', 'src'))
import lexer as L

PATTERNS = [ROOT + '/lightharness/examples/**/*.light',
            ROOT + '/lightharness/src/**/*.light',
            ROOT + '/lightharness/tests/**/*.light',
            ROOT + '/light-merge/examples/**/*.light',
            ROOT + '/light-merge/stdlib/**/*.light',
            ROOT + '/light-merge/bootstrap/**/*.light',
            ROOT + '/light-merge/src/**/*.light',
            ROOT + '/light-merge/tests/**/*.light']
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))
print('语料文件数：%d' % len(CORPUS))

def read(f):
    return open(f, encoding='utf-8', errors='replace').read()

HITS = []  # (rel, lineno, tokens around)
total_seqs = 0
for f in CORPUS:
    rel = os.path.relpath(f, ROOT).replace('\\', '/')
    try:
        toks = L.Lexer(read(f), deterministic=True).tokenize()
    except Exception as e:
        continue
    seq = [(t.type.name, t.value, t.line) for t in toks if t.type.name not in ('EOF', 'NEWLINE')]
    total_seqs += 1
    for idx in range(len(seq) - 1):
        tname, tval, tline = seq[idx]
        if tname == 'IDENTIFIER' and tval.endswith('_'):
            nxt_name, nxt_val, nxt_line = seq[idx + 1]
            # 后继为汉字开头的 token
            if isinstance(nxt_val, str) and nxt_val and '\u4e00' <= nxt_val[0] <= '\u9fff':
                ctx_before = seq[idx - 2][1] if idx >= 2 else ''
                ctx_prev = seq[idx - 1][1] if idx >= 1 else ''
                HITS.append((rel, tline, tval, nxt_name, nxt_val, (ctx_before, ctx_prev)))

print('\n=== IDENTIFIER 以 _ 结尾 且 后继为汉字 的 token 对（%d 处）===' % len(HITS))
for rel, line, tval, nxt_name, nxt_val, (b, p) in HITS:
    print('  %-58s :%4d  [%s](%s) -> [%s](%s)   前文:(%s|%s)' % (
        rel, line, tval, 'I', nxt_val, nxt_name, b, p))

# 汇总同文件是否注册了 tval 前缀（预扫描）
print('\n=== 各文件 user_definitions 是否含该 _ 结尾前缀 ===')
from collections import defaultdict
byfile = defaultdict(set)
for rel, line, tval, nxt_name, nxt_val, ctx in HITS:
    byfile[rel].add(tval)
for rel, vals in sorted(byfile.items()):
    print('  %s : %s' % (rel, sorted(vals)))