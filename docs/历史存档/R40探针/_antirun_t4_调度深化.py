# -*- coding: utf-8 -*-
"""_antirun_t4_调度深化.py —— 第 15 轮任务 4 反跑判据（schedule 深化 + jobs 品牌/类型域）

对象：src/调度深化.light（字节级备份 → 变异 → 跑测试 → 断言真红 → 恢复 → 断言真绿）
判据（3/3）：
  A. 投影不再尊重继承切点（`事件["seq"] < 继承数` → `事件["seq"] < -1`）
     → 继承内事件被误折叠，2f「继承切点 忽略继承内事件」红；恢复 → 绿
  B. 事务收尾不再校验身份（删掉 `如果 尾表[归属标识] != 本标记: 返回 假`）
     → 旧标记会误删后到事务的尾，3f/3g 红；恢复 → 绿
  C. 任务终态漏 failed（`返回 值 == "failed"` → `返回 假`）
     → 4l/4q 红；恢复 → 绿
用法：cd lightharness && python _antirun_t4_调度深化.py
退出码：全部判据通过 0（打印 ALL OK）；任一失败 1。
安全：恢复一律走 finally，异常退出也不会残留变异（第13轮教训 C 判据变异残留）。
同时提醒：本脚本原地改 src/，**不得与 运行.py 并行执行**（第14轮教训：并行会读到被改版本导致假红）。
"""
import hashlib
import subprocess
import sys

TARGET = "src/调度深化.light"
TEST = "examples/test_调度深化.light"
PASS_LINE = "test_调度深化 PASS"


def _nl(data: bytes) -> str:
    """按目标文件实际换行风格（CRLF/LF）生成变异串换行。"""
    return "\r\n" if b"\r\n" in data else "\n"


A_OLD = (
    "  如果 字典包含键(事件, \"seq\") == 真:\n"
    "    如果 事件[\"seq\"] < 继承数:\n"
    "      返回 状态\n"
)
A_NEW = (
    "  如果 字典包含键(事件, \"seq\") == 真:\n"
    "    如果 事件[\"seq\"] < 0 - 1:\n"
    "      返回 状态\n"
)

B_OLD = (
    "  如果 字典包含键(尾表, 归属标识) == 假:\n"
    "    返回 假\n"
    "  如果 尾表[归属标识] != 本标记:\n"
    "    返回 假\n"
)
B_NEW = (
    "  如果 字典包含键(尾表, 归属标识) == 假:\n"
    "    返回 假\n"
)

C_OLD = '  返回 值 == "failed"\n'
C_NEW = "  返回 假\n"


def run_test():
    p = subprocess.run(
        [sys.executable, "运行.py", TEST],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def write_bytes(path, data):
    with open(path, "wb") as f:
        f.write(data)


def main():
    original = read_bytes(TARGET)
    digest = hashlib.sha256(original).hexdigest()
    nl = _nl(original)
    results = []

    def case(name, old, new):
        old_b = old.replace("\n", nl).encode("utf-8")
        new_b = new.replace("\n", nl).encode("utf-8")
        mutated = original.replace(old_b, new_b)
        if mutated == original:
            results.append((name, False, "skip: 变异未命中"))
            return
        try:
            write_bytes(TARGET, mutated)
            rc, out = run_test()
            results.append((name, rc != 0, "判红运行 rc=%d" % rc))
        finally:
            write_bytes(TARGET, original)

    try:
        case("A 投影忽略继承切点", A_OLD, A_NEW)
        case("B 事务收尾不校验身份", B_OLD, B_NEW)
        case("C 任务终态漏 failed", C_OLD, C_NEW)
    finally:
        write_bytes(TARGET, original)

    ok_restore = hashlib.sha256(read_bytes(TARGET)).hexdigest() == digest
    rc_green, out_green = run_test()
    ok_green = rc_green == 0 and PASS_LINE in out_green

    ok = ok_restore and ok_green and all(r for _, r, _ in results)
    print("=== 第 15 轮任务 4 反跑判据（schedule 深化 + jobs 品牌/类型域）===")
    for name, red, note in results:
        print("%s %s (%s)" % ("✓" if red else "✗", name, note))
    print("%s 字节级恢复校验 (sha256 %s)" % ("✓" if ok_restore else "✗", digest[:12]))
    print("%s 恢复后回归绿 (rc=%d，PASS 已打印)" % ("✓" if ok_green else "✗", rc_green))
    if ok:
        print("ALL OK")
    else:
        print("=== 结果：存在失败 ===")
        print((out_green or "")[-600:])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
