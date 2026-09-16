# -*- coding: utf-8 -*-
"""_antirun_t2_子代理续传.py —— 第 16 轮任务 2 反跑判据（subagent 子代理续传 下）

对象：src/子代理续传.light（字节级备份 → 变异 → 跑测试 → 断言真红 → 恢复 → 断言真绿）
判据（3/3）：
  A. 结算摘要 completed 分支错（`结算摘要` 的 completed 文案被改）→ 1h「摘要 completed」红；恢复 → 绿
  B. 诊断项原因白名单放宽（`是子代理诊断项` 接受任意 reason）→ 2c「非法原因拒绝」红；恢复 → 绿
  C. 模型路由键改分隔符拼接（绕过 L-133 JSON 编码绕法，用 "|" 拼）→ 4a「模型路由键 唯一编码」红；恢复 → 绿
用法：python _antirun_t2_子代理续传.py
退出码：全部判据通过 0（打印 ALL OK）；任一失败 1。
安全：恢复一律走 finally，异常退出也不会残留变异。
提醒：本脚本原地改 src/，**不得与 运行.py 并行执行**（并行会读到被改版本导致假红）。
"""
import hashlib
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(BASE, "src", "子代理续传.light")
TEST = os.path.join(BASE, "examples", "test_子代理续传.light")
ENTRY = os.path.join(BASE, "运行.py")
PASS_LINE = "test_子代理续传 PASS"


def _nl(data: bytes) -> str:
    """按目标文件实际换行风格（CRLF/LF）生成变异串换行。"""
    return "\r\n" if b"\r\n" in data else "\n"


A_OLD = (
    "  如果 停止原因 == \"completed\":\n"
    "    返回 主语 + \" finished and will do no further work unless you send it more.\"\n"
)
A_NEW = (
    "  如果 停止原因 == \"completed\":\n"
    "    返回 主语 + \" completed-task.\"\n"
)

B_OLD = (
    "  设 原因 为 值[\"reason\"]\n"
    "  返回 原因 == \"corrupt\" 或 原因 == \"unsupported\" 或 原因 == \"unavailable\"\n"
)
B_NEW = (
    "  设 原因 为 值[\"reason\"]\n"
    "  返回 真\n"
)

C_OLD = (
    "段落 模型路由键 接收 路线:\n"
    "  返回 序列化JSON([路线[\"provider\"], 路线[\"model\"]])\n"
)
C_NEW = (
    "段落 模型路由键 接收 路线:\n"
    "  返回 路线[\"provider\"] + \"|\" + 路线[\"model\"]\n"
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
        case("A 结算摘要 completed 分支错", A_OLD, A_NEW)
        case("B 诊断项原因白名单放宽", B_OLD, B_NEW)
        case("C 模型路由键改分隔符拼接", C_OLD, C_NEW)
    finally:
        write_bytes(TARGET, original)

    ok_restore = hashlib.sha256(read_bytes(TARGET)).hexdigest() == digest
    rc_green, out_green = run_test()
    ok_green = rc_green == 0 and PASS_LINE in out_green

    ok = ok_restore and ok_green and all(r for _, r, _ in results)
    print("=== 第 16 轮任务 2 反跑判据（subagent 子代理续传 下）===")
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
