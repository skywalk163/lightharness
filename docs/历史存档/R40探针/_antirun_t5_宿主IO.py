# -*- coding: utf-8 -*-
"""_antirun_t5_宿主IO.py —— 第 17 轮任务 5 反跑判据（宿主 IO 抽象层原型）

对象：src/宿主IO.light（字节级备份 → 变异 → 跑测试 → 断言真红 → 恢复 → 断言真绿）
判据（3/3）：
  A. 文件系统读文件返回错内容（读文件 的 返回 造成功结果(项["内容"], ...) 改为返回 "WRONG"）→ 4c「读文件返回写入内容」红；恢复 → 绿
  B. 进程等待返回错退出码（取进程结果 的 退出码 改为 0）→ 5b「退出码==42」红；恢复 → 绿
  C. 重试判定翻转（带重试执行 的 可重试表.包含(码) == 假 改为 == 真）→ 6c「不可重试错误不重试(1次)」红；恢复 → 绿
用法：python _antirun_t5_宿主IO.py
退出码：全部判据通过 0（打印 ALL OK）；任一失败 1。
安全：恢复一律走 finally，异常退出也不会残留变异。
提醒：本脚本原地改 src/，**不得与 运行.py 并行执行**（并行会读到被改版本导致假红）。
"""
import hashlib
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(BASE, "src", "宿主IO.light")
TEST = os.path.join(BASE, "examples", "test_宿主IO.light")
ENTRY = os.path.join(BASE, "运行.py")
PASS_LINE = "test_宿主IO PASS"


def _nl(data: bytes) -> str:
    """按目标文件实际换行风格（CRLF/LF）生成变异串换行。"""
    return "\r\n" if b"\r\n" in data else "\n"


A_OLD = "  返回 造成功结果(项[\"内容\"], {\"操作\": \"read\", \"路径\": 规范, \"请求ID\": 请求ID})   # 反跑 A 变异锚点：改 项[\"内容\"] 即返回错内容\n"
A_NEW = "  返回 造成功结果(\"WRONG-CONTENT\", {\"操作\": \"read\", \"路径\": 规范, \"请求ID\": 请求ID})   # 反跑 A 变异锚点：改 项[\"内容\"] 即返回错内容\n"

B_OLD = "  返回 造成功结果({\"进程ID\": 进程ID, \"退出码\": 退出码, \"标准输出\": 输出, \"标准错误\": 句柄[\"标准错误\"], \"状态\": \"已退出\"}, {\"操作\": \"wait\", \"进程ID\": 进程ID, \"请求ID\": 请求ID})   # 反跑 B 变异锚点：改 退出码/输出 即返回错结果\n"
B_NEW = "  返回 造成功结果({\"进程ID\": 进程ID, \"退出码\": 0, \"标准输出\": 输出, \"标准错误\": 句柄[\"标准错误\"], \"状态\": \"已退出\"}, {\"操作\": \"wait\", \"进程ID\": 进程ID, \"请求ID\": 请求ID})   # 反跑 B 变异锚点：改 退出码/输出 即返回错结果\n"

C_OLD = "    如果 可重试表.包含(码) == 假:\n"
C_NEW = "    如果 可重试表.包含(码) == 真:\n"


def run_test():
    p = subprocess.run(
        [sys.executable, ENTRY, TEST],
        cwd=BASE, capture_output=True, text=True, encoding="utf-8", errors="replace",
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
        case("A 文件系统读错内容", A_OLD, A_NEW)
        case("B 进程退出码被改", B_OLD, B_NEW)
        case("C 重试判定翻转", C_OLD, C_NEW)
    finally:
        write_bytes(TARGET, original)

    ok_restore = hashlib.sha256(read_bytes(TARGET)).hexdigest() == digest
    rc_green, out_green = run_test()
    ok_green = rc_green == 0 and PASS_LINE in out_green

    ok = ok_restore and ok_green and all(r for _, r, _ in results)
    print("=== 第 17 轮任务 5 反跑判据（宿主 IO 抽象层原型）===")
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
