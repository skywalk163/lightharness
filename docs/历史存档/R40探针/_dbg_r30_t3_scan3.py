# -*- coding: utf-8 -*-
"""R30 任务3 扫描3：剔除注释后统计 幂X / X类型 / 记录 模式（注释不参与词法）。"""
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


def lexable(text):
    """剔除注释：行首/行内 '#' 起至行尾不参与词法。"""
    out = []
    for ln in text.splitlines():
        h = ln.find('#')
        out.append(ln if h < 0 else ln[:h])
    return '\n'.join(out)


def toks(text):
    try:
        return [(t.type.name, t.value) for t in lexer.Lexer(text, deterministic=True).tokenize()
                if t.type.name not in ('EOF', 'NEWLINE')]
    except Exception as e:
        return ['ERR:' + type(e).__name__]


def scan(prefix=None, contain=None, drop_prefix=False, limit=30):
    m = {}
    for f in CORPUS:
        try:
            txt = lexable(open(f, encoding='utf-8', errors='replace').read())
        except Exception:
            continue
        for seg in re.findall(r'[\u4e00-\u9fff]+', txt):
            if prefix and not seg.startswith(prefix):
                continue
            if contain and contain not in seg:
                continue
            if drop_prefix and seg.startswith(contain):
                continue
            m[seg] = m.get(seg, 0) + 1
    return m


print('=== 幂 开头（剔除注释后）===')
for k, v in sorted(scan(prefix='幂').items(), key=lambda x: -x[1]):
    if len(k) > 1:
        print('   %-16s %4d  现状: %s' % (k, v, toks(k)))

print('\n=== X类型（类型在词中/词尾，剔除注释后）===')
for k, v in sorted(scan(contain='类型', drop_prefix=True).items(), key=lambda x: -x[1])[:30]:
    print('   %-16s %4d  现状: %s' % (k, v, toks(k)))

print('\n=== 记录类型（剔除注释后）===')
for k, v in sorted(scan(contain='记录类型').items(), key=lambda x: -x[1])[:15]:
    print('   %-16s %4d  现状: %s' % (k, v, toks(k)))

print('\n=== 零除错误 / 幂次 / 记录类型 在剔除注释后的命中 ===')
for t in ('零除错误', '幂次', '记录类型'):
    tot = 0
    files = set()
    for f in CORPUS:
        try:
            txt = lexable(open(f, encoding='utf-8', errors='replace').read())
        except Exception:
            continue
        c = len(re.findall(re.escape(t), txt))
        if c:
            tot += c
            files.add(os.path.relpath(f, ROOT).replace('\\', '/'))
    print('   %-8s %d 次 / %d 文件 %s' % (t, tot, len(files), sorted(files)))
