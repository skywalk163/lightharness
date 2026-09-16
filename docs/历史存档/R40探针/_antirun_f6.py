# -*- coding: utf-8 -*-
# 路6 反跑判据验证：把关键断言改反 → 必须 rc != 0（红）→ 恢复原文件
# 覆盖任务书 §4 路6 的 6 项反跑判据。
import io, os, sys, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))

def run_test(path):
    env = dict(os.environ)
    env['LIGHT_MERGE'] = r'G:\dswork\duan-light-merge\light-merge'
    p = subprocess.run([sys.executable, '运行.py', path],
                       cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return p.returncode

cases = [
    # (文件, 原串, 反串, 说明)
    ('examples/test_交付.light',
     '断言真(通过["有效"], "常规文件通过")  # 反跑：改反 → 红',
     '断言真(通过["有效"] == 假, "常规文件通过")  # 反跑：改反 → 红',
     '交付物判定（常规文件有效）改反'),
    ('examples/test_交付.light',
     '断言相等(长度(结果["未交付"]), 1, "未声明为未交付")  # 反跑：改反 → 红',
     '断言相等(长度(结果["未交付"]), 0, "未声明为未交付")  # 反跑：改反 → 红',
     '文件变更 vs 交付物（显式交付）改反'),
    ('examples/test_交付.light',
     '断言相等(长度(可见段), 2, "read 不可见时只留 2 段")  # 反跑：改反 → 红',
     '断言相等(长度(可见段), 3, "read 不可见时只留 2 段")  # 反跑：改反 → 红',
     'scoped tool 豁免（过滤可见指导）改反'),
    ('examples/test_交付.light',
     '断言真(判定完全限定("C:\\\\proj", "win32"), "win32 盘符完全限定")  # 反跑：改反 → 红',
     '断言真(判定完全限定("C:\\\\proj", "win32") == 假, "win32 盘符完全限定")  # 反跑：改反 → 红',
     'workspace qualified path（win32 完全限定）改反'),
    ('examples/test_交付.light',
     '断言真(抛了, "重复光标应抛错")  # 反跑：改反 → 红',
     '断言真(抛了 == 假, "重复光标应抛错")  # 反跑：改反 → 红',
     'mcp 分页循环（重复光标拒绝）改反'),
    ('examples/test_交付.light',
     '断言相等(长度(框架), 3, "框架三块")  # 反跑：改反 → 红',
     '断言相等(长度(框架), 2, "框架三块")  # 反跑：改反 → 红',
     'compaction summarizer（框架块数）改反'),
]

ok = True
for path, old, new, desc in cases:
    full = os.path.join(ROOT, path)
    with io.open(full, encoding='utf-8-sig', newline='') as f:
        c = f.read()
    if old not in c:
        print('MISS:', desc)
        ok = False
        continue
    c2 = c.replace(old, new, 1)
    with io.open(full, 'w', encoding='utf-8', newline='') as f:
        f.write(c2)
    rc = run_test(path)
    with io.open(full, 'w', encoding='utf-8', newline='') as f:
        f.write(c)
    if rc == 0:
        print('反跑不红 FAIL:', desc, '(rc=0 应红)')
        ok = False
    else:
        print('反跑即红 PASS:', desc, '(rc=%d)' % rc)

print('ALL OK' if ok else 'HAS FAIL')
sys.exit(0 if ok else 1)
