# -*- coding: utf-8 -*-
"""R35 探针2：撤除 MERGE_WHOLE 后，3 条在更细上下文矩阵下的实际 token 流。

目的：定位「哪种上下文会劈开、哪种不会」，推断劈开发生的规则层。
"""
import os
import sys

ROOT = r'G:/dswork/duan-light-merge'
sys.path.insert(0, os.path.join(ROOT, 'light-merge', 'src'))
import lexer  # noqa: E402

CTXS = [
    ('裸串',        '{X}'),
    ('裸串+换行',    '{X}\n'),
    ('设名',        '设 {X} 为 1\n'),
    ('值位',        '设 甲 为 {X}\n'),
    ('调用语境',     '返回 {X}(1)\n'),
    ('调用语境行首',  '{X}(1)\n'),
    ('传参首位',     '断言相等({X}, 1, "t")\n'),
    ('传参次位',     '断言相等(1, {X}, "t")\n'),
    ('成员访问',     '设 r 为 结果.{X}\n'),
    ('段落名',      '段落 {X}:\n    返回 1\n'),
    ('列表元素',     '设 l 为 [{X}, 2]\n'),
    ('条件位',      '如果 {X}:\n    返回 1\n'),
    ('打印位',      '打印 {X}\n'),
    ('算术位',      '设 y 为 {X} + 1\n'),
    ('返回位',      '返回 {X}\n'),
    ('字典键',      '设 d 为 {{"{X}": 1}}\n'),
]

WORDS = ['整理模型消息', '非空块', '记录类型']


def tk(src):
    try:
        return [(t.type.name, t.value) for t in
                lexer.Lexer(src, deterministic=True).tokenize()
                if t.type.name not in ('EOF', 'NEWLINE')]
    except Exception as e:
        return [('ERR', type(e).__name__ + ':' + str(e)[:30])]


def fmt(toks):
    return ' '.join('%s·%s' % (k, v) for k, v in toks)


def run(mw):
    orig = lexer.Lexer._P0A_MERGE_WHOLE
    lexer.Lexer._P0A_MERGE_WHOLE = frozenset(mw)
    try:
        out = {}
        for w in WORDS:
            for tag, tpl in CTXS:
                out[(w, tag)] = tk(tpl.replace('{X}', w))
        return out
    finally:
        lexer.Lexer._P0A_MERGE_WHOLE = orig


def main():
    base = run(lexer.Lexer._P0A_MERGE_WHOLE)
    gone = run(set())
    for w in WORDS:
        print('=' * 70)
        print('【%s】' % w)
        for tag, _ in CTXS:
            a, b = base[(w, tag)], gone[(w, tag)]
            flag = 'OK ' if a == b else '★变'
            print('  %s %-12s' % (flag, tag))
            if a != b:
                print('       基线: %s' % fmt(a))
                print('       撤除: %s' % fmt(b))

    print()
    print('=' * 70)
    print('=== 对照：常见形态是否本就不切（撤除态下看真实切分） ===')
    for probe in ['甲加乙', '非甲', '非空', '数类型', '内容类型', '记录类型',
                  '整理模型', '模型消息', '于类型', '定义幂', '自加乙']:
        print('  传参位 %-8s -> %s' % (probe,
              fmt(gone[('整理模型消息', '传参首位')][:0] or tk('断言相等(%s, 1, "t")\n' % probe))))
        print('  调用位 %-8s -> %s' % (probe, fmt(tk('返回 %s(1)\n' % probe))))


if __name__ == '__main__':
    main()
