# -*- coding: utf-8 -*-
"""R28 任务5 清理后验证：对比 任务123落地快照 vs 当前清理后 lexer。

口径：全语料 .light 文件 tokenize 序列（type, value）逐文件比对，必须零差异。
仅本轮清理产生的死代码删除不应改变任何 token 序列。
"""
import os
import sys
import glob
import hashlib
import importlib.util

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'

PATTERNS = [HARNESS + '/examples/**/*.light', HARNESS + '/src/**/*.light',
            HARNESS + '/tests/**/*.light', LIGHTP + '/examples/**/*.light',
            LIGHTP + '/stdlib/**/*.light', LIGHTP + '/bootstrap/**/*.light',
            LIGHTP + '/src/**/*.light', LIGHTP + '/tests/**/*.light']
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))


def read(f):
    return open(f, encoding='utf-8', errors='replace').read()


def load_lexer_from(path, modname):
    spec = importlib.util.spec_from_file_location(modname, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def token_seq(text, lexer_mod):
    try:
        toks = lexer_mod.Lexer(text, deterministic=True).tokenize()
        return [(x.type.name, x.value) for x in toks
                if x.type.name not in ('EOF', 'NEWLINE')]
    except Exception as e:
        # R26 口径：词法错误文件返回错误标记（快照侧同口径）
        return ['ERR:' + type(e).__name__]


def main():
    cur_path = os.path.join(LIGHTP, 'src', 'lexer.py')
    sys.path.insert(0, os.path.join(LIGHTP, 'src'))
    snap_mod = load_lexer_from(
        os.path.join(HARNESS, '_lexer_R28_任务123落地_快照.py'), 'lx_snap')
    cur_mod = load_lexer_from(cur_path, 'lx_cur')

    print('=' * 72)
    print('R28 任务5 清理后验证（快照 vs 当前）')
    print('=' * 72)
    print('快照 CS=%s | 当前 CS=%s' % (
        sorted(snap_mod._COMPOUND_SAFE_SINGLE_KEYWORDS),
        sorted(cur_mod._COMPOUND_SAFE_SINGLE_KEYWORDS)))
    print('语料 = %d 文件' % len(CORPUS))
    print('-' * 72)

    diff_files = []
    err_files = []
    n = 0
    for f in CORPUS:
        text = read(f)
        s1 = token_seq(text, snap_mod)
        s2 = token_seq(text, cur_mod)
        if s1 != s2:
            diff_files.append((f, s1, s2))
        if s2 and isinstance(s2[0], str) and s2[0].startswith('ERR:'):
            err_files.append(f)
        n += 1

    print('比对文件数: %d' % n)
    print('token 序列差异文件: %d' % len(diff_files))
    for f, s1, s2 in diff_files[:5]:
        print('  DIFF: %s' % f)
        print('    快照: %s' % (s1[:8],))
        print('    当前: %s' % (s2[:8],))
    print('词法错误文件: %d（R26 口径遗留，不阻断）' % len(err_files))
    print('=' * 72)
    ok = len(diff_files) == 0
    print('RESULT: %s' % ('PASS 零差异' if ok else 'FAIL 有差异'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())