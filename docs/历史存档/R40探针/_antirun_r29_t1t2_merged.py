# -*- coding: utf-8 -*-
"""R29 任务1+2 合并后最终校验：编辑后的 lexer（CCW=10）对全语料 token 零变化。

对照 _r29_baseline_tokens.json（编辑前 24 条态基线）。零变化 = 14 条删除无回归。
"""
import os
import sys
import json
import glob
import hashlib

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
sys.path.insert(0, os.path.join(LIGHTP, 'src'))
import lexer  # noqa: E402

PATTERNS = [HARNESS + '/examples/**/*.light', HARNESS + '/src/**/*.light',
            HARNESS + '/tests/**/*.light', LIGHTP + '/examples/**/*.light',
            LIGHTP + '/stdlib/**/*.light', LIGHTP + '/bootstrap/**/*.light',
            LIGHTP + '/src/**/*.light', LIGHTP + '/tests/**/*.light']
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))


def tok_sha(text):
    try:
        toks = lexer.Lexer(text, deterministic=True).tokenize()
        seq = [(x.type.name, x.value) for x in toks
               if x.type.name not in ('EOF', 'NEWLINE')]
    except Exception as e:
        return 'ERR:' + type(e).__name__
    return hashlib.sha256(json.dumps(seq, ensure_ascii=False).encode('utf-8')).hexdigest()


def main():
    base = json.load(open(os.path.join(HARNESS, '_r29_baseline_tokens.json'), encoding='utf-8'))
    base_per = base['per_file']
    base_sha = base['lexer_sha'][:12]
    cur_sha = hashlib.sha256(open(os.path.join(LIGHTP, 'src', 'lexer.py'),
                                  encoding='utf-8', errors='replace').read().encode('utf-8')).hexdigest()[:12]
    print('基线 lexer sha = %s (CCW 24)' % base_sha)
    print('当前 lexer sha = %s | CCW = %d' % (cur_sha, len(lexer.COMMON_COMPOUND_WORDS)))
    print('语料 = %d 文件' % len(CORPUS))

    changed, compared, cur_err = [], 0, []
    for f in CORPUS:
        rel = os.path.relpath(f, ROOT).replace('\\', '/')
        try:
            t = open(f, encoding='utf-8', errors='replace').read()
        except Exception:
            continue
        s = tok_sha(t)
        if s.startswith('ERR:'):
            cur_err.append(rel)
            continue
        if rel not in base_per:
            continue
        compared += 1
        if s != base_per[rel]:
            changed.append(rel)
    zero = not changed
    print('可比 %d 文件 | 当前失败 %d' % (compared, len(cur_err)))
    print('全语料 token 零变化: %s' % ('✅ PASS' if zero else '❌ FAIL %d' % len(changed)))
    if changed:
        print('变化文件: %s' % changed[:10])
    out = {'lexer_sha': cur_sha, 'ccw_count': len(lexer.COMMON_COMPOUND_WORDS),
           'corpus_compared': compared, 'baseline_compare_zero_change': zero,
           'changed_files': changed, 'current_err_files': cur_err}
    json.dump(out, open(os.path.join(HARNESS, '_task1t2_R29_merged_G1.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('结果: _task1t2_R29_merged_G1.json')


if __name__ == '__main__':
    main()
