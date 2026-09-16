# -*- coding: utf-8 -*-
"""R29 任务1+2 隔离分析：不改主树，进程内 monkeypatch COMMON_COMPOUND_WORDS。

步骤：
  1) 用当前（完整 37 条）lexer 对全语料 tokenize，生成固定基线快照
     _r29_baseline_tokens.json（供后续收口/最终验证比对）。
  2) 对 A批(9)+B批(10) 每条目，临时从 CCW 移除，重验：
       G1 语料门：命中语料文件 token 序列零变化
       隔离中立：条目自身单独 tokenize 是否变化（R23「隔离非中立」指示）
  3) 输出 _r29_t1t2_analysis.json 供裁决删除清单。

不写主树、不并发测试。
"""
import os
import sys
import json
import glob
import hashlib
import time

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

ENTRIES_A = ['位与', '位异或', '位或', '位非', '异步写入文件', '异步睡眠',
             '异步读取文件', '异步追加文件', '并发等待']
ENTRIES_B = ['导入错误', '类型错误', '零除错误', '设指针', '设指针值', '设系统',
             '设系统错误码', '设置', '设置数组', '低级关闭']


def read(f):
    return open(f, encoding='utf-8', errors='replace').read()


def tok_sha(text):
    try:
        toks = lexer.Lexer(text, deterministic=True).tokenize()
        seq = [(x.type.name, x.value) for x in toks
               if x.type.name not in ('EOF', 'NEWLINE')]
    except Exception as e:
        return 'ERR:' + type(e).__name__
    return hashlib.sha256(json.dumps(seq, ensure_ascii=False).encode('utf-8')).hexdigest()


def main():
    t0 = time.time()
    sha_full = hashlib.sha256(read(os.path.join(LIGHTP, 'src', 'lexer.py')).encode('utf-8')).hexdigest()
    print('lexer sha      = %s' % sha_full[:12])
    print('CCW 总数       = %d' % len(lexer.COMMON_COMPOUND_WORDS))
    print('语料文件数     = %d' % len(CORPUS))

    # 1) 基线快照
    base = {}
    texts = {}
    for f in CORPUS:
        rel = os.path.relpath(f, ROOT).replace('\\', '/')
        t = read(f)
        texts[rel] = t
        base[rel] = tok_sha(t)
    json.dump({'lexer_sha': sha_full, 'per_file': base},
              open(os.path.join(HARNESS, '_r29_baseline_tokens.json'), 'w', encoding='utf-8'),
              ensure_ascii=False)
    print('基线快照已存 _r29_baseline_tokens.json（可比 %d 文件）' % len(base))

    # 2) 逐条隔离重验
    base_set = lexer.COMMON_COMPOUND_WORDS

    def analyze(batch, entries):
        print('\n=== %s（%d 条）===' % (batch, len(entries)))
        res = {}
        for e in entries:
            # 隔离中立：条目自身在完整集 vs 移除集下的 token 流
            lexer.COMMON_COMPOUND_WORDS = base_set
            iso_full = tok_sha(e)
            lexer.COMMON_COMPOUND_WORDS = frozenset(base_set - {e})
            iso_patched = tok_sha(e)
            iso_changed = (iso_full != iso_patched)
            # G1：命中语料文件重验
            hits = [rel for rel, t in texts.items() if e in t]
            changed = [rel for rel in hits if tok_sha(texts[rel]) != base[rel]]
            res[e] = {'hits': len(hits), 'changed_files': changed,
                      'iso_token_changed': iso_changed,
                      'g1_pass': (len(changed) == 0)}
            print('  %-7s 命中=%2d 变化=%2d 隔离变=%s G1=%s'
                  % (e, len(hits), len(changed), iso_changed, len(changed) == 0))
        lexer.COMMON_COMPOUND_WORDS = base_set
        return res

    ra = analyze('A批', ENTRIES_A)
    rb = analyze('B批', ENTRIES_B)

    out = {'lexer_sha': sha_full, 'A': ra, 'B': rb}
    json.dump(out, open(os.path.join(HARNESS, '_r29_t1t2_analysis.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('\n分析完成，用时 %.1fs，结果 _r29_t1t2_analysis.json' % (time.time() - t0))
    # 汇总可删候选
    deletable = [e for e, v in {**ra, **rb}.items() if v['g1_pass']]
    kept = [e for e, v in {**ra, **rb}.items() if not v['g1_pass']]
    print('可删候选(%d): %s' % (len(deletable), deletable))
    print('保留( %d): %s' % (len(kept), kept))


if __name__ == '__main__':
    main()
