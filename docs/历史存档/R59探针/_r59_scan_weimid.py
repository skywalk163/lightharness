# -*- coding: utf-8 -*-
"""R59 任务1-A 风险扫描：全语料里「汉字串含 `为` 且 `为` 后有内容」的形态。

目的：界定把「`为`+非值起始汉字」纳入切分（L-174 变体修复）会波及哪些语料串。
输出：
  - 受影响串（`为` 后有 Han 且整串前方紧邻 Han，即 _glued_to_prev 形态）及其出现文件数
  - 对照：`为` 在词尾的串（不受影响）
"""
import os
import re
import sys
from collections import Counter

ROOT = r'G:\dswork\duan-light-merge'
SKIP = {'.git', '__pycache__', '.venv', 'node_modules', '.mypy_cache'}
HAN_RUN = re.compile(r'[\u4e00-\u9fff]+')

mid_wei = Counter()      # 为 后有 Han，且整串前紧邻 Han（会受影响）
tail_wei = Counter()     # 为 在词尾（不受影响，参考）
mid_wei_files = {}
n_files = 0

for base in (os.path.join(ROOT, 'light-merge'), os.path.join(ROOT, 'lightharness')):
    for dp, dn, fn in os.walk(base):
        dn[:] = [d for d in dn if d not in SKIP]
        for f in fn:
            if not f.endswith('.light'):
                continue
            p = os.path.join(dp, f)
            n_files += 1
            try:
                txt = open(p, encoding='utf-8', errors='replace').read()
            except Exception:
                continue
            for m in HAN_RUN.finditer(txt):
                run = m.group(0)
                if '为' not in run:
                    continue
                i = run.find('为')
                # 取所有 为 的位置
                for i in [k for k, c in enumerate(run) if c == '为']:
                    if i < len(run) - 1:
                        # 为非尾：受影响候选
                        prev_han = m.start() > 0 and HAN_RUN.match(txt, m.start() - 1)
                        # 判断前一字是否 Han（glued）
                        glued = False
                        if m.start() > 0:
                            pc = txt[m.start() - 1]
                            glued = '\u4e00' <= pc <= '\u9fff'
                        key = (run, glued)
                        mid_wei[key] += 1
                        if glued:
                            mid_wei_files.setdefault(run, set()).add(p)
                    else:
                        tail_wei[run] += 1

print('语料文件数 =', n_files)
print()
print('=== A. 受影响候选：整串含 为 且 为后仍有内容 ===')
print('   （glued=True 表示整串前紧邻汉字，是 _glued_to_prev 形态 → 扩展规则会动它）')
rows = sorted(mid_wei.items(), key=lambda kv: -kv[1])
for (run, glued), c in rows[:80]:
    print('   glued=%-5s cnt=%-5d %r' % (glued, c, run))
print('   ... 共 %d 种 (run,glued) 组合' % len(rows))
print()
print('=== B. glued=True 的串 及其所在文件 ===')
gl = [(r, c, sorted(mid_wei_files.get(r, []))[:3]) for (r, g), c in mid_wei.items() if g]
gl.sort(key=lambda t: -t[1])
for r, c, fs in gl[:60]:
    print('   cnt=%-5d %r   files=%s' % (c, r, [os.path.relpath(x, ROOT) for x in fs]))
print('   glued=True 组合数 =', len(gl))
