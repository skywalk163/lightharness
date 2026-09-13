# -*- coding: utf-8 -*-
# 任务5 反跑判据验证：把 src 关键逻辑改反 → 必须 rc != 0（红）→ 字节级恢复 → 必须绿。
# 判据 A：ALREADY_IN_FLIGHT 校验失效（校验链关键节点不可破坏）→ test_授权链 单键单尝试断言红。
# 判据 B：NOT_COMMITTED 不再抛（提交契约破坏）→ test_授权链 NOT_COMMITTED 断言红。
# 判据 C：结算广播去掉 INVARIANT 重抛（监听器失败隔离破坏）→ test_授权链 INVARIANT重抛断言红。
# 字节级备份/恢复 src：以二进制读写，恢复时写回原字节（含 BOM/换行不变）。
import io, os, sys, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))


def run_test(path):
    env = dict(os.environ)
    env['LIGHT_MERGE'] = r'G:\dswork\duan-light-merge\light-merge'
    p = subprocess.run([sys.executable, '运行.py', path],
                       cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return p.returncode


cases = [
    # (src 文件, 原串, 反串, 目标测试, 说明)
    (os.path.join(ROOT, 'src', '授权链.light'),
     '    如果 字典包含键(服务["运行表"], 键):\n        抛授权错误("\\"" + 键 + "\\" 的授权尝试已在运行", 码已在飞)',
     '    如果 假:  # 反跑：ALREADY_IN_FLIGHT 校验失效 → 红\n        抛授权错误("\\"" + 键 + "\\" 的授权尝试已在运行", 码已在飞)',
     'examples/test_授权链.light',
     'ALREADY_IN_FLIGHT 校验失效 → 单键单尝试断言红'),
    (os.path.join(ROOT, 'src', '授权链.light'),
     '    如果 观察["已提交"] != 真:\n        抛授权错误("授权流程 \\"" + 流程["键"] + "\\" 在此尝试中解析但未提交凭据记录", 码未提交)',
     '    如果 观察["已提交"] != 真:\n        返回 ["状态":"authorized"]  # 反跑：NOT_COMMITTED 不再抛 → 红',
     'examples/test_授权链.light',
     'NOT_COMMITTED 不再抛 → 提交契约断言红'),
    (os.path.join(ROOT, 'src', '授权链.light'),
     '    如果 不变失败 != 空:\n        抛出 不变失败',
     '    如果 不变失败 != 空:\n        设 占位 为 0  # 反跑：去掉 INVARIANT 重抛 → 红',
     'examples/test_授权链.light',
     '结算广播去掉 INVARIANT 重抛 → INVARIANT断言红'),
]

ok = True
for full, old, new, test_path, desc in cases:
    with io.open(full, 'rb') as f:
        data = f.read()
    old_b = old.encode('utf-8')
    new_b = new.encode('utf-8')
    if old_b not in data:
        print('MISS:', desc)
        ok = False
        continue
    data2 = data.replace(old_b, new_b, 1)
    with io.open(full, 'wb') as f:
        f.write(data2)
    rc = run_test(test_path)
    with io.open(full, 'wb') as f:
        f.write(data)  # 字节级恢复
    rc2 = run_test(test_path)
    if rc == 0:
        print('反跑不红 FAIL:', desc, '(rc=0 应红)')
        ok = False
    else:
        print('反跑即红 PASS:', desc, '(rc=%d)' % rc)
    if rc2 != 0:
        print('恢复未绿 FAIL:', desc, '(rc=%d)' % rc2)
        ok = False
    else:
        print('恢复即绿 PASS:', desc)

print('ALL OK' if ok else 'HAS FAIL')
sys.exit(0 if ok else 1)
