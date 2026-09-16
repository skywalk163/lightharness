# -*- coding: utf-8 -*-
"""R26 A/B 变体框架：把 5 处词首并入站的 CS 判定换成 _P0A_HEAD_MERGE_SINGLE，
再按候选类别定义逐一变体跑全语料 token 比对。只读磁盘、只写临时文件。

用法：python _r26_ab.py [variant ...]
变体：keep / F / FnCS / Fdual / singles_minus_hard
"""
import os
import sys
import json
import glob
import time
import tempfile
import importlib.util

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
LEXER = os.path.join(LIGHTP, 'src', 'lexer.py')
sys.path.insert(0, os.path.join(LIGHTP, 'src'))

PATTERNS = [HARNESS + '/examples/**/*.light', HARNESS + '/src/**/*.light',
            HARNESS + '/tests/**/*.light', LIGHTP + '/examples/**/*.light',
            LIGHTP + '/stdlib/**/*.light', LIGHTP + '/bootstrap/**/*.light',
            LIGHTP + '/src/**/*.light', LIGHTP + '/tests/**/*.light']
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))

# 插入点：模块末尾（Lexer 类 + 断言之后），运行时查找故可后置
ANCHOR = "del _assert_F, _assert_DUAL, _assert_TAM, _assert_TAM_new\n"

_F = ("frozenset(_k for _k in (_ALL_KEYWORDS_WITH_VERBS - Lexer._P0A_OP - _OPERATOR_KEYWORDS "
      "- Lexer._P0A_NEVER_SPLIT - _AWAIT_KEYWORDS - _VALUE_LITERAL_KEYWORDS) if len(_k) == 1)")
CLASS_DEFS = {
    'keep': "frozenset(_COMPOUND_SAFE_SINGLE_KEYWORDS)",
    'F': _F,
    'FnCS': "(frozenset(_COMPOUND_SAFE_SINGLE_KEYWORDS) & %s)" % _F,
    'CSplusF': "(frozenset(_COMPOUND_SAFE_SINGLE_KEYWORDS) | %s)" % _F,
    'CS_minus12': ("frozenset(_COMPOUND_SAFE_SINGLE_KEYWORDS - "
                   "{'余','例','出','则','常','引','接','末','试','跳','长','首'})"),
    'CS_minus20': ("frozenset(_COMPOUND_SAFE_SINGLE_KEYWORDS - "
                   "{'余','例','出','则','常','引','接','末','试','跳','长','首',"
                   "'乘','减','到','加','模','真','空','除'})"),
}


def read(f):
    return open(f, encoding='utf-8', errors='replace').read()


def build_variant_src(variant):
    src = read(LEXER)
    # 1) 插入类别定义（在 CS 定义之后）
    assert ANCHOR in src, 'anchor not found'
    src = src.replace(ANCHOR, ANCHOR + "\n\n_P0A_HEAD_MERGE_SINGLE = " + CLASS_DEFS[variant], 1)
    # 2) 三处嵌入式扫描 & 类属性引用
    n1 = src.count('sub_kw in self.compound_safe_single_keywords')
    src = src.replace('sub_kw in self.compound_safe_single_keywords',
                      'sub_kw in _P0A_HEAD_MERGE_SINGLE')
    # 3) _match_keyword / _skip_compound_safe_and_match
    n2 = src.count('candidate in _COMPOUND_SAFE_SINGLE_KEYWORDS and pos + 1 < text_len:')
    src = src.replace('candidate in _COMPOUND_SAFE_SINGLE_KEYWORDS and pos + 1 < text_len:',
                      'candidate in _P0A_HEAD_MERGE_SINGLE and pos + 1 < text_len:')
    n3 = src.count('candidate in _compound_safe and pos + 1 < text_len:')
    src = src.replace('candidate in _compound_safe and pos + 1 < text_len:',
                      'candidate in _P0A_HEAD_MERGE_SINGLE and pos + 1 < text_len:')
    # 4) 第一层局部缓存 + remaining/keyword 判定
    n4 = src.count('_compound_safe = _COMPOUND_SAFE_SINGLE_KEYWORDS')
    src = src.replace('_compound_safe = _COMPOUND_SAFE_SINGLE_KEYWORDS',
                      '_compound_safe = _P0A_HEAD_MERGE_SINGLE')
    print('  [%s] sites: embed=%d mk=%d skip=%d local=%d' % (variant, n1, n2, n3, n4))
    return src


def load_src(tag, src):
    d = os.path.join(tempfile.gettempdir(), 'r26ab_' + tag)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, 'lxr_%s.py' % tag)
    open(p, 'w', encoding='utf-8', newline='').write(src)
    spec = importlib.util.spec_from_file_location('lxr_%s' % tag, p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules['lxr_%s' % tag] = mod
    spec.loader.exec_module(mod)
    return mod


def toks(mod, text):
    try:
        return repr([(t.type.name, t.value)
                     for t in mod.Lexer(text, deterministic=True).tokenize()
                     if t.type.name not in ('EOF', 'NEWLINE')])
    except Exception as e:  # noqa
        return 'ERR:' + type(e).__name__


def first_diff(a, b):
    """返回 (idx, a_tokens, b_tokens) —— 首个差异位置及两侧上下文。"""
    import ast as _ast
    la, lb = _ast.literal_eval(a), _ast.literal_eval(b)
    for k in range(max(len(la), len(lb))):
        ta = la[k] if k < len(la) else None
        tb = lb[k] if k < len(lb) else None
        if ta != tb:
            return k, la[max(0, k - 3):k + 5], lb[max(0, k - 3):k + 5]
    return -1, [], []


def main():
    variants = sys.argv[1:] or ['keep', 'F', 'FnCS']
    t0 = time.time()
    SRC = {f: read(f) for f in CORPUS}
    print('语料 %d 文件' % len(CORPUS))
    import lexer as base
    base_t = {f: toks(base, SRC[f]) for f in CORPUS}

    out = {}
    for v in variants:
        src = build_variant_src(v)
        try:
            mod = load_src(v, src)
        except Exception as e:
            print('  [%s] 导入失败: %s: %s' % (v, type(e).__name__, e))
            continue
        cls = mod._P0A_HEAD_MERGE_SINGLE
        print('  [%s] |class|=%d' % (v, len(cls)))
        d = {}
        for f in CORPUS:
            t = toks(mod, SRC[f])
            if t != base_t[f]:
                d[f] = (base_t[f], t)
        pairs = sorted((os.path.relpath(f, ROOT).replace('\\', '/'), f) for f in d)
        print('  [%s] 变化 %d 文件' % (v, len(pairs)))
        for fn, full in pairs[:10]:
            k, ca, cb = first_diff(*d[full])
            print('      -', fn, '@tok', k)
            print('        base:', ca)
            print('        var :', cb)
        out[v] = {'class_size': len(cls), 'changed': len(pairs),
                  'files': [fn for fn, _ in pairs[:60]],
                  'samples': [{'file': fn, 'idx': first_diff(*d[full])[0],
                               'base': first_diff(*d[full])[1],
                               'var': first_diff(*d[full])[2]} for fn, full in pairs[:10]]}
    json.dump({'corpus': len(CORPUS), 'variants': out},
              open(HARNESS + '/_r26_ab_result.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('\n耗时 %.1fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
