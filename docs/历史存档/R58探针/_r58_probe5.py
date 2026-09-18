# -*- coding: utf-8 -*-
"""R58 探针5：界定 L-174 修复的影响面。
① `因为/认为` 是否关键字；② user_definitions 在 `设甲为三` 下的内容；
③ 全语料 `为` 紧跟中文数字 的实际语境。只读。
"""
from __future__ import print_function
import os, io, re, sys

ROOT = r'G:\dswork\duan-light-merge'
LM = os.path.join(ROOT, 'light-merge')
sys.path.insert(0, os.path.join(LM, 'src'))
import lexer as L
from lexer import Lexer

out = []
out.append('=== ① 关键字表核对 ===')
for w in ('因为', '认为', '称为', '记为', '数为', '因为', '为', '作为', '行为'):
    out.append('  %-6s in ALL_KEYWORDS_WITH_VERBS=%s in ALL_KEYWORDS=%s' % (
        w, w in L._ALL_KEYWORDS_WITH_VERBS, w in L.ALL_KEYWORDS))
out.append('  Lexer._match_keyword("因为百分数",0) = %s' % (Lexer()._match_keyword('因为百分数', 0),))
out.append('  Lexer._match_keyword("甲为三",0)    = %s' % (Lexer()._match_keyword('甲为三', 0),))

out.append('')
out.append('=== ② user_definitions 实测 ===')
for src in ('设甲为三。\n打印 甲。\n', '设 甲为三。\n打印 甲。\n', '设 甲 为 三。\n'):
    ud = Lexer()._scan_user_definitions(src)
    out.append('  %r -> user_definitions=%s' % (src, sorted(ud)))
    out.append('      is_han(因为)=%s' % ('x',))

out.append('')
out.append('=== ③ 全语料 `为` 紧跟中文数字 的语境 ===')
NUMS = '零一二三四五六七八九十百千万'
pat = re.compile('为[%s]' % NUMS)
SKIP = {'.git', '__pycache__', '.venv', 'node_modules', '.mypy_cache', 'docs'}
ctxs = {}
for r in (LM, os.path.join(ROOT, 'lightharness')):
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
            for m in pat.finditer(src):
                a = m.start()
                # 取该汉字游程
                s = a
                while s > 0 and '\u4e00' <= src[s - 1] <= '\u9fff':
                    s -= 1
                e = a
                while e < len(src) and '\u4e00' <= src[e] <= '\u9fff':
                    e += 1
                run = src[s:e]
                ctxs.setdefault(run, []).append((os.path.relpath(p, ROOT),
                                                 src[max(0, a - 8):e + 6].replace('\n', '\\n')))
out.append('  共 %d 种汉字段形态 / %d 处' % (len(ctxs), sum(len(v) for v in ctxs.values())))
for run in sorted(ctxs, key=lambda k: -len(ctxs[k]))[:60]:
    out.append('    %-16s x%-3d  e.g. %s | %s' % (
        run, len(ctxs[run]), ctxs[run][0][1], ctxs[run][0][0]))

txt = '\n'.join(out)
io.open(os.path.join(ROOT, 'lightharness', '_r58_probe5.txt'), 'w', encoding='utf-8').write(txt)
print(txt[:14000])
