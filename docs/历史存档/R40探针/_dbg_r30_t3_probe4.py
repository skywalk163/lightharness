# -*- coding: utf-8 -*-
"""R30 任务3 探针4：单字 VERB_ARITY / OPERATOR_VERBS 枚举 + 语料 X类型( 与 幂X( 形态。"""
import glob
import os
import re
import sys

ROOT = r'G:/dswork/duan-light-merge'
sys.path.insert(0, os.path.join(ROOT, 'light-merge', 'src'))
import lexer  # noqa: E402
from keywords import VERB_ARITY  # noqa: E402

print('=== OPERATOR_VERBS ===', sorted(lexer.OPERATOR_VERBS))
print('\n=== 单字 VERB_ARITY（不在 HM/DUAL 的）===')
hm = lexer._P0A_HEAD_MERGE_SINGLE
dual = lexer._P0A_HEAD_MERGE_DUAL
for k in sorted(VERB_ARITY):
    if len(k) == 1:
        tag = []
        if k in dual:
            tag.append('DUAL')
        if k in hm:
            tag.append('HM')
        if k in lexer.Lexer._P0A_OP:
            tag.append('_P0A_OP')
        if k in lexer.OPERATOR_VERBS:
            tag.append('OPV')
        print('   %s  %s' % (k, ','.join(tag) or 'plain'))

PATTERNS = [ROOT + '/lightharness/examples/**/*.light',
            ROOT + '/lightharness/src/**/*.light',
            ROOT + '/lightharness/tests/**/*.light',
            ROOT + '/light-merge/examples/**/*.light',
            ROOT + '/light-merge/stdlib/**/*.light',
            ROOT + '/light-merge/bootstrap/**/*.light',
            ROOT + '/light-merge/src/**/*.light',
            ROOT + '/light-merge/tests/**/*.light']
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))


def lexable(text):
    return '\n'.join(ln[:ln.find('#')] if ln.find('#') >= 0 else ln
                     for ln in text.splitlines())


def toks(text):
    try:
        return [(t.type.name, t.value) for t in lexer.Lexer(text, deterministic=True).tokenize()
                if t.type.name not in ('EOF', 'NEWLINE')]
    except Exception as e:
        return ['ERR:' + type(e).__name__]


print('\n=== 语料中「X类型(」形态（X 为汉字，类型 在词尾且整串后紧跟 ( ）===')
m = {}
for f in CORPUS:
    try:
        txt = lexable(open(f, encoding='utf-8', errors='replace').read())
    except Exception:
        continue
    for mseg in re.finditer(r'([\u4e00-\u9fff]+)\(', txt):
        seg = mseg.group(1)
        if seg.endswith('类型') and len(seg) > 2:
            m[seg] = m.get(seg, 0) + 1
for k, v in sorted(m.items(), key=lambda x: -x[1]):
    print('   %-18s %4d  现状: %s' % (k, v, toks(k + '(')))

print('\n=== 语料中 X+左括号 且 X 以单字运算符动词开头（幂/加/减/乘/除/模…）===')
m2 = {}
for f in CORPUS:
    try:
        txt = lexable(open(f, encoding='utf-8', errors='replace').read())
    except Exception:
        continue
    for mseg in re.finditer(r'([\u4e00-\u9fff]+)\(', txt):
        seg = mseg.group(1)
        if len(seg) > 1 and seg[0] in ('幂', '取', '用', '开', '关', '等', '是', '首', '末', '余', '长', '列', '设', '写', '读'):
            m2[seg] = m2.get(seg, 0) + 1
for k, v in sorted(m2.items(), key=lambda x: -x[1])[:40]:
    print('   %-18s %4d  现状: %s' % (k, v, toks(k + '(')))
