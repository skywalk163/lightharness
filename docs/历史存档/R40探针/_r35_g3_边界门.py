# -*- coding: utf-8 -*-
"""R35 G3 边界门：五种边界形态 token 流比对（reference vs 变体）。

用法：python _r35_g3_边界门.py <variant_name>
变体来自 _r35_variants.VARIANTS。变体须已撤条目（否则 G3 无意义）。

形态：
  F1 设名       设 X 为 1
  F2 函数名     返回 X(1)
  F3 成员访问   设 r 为 结果.X
  F4 段落名     段落 X:
  F5 传参位     断言相等(X, 1, "t")
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _r35_g1_engine as E  # noqa: E402

ENTRIES = ['整理模型消息', '非空块', '记录类型']

FORMS = lambda X: [
    ('F1 设名',     '设 X 为 1\n'.replace('X', X)),
    ('F2 函数名',   '返回 X(1)\n'.replace('X', X)),
    ('F3 成员访问', '设 r 为 结果.X\n'.replace('X', X)),
    ('F4 段落名',   '段落 X:\n    返回 1\n'.replace('X', X)),
    ('F5 传参位',   '断言相等(X, 1, "t")\n'.replace('X', X)),
]

CHILD = r'''
import json, sys
srcdir, out = sys.argv[2], sys.argv[3]
sys.path.insert(0, srcdir)
import lexer
entries = json.loads(sys.argv[4])
forms = json.loads(sys.argv[5])
res = {}
for X in entries:
    for tag, tpl in forms:
        src = tpl.replace('X', X)
        try:
            res[X + '|' + tag] = [(t.type.name, t.value) for t in
                                  lexer.Lexer(src, deterministic=True).tokenize()
                                  if t.type.name not in ('EOF', 'NEWLINE')]
        except Exception as e:
            res[X + '|' + tag] = ['ERR:' + type(e).__name__]
json.dump(res, open(out, 'w', encoding='utf-8'))
'''


def collect(srcdir, tmpname):
    import tempfile
    tmp = tempfile.mkdtemp(prefix='r35g_')
    ch = os.path.join(tmp, 'child.py')
    out = os.path.join(tmp, 'out.json')
    open(ch, 'w', encoding='utf-8').write(CHILD)
    r = subprocess.run([sys.executable, ch, 'child', srcdir, out,
                        json.dumps(ENTRIES), json.dumps(FORMS('X'))],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    if not os.path.exists(out):
        raise SystemExit('G3 子进程失败: %s' % r.stderr[-1500:])
    return json.load(open(out, encoding='utf-8'))


def fmt(toks):
    return ' '.join('%s·%s' % (k, v) for k, v in toks)


def main():
    name = sys.argv[1]
    from _r35_variants import VARIANTS
    patches = VARIANTS[name]
    refdir = E.materialize('g3ref')
    vardir = E.materialize(name, patches)
    a = collect(refdir, 'ref')
    b = collect(vardir, name)
    print('=== G3 边界门：%s vs reference ===' % name)
    allok = True
    for X in ENTRIES:
        bad = []
        for tag, _ in FORMS(X):
            k = X + '|' + tag
            if a[k] != b[k]:
                bad.append((tag, a[k], b[k]))
        print('  %-8s %s' % (X, 'G3通过' if not bad else 'G3失败 %s' % [t for t, _, _ in bad]))
        for tag, x, y in bad:
            allok = False
            print('      [%s]' % tag)
            print('        基线: %s' % fmt(x))
            print('        变体: %s' % fmt(y))
    print('总判定：%s' % ('G3 全部通过' if allok else 'G3 有失败'))
    return 0 if allok else 1


if __name__ == '__main__':
    sys.exit(main())
