# -*- coding: utf-8 -*-
"""R33 活性探针：确认撤 NEVER_SPLIT 字后变体确实改变类别（非假绿），
并对合成用例验证 G2 编译门、G3 边界门可用。"""
import importlib
import os
import sys

ROOT = r'G:/dswork/duan-light-merge'
SRC = os.path.join(ROOT, 'lightharness', '_r33_lexer_head.py')
LH = os.path.join(ROOT, 'lightharness')
sys.path.insert(0, os.path.join(ROOT, 'light-merge', 'src'))
sys.path.insert(0, LH)


def remove_char_from_line(line, c):
    new = line.replace("'%s', " % c, '', 1)
    if new != line:
        return new
    new = line.replace(", '%s'" % c, '', 1)
    if new != line:
        return new
    return line.replace("'%s'" % c, '', 1)


def neutralize_hm_assert(lines):
    out = []
    i = 0
    while i < len(lines):
        l = lines[i]
        if l.strip().startswith('assert _P0A_HEAD_MERGE_SINGLE == ('):
            i += 1
            while i < len(lines) and not lines[i].rstrip().endswith('))'):
                i += 1
            i += 1
            out.append('# neutralized\n')
            continue
        out.append(l)
        i += 1
    return out


def build_variant(tag, c):
    lines = open(SRC, encoding='utf-8').read().splitlines(keepends=True)
    i0 = next(i for i, l in enumerate(lines)
              if l.strip().startswith('_P0A_NEVER_SPLIT = frozenset('))
    lines[i0] = remove_char_from_line(lines[i0], c)
    lines = neutralize_hm_assert(lines)
    name = '_r33_probe_' + tag
    open(os.path.join(LH, name + '.py'), 'w', encoding='utf-8').write(''.join(lines))
    sys.modules.pop(name, None)
    return importlib.import_module(name)


def toks(mod, src):
    return [(t.type.name, t.value) for t in mod.Lexer(src, deterministic=True).tokenize()
            if t.type.name not in ('EOF', 'NEWLINE')]


def main():
    base = importlib.import_module('lexer')
    print('=== 活性校验（变体须与基线类别不同；模为冗余删除应无派生变化）===')
    for c, tag in [('模', 'mo'), ('步', 'bu'), ('至', 'zhi'), ('到', 'dao')]:
        mod = build_variant(tag, c)
        f_base = frozenset(base.Lexer._TRAILING_ALIAS_CLASS)
        f_var = frozenset(mod.Lexer._TRAILING_ALIAS_CLASS)
        ns_base = frozenset(base.Lexer._P0A_NEVER_SPLIT)
        ns_var = frozenset(mod.Lexer._P0A_NEVER_SPLIT)
        hm_base = frozenset(base._P0A_HEAD_MERGE_SINGLE)
        hm_var = frozenset(mod._P0A_HEAD_MERGE_SINGLE)
        suff_base = frozenset(base.Lexer._P0A_SUFFIX_SPLIT_SINGLE)
        suff_var = frozenset(mod.Lexer._P0A_SUFFIX_SPLIT_SINGLE)
        print('字 %s: NEVER_SPLIT %s→%s | F %s→%s | HM %s→%s | SUFFIX %s→%s'
              % (c, c in ns_base, c in ns_var, c in f_base, c in f_var,
                 c in hm_base, c in hm_var, c in suff_base, c in suff_var))
        assert c not in ns_var, '变体未删净 NEVER_SPLIT'

    print()
    print('=== G3 边界探针：词尾并入（撤字后该字入 F，词尾应整词并入标识符）===')
    # 模 在词尾：合成 "建模"（建 词首 + 模 词尾）。基线 模∈exclude→词尾不并入；
    # 变体 模∈F→词尾并入 → 两态 token 流应不同（证明变体活性 + 边界形态变化）。
    for c, tag, word in [('模', 'mo', '建模'), ('步', 'bu', '同步'),
                         ('至', 'zhi', '乃至'), ('到', 'dao', '遇到')]:
        mod = build_variant(tag, c)
        src = '段落 主:\n    设 %s 为 空\n' % word
        b = toks(base, src)
        k = toks(mod, src)
        print('  %s: 基线=%s 变体=%s' % (word, b, k))

    print()
    print('=== G2 编译门探针（含目标字的合法语句须 rc=0）===')
    probes = {
        '模': '段落 主:\n    设 甲 为 3\n    设 乙 为 2\n    设 余数 为 甲 模 乙\n',
        '步': '段落 主:\n    设 列表 为 从1到10步2\n',
        '至': '段落 主:\n    设 列表 为 从1至10\n',
        '到': '段落 主:\n    设 列表 为 从1到10\n',
    }
    for c, tag in [('模', 'mo'), ('步', 'bu'), ('至', 'zhi'), ('到', 'dao')]:
        mod = build_variant(tag, c)
        try:
            t = toks(mod, probes[c])
            print('  %s: token 数=%d  OK' % (c, len(t)))
        except Exception as e:
            print('  %s: 异常 %s' % (c, type(e).__name__))


if __name__ == '__main__':
    main()
