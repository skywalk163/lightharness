# -*- coding: utf-8 -*-
# _antirun_team_v2.py —— 任务2（团队域 v2）反跑判据（≥3 项，字节级备份/恢复 src）
#
# A：事件版本仍用 1（#65 送达通知 version 改回 1）-> test_团队事件v2 必红；恢复 -> 绿
# B：#66 task-board v2 标记改错（投影 data.version 改 1）-> test_团队事件v2 必红；恢复 -> 绿
# C：团队工具参数校验放宽（#66 wait 超时下限 10000 降到 1000）-> test_团队工具 必红；恢复 -> 绿
#
# 字节级备份：修改前 read 原文件全部字节；修改后跑测试判红；finally 中原字节写回判绿。
# 跑 .light 测试：python 运行.py examples/test_xxx.light，rc=0 为通过。

import os
import sys
import subprocess

ROOT = r"G:\dswork\duan-light-merge\lightharness"
LIGHT_MERGE = r"G:\dswork\duan-light-merge\light-merge"
os.environ["LIGHT_MERGE"] = LIGHT_MERGE


def run_light(name):
    r = subprocess.run(
        [sys.executable, "运行.py", "examples/%s.light" % name],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return r.returncode


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def write_bytes(path, data):
    with open(path, "wb") as f:
        f.write(data)


def patch_text(path, old, new):
    data = read_bytes(path)
    text = data.decode("utf-8")
    assert old in text, "锚点未找到: " + old
    text = text.replace(old, new, 1)
    write_bytes(path, text.encode("utf-8"))


results = []

# ---- A：#65 送达通知 version 改回 1（delivery 未跟随移除）----
pA = os.path.join(ROOT, "src", "团队依赖图.light")
oldA = '{"version": 2, "teamId": 团队标识, "messageId": 消息标识, "targetId": 目标标识}'
newA = '{"version": 1, "teamId": 团队标识, "messageId": 消息标识, "targetId": 目标标识}'
bakA = read_bytes(pA)
try:
    patch_text(pA, oldA, newA)
    rcA = run_light("test_团队事件v2")
    results.append(("A 事件版本仍用1->红", rcA != 0, rcA))
finally:
    write_bytes(pA, bakA)
    rcA2 = run_light("test_团队事件v2")
    results.append(("A 恢复->绿", rcA2 == 0, rcA2))

# ---- B：#66 投影 data.version 改 1（task-board v2 标记改错）----
pB = os.path.join(ROOT, "src", "团队看板.light")
oldB = '"data": {"version": 2, "teamId": 团队标识, "task": 任务}'
newB = '"data": {"version": 1, "teamId": 团队标识, "task": 任务}'
bakB = read_bytes(pB)
try:
    patch_text(pB, oldB, newB)
    rcB = run_light("test_团队事件v2")
    results.append(("B task-board v2标记改错->红", rcB != 0, rcB))
finally:
    write_bytes(pB, bakB)
    rcB2 = run_light("test_团队事件v2")
    results.append(("B 恢复->绿", rcB2 == 0, rcB2))

# ---- C：#65/团队工具 等待超时下限 10000 放宽到 1000（参数校验放宽）----
pC = os.path.join(ROOT, "src", "团队工具.light")
oldC = "  如果 毫秒 < 等待超时下限: 返回 假"
newC = "  如果 毫秒 < 1000: 返回 假"
bakC = read_bytes(pC)
try:
    patch_text(pC, oldC, newC)
    rcC = run_light("test_团队工具")
    results.append(("C 团队工具参数校验放宽->红", rcC != 0, rcC))
finally:
    write_bytes(pC, bakC)
    rcC2 = run_light("test_团队工具")
    results.append(("C 恢复->绿", rcC2 == 0, rcC2))

print("=" * 60)
ok = True
for name, flag, rc in results:
    print("[%s] %-32s (rc=%d)" % ("PASS" if flag else "FAIL", name, rc))
    if not flag:
        ok = False
print("=" * 60)
print("反跑总结:", "全部符合判据" if ok else "存在反例不符")
sys.exit(0 if ok else 1)
