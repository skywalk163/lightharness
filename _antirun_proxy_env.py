# -*- coding: utf-8 -*-
# 任务3 反跑判据验证（_antirun_proxy_env.py）
# 逐项：把实现改错 → 测试必须红（rc != 0）→ 字节级恢复 src → 必须绿（rc == 0）
# A：环回豁免去掉（localhost 不再判环回）→ 断言红；恢复 → 绿
# B：启动环境层级优先级反转（进程层排到最后）→ 断言红；恢复 → 绿
# C：proxyForUrl 选中改错（http URL 误选 https 代理）→ 断言红；恢复 → 绿
import io, os, sys, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))

def run_test(test):
    p = subprocess.run([sys.executable, '运行.py', test],
                       cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return p.returncode

def read_src(path):
    with io.open(path, encoding='utf-8-sig', newline='') as f:
        return f.read().replace('\r\n', '\n')

def write_src(path, text):
    with io.open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(text.replace('\n', '\r\n'))

cases = [
    # A：环回豁免去掉 —— localhost 判定改反
    ('src/代理策略.light', 'examples/test_代理策略.light',
     '  如果 主机 == "localhost":\n    返回 真',
     '  如果 主机 == "localhost":\n    返回 假',
     'A 环回豁免去掉（localhost 不豁免）'),
    # C：proxyForUrl 选中改错 —— https: 分支误取 http 代理（对仅 https 代理的策略必红）
    ('src/代理策略.light', 'examples/test_代理策略.light',
     '  如果 网址["协议"] == "https:":\n    如果 字典包含键(策略, "https代理"):\n      设 代理 为 策略["https代理"]',
     '  如果 网址["协议"] == "https:":\n    如果 字典包含键(策略, "https代理"):\n      设 代理 为 策略["http代理"]',
     'C proxyForUrl 选中改错（https 误取 http 代理）'),
    # B：启动环境层级优先级反转 —— 来源序 进程排最后
    ('src/启动环境.light', 'examples/test_启动环境.light',
     '设 来源序 为 ["process", "project-env", "user-env"]',
     '设 来源序 为 ["user-env", "project-env", "process"]',
     'B 启动环境层级优先级反转（user-env 最可信）'),
]

ok = True
for rel, test, old, new, desc in cases:
    src = os.path.join(ROOT, rel)
    orig = read_src(src)
    if old not in orig:
        print('MISS:', desc)
        ok = False
        continue
    write_src(src, orig.replace(old, new, 1))
    rc_bad = run_test(test)
    write_src(src, orig)
    rc_ok = run_test(test)
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
