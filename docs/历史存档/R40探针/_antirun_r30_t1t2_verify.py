# -*- coding: utf-8 -*-
"""R30 任务1+2 最终验证：词首前缀类通用化 + CCW 删 6 条。

G1 语料门：编辑后 lexer 对全语料 tokenize，对照 _r29_baseline_tokens.json（CCW=10 态）
           → 零变化。
G3 边界门：6 条目标词的边界形态（调用/列表/条件/设名/段落名/字符串）撤后仍整词并入；
          反向形态（位独立 / 当为循环关键字 / 非为逻辑关键字）不受影响。
输出：_task1t2_R30_证据.json + 控制台摘要。
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

TASK1 = ['位与', '位异或', '位或', '位非']
TASK2 = ['应当', '除非']


def seq(text):
    try:
        t = lexer.Lexer(text, deterministic=True).tokenize()
        return [(x.type.name, x.value) for x in t if x.type.name not in ('EOF', 'NEWLINE')]
    except Exception as e:
        return ['ERR:' + type(e).__name__ + ':' + str(e)[:40]]


def tsha(text):
    s = seq(text)
    return hashlib.sha256(json.dumps(s, ensure_ascii=False).encode('utf-8')).hexdigest()


def g3_forms(w):
    return ['设 %s 为 7' % w, '段落 %s 接收 a:\n  返回 a' % w, '返回 %s(1)' % w,
            '设 x 为 [ %s ]' % w, '如果 %s 那么 返回 1' % w, '打印("%s")' % w]


def is_merged(tokens, w):
    return any(t[0] == 'IDENTIFIER' and t[1] == w for t in tokens)


def main():
    base = json.load(open(os.path.join(HARNESS, '_r29_baseline_tokens.json'), encoding='utf-8'))
    base_per = base['per_file']
    cur_sha = hashlib.sha256(open(os.path.join(LIGHTP, 'src', 'lexer.py'),
                                  'rb').read()).hexdigest()[:12]
    print('=' * 72)
    print('R30 任务1+2 最终验证 | lexer sha=%s | CCW=%s | PREFIX=%s'
          % (cur_sha, sorted(lexer.COMMON_COMPOUND_WORDS), sorted(lexer._P0A_HEAD_MERGE_PREFIX)))
    print('=' * 72)

    # G1
    changed, compared, cur_err, skipped_base_err = [], 0, [], []
    for f in CORPUS:
        rel = os.path.relpath(f, ROOT).replace('\\', '/')
        try:
            t = open(f, encoding='utf-8', errors='replace').read()
        except Exception:
            continue
        if rel not in base_per:
            continue
        if base_per[rel].startswith('ERR:'):
            skipped_base_err.append(rel)   # 基线即失败的既有错误文件，排除
            continue
        s = tsha(t)
        if s.startswith('ERR:'):
            cur_err.append(rel)
            continue
        compared += 1
        if s != base_per[rel]:
            changed.append(rel)
    print('[G1] 可比 %d 文件 | 当前失败 %d | 基线即有错误排除 %d %s | 零变化: %s'
          % (compared, len(cur_err), len(skipped_base_err), skipped_base_err,
             '✅ PASS' if not changed else '❌ FAIL %d' % len(changed)))
    if changed:
        print('     变化: %s' % changed[:8])

    # G3 边界形态（字符串态单独校验）
    print('\n[G3] 边界形态（撤后仍整词并入；末列为字符串态）:')
    g3 = {}
    for w in TASK1 + TASK2:
        merged = [is_merged(seq(fm), w) for fm in g3_forms(w)]
        str_toks = seq('打印("%s")' % w)
        str_ok = any(t[0] == 'STRING' and t[1] == w for t in str_toks)
        g3[w] = {'forms_merged': merged, 'str_ok': str_ok,
                 'all_merged': all(merged[:5]) and str_ok}
        print('  %-6s %s | 字符串态=%s'
              % (w, ['✓' if m else '✗' for m in merged[:5]],
                 '✓' if str_ok else '✗'))
    # 反向形态
    print('\n[G3-反向] 关键字/独立使用不受影响:')
    rev = {}
    for label, src in [('位 独立', '设 位 为 1'), ('位 为 1', '位 为 1'),
                       ('当 循环', '当 x > 0:\n  返回 1'), ('非 逻辑', '设 y 为 非 真'),
                       ('与 运算', '设 z 为 甲 与 乙')]:
        rev[label] = seq(src)
        print('  %-10s %s' % (label, rev[label]))

    ok = (not changed) and all(g3[w]['all_merged'] for w in TASK1 + TASK2)
    end_sha = hashlib.sha256(open(os.path.join(LIGHTP, 'src', 'lexer.py'),
                                  'rb').read()).hexdigest()[:12]
    if end_sha != cur_sha:
        print('\n[!] lexer.py 运行期间被并发写入（%s → %s）：证据作废，须静置后重跑！'
              % (cur_sha, end_sha))
        ok = False
    out = {'lexer_sha': cur_sha, 'lexer_sha_end': end_sha, 'sha_stable': end_sha == cur_sha,
           'ccw': sorted(lexer.COMMON_COMPOUND_WORDS),
           'prefix': sorted(lexer._P0A_HEAD_MERGE_PREFIX),
           'corpus_compared': compared, 'g1_zero_change': not changed,
           'g1_changed_files': changed, 'g1_skipped_base_err': skipped_base_err,
           'g3': g3, 'reverse': rev, 'all_pass': ok}
    json.dump(out, open(os.path.join(HARNESS, '_task1t2_R30_证据.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('\n结论: %s（证据 _task1t2_R30_证据.json）' % ('✅ ALL PASS' if ok else '❌ FAIL'))


if __name__ == '__main__':
    main()
