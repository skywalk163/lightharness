# -*- coding: utf-8 -*-
"""_antirun_repair.py —— 第 10 轮任务 1 反跑判据（repair 域复刻，字节级备份/恢复 src）

对象：src/会话格式.light（字节级备份/恢复）
判据：
  A. 未闭合 tool-call 合成 result 错误码改错（恢复码工具未启动 → 恢复码结果未知）→ 红；恢复 → 绿
  B. 序号基线改错（最后真实事件 seq+1 → 从 0 开始）→ 红；恢复 → 绿
  C. 平衡日志返回空改错（去掉轮闭合判断）→ 红；恢复 → 绿
用法：cd lightharness && python _antirun_repair.py
退出码：全部判据通过 0；任一失败 1。
"""
import hashlib
import subprocess
import sys

TARGET = "src/会话格式.light"
TEST = "examples/test_修复_repair.light"

A_OLD = '错误["代码"] 为 恢复码工具未启动'
A_NEW = '错误["代码"] 为 恢复码结果未知  # antirun A'
B_OLD = '设 序号 为 最后事件["序号"] + 1'
B_NEW = '设 序号 为 0  # antirun B'
C_OLD = "如果 (有开启轮次 == 假) 或 (长度(事件表) == 0):"
C_NEW = "如果 长度(事件表) == 0:  # antirun C"


def run_test():
    p = subprocess.run(
        [sys.executable, "运行.py", TEST],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return p.returncode


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def write_bytes(path, data):
    with open(path, "wb") as f:
        f.write(data)


def main():
    original = read_bytes(TARGET)
    digest = hashlib.sha256(original).hexdigest()
    results = []

    def case(name, old, new):
        mutated = original.replace(old.encode("utf-8"), new.encode("utf-8"))
        if mutated == original:
            results.append((name, False, "skip: 变异未命中"))
            return
        write_bytes(TARGET, mutated)
        rc = run_test()
        results.append((name, rc != 0, "判红运行 rc=%d" % rc))
        write_bytes(TARGET, original)

    case("A 错误码改错(TOOL_NOT_STARTED→OUTCOME_UNKNOWN)", A_OLD, A_NEW)
    case("B 序号基线改错(从0开始)", B_OLD, B_NEW)
    case("C 平衡日志返回空改错", C_OLD, C_NEW)

    ok_restore = hashlib.sha256(read_bytes(TARGET)).hexdigest() == digest
    rc_green = run_test()

    ok = ok_restore and rc_green == 0 and all(r for _, r, _ in results)
    print("=== 第 10 轮任务 1 反跑判据（repair 域复刻）===")
    for name, red, note in results:
        print("%s %s (%s)" % ("✓" if red else "✗", name, note))
    print("%s 字节级恢复校验 (sha256 %s)" % ("✓" if ok_restore else "✗", digest[:12]))
    print("%s 恢复后回归绿 (rc=%d)" % ("✓" if rc_green == 0 else "✗", rc_green))
    print("=== 结果：%s ===" % ("全部通过" if ok else "存在失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
