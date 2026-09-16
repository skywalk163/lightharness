# -*- coding: utf-8 -*-
# 任务4 反跑判据验证：字节级备份/恢复 src，改反修复点 → 红，恢复 → 绿。
# A：取最后回答块表 改回只收 text 块（丢弃 reasoning 分支）→ reasoning-only 非空断言红；恢复 → 绿
# B：造显示文本 删字典查找（内置命中改反）→ shipped 字典文案断言红；恢复 → 绿
import os, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TEST = 'examples/test_修复_子智能体预设.light'
SUB = os.path.join(ROOT, 'src', '子智能体.light')
PRE = os.path.join(ROOT, 'src', '预设.light')

def run_test():
    p = subprocess.run([sys.executable, '运行.py', TEST],
                       cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return p.returncode

def read_text(path):
    with open(path, 'rb') as f:
        return f.read().decode('utf-8')

def write_text(path, text):
    with open(path, 'wb') as f:
        f.write(text.encode('utf-8'))

def check(desc, path, old, new, bad_expected=1):
    """old→new 应变红（rc!=0）；恢复后应绿。返回是否全过。"""
    ok = True
    orig = read_text(path)
    if old not in orig:
        print('MISS:', desc, '目标文本未找到')
        return False
    write_text(path, orig.replace(old, new, 1))
    rc_bad = run_test()
    write_text(path, orig)
    rc_ok = run_test()
    if (rc_bad == 0) == bool(bad_expected):
        print('反跑不%s FAIL: %s (rc=%d)' % ('红' if bad_expected else '绿', desc, rc_bad))
        ok = False
    else:
        print('反跑即红 PASS: %s (rc=%d)' % (desc, rc_bad) if bad_expected else '反跑即绿 PASS: %s' % desc)
    if rc_ok != 0:
        print('恢复不绿 FAIL: %s (rc=%d)' % (desc, rc_ok))
        ok = False
    else:
        print('恢复即绿 PASS: %s' % desc)
    return ok

all_ok = True

# A：取最后回答块表 丢弃 reasoning 分支（改回只收 text）
all_ok &= check('A 取最后回答块表改回只收text',
                SUB,
                '            如果 块.包含("type") 且 (块["type"] == "text" 或 块["type"] == "reasoning"):',
                '            如果 块.包含("type") 且 块["type"] == "text":')

# B：造显示文本 删字典查找（内置命中条件改反 → shipped 走回退 id）
all_ok &= check('B 造显示文本删字典查找',
                PRE,
                '    如果 (内置 != 空): 返回 ["name": 内置["名称"], "description": 内置["描述"]]',
                '    如果 (内置 == 空): 返回 ["name": 内置["名称"], "description": 内置["描述"]]')

print('ALL OK' if all_ok else 'HAS FAIL')
sys.exit(0 if all_ok else 1)
