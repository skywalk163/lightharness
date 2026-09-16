# -*- coding: utf-8 -*-
"""R26 A/B：基线（_r26_baseline_lexer.py，R25 态）vs 修改后工作树 lexer.py。
输出 _r26_ab_final.json。全语料 token 必须零变化。"""
import os
import sys
import json
import glob
import time
import importlib.util

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
BASE_SRC = HARNESS + '/_r26_baseline_lexer.py'
NEW_SRC = os.path.join(LIGHTP, 'src', 'lexer.py')
sys.path.insert(0, os.path.join(LIGHTP, 'src'))

PATTERNS = [HARNESS + '/examples/**/*.light', HARNESS + '/src/**/*.light',
            HARNESS + '/tests/**/*.light', LIGHTP + '/examples/**/*.light',
            LIGHTP + '/stdlib/**/*.light', LIGHTP + '/bootstrap/**/*.light',
            LIGHTP + '/src/**/*.light', LIGHTP + '/tests/**/*.light']
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))


def read(f):
    return open(f, encoding='utf-8', errors='replace').read()


def load_src(tag, path, text=None):
    d = os.path.join(os.environ.get('TEMP', '/tmp'), 'r26f_' + tag)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, 'lxr_%s.py' % tag)
    open(p, 'w', encoding='utf-8', newline='').write(text if text is not None else read(path))
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
    import ast as _ast
    la, lb = _ast.literal_eval(a), _ast.literal_eval(b)
    for k in range(max(len(la), len(lb))):
        ta = la[k] if k < len(la) else None
        tb = lb[k] if k < len(lb) else None
        if ta != tb:
            return k, la[max(0, k - 3):k + 5], lb[max(0, k - 3):k + 5]
    return -1, [], []


def main():
    t0 = time.time()
    SRC = {f: read(f) for f in CORPUS}
    base = load_src('base', BASE_SRC)
    new = load_src('new', NEW_SRC)
    print('基线 CS=%d  F=%d  |  新版 CS=%d  HEAD=%d  ｜ 语料 %d 文件'
          % (len(base._COMPOUND_SAFE_SINGLE_KEYWORDS), len(base.Lexer._TRAILING_ALIAS_CLASS),
             len(new._COMPOUND_SAFE_SINGLE_KEYWORDS), len(new._P0A_HEAD_MERGE_SINGLE),
             len(CORPUS)))

    base_t = {f: toks(base, SRC[f]) for f in CORPUS}
    d = {}
    for f in CORPUS:
        t = toks(new, SRC[f])
        if t != base_t[f]:
            d[f] = (base_t[f], t)
    pairs = sorted((os.path.relpath(f, ROOT).replace('\\', '/'), f) for f in d)
    print('token 变化 %d/%d 文件' % (len(pairs), len(CORPUS)))
    for fn, full in pairs[:12]:
        k, ca, cb = first_diff(*d[full])
        print('   -', fn, '@tok', k)
        print('     base:', ca)
        print('     new :', cb)
    json.dump({'corpus': len(CORPUS), 'changed': len(pairs),
               'files': [fn for fn, _ in pairs[:80]],
               'seconds': round(time.time() - t0, 1)},
              open(HARNESS + '/_r26_ab_final.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('耗时 %.1fs  → _r26_ab_final.json' % (time.time() - t0))


if __name__ == '__main__':
    main()
