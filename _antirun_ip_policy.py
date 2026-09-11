# -*- coding: utf-8 -*-
# 任务3 反跑判据验证：把判定改反 → 必须 rc != 0（红）→ 恢复原文件 → 绿
# A：127.0.0.1 私网判定改错（放行）→ 断言红；恢复 → 绿
# B：8.8.8.8 公网判定改错（拒绝）→ 断言红；恢复 → 绿
import io, os, sys, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'src', '抓取策略.light')
TEST = 'examples/test_IP安全校验.light'

def run_test():
    p = subprocess.run([sys.executable, '运行.py', TEST],
                       cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return p.returncode

with io.open(SRC, encoding='utf-8-sig', newline='') as f:
    orig = f.read().replace('\r\n', '\n')

def write_src(text):
    with io.open(SRC, 'w', encoding='utf-8', newline='') as f:
        f.write(text.replace('\n', '\r\n'))

cases = [
    # A: 127/8 放行改反
    (' 如果 a == 127:\n    返回 假',
     ' 如果 a == 127:\n    返回 真',
     'A 127.0.0.1 私网判定改反'),
    # B: IPv4 公网兜底拒绝改反
    ('  如果 a >= 240:\n    返回 假\n  返回 真\n',
     '  如果 a >= 240:\n    返回 假\n  返回 假\n',
     'B 8.8.8.8 公网判定改反'),
]

ok = True
for old, new, desc in cases:
    if old not in orig:
        print('MISS:', desc)
        ok = False
        continue
    write_src(orig.replace(old, new, 1))
    rc_bad = run_test()
    write_src(orig)
    rc_ok = run_test()
    if rc_bad == 0:
        print('反跑不红 FAIL:', desc)
        ok = False
    else:
        print('反跑即红 PASS:', desc, '(rc=%d)' % rc_bad)
    if rc_ok != 0:
        print('恢复不绿 FAIL:', desc, '(rc=%d)' % rc_ok)
        ok = False
    else:
        print('恢复即绿 PASS:', desc)

print('ALL OK' if ok else 'HAS FAIL')
sys.exit(0 if ok else 1)
