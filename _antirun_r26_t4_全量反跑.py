# -*- coding: utf-8 -*-
"""R26 任务4 全量反跑：词首并入通用化边界测试 + 全语料 token 零变化验证。

对比维度：
  [A] 边界测试用例执行：test_R26_词首并入正向/反向/混合 三个 .light 文件 rc=0
  [B] pytest token 层测试：tests/test_R26_词首并入_token.py（50+ passed）
  [C] 全语料 tokenize 序列快照：837+ 文件，输出 token 序列指纹（供任务1-3完成后比对）
  [D] 性能基线：全语料 tokenize 耗时（10 次取平均），对标第25轮基线 9.63s

前提说明：任务1-3（词首并入正面规则 + CS表缩减）尚未落地时，本脚本以"当前磁盘 lexer"
为基准记录快照与基线。任务1-3 合并后再次执行本脚本，即可得到 token 变化清单与性能对比。

输出：_task4_R26_反跑结果.json + 控制台摘要。
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
    'examples/test_R26_词首并入正向.light',
    'examples/test_R26_词首并入反向.light',
    'examples/test_R26_词首并入混合.light',
]

PYTEST_FILE = 'tests/test_R26_词首并入_token.py'

# 第25轮性能基线（秒）
R25_BASELINE_SEC = 9.63

# 基线快照文件（首次运行时自动创建）
BASELINE_SNAPSHOT = os.path.join(HARNESS, '_antirun_r26_基线快照.json')


def read(f):
    return open(f, encoding='utf-8', errors='replace').read()


def sha_text(t):
    return hashlib.sha256(t.encode('utf-8')).hexdigest()


def tokenize_fingerprint(text):
    """返回 (kinds,values) 序列指纹，排除 EOF/NEWLINE 噪声。"""
    import lexer
    try:
        toks = lexer.Lexer(text, deterministic=True).tokenize()
        seq = [(x.type.name, x.value) for x in toks if x.type.name not in ('EOF', 'NEWLINE')]
        return sha_text(json.dumps(seq, ensure_ascii=False)), len(seq)
    except Exception as e:
        return 'ERR:' + type(e).__name__, 0


def main():
    t0 = time.time()
    import lexer as lx

    # 命令行参数：--baseline 写入基线快照；默认比对基线
    write_baseline = '--baseline' in sys.argv
    compare_baseline = not write_baseline

    lexer_sha = sha_text(read(LEXER))
    cs_len = len(lx.Lexer.compound_safe_single_keywords)

    # 检测任务1-2是否已落地
    has_head_merge = hasattr(lx, '_P0A_HEAD_MERGE_SINGLE')
    has_head_split = hasattr(lx, '_P0A_HEAD_SPLIT_SINGLE')
    print('=' * 72)
    print('R26 任务4 全量反跑')
    print('=' * 72)
    print('lexer sha = %s | CS表 = %d 字 | 语料 = %d 文件'
          % (lexer_sha[:12], cs_len, len(CORPUS)))
    print('任务1 _P0A_HEAD_MERGE_SINGLE : %s'
          % ('已落地(%d字)' % len(lx._P0A_HEAD_MERGE_SINGLE) if has_head_merge else '未落地'))
    print('任务1 _P0A_HEAD_SPLIT_SINGLE : %s'
          % ('已落地(%d字)' % len(lx._P0A_HEAD_SPLIT_SINGLE) if has_head_split else '未落地'))
    print('-' * 72)

    # [A] 边界测试用例执行
    print('[A] 边界测试用例（.light）执行')
    boundary_rc = {}
    for rel in BOUNDARY_TESTS:
        r = subprocess.run([PY, os.path.join(HARNESS, '运行.py'), os.path.join(HARNESS, rel)],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=300, cwd=HARNESS)
        boundary_rc[rel] = r.returncode
        tail = (r.stdout or '')[-200:]
        err = (r.stderr or '')[-200:]
        print('  %-42s rc=%d' % (os.path.basename(rel), r.returncode))
        if r.returncode != 0:
            if err:
                print('    stderr: %s' % err.replace('\n', ' | '))
            elif tail:
                print('    stdout: %s' % tail.replace('\n', ' | '))
    boundary_ok = all(v == 0 for v in boundary_rc.values())

    # [B] pytest token 层测试
    print('\n[B] pytest token 层测试')
    pytest_target = os.path.join(HARNESS, PYTEST_FILE)
    pr = subprocess.run([PY, '-m', 'pytest', pytest_target, '-v', '--tb=short', '-q',
                         '--no-header', '-p', 'no:cacheprovider'],
                        capture_output=True, text=True, encoding='utf-8',
                        errors='replace', timeout=600, cwd=HARNESS)
    pytest_rc = pr.returncode
    tail = (pr.stdout or '')[-3000:]
    print(tail)
    if pr.stderr:
        print('stderr:', pr.stderr[-500:])

    # 解析 passed/failed/skipped 计数
    import re
    m = re.search(r'(\d+) passed', tail)
    passed = int(m.group(1)) if m else 0
    m = re.search(r'(\d+) failed', tail)
    failed = int(m.group(1)) if m else 0
    m = re.search(r'(\d+) skipped', tail)
    skipped = int(m.group(1)) if m else 0
    m = re.search(r'(\d+) error', tail)
    errors = int(m.group(1)) if m else 0

    # [C] 全语料 token 快照
    print('\n[C] 全语料 tokenize 快照（%d 文件）' % len(CORPUS))
    snapshot = {}
    err_files = []
    for f in CORPUS:
        try:
            t = read(f)
        except Exception:
            err_files.append(os.path.relpath(f, ROOT))
            continue
        fp, ntok = tokenize_fingerprint(t)
        rel = os.path.relpath(f, ROOT).replace('\\', '/')
        snapshot[rel] = {'sha': fp, 'n': ntok}
        if fp.startswith('ERR:'):
            err_files.append(rel)
    print('  成功 %d | 失败 %d' % (len(snapshot), len(err_files)))
    if err_files:
        print('  失败文件: %s' % err_files[:10])
    # 整体语料指纹（所有文件指纹的聚合）
    corpus_fp = sha_text(json.dumps({k: v['sha'] for k, v in snapshot.items()},
                                     ensure_ascii=False, sort_keys=True))
    print('  全语料聚合指纹 = %s' % corpus_fp[:16])

    # 基线写入 / 比对
    baseline_changes = []
    if write_baseline:
        baseline_data = {
            'lexer_sha': lexer_sha,
            'cs_len': cs_len,
            'corpus_files': len(CORPUS),
            'corpus_aggregate_fingerprint': corpus_fp,
            'per_file': {k: {'sha': v['sha'], 'n': v['n']} for k, v in snapshot.items()},
        }
        json.dump(baseline_data, open(BASELINE_SNAPSHOT, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        print('  ✅ 基线快照已写入: %s' % BASELINE_SNAPSHOT)
    elif compare_baseline and os.path.exists(BASELINE_SNAPSHOT):
        baseline_data = json.load(open(BASELINE_SNAPSHOT, encoding='utf-8'))
        baseline_per = baseline_data.get('per_file', {})
        baseline_fp = baseline_data.get('corpus_aggregate_fingerprint', '')
        changed, added, removed = [], [], []
        for f, v in snapshot.items():
            if f in baseline_per:
                if v['sha'] != baseline_per[f]['sha']:
                    changed.append(f)
            else:
                added.append(f)
        for f in baseline_per:
            if f not in snapshot:
                removed.append(f)
        baseline_changes = changed
        print('  基线聚合指纹 = %s' % baseline_fp[:16])
        if changed:
            print('  ⚠️  %d 文件 token 序列变化:' % len(changed))
            for f in changed[:15]:
                print('     %s' % f)
        if added:
            print('  ➕ %d 文件新增' % len(added))
        if removed:
            print('  ➖ %d 文件移除' % len(removed))
        if not (changed or added or removed):
            print('  ✅ 全语料 token 零变化')
    elif compare_baseline:
        print('  ⚠️  未找到基线快照，建议先运行 --baseline 创建')

    # [D] 性能基线：纯 tokenize 计时（不含 json/sha 后处理，与第25轮口径一致）
    print('\n[D] 性能基线（全语料纯 tokenize × 10 次取平均，不含哈希后处理）')
    texts = []
    for f in CORPUS:
        try:
            texts.append(read(f))
        except Exception:
            pass
    timings = []
    for i in range(10):
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
    print('  各次耗时: %s' % ['%.2f' % t for t in timings])
    print('  平均 = %.2fs | 中位 = %.2fs' % (avg, med))
    print('  第25轮基线 = %.2fs' % R25_BASELINE_SEC)
    delta = avg - R25_BASELINE_SEC
    print('  相对基线: %+.2fs (%+.1f%%)' % (delta, delta / R25_BASELINE_SEC * 100))

    result = {
        'lexer_sha': lexer_sha,
        'cs_len': cs_len,
        'task1_head_merge_landed': has_head_merge,
        'task1_head_split_landed': has_head_split,
        'corpus_files': len(CORPUS),
        'corpus_aggregate_fingerprint': corpus_fp,
        'boundary_tests': boundary_rc,
        'boundary_ok': boundary_ok,
        'pytest_rc': pytest_rc,
        'pytest_passed': passed,
        'pytest_failed': failed,
        'pytest_skipped': skipped,
        'pytest_errors': errors,
        'token_error_files': err_files,
        'baseline_compare': {
            'changed_files': baseline_changes,
            'zero_change': len(baseline_changes) == 0 if compare_baseline else None,
        },
        'perf_timings_sec': [round(t, 3) for t in timings],
        'perf_avg_sec': round(avg, 3),
        'perf_median_sec': round(med, 3),
        'r25_baseline_sec': R25_BASELINE_SEC,
        'perf_delta_sec': round(delta, 3),
        'seconds': round(time.time() - t0, 1),
    }
    out = os.path.join(HARNESS, '_task4_R26_反跑结果.json')
    json.dump(result, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print('\n' + '=' * 72)
    print('结果摘要')
    print('=' * 72)
    print('[A] 边界测试 rc 全0 : %s' % boundary_ok)
    print('[B] pytest passed=%d failed=%d skipped=%d errors=%d'
          % (passed, failed, skipped, errors))
    print('[C] 全语料 token 快照 : %d 文件，聚合指纹 %s'
          % (len(snapshot), corpus_fp[:16]))
    if compare_baseline and baseline_changes:
        print('    ⚠️  基线比对：%d 文件 token 变化' % len(baseline_changes))
    elif compare_baseline and not baseline_changes and os.path.exists(BASELINE_SNAPSHOT):
        print('    ✅ 基线比对：全语料 token 零变化')
    elif write_baseline:
        print('    ✅ 基线快照已写入')
    print('[D] 性能 : 平均 %.2fs（R25基线 %.2fs，%+.1f%%）'
          % (avg, R25_BASELINE_SEC, delta / R25_BASELINE_SEC * 100))
    print('\n结果文件: %s' % out)


if __name__ == '__main__':
    main()
