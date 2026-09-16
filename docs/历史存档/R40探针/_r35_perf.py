# -*- coding: utf-8 -*-
"""_r35_perf.py —— 第35轮 任务5.1 性能对比

口径：
  · 语料 = lightharness 全部 .light（src/ + examples/ + tests/），与任务书一致
  · 变体 A = 改动前（git show HEAD:src/lexer.py）
    变体 B = 改动后（当前工作树 src/lexer.py）
  · 两个变体各自在**独立子进程**中跑（完整 src 副本 ⇒ 派生集合隔离、无串扰）
  · 每变体：1 次预热 + 3 次计时，报告 3 次耗时与最优值
  · 输出 JSON：_r35_perf.json

用法：
  python _r35_perf.py            # 跑 A/B 两变体
  python _r35_perf.py A          # 只跑 A
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LM_SRC = os.path.join(ROOT, 'light-merge', 'src')
LH = os.path.join(ROOT, 'lightharness')
PATS = [LH + '/src/**/*.light', LH + '/examples/**/*.light',
        LH + '/tests/**/*.light']
OUT = os.path.join(LH, '_r35_perf.json')

CHILD = r'''
import glob, json, os, sys, time
srcdir, out, reps = sys.argv[2], sys.argv[3], int(sys.argv[4])
sys.path.insert(0, srcdir)
cfg = json.load(open(os.path.join(os.path.dirname(srcdir), '_r35_perf_cfg.json'),
                     encoding='utf-8'))
import lexer
files = sorted(set(sum((glob.glob(g, recursive=True) for g in cfg['pats']), [])))
def one_pass():
    n = 0
    for f in files:
        try:
            src = open(f, encoding='utf-8').read()
        except Exception:
            continue
        try:
            n += len(lexer.Lexer(src, deterministic=True).tokenize())
        except Exception:
            pass
    return n
one_pass()                      # 预热（不计时）
ts, toks = [], 0
for _ in range(reps):
    t0 = time.perf_counter()
    toks = one_pass()
    ts.append(time.perf_counter() - t0)
json.dump({'files': len(files), 'tokens': toks, 'times': ts,
           'best': min(ts), 'median': sorted(ts)[len(ts) // 2]},
          open(out, 'w', encoding='utf-8'))
print('  files=%d tokens=%d times=%s best=%.3fs'
      % (len(files), toks, [round(x, 3) for x in ts], min(ts)))
'''


def run_variant(tag, reps=3):
    """把 light-merge/src 复制到临时目录，用 tag 指定的 lexer 跑计时。"""
    tmp = tempfile.mkdtemp(prefix='r35perf_')
    d = os.path.join(tmp, 'src')
    shutil.copytree(LM_SRC, d,
                    ignore=shutil.ignore_patterns('__pycache__'))
    if tag == 'A':
        before = subprocess.run(
            ['git', '-C', os.path.join(ROOT, 'light-merge'),
             'show', 'HEAD:src/lexer.py'],
            capture_output=True)
        open(os.path.join(d, 'lexer.py'), 'wb').write(before.stdout)
        label = 'A 改动前 (HEAD)'
    else:
        shutil.copyfile(os.path.join(LM_SRC, 'lexer.py'),
                        os.path.join(d, 'lexer.py'))
        label = 'B 改动后 (R35)'
    json.dump({'pats': PATS},
              open(os.path.join(tmp, '_r35_perf_cfg.json'), 'w',
                   encoding='utf-8'))
    ch = os.path.join(tmp, 'child.py')
    out = os.path.join(tmp, 'out.json')
    open(ch, 'w', encoding='utf-8').write(CHILD)
    print('[%s] %s' % (tag, label))
    subprocess.run([sys.executable, ch, 'child', d, out, str(reps)],
                   check=True)
    res = json.load(open(out, encoding='utf-8'))
    res['tag'], res['label'] = tag, label
    # 记录 lexer 身份
    import hashlib
    res['lexer_sha'] = hashlib.sha256(
        open(os.path.join(d, 'lexer.py'), 'rb').read()).hexdigest()[:16]
    shutil.rmtree(tmp, ignore_errors=True)
    return res


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else 'AB'
    res = {}
    runs = {'A': [], 'B': []}
    for tag in which:
        r = run_variant(tag)
        runs[tag].append(r)
        # 同一 tag 多次跑时，取**全局最优**的一次（消除顺序/缓存偏差）
        if tag not in res or r['best'] < res[tag]['best']:
            res[tag] = r
    for tag in ('A', 'B'):
        if runs[tag]:
            res[tag]['runs'] = [x['best'] for x in runs[tag]]
            res[tag]['all_times'] = [t for x in runs[tag] for t in x['times']]
    if 'A' in res and 'B' in res:
        a, b = res['A'], res['B']
        d = b['best'] - a['best']
        res['delta'] = {
            'best_abs_s': round(d, 4),
            'best_pct': round(d / a['best'] * 100, 3),
            'per_file_us': round(d / a['files'] * 1e6, 2),
            'per_million_token_s': round(
                d / a['tokens'] * 1e6, 4) if a['tokens'] else None,
            'verdict': ('B 更快' if d < -1e-4 else
                        ('A 更快' if d > 1e-4 else
                         ('持平（|Δ| < 0.1ms）' if abs(d) < 1e-4 else '见数值'))),
        }
        print('')
        print('=== 性能对比（语料 %d 文件 / %d token）===' % (a['files'], a['tokens']))
        print('  A 改动前 best=%.4fs  times=%s' % (a['best'], [round(x, 3) for x in a['times']]))
        print('  B 改动后 best=%.4fs  times=%s' % (b['best'], [round(x, 3) for x in b['times']]))
        print('  Δbest = %+.4fs (%+.3f%%)  每文件 %+.1f μs  ⇒ %s'
              % (res['delta']['best_abs_s'], res['delta']['best_pct'],
                 res['delta']['per_file_us'], res['delta']['verdict']))
    json.dump(res, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False,
              indent=2)
    print('')
    print('已写出', OUT)


if __name__ == '__main__':
    main()
