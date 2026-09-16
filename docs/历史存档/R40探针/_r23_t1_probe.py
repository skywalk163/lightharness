# -*- coding: utf-8 -*-
"""R23 任务1 探针：`己` 词尾并入是否已被第21轮上下文敏感切词覆盖。

只读探针，不改文件。输出：
 1) test_L120.light 在「有己/无己」两种表状态下的 token 序列差异
 2) 片段探针 `错误己` / `捕获 异常 错误己:` 的切分
"""
import sys

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
sys.path.insert(0, LIGHTP + '/src')
import lexer as L  # noqa


def dump(src):
    return [(t.type.name, t.value) for t in L.Lexer(src).tokenize()]


def show(tag, src, limit=200):
    try:
        toks = dump(src)
    except Exception as e:  # noqa
        print(f'  {tag}: ERR {type(e).__name__}: {e}')
        return
    s = ' '.join(f'{t[0][:4]}:{t[1]}' for t in toks)
    print(f'  {tag}: {s[:limit]}')


def main():
    cur = frozenset(L._TRAILING_ALIAS_MERGE)
    print(f'当前 _TRAILING_ALIAS_MERGE = {sorted(cur)}')

    dep = HARNESS + '/examples/test_L120.light'
    src = open(dep, encoding='utf-8', errors='replace').read()

    with_tam = dump(src)
    try:
        L._TRAILING_ALIAS_MERGE = frozenset()
        without_tam = dump(src)
    finally:
        L._TRAILING_ALIAS_MERGE = cur
    print(f'\n[1] test_L120.light token 数：有表={len(with_tam)} 无表={len(without_tam)}  '
          f'{"相同" if with_tam == without_tam else "不同"}')
    if with_tam != without_tam:
        import difflib
        a = [f'{t[0]}:{t[1]}' for t in with_tam]
        b = [f'{t[0]}:{t[1]}' for t in without_tam]
        for line in difflib.unified_diff(a, b, '有表', '无表', lineterm='', n=2):
            print('   ', line)

    print('\n[2] 片段探针（有表）:')
    for frag in ('错误己', '捕获 异常 错误己:', '自己 己任 自己的 错误己'):
        show(frag, frag)
    print('\n[3] 片段探针（无表）:')
    L._TRAILING_ALIAS_MERGE = frozenset()
    try:
        for frag in ('错误己', '捕获 异常 错误己:', '自己 己任 自己的 错误己'):
            show(frag, frag)
    finally:
        L._TRAILING_ALIAS_MERGE = cur

    print('\n[4] 关键字表探查:')
    from keywords import ALL_KEYWORDS
    for k in ('己', '错误', '异常', '捕获', '自己'):
        print(f'   {k}: in ALL_KEYWORDS={k in ALL_KEYWORDS}')
    print(f'   _P0A_OP 含 己: {"己" in getattr(L.Lexer, "_P0A_OP", set())}')
    try:
        inst = L.Lexer('甲')
        print(f'   实例 _P0A_OP 含 己/真/空/是: '
              f'{"己" in inst._P0A_OP}/{"真" in inst._P0A_OP}/{"空" in inst._P0A_OP}/{"是" in inst._P0A_OP}')
        print(f'   _P0A_OP 大小 {len(inst._P0A_OP)}')
    except Exception as e:  # noqa
        print('   探查 _P0A_OP 失败:', e)


if __name__ == '__main__':
    main()
