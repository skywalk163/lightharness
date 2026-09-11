# -*- coding: utf-8 -*-
# 任务3 反跑判据验证：把关键断言/实现改反 → 必须 rc != 0（红）→ 恢复原文件
# 覆盖：
#   1) 团队依赖图 version 改回 1 → 红（4 处）
#   2) 守卫「paused 拒绝」改「放行」→ 红
#   3) 守卫「引用不匹配放行」改「拒绝」→ 红
import io, os, sys, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))

def run_test(path):
    env = dict(os.environ)
    env['LIGHT_MERGE'] = r'G:\dswork\duan-light-merge\light-merge'
    p = subprocess.run([sys.executable, '运行.py', path],
                       cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return p.returncode

cases = [
    # --- 团队依赖图 version 2→1 反跑（改 src 后 test_团队依赖图 应红）---
    ('src/团队依赖图.light',
     '返回 {"version": 2, "teamId": 团队标识, "member": 成员快照}',
     '返回 {"version": 1, "teamId": 团队标识, "member": 成员快照}',
     'examples/test_团队依赖图.light',
     '成员通知 version 改回 1 → 红'),
    ('src/团队依赖图.light',
     '返回 {"version": 2, "teamId": 团队标识, "task": 任务快照}',
     '返回 {"version": 1, "teamId": 团队标识, "task": 任务快照}',
     'examples/test_团队依赖图.light',
     '任务通知 version 改回 1 → 红'),
    ('src/团队依赖图.light',
     '返回 {"version": 2, "teamId": 团队标识, "message": 消息快照}',
     '返回 {"version": 1, "teamId": 团队标识, "message": 消息快照}',
     'examples/test_团队依赖图.light',
     '排队通知 version 改回 1 → 红'),
    ('src/团队依赖图.light',
     '返回 {"version": 2, "teamId": 团队标识, "messageId": 消息标识, "targetId": 目标标识}',
     '返回 {"version": 1, "teamId": 团队标识, "messageId": 消息标识, "targetId": 目标标识}',
     'examples/test_团队依赖图.light',
     '送达通知 version 改回 1 → 红'),
    # --- 守卫 paused 拒绝改放行 → 红 ---
    ('src/目标折叠.light',
     '抛出 新建 错误("the model cannot resume a paused goal; the user must resume it")',
     '返回 真',
     'examples/test_目标恢复守卫.light',
     '守卫 paused 拒绝改放行 → 红'),
    # --- 守卫 引用不匹配放行改拒绝 → 红 ---
    ('examples/test_目标恢复守卫.light',
     '断言相等(判定模型可恢复(暂停目标, 异编号引用), 真, "paused 但 id 不匹配 → 放行")',
     '断言相等(判定模型可恢复(暂停目标, 异编号引用), 假, "paused 但 id 不匹配 → 放行")',
     'examples/test_目标恢复守卫.light',
     '引用不匹配放行改拒绝 → 红'),
]

ok = True
for src_path, old, new, test_path, desc in cases:
    full = os.path.join(ROOT, src_path)
    with io.open(full, encoding='utf-8-sig', newline='') as f:
        c = f.read()
    if old not in c:
        print('MISS:', desc)
        ok = False
        continue
    c2 = c.replace(old, new, 1)
    with io.open(full, 'w', encoding='utf-8', newline='') as f:
        f.write(c2)
    rc = run_test(test_path)
    with io.open(full, 'w', encoding='utf-8', newline='') as f:
        f.write(c)
    if rc == 0:
        print('反跑不红 FAIL:', desc, '(rc=0 应红)')
        ok = False
    else:
        print('反跑即红 PASS:', desc, '(rc=%d)' % rc)

print('ALL OK' if ok else 'HAS FAIL')
sys.exit(0 if ok else 1)
