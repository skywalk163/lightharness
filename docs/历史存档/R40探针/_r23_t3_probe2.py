# -*- coding: utf-8 -*-
"""R23 任务3 细探针：20 条「仅语料中立（隔离非中立）」的逐词 token 差异。"""
import sys

ROOT = r'G:/dswork/duan-light-merge'
sys.path.insert(0, ROOT + '/light-merge/src')
import lexer as L  # noqa

CUR = frozenset(L.COMMON_COMPOUND_WORDS)
WORDS = ['位与', '位或', '位非', '函数对象', '幂次', '并发等待', '异步睡眠', '当前', '当然',
         '枚举值', '类型错误', '终点', '结构体值', '设指针', '设指针值', '设系统',
         '设系统错误码', '设置', '设置数组', '除非']


def tok(src):
    try:
        return ' | '.join(f'{t.type.name}={t.value!r}' for t in L.Lexer(src).tokenize()
                          if t.type.name != 'EOF')
    except Exception as e:  # noqa
        return 'ERR ' + type(e).__name__


for w in WORDS:
    a = tok(w)
    L.COMMON_COMPOUND_WORDS = CUR - {w}
    try:
        b = tok(w)
    finally:
        L.COMMON_COMPOUND_WORDS = CUR
    flag = '同位' if a == b else '★差异'
    print(f'{w:8s} {flag}\n    含条: {a}\n    去条: {b}')
