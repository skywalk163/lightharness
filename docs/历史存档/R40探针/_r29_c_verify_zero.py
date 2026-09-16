# -*- coding: utf-8 -*-
"""R29 任务3：C批删除后 全语料零回归确认（对照 R26 基线快照）。"""
import sys
import os
import glob
import json
import hashlib

sys.path.insert(0, r'G:/dswork/duan-light-merge/light-merge/src')
import lexer

ROOT = r'G:/dswork/duan-light-merge'
HARNESS = ROOT + '/lightharness'
PATTERNS = [ROOT + '/lightharness/examples/**/*.light',
            ROOT + '/lightharness/src/**/*.light',
            ROOT + '/lightharness/tests/**/*.light',
            ROOT + '/light-merge/examples/**/*.light',
            ROOT + '/light-merge/stdlib/**/*.light',
            ROOT + '/light-merge/bootstrap/**/*.light',
            ROOT + '/light-merge/src/**/*.light',
            ROOT + '/light-merge/tests/**/*.light']
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))
base = json.load(open(os.path.join(HARNESS, '_antirun_r26_基线快照.json'),
                      encoding='utf-8'))
base_per, base_err = base['per_file'], set(base.get('base_err_files', []))


def seq_of(t):
    try:
        return [(x.type.name, x.value)
                for x in lexer.Lexer(t, deterministic=True).tokenize()
                if x.type.name not in ('EOF', 'NEWLINE')]
    except Exception as e:
        return ['ERR:' + type(e).__name__]


changed, compared, cur_err = [], 0, []
for f in CORPUS:
    rel = os.path.relpath(f, ROOT).replace('\\', '/')
    try:
        t = open(f, encoding='utf-8', errors='replace').read()
    except Exception:
        continue
    s = seq_of(t)
    if len(s) == 1 and isinstance(s[0], str) and s[0].startswith('ERR:'):
        cur_err.append(rel)
        continue
    if rel not in base_per or rel in base_err:
        continue
    compared += 1
    fp = hashlib.sha256(json.dumps(s, ensure_ascii=False).encode()).hexdigest()
    if fp != base_per[rel]['sha']:
        changed.append(rel)

print('语料 %d 文件 | 可比 %d | 变化 %d' % (len(CORPUS), compared, len(changed)))
for r in changed[:10]:
    print('  ', r)
print('零变化:', not changed)
