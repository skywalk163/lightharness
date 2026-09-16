# -*- coding: utf-8 -*-
"""R30 任务3：3 条 CCW 撤除后的通用化效果探针。

对 零除错误 / 幂次 / 记录类型 / 零 个（反向）分别用两种口径分词：
  A) CCW 原样保留（对照：目标词整词成 IDENTIFIER）
  B) 从 CCW 移除该目标词（撤除后：应由新通用规则接住，仍整词成 IDENTIFIER）
"""
import sys
sys.path.insert(0, 'G:/dswork/duan-light-merge/light-merge/src')
sys.path.insert(0, '.')
import lexer

CASES = [
    ('零除错误', '捕获 零除错误:\n    抛 消息("出错了")\n'),
    ('幂次',     '设 x 为 幂次(2, 10)\n'),
    ('记录类型', '设 x 为 记录类型(用户)\n'),
    ('反向:零个', '设 零 个 为 真\n'),
]

TARGET = {'零除错误', '幂次', '记录类型'}


def show(tag, code):
    old = lexer.COMMON_COMPOUND_WORDS
    out = []
    for label in ('A_CCW保留', 'B_CCW撤除'):
        if label == 'B_CCW撤除':
            lexer.COMMON_COMPOUND_WORDS = old - TARGET
        else:
            lexer.COMMON_COMPOUND_WORDS = old
        toks = [t for t in lexer.Lexer(code, deterministic=True).tokenize()
                if t.type.name not in ('EOF', 'NEWLINE')]
        out.append('    '.join(f'{t.type.name}:{t.value}' for t in toks))
        if label == 'B_CCW撤除':
            lexer.COMMON_COMPOUND_WORDS = old
    print(f'[{tag}] {code.strip()[:40]!r}')
    print(f'  A_CCW保留: {out[0]}')
    print(f'  B_CCW撤除: {out[1]}')
    print(f'  {"OK 零变化" if out[0] == out[1] else "!! 有差异"}')
    print()


for tag, code in CASES:
    show(tag, code)
