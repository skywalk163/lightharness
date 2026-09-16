# -*- coding: utf-8 -*-
"""_antirun_t4_宿主工具.py —— 第 17 轮任务 4 反跑判据（宿主工具接线原型）

对象：src/宿主工具.light（字节级备份 → 变异 → 跑测试 → 断言真红 → 恢复 → 断言真绿）
判据（3/3）：
  A. 调用协议跳过执行（调用工具 的 函数(上下文) 改为 空）→ 2b「执行返回计算结果==10」红；恢复 → 绿
  B. 权限控制全放行（检查调用权限 恒返回 真）→ 3a「跨插件调 private 失败」红；恢复 → 绿
  C. 停止不自动注销（插件停止注销工具 不再调用 注销全部）→ 6b「停止后工具不可调用」红；恢复 → 绿
用法：python _antirun_t4_宿主工具.py
退出码：全部判据通过 0（打印 ALL OK）；任一失败 1。
安全：恢复一律走 finally，异常退出也不会残留变异。
提醒：本脚本原地改 src/，**不得与 运行.py 并行执行**（并行会读到被改版本导致假红）。
"""
import hashlib
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(BASE, "src", "宿主工具.light")
TEST = os.path.join(BASE, "examples", "test_宿主工具.light")
ENTRY = os.path.join(BASE, "运行.py")
PASS_LINE = "test_宿主工具 PASS"


def _nl(data: bytes) -> str:
    """按目标文件实际换行风格（CRLF/LF）生成变异串换行。"""
    return "\r\n" if b"\r\n" in data else "\n"


A_OLD = "    设 数据 为 函数(上下文)   # 反跑 A 变异锚点：改 空 即跳过执行\n"
A_NEW = "    设 数据 为 空   # 反跑 A 变异锚点：改 空 即跳过执行\n"

B_OLD = (
    "  如果 可见性 == \"public\":\n"
    "    返回 真\n"
    "  如果 可见性 == \"internal\":\n"
    "    返回 调用者插件名 == 注册者\n"
    "  如果 可见性 == \"private\":\n"
    "    返回 调用者插件名 == 注册者\n"
    "  返回 假\n"
)
B_NEW = "  返回 真\n"

C_OLD = (
    "段落 插件停止注销工具 接收 运行时, 插件名:\n"
    "  返回 注销全部(运行时, 插件名)\n"
)
C_NEW = (
    "段落 插件停止注销工具 接收 运行时, 插件名:\n"
    "  返回 真\n"
)


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
        case("A 调用协议跳过执行", A_OLD, A_NEW)
        case("B 权限控制全放行", B_OLD, B_NEW)
        case("C 停止不自动注销", C_OLD, C_NEW)
    finally:
        write_bytes(TARGET, original)

    ok_restore = hashlib.sha256(read_bytes(TARGET)).hexdigest() == digest
    rc_green, out_green = run_test()
    ok_green = rc_green == 0 and PASS_LINE in out_green

    ok = ok_restore and ok_green and all(r for _, r, _ in results)
    print("=== 第 17 轮任务 4 反跑判据（宿主工具接线原型）===")
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
