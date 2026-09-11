# -*- coding: utf-8 -*-
# 任务4 反跑判据验证：把关键断言改反 → 必须 rc != 0（红）→ 恢复原文件
# 覆盖任务书 §任务4 验收的三项反跑判据。
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
    ('examples/test_会话查询1.5.light',
     '断言相等(抽取事件文本(用户事件), "今天天气如何", "user 文本抽取")  # 反跑：改反 → 红',
     '断言相等(抽取事件文本(用户事件), "别的文本", "user 文本抽取")  # 反跑：改反 → 红',
     '抽取 user/message 文本改反'),
    ('examples/test_会话查询1.5.light',
     '断言相等(记录表[0]["表面"], "shadowed", "replace 后旧节点 shadowed")  # 反跑：改反 → 红',
     '断言相等(记录表[0]["表面"], "current", "replace 后旧节点 shadowed")  # 反跑：改反 → 红',
     'surface replace 后旧事件改 current 改反'),
    ('examples/test_会话查询1.5.light',
     '断言真(抛时间, "时间不等应抛错")  # 反跑：改反 → 红',
     '断言真(抛时间 == 假, "时间不等应抛错")  # 反跑：改反 → 红',
     '头兼容时间不等放行改反'),
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
