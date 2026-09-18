# -*- coding: utf-8 -*-
"""R58 探针3：扫描全语料中「中文数字 + HM/DUAL 字 + 中文数字」形态，评估 R30 收窄的影响面。只读。"""
from __future__ import print_function
import os, io, re, sys

ROOT = r'G:\dswork\duan-light-merge'
SKIP = {'.git', '__pycache__', '.venv', 'node_modules', '.mypy_cache'}
sys.path.insert(0, os.path.join(ROOT, 'light-merge', 'src'))
import lexer as L

NUMS = ''.join(sorted(L._SIMPLE_CHINESE_NUMBERS))
CLS = ''.join(sorted(L._R30_NUM_HEAD_MERGE_CLASS))
# 数字 + 正面类别字 + 数字
pat = re.compile('[%s][%s][%s]' % (re.escape(NUMS), re.escape(CLS), re.escape(NUMS)))
names = re.compile('[%s][%s][%s]' % (re.escape(NUMS), re.escape(CLS), re.escape(NUMS)))
# 名字类：数字+类别字+数字 之后仍接汉字（如 一模一样 / 一分为二 不是，模是DUAL）
pat2 = re.compile('[%s][%s][%s][\u4e00-\u9fff]' % (re.escape(NUMS), re.escape(CLS), re.escape(NUMS)))

hits = {}
hits2 = {}
other = {}
for r in (os.path.join(ROOT, 'light-merge'), os.path.join(ROOT, 'lightharness')):
    for dp, dn, fn in os.walk(r):
        dn[:] = [d for d in dn if d not in SKIP]
        for f in fn:
            if not f.endswith('.light'):
                continue
            p = os.path.join(dp, f)
            try:
                src = io.open(p, encoding='utf-8').read()
            except Exception:
                continue
            for m in re.finditer('[%s][%s][%s]' % (re.escape(NUMS), re.escape(CLS), re.escape(NUMS)), src):
                frag = src[max(0, m.start() - 3):m.end() + 4].replace('\n', '\\n')
                key = m.group(0)
                hits.setdefault(key, []).append((os.path.relpath(p, ROOT), frag))
            for m in pat2.finditer(src):
                key = m.group(0)
                hits2.setdefault(key, []).append((os.path.relpath(p, ROOT),
                                                  src[max(0, m.start() - 3):m.end() + 3].replace('\n', '\\n')))

print('=== [数字][HM/DUAL][数字] 命中（四字及以上会被 pat2 覆盖） ===')
for k in sorted(hits, key=lambda k: -len(hits[k])):
    print('  %-6s x%d   e.g. %s' % (k, len(hits[k]), hits[k][0][1]))
print()
print('=== [数字][HM/DUAL][数字][汉字] （疑为名字而非算术） ===')
for k in sorted(hits2, key=lambda k: -len(hits2[k])):
    print('  %-8s x%d   e.g. %s | %s' % (k, len(hits2[k]), hits2[k][0][1], hits2[k][0][0]))

print()
print('=== 指名核对 ===')
for w in ('一模一样', '一分为二', '一举两得', '三加五', '一加一', '三乘五', '零除错误',
          '百分之百', '一如既往', '一五一十'):
    tot = 0
    for k, v in list(hits.items()) + list(hits2.items()):
        if w.startswith(k) or k.startswith(w):
            tot += len(v)
    print('  %-8s 相关命中 %d' % (w, tot))
