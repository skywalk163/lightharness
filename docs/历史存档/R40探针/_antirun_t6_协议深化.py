# -*- coding: utf-8 -*-
"""_antirun_t6_协议深化.py —— 第 15 轮任务 6 反跑判据（ACP + hook-protocol 深化域）

对象：src/协议深化.light（字节级备份 → 变异 → 跑测试 → 断言真红 → 恢复 → 断言真绿）
判据（3/3）：
  A. MCP 配置构造改坏（解析MCP配置 传输键 "stdio" → "STDIO"）
     → 判据A:stdio round-trip / http round-trip 断言红；恢复 → 绿
  B. 空批次/用量变异（助手更新批次 空块表提前返回 空，或用量条不再追加）
     → 判据B:空批次序列化 / 用量批次往返 断言红；恢复 → 绿
  C. 运行器成功码变异（运行钩子 成功分支 `设 退出码 为 执行结果["退出码"]`
     改为恒 0，破坏「空 → 空」语义）
     → 运行:成功退出码 / 运行:信号死亡 断言红；恢复 → 绿
用法：cd lightharness && python _antirun_t6_协议深化.py
退出码：全部判据通过 0（打印 ALL OK）；任一失败 1。
安全：恢复一律走 finally，异常退出也不会残留变异（第13轮教训 C 判据变异残留）。
同时提醒：本脚本原地改 src/，**不得与 运行.py 并行执行**（第14轮教训：并行会读到被改版本导致假红）。
"""
import hashlib
import subprocess
import sys

TARGET = "src/协议深化.light"
TEST = "examples/test_协议深化.light"
PASS_LINE = "test_协议深化 PASS"


def _nl(data: bytes) -> str:
    """按目标文件实际换行风格（CRLF/LF）生成变异串换行。"""
    return "\r\n" if b"\r\n" in data else "\n"


A_TRANSPORT = '"传输": "stdio"'
A_MUTATED = '"传输": "STDIO"'

# 判据 B：空块表分支提前返回 空（而不是走完整个批次构造返回更新表）
B_OLD = (
    "  设 用量 为 占用更新(用量记录, 用量总数)\n"
    "  遍历 用量项 之 用量:\n"
    "    列表追加(更新表, 用量项)\n"
    "  返回 更新表\n"
)
B_NEW = (
    "  设 用量 为 占用更新(用量记录, 用量总数)\n"
    "  返回 空\n"
)

# 判据 C：成功分支退出码原样透传被破坏（空 → 0）
C_OLD = "  设 退出码 为 执行结果[\"退出码\"]\n"
C_NEW = "  设 退出码 为 0\n"


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
        case("A MCP 传输键改错", A_TRANSPORT, A_MUTATED)
        case("B 空批次提前返回 空", B_OLD, B_NEW)
        case("C 成功码恒 0", C_OLD, C_NEW)
    finally:
        write_bytes(TARGET, original)

    ok_restore = hashlib.sha256(read_bytes(TARGET)).hexdigest() == digest
    rc_green, out_green = run_test()
    ok_green = rc_green == 0 and PASS_LINE in out_green

    ok = ok_restore and ok_green and all(r for _, r, _ in results)
    print("=== 第 15 轮任务 6 反跑判据（ACP + hook-protocol 深化域）===")
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