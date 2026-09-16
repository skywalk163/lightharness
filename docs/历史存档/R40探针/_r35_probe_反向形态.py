# -*- coding: utf-8 -*-
"""R35 反向形态探针：确认通用规则**不**误伤关键字的正常语义用法。

用法：python _r35_probe_反向形态.py <variant>
"""
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _r35_g1_engine as E  # noqa: E402

# (标签, 源码) —— 期望：变体与 reference token 流一致
PROBES = [
    ('非 一元取反（带空格）',   '设 甲 为 真\n设 乙 为 非 甲\n'),
    ('非 一元取反（条件位）',   '设 甲 为 真\n如果 非 甲:\n    返回 1\n'),
    ('非 单字变量名（无空格）', '设 甲 为 真\n如果 非甲:\n    返回 1\n'),
    ('非 双字变量名（无空格）', '设 甲乙 为 真\n如果 非甲乙:\n    返回 1\n'),
    ('取模 甲模乙（守卫）',     '设 甲 为 7\n设 乙 为 3\n断言相等(甲模乙, 1, "取模")\n'),
    ('取模 带空格',            '设 甲 为 7\n设 乙 为 3\n断言相等(甲 模 乙, 1, "取模")\n'),
    ('类型 声明语句',          '类型 甲 = 记录\n'),
    ('类型 裸关键字',          '设 x 为 1\n返回 类型\n'),
    ('模型 复合名',            '设 模型 为 1\n返回 模型\n'),
    ('非空 复合名',            '设 非空 为 1\n返回 非空\n'),
    ('记录类型 段落名',        '段落 记录类型:\n    返回 1\n'),
    ('成员访问 X类型',         '设 r 为 结果.期望类型\n'),
]

CHILD = r'''
import json, sys
srcdir, out, probes = sys.argv[2], sys.argv[3], json.loads(sys.argv[4])
sys.path.insert(0, srcdir)
import lexer
res = {}
for tag, src in probes:
    try:
        res[tag] = [(t.type.name, t.value) for t in
                    lexer.Lexer(src, deterministic=True).tokenize()
                    if t.type.name not in ('EOF', 'NEWLINE')]
    except Exception as e:
        res[tag] = ['ERR:' + type(e).__name__]
json.dump(res, open(out, 'w', encoding='utf-8'))
'''


def collect(srcdir):
    tmp = tempfile.mkdtemp(prefix='r35r_')
    ch = os.path.join(tmp, 'child.py')
    out = os.path.join(tmp, 'out.json')
    open(ch, 'w', encoding='utf-8').write(CHILD)
    r = subprocess.run([sys.executable, ch, 'child', srcdir, out,
                        json.dumps(PROBES)],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    if not os.path.exists(out):
        raise SystemExit('反向探针子进程失败: %s' % r.stderr[-1500:])
    return json.load(open(out, encoding='utf-8'))


def fmt(toks):
    return ' '.join('%s·%s' % (k, v) for k, v in toks)


def main():
    name = sys.argv[1]
    from _r35_variants import VARIANTS
    a = collect(E.materialize('rref'))
    b = collect(E.materialize(name, VARIANTS[name]))
    print('=== 反向形态：%s vs reference ===' % name)
    bad = 0
    for tag, _ in PROBES:
        same = a[tag] == b[tag]
        print('  %-22s %s' % (tag, '一致' if same else '★变化'))
        if not same:
            bad += 1
            print('        基线: %s' % fmt(a[tag]))
            print('        变体: %s' % fmt(b[tag]))
        else:
            print('        %s' % fmt(a[tag]))
    print('反向形态变化数 = %d' % bad)
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
