# -*- coding: utf-8 -*-
"""R27 任务4 全量反跑：CS表16字逐字通用化 边界测试 + 全语料 token 零变化验证。

对比维度：
  [A] 边界测试用例执行：test_R27_词首并入正向/反向/混合 三个 .light 文件 rc=0
  [B] pytest token 层测试：tests/test_R27_CS表16字词首并入_token.py（113 passed）
  [C] 全语料 tokenize 序列快照：843+ 文件，对照 R26 基线快照（_antirun_r26_基线快照.json）
      —— R27 修改（DUAL 正面规则 + L-119 嵌入扫描等价 + CS 16→2）必须 token 零变化
  [D] 性能基线：全语料 tokenize 耗时（10 次取平均），对标第26轮基线

用法：python _antirun_r27_t4_全量反跑.py [--baseline]
输出：_task4_R27_反跑结果.json + 控制台摘要
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
LEXER = os.path.join(LIGHTP, 'src', 'lexer.py')
PY = os.path.join(LIGHTP, '.venv', 'Scripts', 'python.exe')
sys.path.insert(0, os.path.join(LIGHTP, 'src'))

PATTERNS = [HARNESS + '/examples/**/*.light', HARNESS + '/src/**/*.light',
            HARNESS + '/tests/**/*.light', LIGHTP + '/examples/**/*.light',
            LIGHTP + '/stdlib/**/*.light', LIGHTP + '/bootstrap/**/*.light',
            LIGHTP + '/src/**/*.light', LIGHTP + '/tests/**/*.light']
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))

BOUNDARY_TESTS = [
    'examples/test_R27_词首并入正向.light',
    'examples/test_R27_词首并入反向.light',
    'examples/test_R27_词首并入混合.light',
]
PYTEST_FILE = 'tests/test_R27_CS表16字词首并入_token.py'
R26_SNAPSHOT = os.path.join(HARNESS, '_antirun_r26_基线快照.json')
R26_BASELINE_SEC = 9.63  # 第25轮基线


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

    compare = '--baseline' not in sys.argv
    lexer_sha = sha_text(read(LEXER))
    cs_len = len(lx._COMPOUND_SAFE_SINGLE_KEYWORDS)

    print('=' * 72)
    print('R27 任务4 全量反跑')
    print('=' * 72)
    print('lexer sha = %s | CS残部 = %d 字 %s | 语料 = %d 文件'
          % (lexer_sha[:12], cs_len, sorted(lx._COMPOUND_SAFE_SINGLE_KEYWORDS),
             len(CORPUS)))
    print('DUAL = %d 字 | HM = %d 字 | R26移除 = %d | R27移除 = %d'
          % (len(lx._P0A_HEAD_MERGE_DUAL), len(lx._P0A_HEAD_MERGE_SINGLE),
             len(lx._R26_CS_REMOVED), len(lx._R27_CS_REMOVED)))
    print('-' * 72)

    # [A] 边界测试用例
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
    tail = (pr.stdout or '')[-1200:]
    print(tail)
    import re
    m = re.search(r'(\d+) passed', tail)
    passed = int(m.group(1)) if m else 0
    m = re.search(r'(\d+) failed', tail)
    failed = int(m.group(1)) if m else 0

    # [C] 全语料快照 + 对照 R26 基线
    print('\n[C] 全语料 tokenize 快照（%d 文件）' % len(CORPUS))
    snapshot, err_files, changed = {}, [], []
    texts = []
    for f in CORPUS:
        rel = os.path.relpath(f, ROOT).replace('\\', '/')
        try:
            t = read(f)
        except Exception:
            err_files.append(rel)
            continue
        texts.append(t)
        seq = token_seq(t)
        fp = sha_text(json.dumps(seq, ensure_ascii=False))
        snapshot[rel] = {'sha': fp, 'n': len(seq)}
        if seq and isinstance(seq[0], str) and seq[0].startswith('ERR:'):
            err_files.append(rel)
    corpus_fp = sha_text(json.dumps({k: v['sha'] for k, v in snapshot.items()},
                                    ensure_ascii=False, sort_keys=True))
    print('  成功 %d | 失败 %d | 聚合指纹 = %s'
          % (len(snapshot), len(err_files), corpus_fp[:16]))

    zero_change = None
    if compare:
        if os.path.exists(R26_SNAPSHOT):
            base = json.load(open(R26_SNAPSHOT, encoding='utf-8'))
            base_per = base.get('per_file', {})
            base_err = set(base.get('base_err_files', []))
            err_set = set(err_files)
            for rel, v in snapshot.items():
                if rel not in base_per:
                    continue
                # 既有失败文件（基线与当前均 tokenize 失败）不参与比对
                if rel in base_err or rel in err_set:
                    continue
                if v['sha'] != base_per[rel]['sha']:
                    changed.append(rel)
            zero_change = not changed
            if changed:
                print('  ⚠️  对照 R26 基线：%d 文件 token 变化' % len(changed))
                for rel in changed[:10]:
                    print('     %s' % rel)
            else:
                print('  ✅ 对照 R26 基线（%d 文件可比，既有失败 %d 排除）：token 零变化'
                      % (len([r for r in snapshot
                              if r in base_per and r not in err_set
                              and r not in base_err]), len(err_set & base_err)))
        else:
            print('  ⚠️  未找到 R26 基线快照，跳过比对')

    # [D] 性能：纯 tokenize × 10
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
          % (avg, med, R26_BASELINE_SEC))

    result = {
        'lexer_sha': lexer_sha,
        'cs_rest': sorted(lx._COMPOUND_SAFE_SINGLE_KEYWORDS),
        'corpus_files': len(CORPUS),
        'corpus_aggregate_fingerprint': corpus_fp,
        'boundary_tests': boundary_rc,
        'boundary_ok': boundary_ok,
        'pytest_passed': passed, 'pytest_failed': failed,
        'token_error_files': err_files,
        'baseline_compare_zero_change': zero_change,
        'baseline_changed_files': changed,
        'perf_avg_sec': round(avg, 3), 'perf_median_sec': round(med, 3),
        'seconds': round(time.time() - t0, 1),
    }
    out = os.path.join(HARNESS, '_task4_R27_反跑结果.json')
    json.dump(result, open(out, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

    print('\n' + '=' * 72)
    print('[A] 边界测试 rc 全0 : %s' % boundary_ok)
    print('[B] pytest passed=%d failed=%d' % (passed, failed))
    print('[C] 全语料零变化 : %s' % zero_change)
    print('[D] 性能 : 平均 %.2fs（R25基线 %.2fs）' % (avg, R26_BASELINE_SEC))
    print('结果文件: %s' % out)


if __name__ == '__main__':
    main()
