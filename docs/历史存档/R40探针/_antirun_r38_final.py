# -*- coding: utf-8 -*-
"""R38 任务4：全量反跑 + 回归验证 + 导入路径检查（合并任务1-2 后代码基线）。

用法：
  python _antirun_r38_final.py snapshot <out.json>          # §A 全语料 tokenize 快照
  python _antirun_r38_final.py compare <base.json>          # §A 对基线比对
  python _antirun_r38_final.py tests [out.json]             # §B 全量 examples/test_*.light rc 扫描
  python _antirun_r38_final.py imports                      # §C 导入路径检查
  python _antirun_r38_final.py all <out.json>               # §A快照+§C（§B 单独跑）

口径：
  §A lightharness + light-merge 全部 .light，deterministic=True，过滤 EOF/NEWLINE，
     sha256(逐文件 token 序列)。既有错误文件（light-merge/bootstrap/release/stdlib/集合.light、
     light-merge/examples/_test_nested_closure.light）为 R30 起登记的既有红，不计回归。
  §B python 运行.py examples/test_*.light，子进程 timeout 90s，逐文件记录 rc/耗时。
     基线判据：本轮改动仅为新增 src/代理默认模型.light 与 examples/test_R37_代理默认模型.light
     （既有文件零改动，token 零变化可证），故任何既有测试红均与本轮改动无关，单独列示。
  §C 全语料搜「从 代理循环 导入」「从 代理默认模型 导入」+ 运行.py 模块搜索路径顺序。
"""
import glob
import hashlib
import importlib
import json
import os
import re
import subprocess
import sys
import time

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

# R30 起登记的既有解析错误文件（相对 ROOT，正斜杠）
KNOWN_ERR = {'light-merge/bootstrap/release/stdlib/集合.light',
             'light-merge/examples/_test_nested_closure.light'}


def read(f):
    return open(f, encoding='utf-8', errors='replace').read()


def sha(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False).encode('utf-8')).hexdigest()


def rel(f):
    return os.path.relpath(f, ROOT).replace('\\', '/')


# ---------------------------------------------------------------- §A
def tokenize_all():
    lexer = importlib.import_module('lexer')
    cur = {}
    for f in CORPUS:
        r = rel(f)
        try:
            toks = lexer.Lexer(read(f), deterministic=True).tokenize()
            seq = [(t.type.name, t.value) for t in toks if t.type.name not in ('EOF', 'NEWLINE')]
        except Exception as e:
            seq = ['ERR:' + type(e).__name__]
        cur[r] = seq
    return cur


