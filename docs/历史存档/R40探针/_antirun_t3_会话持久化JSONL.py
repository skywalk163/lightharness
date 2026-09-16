# -*- coding: utf-8 -*-
"""_antirun_t3_会话持久化JSONL.py —— 第14轮 任务3（JSONL 持久化域）反跑判据

对象：lightharness/src/会话持久化JSONL.light（字节级备份 -> 变异 -> 跑本路测试 -> 断红 -> 恢复 -> 断绿）
判据（≥3 项）：
  A. 行序列化去掉尾换行 -> 测试红
  B. 迁移校验不再检查 seq 连续 -> 测试红
  C. 事件生成不按 seq 排序 -> 测试红
恢复放在 try/finally 异常安全路径；恢复后 sha256 逐字节一致 + 回归绿，输出 ALL OK。
用法：cd G:\\dswork\\duan-light-merge && python _antirun_t3_会话持久化JSONL.py
退出码：全部通过 0；任一失败 1。
"""
import hashlib
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(BASE, "src", "会话持久化JSONL.light")
TEST = os.path.join("examples", "test_会话持久化JSONL.light")

A_OLD = ("段落 行序列化 接收 对象:\n"
         "  返回 序列化JSON(对象) + \"\\n\"")
A_NEW = ("段落 行序列化 接收 对象:\n"
         "  返回 序列化JSON(对象)  # antirun A")
B_OLD = "如果 当前序号 != 前序 + 1:"
B_NEW = "如果 当前序号 == 前序 + 999:  # antirun B"
C_OLD = "如果 结果[内][\"序号\"] < 结果[最小][\"序号\"]:"
C_NEW = "如果 结果[内][\"序号\"] < 结果[最小][\"序号\"] - 100000:  # antirun C"


def run_test():
    env = dict(os.environ)
    env["LIGHT_MERGE"] = r"G:\dswork\duan-light-merge\light-merge"
    p = subprocess.run(
        [sys.executable, "运行.py", TEST],
        cwd=BASE, capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=env,
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
            results.append((name, False, "skip: 变异锚点未命中"))
            return
        write_bytes(TARGET, mutated)
        try:
            rc = run_test()
            results.append((name, rc != 0, "变异后运行 rc=%d（期望非 0，真红）" % rc))
        finally:
            write_bytes(TARGET, original)

    try:
        case("A 行序列化去掉尾换行 -> 红", A_OLD, A_NEW)
        case("B 迁移校验不再检查 seq 连续 -> 红", B_OLD, B_NEW)
        case("C 事件生成不按 seq 排序 -> 红", C_OLD, C_NEW)
    finally:
        write_bytes(TARGET, original)

    ok_restore = hashlib.sha256(read_bytes(TARGET)).hexdigest() == digest
    rc_green = run_test()

    ok = ok_restore and rc_green == 0 and all(r for _, r, _ in results)
    print("=== 第14轮 任务3 反跑判据（JSONL 持久化域 会话持久化JSONL）===")
    for name, red, note in results:
        print("%s %s (%s)" % ("PASS" if red else "FAIL", name, note))
    print("%s 字节级恢复校验 (sha256 %s)" % ("PASS" if ok_restore else "FAIL", digest[:12]))
    print("%s 恢复后回归绿 (rc=%d)" % ("PASS" if rc_green == 0 else "FAIL", rc_green))
    print("ALL OK" if ok else "ANTIRUN FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
