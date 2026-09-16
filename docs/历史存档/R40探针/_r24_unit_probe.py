# -*- coding: utf-8 -*-
"""R24 单测回归根因探针：内存态加载 HEAD 与修复态 lexer，对失败用例逐串对拍。"""
import os
import subprocess
import sys
import types

ROOT = r'G:\dswork\duan-light-merge'
LIGHTP = os.path.join(ROOT, 'light-merge')
SRC = os.path.join(LIGHTP, 'src')
LEXER = os.path.join(SRC, 'lexer.py')
BASE_REV = 'ca5741a8'

CASES = [
    '如果为真',
    '如果数小于等于二那么返回一',
    '己姓名',
    '段落阶乘接收n',
    '人之构造',
    '对象之方法',
    '不在',
    '对于',
    '甲属于乙',
    '九十那么大',
    '设甲为三。',
    '设 甲 为 百分位数',
    '二元运算符表等于甲',
    '甲加乙',
    '甲大于乙',
    '自之姓名',
]


def make_lexer(src_text, tag):
    if SRC not in sys.path:
        sys.path.insert(0, SRC)
    mod = types.ModuleType(f'_probe_{tag}')
    mod.__file__ = f'<probe:{tag}>'
    exec(compile(src_text, mod.__file__, 'exec'), mod.__dict__)
    return mod


def pairs(mod, s):
    return [(t.type.name, t.value) for t in mod.Lexer(s, deterministic=True).tokenize()]


def main():
    head_src = subprocess.check_output(
        ['git', '-C', LIGHTP, 'show', f'{BASE_REV}:src/lexer.py']).decode('utf-8')
    with open(LEXER, 'r', encoding='utf-8') as f:
        cur_src = f.read()
    head = make_lexer(head_src, 'head')
    cur = make_lexer(cur_src, 'cur')

    for s in CASES:
        try:
            h = pairs(head, s)
        except Exception as e:
            h = f'<ERR {e}>'
        try:
            c = pairs(cur, s)
        except Exception as e:
            c = f'<ERR {e}>'
        mark = 'DIFF' if h != c else 'same'
        print(f'[{mark}] {s!r}')
        if h != c:
            print(f'      HEAD: {h}')
            print(f'      CUR : {c}')


if __name__ == '__main__':
    main()
