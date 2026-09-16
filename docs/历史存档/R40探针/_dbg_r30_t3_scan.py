# -*- coding: utf-8 -*-
"""R30 任务3 场景定位扫描：全语料中 零除错误/幂次/记录类型 及其同形模式的出现。"""
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
print('语料文件数：', len(CORPUS))

TARGETS = ['零除错误', '幂次', '记录类型']
hits = {t: [] for t in TARGETS}
for f in CORPUS:
    try:
        txt = open(f, encoding='utf-8', errors='replace').read()
    except Exception:
        continue
    rel = os.path.relpath(f, ROOT).replace('\\', '/')
    for t in TARGETS:
        for m in re.finditer(re.escape(t), txt):
            line = txt.count('\n', 0, m.start()) + 1
            hits[t].append((rel, line))

for t, h in hits.items():
    print('\n=== %s：%d 次 / %d 文件 ===' % (t, len(h), len(set(r for r, _ in h))))
    for rel, ln in h:
        print('   %s:%d' % (rel, ln))

# 模式扫描：以中文数字开头、第二字是关键字的汉字串
print('\n\n=== 模式：中文数字词首 + 关键字开头余部（语料出现统计） ===')
nums = sorted(lexer._SIMPLE_CHINESE_NUMBERS)
kw_by_len = {}
for w in lexer._ALL_KEYWORDS_WITH_VERBS:
    kw_by_len.setdefault(len(w), set()).add(w)


def match_kw_at(s, p):
    for L in sorted(kw_by_len, reverse=True):
        if p + L <= len(s) and s[p:p + L] in kw_by_len[L]:
            return s[p:p + L], L
    return None, 0


pat_count = {}
pat_files = {}
for f in CORPUS:
    try:
        txt = open(f, encoding='utf-8', errors='replace').read()
    except Exception:
        continue
    rel = os.path.relpath(f, ROOT).replace('\\', '/')
    for m in re.finditer(r'[\u4e00-\u9fff]+', txt):
        seg = m.group(0)
        if seg[0] in nums and len(seg) >= 2 and seg[1] not in nums:
            kw, L = match_kw_at(seg, 1)
            if kw:
                key = seg[0] + kw
                pat_count[key] = pat_count.get(key, 0) + 1
                pat_files.setdefault(key, set()).add(rel)
for key in sorted(pat_count, key=lambda k: -pat_count[k]):
    print('   %-12s %5d 次 / %d 文件  e.g. %s'
          % (key, pat_count[key], len(pat_files[key]), sorted(pat_files[key])[0]))
