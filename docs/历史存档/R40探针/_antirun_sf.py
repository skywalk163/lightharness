# -*- coding: utf-8 -*-
# 反跑判据验证：把关键断言改反 → 必须 rc != 0（红）→ 恢复原文件
import io, os, sys, subprocess, shutil

ROOT = os.path.dirname(os.path.abspath(__file__))

def run_test(path):
    env = dict(os.environ)
    env['LIGHT_MERGE'] = r'G:\dswork\duan-light-merge\light-merge'
    p = subprocess.run([sys.executable, '运行.py', path],
                       cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return p.returncode

cases = [
    # (文件, 原串, 反串, 说明)
    ('examples/test_会话格式.light',
     '断言相等(行["type"], "user/message", "编码类型")',
     '断言相等(行["type"], "user/other", "编码类型")',
     'V3 编解码类型改反'),
    ('examples/test_会话格式.light',
     '断言相等(回读2.事件数(), 2, "recoverable 跳过坏行")',
     '断言相等(回读2.事件数(), 99, "recoverable 跳过坏行")',
     'recoverable 事件数改反'),
    ('examples/test_会话V3迁移.light',
     '断言相等(版本文本(终头["版本"]), "3.0", "全链迁移到 3.0")',
     '断言相等(版本文本(终头["版本"]), "2.0", "全链迁移到 3.0")',
     '全链终版本改反'),
    ('examples/test_会话V3迁移.light',
     '断言相等(终事件[3]["类型"], "brand/v0-mystery", "未知事件类型保留")',
     '断言相等(终事件[3]["类型"], "brand/rewritten", "未知事件类型保留")',
     '未知事件保留改反'),
    ('examples/test_会话V3迁移.light',
     '断言相等(结果3["事件"][1]["数据"]["名称"], "tool/ptc-dispatch-render", "工具名重命名")',
     '断言相等(结果3["事件"][1]["数据"]["名称"], "tool/code-dispatch-render", "工具名重命名")',
     'PTC 工具名改反'),
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
