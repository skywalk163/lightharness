# -*- coding: utf-8 -*-
"""R33 共享引擎库：_P0A_NEVER_SPLIT 单字隔离验证核心逻辑。

g1_for_char(c) 以「改动前快照 _r33_lexer_head.py」为基线，构建「仅移除 c」的变体
模块，对全语料 tokenize 比对，返回 G1 结果。与当前工作区 lexer.py 是否已应用
删除无关（用快照作基线），可复现复刻第33轮任务1-4 的逐字验证。
"""
import glob
import hashlib
import importlib
import json
import os
import sys

ROOT = r'G:/dswork/duan-light-merge'
SRC = os.path.join(ROOT, 'lightharness', '_r33_lexer_head.py')
LH = os.path.join(ROOT, 'lightharness')
sys.path.insert(0, os.path.join(ROOT, 'light-merge', 'src'))
sys.path.insert(0, LH)

PATTERNS = [ROOT + '/lightharness/examples/**/*.light',
            ROOT + '/lightharness/src/**/*.light',
            ROOT + '/lightharness/tests/**/*.light',
            ROOT + '/light-merge/examples/**/*.light',
            ROOT + '/light-merge/stdlib/**/*.light',
            ROOT + '/light-merge/bootstrap/**/*.light',
            ROOT + '/light-merge/src/**/*.light',
            ROOT + '/light-merge/tests/**/*.light']
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))
READ = {f: open(f, encoding='utf-8', errors='replace').read() for f in CORPUS}


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
            out.append('# _R33 isolation: HM 自校验在撤 NEVER_SPLIT 字时合法放宽'
                       '（该字入 HM 属预期副作用，由 DUAL/词尾并入兜底，不影响 token 流）\n')
            continue
        out.append(l)
        i += 1
    return out


def build_variant(tag, c):
    lines = open(SRC, encoding='utf-8').read().splitlines(keepends=True)
    i0 = next(i for i, l in enumerate(lines)
              if l.strip().startswith('_P0A_NEVER_SPLIT = frozenset('))
    assert lines[i0].count("'%s'" % c) == 1, (tag, c)
    lines[i0] = remove_char_from_line(lines[i0], c)
    assert "'%s'" % c not in lines[i0]
    lines = neutralize_hm_assert(lines)
    name = '_r33_var_' + tag
    open(os.path.join(LH, name + '.py'), 'w', encoding='utf-8').write(''.join(lines))
    sys.modules.pop(name, None)
    mod = importlib.import_module(name)
    assert c not in mod.Lexer._P0A_NEVER_SPLIT
    return mod


def sha(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False).encode()).hexdigest()


def seqs_of(mod):
    out = {}
    for f in CORPUS:
        rel = os.path.relpath(f, ROOT).replace('\\', '/')
        try:
            toks = mod.Lexer(READ[f], deterministic=True).tokenize()
            out[rel] = [(t.type.name, t.value) for t in toks
                        if t.type.name not in ('EOF', 'NEWLINE')]
        except Exception as e:
            out[rel] = ['ERR:' + type(e).__name__]
    return out


def g1_for_char(c, tag):
    """以快照（改动前 lexer.py）为基线，撤 c 后全语料比对。返回结果 dict。"""
    snap_name = '_r33_lexer_head'
    sys.modules.pop(snap_name, None)
    snap_mod = importlib.import_module(snap_name)
    base = seqs_of(snap_mod)
    base_ns = sorted(snap_mod.Lexer._P0A_NEVER_SPLIT)
    base_err = {r for r in base if len(base[r]) == 1 and base[r][0].startswith('ERR:')}
    mod = build_variant(tag, c)
    cur = seqs_of(mod)
    changed = [r for r in base if sha(cur[r]) != sha(base[r]) and r not in base_err]
    new_err = sorted({r for r in cur if len(cur[r]) == 1
                      and cur[r][0].startswith('ERR:')} - base_err)
    f_var = frozenset(mod.Lexer._TRAILING_ALIAS_CLASS)
    hm_var = frozenset(mod._P0A_HEAD_MERGE_SINGLE)
    return {
        'char': c, 'base_ns': base_ns,
        'changed': changed, 'new_err': new_err,
        'ok': not changed and not new_err,
        'enters_F': c in f_var, 'enters_HM': c in hm_var,
        'corpus': len(CORPUS),
    }
