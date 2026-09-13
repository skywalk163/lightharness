# -*- coding: utf-8 -*-
"""_antirun_t3_网关协议.py —— 第 16 轮任务 3 反跑判据（api 网关协议）

对象：src/网关协议.light（字节级备份 → 变异 → 跑测试 → 断言真红 → 恢复 → 断言真绿）
判据（3/3）：
  A. 数据帧 round-trip 错位（`造项目帧` 的 "value" 字段被改名为 "data"）→
     1a「项目帧 round-trip 判别」红（是服务器项目帧 因精确键不匹配返回假）；恢复 → 绿
  B. 错误帧空 details 丢字段（`造错误帧` 构造时丢弃 "details" 键）→
     1e「错误帧 round-trip 判别」红（是服务器错误帧 因缺 details 精确键返回假）；恢复 → 绿
  C. 错误码表变异（网关错误码表 首码 "gateway/ambiguous-endpoint" 改错）→
     2b「命中错误码」红；恢复 → 绿
用法：python _antirun_t3_网关协议.py
退出码：全部判据通过 0（打印 ALL OK）；任一失败 1。
安全：恢复一律走 finally，异常退出也不会残留变异。
提醒：本脚本原地改 src/，**不得与 运行.py 并行执行**（并行会读到被改版本导致假红）。
注：分发文档 B 判据原文为「空负载的心跳帧序列化不丢字段」，但上游 stream-protocol.ts
    实际无心跳帧（仅 ready/emit/waterfall/cancel + open/cancel/item/error/end 帧），
    故据实以「错误帧空 details 不丢字段」作为 B 边界判据。
"""
import hashlib
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(BASE, "src", "网关协议.light")
TEST = os.path.join(BASE, "examples", "test_网关协议.light")
ENTRY = os.path.join(BASE, "运行.py")
PASS_LINE = "test_网关协议 PASS"


def _nl(data: bytes) -> str:
    """按目标文件实际换行风格（CRLF/LF）生成变异串换行。"""
    return "\r\n" if b"\r\n" in data else "\n"


A_OLD = (
    "段落 造项目帧 接收 流标识, 值:\n"
    "  返回 {\"type\": \"item\", \"streamId\": 流标识, \"value\": 值}\n"
)
A_NEW = (
    "段落 造项目帧 接收 流标识, 值:\n"
    "  返回 {\"type\": \"item\", \"streamId\": 流标识, \"data\": 值}\n"
)

B_OLD = (
    "段落 造错误帧 接收 流标识, 码, 消息, 细节:\n"
    "  返回 {\"type\": \"error\", \"streamId\": 流标识, \"error\": {\"code\": 码, \"message\": 消息, \"details\": 细节}}\n"
)
B_NEW = (
    "段落 造错误帧 接收 流标识, 码, 消息, 细节:\n"
    "  返回 {\"type\": \"error\", \"streamId\": 流标识, \"error\": {\"code\": 码, \"message\": 消息}}\n"
)

C_OLD = (
    "  返回 [\"gateway/ambiguous-endpoint\", \"gateway/arguments-invalid\", \"gateway/binding-invalid\",\n"
)
C_NEW = (
    "  返回 [\"gateway/ambiguous_endpoint\", \"gateway/arguments-invalid\", \"gateway/binding-invalid\",\n"
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
        case("A 数据帧 value 字段改名 data", A_OLD, A_NEW)
        case("B 错误帧丢弃 details 字段", B_OLD, B_NEW)
        case("C 网关错误码表首码改错", C_OLD, C_NEW)
    finally:
        write_bytes(TARGET, original)

    ok_restore = hashlib.sha256(read_bytes(TARGET)).hexdigest() == digest
    rc_green, out_green = run_test()
    ok_green = rc_green == 0 and PASS_LINE in out_green

    ok = ok_restore and ok_green and all(r for _, r, _ in results)
    print("=== 第 16 轮任务 3 反跑判据（api 网关协议）===")
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
