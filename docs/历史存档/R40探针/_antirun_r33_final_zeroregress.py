# -*- coding: utf-8 -*-
"""R33 终验：真实（已改）lexer.py 全语料 token 流 == 改动前快照（_r33_lexer_head.py）。
确认 _P0A_NEVER_SPLIT 清零后零回归。"""
import glob
import hashlib
import importlib
import json
import os
import sys

ROOT = r'G:/dswork/duan-light-merge'
SNAP = os.path.join(ROOT, 'lightharness', '_r33_lexer_head.py')
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


def main():
    # 真实（已改）lexer：清缓存后导入
    sys.path.insert(0, os.path.join(ROOT, 'light-merge', 'src'))
    import lexer as real_mod
    sys.modules.pop('lexer', None)
    # 强制重读磁盘
    real_mod = importlib.import_module('lexer')
    ns_real = sorted(real_mod.Lexer._P0A_NEVER_SPLIT)
    print('真实 lexer _P0A_NEVER_SPLIT(%d)=%s' % (len(ns_real), ns_real))
    print('真实 lexer HM(%d)=%s' % (len(real_mod._P0A_HEAD_MERGE_SINGLE),
          sorted(real_mod._P0A_HEAD_MERGE_SINGLE)))
    # 快照（改动前）
    snap_name = '_r33_lexer_head_mod'
    open(os.path.join(LH, snap_name + '.py'), 'w', encoding='utf-8').write(
        open(SNAP, encoding='utf-8').read())
    sys.modules.pop(snap_name, None)
    snap_mod = importlib.import_module(snap_name)
    ns_snap = sorted(snap_mod.Lexer._P0A_NEVER_SPLIT)
    print('快照 lexer _P0A_NEVER_SPLIT(%d)=%s' % (len(ns_snap), ns_snap))
    print('语料文件数：%d' % len(CORPUS))

    base = seqs_of(snap_mod)
    cur = seqs_of(real_mod)
    base_err = {r for r in base if len(base[r]) == 1 and base[r][0].startswith('ERR:')}
    cur_err = {r for r in cur if len(cur[r]) == 1 and cur[r][0].startswith('ERR:')}
    changed = [r for r in base if sha(cur[r]) != sha(base[r]) and r not in base_err]
    new_err = sorted(cur_err - base_err)
    print()
    print('变化文件数 = %d' % len(changed))
    print('新增错误文件数 = %d' % len(new_err))
    if changed:
        for r in changed[:20]:
            print('   ', r)
    if new_err:
        for r in new_err[:20]:
            print('  ERR', r)
    if not changed and not new_err:
        print('✅ 真实 lexer 改动后全语料 token 零变化（零回归）')
    json.dump({'real_ns': ns_real, 'snap_ns': ns_snap,
               'changed': changed, 'new_err': new_err,
               'corpus': len(CORPUS)},
              open(os.path.join(LH, '_antirun_r33_final_zeroregress.json'), 'w',
                   encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
