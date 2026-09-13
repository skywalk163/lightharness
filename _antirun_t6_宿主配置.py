# -*- coding: utf-8 -*-
"""_antirun_t6_宿主配置.py —— 第 17 轮任务 6 反跑判据（宿主配置接线原型）

对象：src/宿主配置.light（字节级备份 → 变异 → 跑测试 → 断言真红 → 恢复 → 断言真绿）
判据（3/3）：
  A. 获取配置跳过当前值（获取配置 的 如果 当前 != 空 改为 如果 假）→ 2b「设置后取当前值==debug」红；恢复 → 绿
  B. 只读可变性检查被删（设置配置 的 只读抛错 改为 设 占位 为 真）→ 4f「只读配置不可改」红；恢复 → 绿
  C. 加载优先级排序翻转（按优先级升序 的 < 改为 >）→ 3d「加载后高优先级生效(log=error)」红；恢复 → 绿
用法：python _antirun_t6_宿主配置.py
退出码：全部判据通过 0（打印 ALL OK）；任一失败 1。
安全：恢复一律走 finally，异常退出也不会残留变异。
提醒：本脚本原地改 src/，**不得与 运行.py 并行执行**（并行会读到被改版本导致假红）。
"""
import hashlib
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(BASE, "src", "宿主配置.light")
TEST = os.path.join(BASE, "examples", "test_宿主配置.light")
ENTRY = os.path.join(BASE, "运行.py")
PASS_LINE = "test_宿主配置 PASS"


def _nl(data: bytes) -> str:
    """按目标文件实际换行风格（CRLF/LF）生成变异串换行。"""
    return "\r\n" if b"\r\n" in data else "\n"


A_OLD = "  如果 当前 != 空:\n"
A_NEW = "  如果 假:\n"

B_OLD = "    抛出 新建 错误(\"宿主配置: 只读配置不可改 \" + 键)\n"
B_NEW = "    设 占位 为 真\n"

C_OLD = "      如果 字典获取(排序[j], \"优先级\", 0) < 字典获取(排序[i], \"优先级\", 0):\n"
C_NEW = "      如果 字典获取(排序[j], \"优先级\", 0) > 字典获取(排序[i], \"优先级\", 0):\n"


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
        case("A 获取配置跳过当前值", A_OLD, A_NEW)
        case("B 只读可变性检查被删", B_OLD, B_NEW)
        case("C 加载优先级排序翻转", C_OLD, C_NEW)
    finally:
        write_bytes(TARGET, original)

    ok_restore = hashlib.sha256(read_bytes(TARGET)).hexdigest() == digest
    rc_green, out_green = run_test()
    ok_green = rc_green == 0 and PASS_LINE in out_green

    ok = ok_restore and ok_green and all(r for _, r, _ in results)
    print("=== 第 17 轮任务 6 反跑判据（宿主配置接线原型）===")
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
