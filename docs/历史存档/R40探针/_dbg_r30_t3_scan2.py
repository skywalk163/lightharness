# -*- coding: utf-8 -*-
"""R30 任务3 场景定位扫描2：语料中 幂X / X类型 模式分布。"""
import glob
import os
import re
import sys

ROOT = r'G:/dswork/duan-light-merge'
sys.path.insert(0, os.path.join(ROOT, 'light-merge', 'src'))
import lexer  # noqa: E402

PATTERNS = [ROOT + '/lightharness/examples/**/*.light',
            ROOT + '/lightharness/src/**/*.light',
            ROOT + '/lightharness/tests/**/*.light',
            ROOT + '/light-merge/examples/**/*.light',
            ROOT + '/light-merge/stdlib/**/*.light',
            ROOT + '/light-merge/bootstrap/**/*.light',
            ROOT + '/light-merge/src/**/*.light',
            ROOT + '/light-merge/tests/**/*.light']
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))


def toks(text):
    try:
        return [(t.type.name, t.value) for t in lexer.Lexer(text, deterministic=True).tokenize()
                if t.type.name not in ('EOF', 'NEWLINE')]
    except Exception as e:
        return ['ERR:' + type(e).__name__]


print('=== 幂 开头的汉字串（词首 幂 + 后随汉字）===')
m2 = {}
for f in CORPUS:
    try:
        txt = open(f, encoding='utf-8', errors='replace').read()
    except Exception:
        continue
    for seg in re.findall(r'[\u4e00-\u9fff]+', txt):
        if seg.startswith('幂') and len(seg) > 1:
            m2[seg] = m2.get(seg, 0) + 1
for k in sorted(m2, key=lambda x: -m2[x]):
    print('   %-14s %4d  现状: %s' % (k, m2[k], toks(k)))

print('\n=== 含 类型 的汉字串（类型 在词中/词尾）===')
m3 = {}
for f in CORPUS:
    try:
        txt = open(f, encoding='utf-8', errors='replace').read()
    except Exception:
        continue
    for seg in re.findall(r'[\u4e00-\u9fff]+', txt):
        if '类型' in seg and not seg.startswith('类型'):
            m3[seg] = m3.get(seg, 0) + 1
for k in sorted(m3, key=lambda x: -m3[x])[:40]:
    print('   %-18s %4d  现状: %s' % (k, m3[k], toks(k)))

print('\n=== 含 记录 的汉字串 ===')
m4 = {}
for f in CORPUS:
    try:
        txt = open(f, encoding='utf-8', errors='replace').read()
    except Exception:
        continue
    for seg in re.findall(r'[\u4e00-\u9fff]+', txt):
        if '记录' in seg:
            m4[seg] = m4.get(seg, 0) + 1
for k in sorted(m4, key=lambda x: -m4[x])[:25]:
    print('   %-18s %4d  现状: %s' % (k, m4[k], toks(k)))
