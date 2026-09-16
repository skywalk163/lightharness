# -*- coding: utf-8 -*-
"""R35 探针4：指定变体 vs reference 的逐文件 token 差异定位。

用法：python _r35_probe_变体diff.py <variant> [最大文件数]
"""
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _r35_g1_engine as E  # noqa: E402
from _r35_variants import VARIANTS  # noqa: E402

CHILD = r'''
import json, sys
srcdir, out, rels, root = sys.argv[2], sys.argv[3], json.loads(sys.argv[4]), sys.argv[5]
sys.path.insert(0, srcdir)
import lexer
res = {}
for rel in rels:
    import os
    p = os.path.join(root, rel.replace('/', os.sep))
    try:
        src = open(p, encoding='utf-8').read()
        res[rel] = [(t.type.name, t.value, t.line) for t in
                    lexer.Lexer(src, deterministic=True).tokenize()
                    if t.type.name not in ('EOF', 'NEWLINE')]
    except Exception as e:
        res[rel] = ['ERR:' + type(e).__name__]
json.dump(res, open(out, 'w', encoding='utf-8'))
'''


def collect(srcdir, rels):
    tmp = tempfile.mkdtemp(prefix='r35d_')
    ch = os.path.join(tmp, 'child.py')
    out = os.path.join(tmp, 'out.json')
    open(ch, 'w', encoding='utf-8').write(CHILD)
    r = subprocess.run([sys.executable, ch, 'child', srcdir, out,
                        json.dumps(rels), E.ROOT],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    if not os.path.exists(out):
        raise SystemExit('diff 子进程失败: %s' % r.stderr[-1500:])
    return json.load(open(out, encoding='utf-8'))


def fmt(toks, n=6):
    return ' '.join('%s·%s' % (t[0], t[1]) for t in toks[:n])


def main():
    name = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    ref = E.run_variant('reference')
    per = E.run_variant(name, VARIANTS[name])
    changed = [k for k, v in ref.items()
               if not v.startswith('ERR:') and ref[k] != per.get(k)]
    print('变体 %s：变化 %d 文件' % (name, len(changed)))
    changed = changed[:limit]
    refdir = E.materialize('dref')
    vardir = E.materialize(name, VARIANTS[name])
    a = collect(refdir, changed)
    b = collect(vardir, changed)
    for rel in changed:
        x, y = a[rel], b[rel]
        i = 0
        while i < min(len(x), len(y)) and x[i][:2] == y[i][:2]:
            i += 1
        print('-' * 70)
        print(rel)
        print('  基线  …%s' % fmt(x[max(0, i - 3):i + 4]))
        print('  变体  …%s' % fmt(y[max(0, i - 3):i + 4]))
        if i < len(x):
            ln = x[i][2]
            p = os.path.join(E.ROOT, rel.replace('/', os.sep))
            lines = open(p, encoding='utf-8').read().splitlines()
            if isinstance(ln, int) and 0 < ln <= len(lines):
                print('  源码 L%s: %s' % (ln, lines[ln - 1].strip()))


if __name__ == '__main__':
    main()