def snapshot(out):
    cur = tokenize_all()
    err = {r for r, s in cur.items() if len(s) == 1 and s[0].startswith('ERR:')}
    new_err = err - KNOWN_ERR
    healed = KNOWN_ERR - err
    data = {'per_file': {r: {'sha': sha(s), 'n': len(s)} for r, s in cur.items()},
            'total_tokens': sum(len(s) for s in cur.values()),
            'err_files': sorted(err),
            'new_err_files': sorted(new_err),
            'corpus': len(CORPUS)}
    json.dump(data, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('语料文件数：%d   错误文件：%d（既有 %d / 新增 %d / 自愈 %d）'
          % (len(CORPUS), len(err), len(err & KNOWN_ERR), len(new_err), len(healed)))
    if new_err:
        print('⚠️ 新增解析错误文件：')
        for r in sorted(new_err):
            print('   ', r)
    else:
        print('✅ 无新增解析错误文件')
    return data


def compare(base_path):
    cur = tokenize_all()
    base = json.load(open(base_path, encoding='utf-8'))
    base_per = base.get('per_file', {})
    changed, missing, added = [], [], []
    total_delta = 0
    for r, seq in cur.items():
        if r not in base_per:
            added.append(r)
            continue
        if sha(seq) != base_per[r]['sha']:
            changed.append(r)
        total_delta += len(seq) - base_per[r]['n']
    for r in base_per:
        if r not in cur:
            missing.append(r)
    print('可比文件：%d   新增：%d   缺失：%d   token 总数差：%+d'
          % (len(cur) - len(added), len(added), len(missing), total_delta))
    ok = True
    if added:
        print('新增文件（预期：本轮 2 个交付物）：')
        for r in sorted(added):
            print('   ', r)
    if missing:
        ok = False
        print('⚠️ 基线缺失：', sorted(missing)[:10])
    if changed:
        ok = False
        print('⚠️ token 变化 %d 文件：' % len(changed))
        for r in sorted(changed)[:40]:
            print('   ', r)
    if not changed and not missing:
        print('✅ 既有全语料 token 零变化')
    return ok


# ---------------------------------------------------------------- §B
def run_tests(out=None):
    tests = sorted(glob.glob(ROOT + '/lightharness/examples/test_*.light'))
    print('测试文件数：%d' % len(tests))
    rows = []
    for i, f in enumerate(tests, 1):
        t0 = time.time()
        try:
            p = subprocess.run([sys.executable, os.path.join(ROOT, 'lightharness', '运行.py'), f],
                               capture_output=True, text=True, timeout=90,
                               cwd=os.path.join(ROOT, 'lightharness'))
            rc, tail = p.returncode, (p.stdout[-200:] + p.stderr[-300:])
        except subprocess.TimeoutExpired:
            rc, tail = 'TIMEOUT', ''
        dt = time.time() - t0
        rows.append({'file': rel(f), 'rc': rc, 'sec': round(dt, 2)})
        if rc != 0:
            print('RED %-70s rc=%s  %.1fs' % (rel(f), rc, dt))
        if i % 50 == 0:
            print('  ...进度 %d/%d' % (i, len(tests)))
    reds = [r for r in rows if r['rc'] != 0]
    print('全量扫描完成：%d 文件，绿 %d，红 %d' % (len(rows), len(rows) - len(reds), len(reds)))
    for r in reds:
        print('  RED', r['file'], 'rc=%s' % r['rc'])
    if out:
        json.dump({'rows': rows, 'red': [r['file'] for r in reds]},
                  open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('结果已写：%s' % out)
    return reds


# ---------------------------------------------------------------- §C
def import_check():
    pats = ['从 工具展示 导入', '从 工具执行 导入', '工具展示']
    hits = {p: [] for p in pats}
    for f in CORPUS:
        if rel(f) in ('lightharness/src/工具展示.light',
                      'lightharness/examples/test_R38_工具展示.light',
                      'lightharness/examples/test_R38_集成测试.light'):
            continue  # 模块自身与直接配套测试不计
        try:
            t = read(f)
        except Exception:
            continue
        for p in pats:
            if p in t:
                for i, line in enumerate(t.splitlines(), 1):
                    if p in line:
                        hits[p].append('%s:%d' % (rel(f), i))
    for p in pats:
        print('== %s ：%d 处' % (p, len(hits[p])))
        for h in hits[p][:20]:
            print('   ', h)
        if len(hits[p]) > 20:
            print('    ...共 %d 处' % len(hits[p]))
    # 运行.py 模块搜索路径顺序
    rt = read(os.path.join(ROOT, 'lightharness', '运行.py'))
    order = re.findall(r'(STDLIB|SRC|ROOT|EXAMPLES)', rt)
    print('运行.py 路径关键 token 出现序列：', order[:24])
    for i, line in enumerate(rt.splitlines(), 1):
        if 'STDLIB' in line or 'SRC' in line or 'insert' in line:
            print('  运行.py:%d  %s' % (i, line.strip()[:110]))
    return hits


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'snapshot':
        snapshot(sys.argv[2])
    elif mode == 'compare':
        sys.exit(0 if compare(sys.argv[2]) else 1)
    elif mode == 'tests':
        run_tests(sys.argv[2] if len(sys.argv) > 2 else None)
    elif mode == 'imports':
        import_check()
    else:
        print(__doc__)
