# -*- coding: utf-8 -*-
# 任务2 反跑判据验证：把修复改反 → 必须 rc != 0（红）→ 恢复原文件 → 绿
# 判据 A：保留字 空 作变量名改回 → test_agentE5钩子 解析红；恢复 空事件 → 绿
import io, os, sys, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
TEST = os.path.join(ROOT, 'examples', 'test_agentE5钩子.light')

def run_test():
    env = dict(os.environ)
    p = subprocess.run([sys.executable, '运行.py', 'examples/test_agentE5钩子.light'],
                       cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return p.returncode

with io.open(TEST, encoding='utf-8-sig', newline='') as f:
    orig = f.read()

# 改反：空事件 → 空（保留字作变量名）
bad = orig.replace('设 空事件 为 事件', '设 空 为 事件')
with io.open(TEST, 'w', encoding='utf-8', newline='') as f:
    f.write(bad)
rc_bad = run_test()

# 恢复原文件
with io.open(TEST, 'w', encoding='utf-8', newline='') as f:
    f.write(orig)
rc_ok = run_test()

ok = True
if rc_bad == 0:
    print('反跑不红 FAIL: 空 作变量名应解析红 (rc=0)')
    ok = False
else:
    print('反跑即红 PASS: 空 作变量名解析红 (rc=%d)' % rc_bad)
if rc_ok != 0:
    print('恢复不绿 FAIL: 空事件 应通过 (rc=%d)' % rc_ok)
    ok = False
else:
    print('恢复即绿 PASS: 空事件 通过 (rc=0)')

print('ALL OK' if ok else 'HAS FAIL')
sys.exit(0 if ok else 1)
