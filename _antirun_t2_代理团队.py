# -*- coding: utf-8 -*-
"""_antirun_t2_代理团队.py —— 第14轮 任务2（代理团队域）反跑判据

对象：lightharness/src/代理团队.light（字节级备份 -> 变异 -> 跑本路测试 -> 断红 -> 恢复 -> 断绿）
判据（≥3 项）：
  A. 检测依赖环 短路返回（任务图允许环，环检测失效）-> 测试红
  B. 判动作门槛 release 状态校验失效（任意状态可 release）-> 测试红
  C. 确认送达事件 不追加 delivered（消息确认后不标记已读）-> 测试红
恢复放在 try/finally 异常安全路径；恢复后 sha256 逐字节一致 + 回归绿，输出 ALL OK。
用法：cd G:\\dswork\\duan-light-merge && python _antirun_t2_代理团队.py
退出码：全部通过 0；任一失败 1。
"""
import hashlib
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(BASE, "src", "代理团队.light")
TEST = os.path.join("examples", "test_代理团队.light")

A_OLD = ("段落 检测依赖环 接收 任务表, 标识, 访问中, 已访:\n"
         "  如果 列表包含(已访, 标识):")
A_NEW = ("段落 检测依赖环 接收 任务表, 标识, 访问中, 已访:\n"
         "  返回 \"\"  # antirun A\n"
         "  如果 列表包含(已访, 标识):")
B_OLD = ("  如果 动作 == \"release\":\n"
         "    如果 状态 != \"in_progress\":")
B_NEW = ("  如果 动作 == \"release\":\n"
         "    如果 状态 == \"in_progressX\":  # antirun B")
C_OLD = "列表追加(事件表, 事件)"
C_NEW = "设 送达占位 为 事件  # antirun C"


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
        case("A 任务图环检测改为不检测 -> 红", A_OLD, A_NEW)
        case("B 状态流转不再校验(release 门槛失效) -> 红", B_OLD, B_NEW)
        case("C 邮箱消息确认后不标记已读 -> 红", C_OLD, C_NEW)
    finally:
        write_bytes(TARGET, original)

    ok_restore = hashlib.sha256(read_bytes(TARGET)).hexdigest() == digest
    rc_green = run_test()

    ok = ok_restore and rc_green == 0 and all(r for _, r, _ in results)
    print("=== 第14轮 任务2 反跑判据（代理团队域 代理团队）===")
    for name, red, note in results:
        print("%s %s (%s)" % ("PASS" if red else "FAIL", name, note))
    print("%s 字节级恢复校验 (sha256 %s)" % ("PASS" if ok_restore else "FAIL", digest[:12]))
    print("%s 恢复后回归绿 (rc=%d)" % ("PASS" if rc_green == 0 else "FAIL", rc_green))
    print("ALL OK" if ok else "ANTIRUN FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
