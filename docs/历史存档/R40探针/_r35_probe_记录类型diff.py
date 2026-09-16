# -*- coding: utf-8 -*-
"""R35 探针3：记录类型 撤除后 G1 变化的 2 个文件，逐 token 定位差异。"""
import os
import sys

ROOT = r'G:/dswork/duan-light-merge'
sys.path.insert(0, os.path.join(ROOT, 'light-merge', 'src'))
import lexer  # noqa: E402

FILES = ['lightharness/examples/test_R29_CCW精简边界.light',
         'lightharness/examples/test_R30_CCW通用化边界.light']


def tk(src):
    return [(t.type.name, t.value, t.line) for t in
            lexer.Lexer(src, deterministic=True).tokenize()
            if t.type.name not in ('EOF', 'NEWLINE')]


def main():
    for rel in FILES:
        p = os.path.join(ROOT, rel.replace('/', os.sep))
        src = open(p, encoding='utf-8').read()
        orig = lexer.Lexer._P0A_MERGE_WHOLE
        lexer.Lexer._P0A_MERGE_WHOLE = orig                     # 基线（3 条）
        a = tk(src)
        lexer.Lexer._P0A_MERGE_WHOLE = frozenset()              # 撤除
        b = tk(src)
        lexer.Lexer._P0A_MERGE_WHOLE = orig
        print('=' * 70)
        print(rel)
        if a == b:
            print('  无差异')
            continue
        # 找首个差异位置
        i = 0
        while i < min(len(a), len(b)) and a[i][:2] == b[i][:2]:
            i += 1
        print('  首个差异 idx=%d' % i)
        print('    基线: %s' % ' '.join('%s·%s' % (t[0], t[1]) for t in a[max(0, i - 4):i + 5]))
        print('    撤除: %s' % ' '.join('%s·%s' % (t[0], t[1]) for t in b[max(0, i - 4):i + 5]))
        if i < len(a) and a[i][2]:
            ln = a[i][2]
            lines = src.splitlines()
            if 0 < ln <= len(lines):
                print('    源码 L%d: %s' % (ln, lines[ln - 1].strip()))
        # 统计全部差异点
        diffs = [(x, y) for x, y in zip(a, b) if x[:2] != y[:2]]
        print('  差异 token 数 = %d' % len(diffs))
        for x, y in diffs[:6]:
            print('      基线 %s·%s  ->  撤除 %s·%s' % (x[0], x[1], y[0], y[1]))


if __name__ == '__main__':
    main()
