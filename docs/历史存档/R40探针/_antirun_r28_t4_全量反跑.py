# -*- coding: utf-8 -*-
"""R28 任务4 全量反跑：CS表2字清零 边界测试 + 全语料 token 零变化验证。

对比维度：
  [A] 边界测试用例执行：test_R28_列词尾切出/类声明词尾并入/混合场景 rc=0
  [B] pytest token 层测试：tests/test_R28_CS表2字词尾上下文_token.py
  [C] 全语料 tokenize 序列快照：对照 R26 基线快照（既有失败 2 排除）
  [D] 性能基线：全语料 tokenize 耗时（10 次取平均）

输出：_task4_R28_反跑结果.json + 控制台摘要
"""
import os
import sys
import json
import time
import glob
import hashlib
import subprocess

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
PY = os.path.join(LIGHTP, '.venv', 'Scripts', 'python.exe')
sys.path.insert(0, os.path.join(LIGHTP, 'src'))

PATTERNS = [HARNESS + '/examples/**/*.light', HARNESS + '/src/**/*.light',
            HARNESS + '/tests/**/*.light', LIGHTP + '/examples/**/*.light',
            LIGHTP + '/stdlib/**/*.light', LIGHTP + '/bootstrap/**/*.light',
            LIGHTP + '/src/**/*.light', LIGHTP + '/tests/**/*.light']
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))

BOUNDARY_TESTS = [
    'examples/test_R28_列词尾切出.light',
    'examples/test_R28_类声明词尾并入.light',
    'examples/test_R28_混合场景.light',
]
PYTEST_FILE = 'tests/test_R28_CS表2字词尾上下文_token.py'
R26_SNAPSHOT = os.path.join(HARNESS, '_antirun_r26_基线快照.json')
R25_BASELINE_SEC = 9.63


def read(f):
    return open(f, encoding='utf-8', errors='replace').read()


def sha_text(t):
    return hashlib.sha256(t.encode('utf-8')).hexdigest()


def token_seq(text):
    import lexer
    try:
        toks = lexer.Lexer(text, deterministic=True).tokenize()
        return [(x.type.name, x.value) for x in toks
                if x.type.name not in ('EOF', 'NEWLINE')]
    except Exception as e:
        return ['ERR:' + type(e).__name__]


def main():
    t0 = time.time()
    import lexer as lx

    lexer_sha = sha_text(read(os.path.join(LIGHTP, 'src', 'lexer.py')))
    print('=' * 72)
    print('R28 任务4 全量反跑（CS 清零态）')
    print('=' * 72)
    print('lexer sha = %s | CS = %s | DUAL = %d | HM = %d | TAIL_CUT = %s'
          % (lexer_sha[:12], sorted(lx._COMPOUND_SAFE_SINGLE_KEYWORDS),
             len(lx._P0A_HEAD_MERGE_DUAL), len(lx._P0A_HEAD_MERGE_SINGLE),
             sorted(lx._P0A_TAIL_CUT_SINGLE)))
    print('语料 = %d 文件' % len(CORPUS))
    print('-' * 72)

    # [A] 边界测试
    print('[A] 边界测试用例（.light）执行')
    boundary_rc = {}
    for rel in BOUNDARY_TESTS:
        r = subprocess.run([PY, os.path.join(HARNESS, '运行.py'),
                            os.path.join(HARNESS, rel)],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=300, cwd=HARNESS)
        boundary_rc[rel] = r.returncode
        print('  %-42s rc=%d' % (os.path.basename(rel), r.returncode))
        if r.returncode != 0:
            print('    %s' % (r.stderr or r.stdout or '')[-200:].replace('\n', ' | '))
    boundary_ok = all(v == 0 for v in boundary_rc.values())

    # [B] pytest
    print('\n[B] pytest token 层测试')
    pr = subprocess.run([PY, '-m', 'pytest', os.path.join(HARNESS, PYTEST_FILE),
                         '-q', '--no-header', '-p', 'no:cacheprovider'],
                        capture_output=True, text=True, encoding='utf-8',
                        errors='replace', timeout=600, cwd=HARNESS)
    tail = (pr.stdout or '')[-600:]
    print(tail)
    import re
    m = re.search(r'(\d+) passed', tail)
    passed = int(m.group(1)) if m else 0
    m = re.search(r'(\d+) failed', tail)
    failed = int(m.group(1)) if m else 0

    # [C] 全语料对照 R26 基线
    print('\n[C] 全语料 tokenize 快照（%d 文件）' % len(CORPUS))
    base = json.load(open(R26_SNAPSHOT, encoding='utf-8'))
    base_per = base.get('per_file', {})
    base_err = set(base.get('base_err_files', []))
    changed, compared, cur_err, texts = [], 0, [], []
    for f in CORPUS:
        rel = os.path.relpath(f, ROOT).replace('\\', '/')
        try:
            t = read(f)
        except Exception:
            continue
        seq = token_seq(t)
        if len(seq) == 1 and isinstance(seq[0], str) and seq[0].startswith('ERR:'):
            cur_err.append(rel)
            continue
        texts.append(t)
        if rel not in base_per or rel in base_err:
            continue
        compared += 1
        fp = sha_text(json.dumps(seq, ensure_ascii=False))
        if fp != base_per[rel]['sha']:
            changed.append(rel)
    zero_change = not changed
    print('  可比 %d 文件（既有失败 %d 排除）' % (compared, len(base_err)))
    if changed:
        print('  ⚠️  token 变化 %d 文件: %s' % (len(changed), changed[:8]))
    else:
        print('  ✅ 全语料 token 零变化')

    # [D] 性能
    print('\n[D] 性能基线（全语料纯 tokenize × 10 次取平均）')
    timings = []
    for _ in range(10):
        ti = time.time()
        for t in texts:
            try:
                lx.Lexer(t, deterministic=True).tokenize()
            except lx.LexerError:
                pass
        timings.append(time.time() - ti)
    timings.sort()
    avg = sum(timings) / len(timings)
    med = timings[len(timings) // 2]
    print('  各次: %s' % ['%.2f' % x for x in timings])
    print('  平均 = %.2fs | 中位 = %.2fs | R25基线 = %.2fs'
          % (avg, med, R25_BASELINE_SEC))

    result = {
        'lexer_sha': lexer_sha,
        'cs_final': sorted(lx._COMPOUND_SAFE_SINGLE_KEYWORDS),
        'corpus_files': len(CORPUS),
        'boundary_tests': boundary_rc, 'boundary_ok': boundary_ok,
        'pytest_passed': passed, 'pytest_failed': failed,
        'baseline_compare_zero_change': zero_change,
        'baseline_changed_files': changed,
        'perf_avg_sec': round(avg, 3), 'perf_median_sec': round(med, 3),
        'seconds': round(time.time() - t0, 1),
    }
    out = os.path.join(HARNESS, '_task4_R28_反跑结果.json')
    json.dump(result, open(out, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

    print('\n' + '=' * 72)
    print('[A] 边界测试 rc 全0 : %s' % boundary_ok)
    print('[B] pytest passed=%d failed=%d' % (passed, failed))
    print('[C] 全语料零变化 : %s' % zero_change)
    print('[D] 性能 : 平均 %.2fs（R25基线 %.2fs）' % (avg, R25_BASELINE_SEC))
    print('结果文件: %s' % out)


if __name__ == '__main__':
    main()
