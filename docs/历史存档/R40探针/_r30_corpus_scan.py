# -*- coding: utf-8 -*-
"""R30 风险扫描：语料中以 位/应/除 开头的汉字串，及其后随字是否关键字。"""
import os
import sys
import glob
import collections
sys.path.insert(0, r'G:/dswork/duan-light-merge/light-merge/src')
import lexer as L

ROOT = r'G:/dswork/duan-light-merge'
PAT = [ROOT + '/lightharness/examples/**/*.light', ROOT + '/lightharness/src/**/*.light',
       ROOT + '/lightharness/tests/**/*.light', ROOT + '/light-merge/examples/**/*.light',
       ROOT + '/light-merge/stdlib/**/*.light', ROOT + '/light-merge/bootstrap/**/*.light',
       ROOT + '/light-merge/src/**/*.light', ROOT + '/light-merge/tests/**/*.light']
files = sorted(set(sum((glob.glob(g, recursive=True) for g in PAT), [])))

HAN = lambda c: '\u4e00' <= c <= '\u9fff'
matcher = L.Lexer()
HEADS = ['位', '应', '除']
runs = collections.Counter()
kw_runs = collections.Counter()
for f in files:
    try:
        t = open(f, encoding='utf-8', errors='replace').read()
    except Exception:
        continue
    i = 0
    n = len(t)
    while i < n:
        if HAN(t[i]):
            j = i
            while j < n and HAN(t[j]):
                j += 1
            run = t[i:j]
            if run[0] in HEADS:
                runs[run] += 1
                if len(run) > 1:
                    kw, ln = matcher._match_keyword(run, 1)
                    if kw:
                        kw_runs[(run, kw)] += 1
            i = j
        else:
            i += 1

print('=== 以 位/应/除 开头的汉字串（全部）===')
for run, c in sorted(runs.items()):
    print('  %-12s x%d' % (run, c))
print()
print('=== 其中「第2字起可匹配关键字」的串（新规则会并入，需确认不误伤）===')
for (run, kw), c in sorted(kw_runs.items()):
    print('  %-12s 后随关键字=%-6s x%d' % (run, kw, c))
