# -*- coding: utf-8 -*-
# 任务4 反跑判据验证：字节级备份/恢复「测试文件自身」，改判据→红，恢复→绿。
# A：节4 最后非空消息断言期望值改反（"step two" → "step one"）→ 红；恢复 → 绿
# B：删除节11 扫描排序场景（段落定义 + 主调用）→ 红；恢复 → 绿
import os, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TEST = 'examples/test_行为对照_工具子智能体.light'

def run_test():
    p = subprocess.run([sys.executable, '运行.py', TEST],
                       cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return p.returncode

path = os.path.join(ROOT, TEST)
with open(path, 'rb') as f:
    orig_bytes = f.read()
orig = orig_bytes.decode('utf-8')

def write_text(text):
    with open(path, 'wb') as f:
        f.write(text.encode('utf-8'))

# ---- A：断言期望值改反（节4：越过末尾空消息应取 "step two"） ----
old_a = '断言相等(智能体.取最后回答(), "step two", "越过末尾空消息取最后非空")'
new_a = '断言相等(智能体.取最后回答(), "step one", "越过末尾空消息取最后非空")'

# ---- B：删除节11 场景（仅删段落定义，保留主调用 → 未定义段即红） ----
def build_deletion(text):
    start = text.find('段落 节11扫描排序:')
    end_marker = '写 "节11 通过: discovery.spec.ts 扫描排序"'
    end = text.find(end_marker, start)
    if start < 0 or end < 0:
        return None
    nl = end + len(end_marker)
    if text[nl:nl + 2] == '\r\n':
        nl += 2
    elif text[nl:nl + 1] == '\n':
        nl += 1
    return text[:start] + text[nl:]

ok = True

# A
if old_a not in orig:
    print('MISS: A 目标文本未找到')
    ok = False
else:
    write_text(orig.replace(old_a, new_a, 1))
    rc_bad = run_test()
    write_text(orig)
    rc_ok = run_test()
    if rc_bad == 0:
        print('反跑不红 FAIL: A 改断言期望值')
        ok = False
    else:
        print('反跑即红 PASS: A 改断言期望值 (rc=%d)' % rc_bad)
    if rc_ok != 0:
        print('恢复不绿 FAIL: A (rc=%d)' % rc_ok)
        ok = False
    else:
        print('恢复即绿 PASS: A')

# B
deleted = build_deletion(orig)
if deleted is None:
    print('MISS: B 删除目标结构未找到')
    ok = False
else:
    write_text(deleted)
    rc_bad = run_test()
    write_text(orig)
    rc_ok = run_test()
    if rc_bad == 0:
        print('反跑不红 FAIL: B 删节11场景')
        ok = False
    else:
        print('反跑即红 PASS: B 删节11场景 (rc=%d)' % rc_bad)
    if rc_ok != 0:
        print('恢复不绿 FAIL: B (rc=%d)' % rc_ok)
        ok = False
    else:
        print('恢复即绿 PASS: B')

print('ALL OK' if ok else 'HAS FAIL')
sys.exit(0 if ok else 1)
