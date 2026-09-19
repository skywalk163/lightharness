# -*- coding: utf-8 -*-
"""R74 路1 验收：产物函数签名逐模块对拍（HEAD 版 vs 改动版）。

背景：L1（括号式参数名切分）是「编译期零警告、运行期才炸」的静默错编风险，
R65 用血泪换来的护栏就是「改参数语法必须做产物签名对拍，有差异即回退」。
路1 agent 因 429 未做完此项，由路 M 补做。
"""
import subprocess, os, re, glob, shutil, sys, json

LM = r'G:\dswork\duan-light-merge\light-merge'
LH = r'G:\dswork\duan-light-merge\lightharness'
PY = os.path.join(LM, '.venv', 'Scripts', 'python.exe')
PS = os.path.join(LM, 'src', 'parser_stmt.py')
CACHE = os.path.join(LM, 'src', '__pycache__')
TMP = os.path.join(LH, '_scratch_r74')
BAK = os.path.join(TMP, 'parser_stmt_r74_改动版.bak')

os.makedirs(TMP, exist_ok=True)
files = sorted(glob.glob(os.path.join(LH, 'stdlib', '*.light')))
print('stdlib 模块数:', len(files))


def clear_cache():
    if os.path.isdir(CACHE):
        shutil.rmtree(CACHE, ignore_errors=True)


def compile_all(tag):
    res, ok, fail = {}, 0, []
    for f in files:
        o = os.path.join(TMP, tag + '__' + os.path.basename(f) + '.py')
        p = subprocess.run([PY, 'cli/light.py', 'compile', f, '-o', o, '--backend', 'src'],
                           cwd=LM, capture_output=True)
        if p.returncode != 0:
            fail.append(os.path.basename(f))
            res[f] = 'COMPILE_FAIL'
            continue
        ok += 1
        txt = open(o, encoding='utf-8', errors='replace').read()
        sigs = re.findall(r'^def\s+([^\s(]+)\s*\(([^)]*)\)', txt, re.M)
        res[f] = sorted((a, ' '.join(b.split())) for a, b in sigs)
    print('  [%s] 编译成功 %d / 失败 %d' % (tag, ok, len(fail)))
    if fail:
        print('  失败模块:', fail[:8], '...' if len(fail) > 8 else '')
    return res, fail


# ---------- ① 改动版（当前工作树）----------
print('① 编译「改动版」...')
clear_cache()
cur, cur_fail = compile_all('cur')

# ---------- ② HEAD 版（临时回退 parser_stmt.py）----------
print('② 编译「HEAD 版」（临时回退 parser_stmt.py）...')
shutil.copy2(PS, BAK)
head, head_fail = {}, []
try:
    subprocess.run(['git', 'checkout', '--', 'src/parser_stmt.py'], cwd=LM, check=True)
    clear_cache()
    head, head_fail = compile_all('head')
finally:
    shutil.copy2(BAK, PS)
    clear_cache()
    print('  已恢复改动版 parser_stmt.py')

# ---------- ③ 比对 ----------
diffs = []
same = 0
for f in files:
    a, b = cur.get(f), head.get(f)
    if a == b:
        same += 1
    else:
        diffs.append(f)
print()
print('签名完全一致模块: %d / %d' % (same, len(files)))
print('签名有差异模块: %d' % len(diffs))
for f in diffs:
    a, b = cur.get(f), head.get(f)
    print('\n### ' + os.path.basename(f))
    if a == 'COMPILE_FAIL' or b == 'COMPILE_FAIL':
        print('  编译失败差异: cur=%s head=%s' % (a == 'COMPILE_FAIL', b == 'COMPILE_FAIL'))
        continue
    sa, sb = dict(a), dict(b)
    for k in sorted(set(sa) | set(sb)):
        if sa.get(k) != sb.get(k):
            print('  def %s:' % k)
            print('    HEAD: (%s)' % sb.get(k, '<不存在>'))
            print('    改动: (%s)' % sa.get(k, '<不存在>'))

print('\n=== 结论 ===')
print('PASS' if not diffs else 'DIFF: %d 个模块需人工判定' % len(diffs))
