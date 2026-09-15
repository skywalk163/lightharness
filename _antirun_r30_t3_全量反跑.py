# -*- coding: utf-8 -*-
"""R30 任务3 全语料 token 反跑 / 快照工具（支持指定 lexer 模块）。

用法：
  python _antirun_r30_t3_全量反跑.py snapshot <module> <out.json>
      module='lexer'           → light-merge/src/lexer.py（当前工作区版本）
      module='_r30_lexer_head' → git HEAD 版 lexer.py（pre-R30 纯净基线）
      module='_r30_lexer_t12'  → 当前版本剔除任务3 全部改动（= 任务1/2 状态）
  python _antirun_r30_t3_全量反跑.py compare <module> <base.json>

口径：lightharness + light-merge 全部 .light（851 文件），deterministic=True，
过滤 EOF/NEWLINE，sha256(json token 序列) 逐文件比对。
"""
import glob
import hashlib
import importlib
import json
import os
import sys

ROOT = r'G:/dswork/duan-light-merge'
sys.path.insert(0, os.path.join(ROOT, 'light-merge', 'src'))
sys.path.insert(0, os.path.join(ROOT, 'lightharness'))

PATTERNS = [ROOT + '/lightharness/examples/**/*.light',
            ROOT + '/lightharness/src/**/*.light',
            ROOT + '/lightharness/tests/**/*.light',
            ROOT + '/light-merge/examples/**/*.light',
            ROOT + '/light-merge/stdlib/**/*.light',
            ROOT + '/light-merge/bootstrap/**/*.light',
            ROOT + '/light-merge/src/**/*.light',
            ROOT + '/light-merge/tests/**/*.light']
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))


def read(f):
    return open(f, encoding='utf-8', errors='replace').read()


def sha(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False).encode('utf-8')).hexdigest()


def run(module_name):
    lexer = importlib.import_module(module_name)
    print('模块：%-16s  CCW 条数：%d' % (module_name, len(lexer.COMMON_COMPOUND_WORDS)))
    cur = {}
    for f in CORPUS:
        rel = os.path.relpath(f, ROOT).replace('\\', '/')
        try:
            toks = lexer.Lexer(read(f), deterministic=True).tokenize()
            seq = [(t.type.name, t.value) for t in toks
                   if t.type.name not in ('EOF', 'NEWLINE')]
        except Exception as e:
            seq = ['ERR:' + type(e).__name__]
        cur[rel] = seq
    return lexer, cur


def main():
    mode = sys.argv[1]
    module_name = sys.argv[2]
    print('语料文件数：%d' % len(CORPUS))
    lexer, cur = run(module_name)

    if mode == 'snapshot':
        out = sys.argv[3]
        err = {r for r, s in cur.items() if len(s) == 1 and s[0].startswith('ERR:')}
        json.dump({'module': module_name,
                   'per_file': {r: {'sha': sha(s), 'n': len(s)} for r, s in cur.items()},
                   'total_tokens': sum(len(s) for s in cur.values()),
                   'err_files': sorted(err),
                   'ccw': sorted(lexer.COMMON_COMPOUND_WORDS)},
                  open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('快照已写：%s（错误文件 %d）' % (out, len(err)))
        return

    base = json.load(open(sys.argv[3], encoding='utf-8'))
    base_per = base.get('per_file', {})
    changed, missing = [], []
    total_delta = 0
    for rel, seq in cur.items():
        if rel not in base_per:
            missing.append(rel)
            continue
        if sha(seq) != base_per[rel]['sha']:
            changed.append(rel)
        total_delta += len(seq) - base_per[rel]['n']
    print('可比文件：%d   token 总数差：%+d' % (len(cur) - len(missing), total_delta))
    if missing:
        print('⚠️  基线缺失 %d 文件' % len(missing))
    if changed:
        print('⚠️  token 变化 %d 文件：' % len(changed))
        for rel in changed[:40]:
            print('   %s' % rel)
    else:
        print('✅ 全语料 token 零变化')


if __name__ == '__main__':
    main()
