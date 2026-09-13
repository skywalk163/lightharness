# -*- coding: utf-8 -*-
"""_antirun_t1_文件系统工具.py —— 第14轮 任务1（fs 工具域）反跑判据

对象：lightharness/src/文件系统工具.light（字节级备份 -> 变异 -> 跑本路测试 -> 断红 -> 恢复 -> 断绿）
判据（≥3 项）：
  A. 行差分表 LCS 匹配条件失效（不再计算公共子序列，等价逐行比较退化）-> 测试红
  B. 施加编辑 多命中条件放宽（不再要求唯一或 replace_all）-> 测试红
  C. 解析读参数 limit 上界校验放宽（>2000 通过）-> 测试红
恢复放在 finally/异常安全路径（第13轮教训）；恢复后 sha256 逐字节一致 + 回归绿，输出 ALL OK。
用法：cd G:\\dswork\\duan-light-merge && python _antirun_t1_文件系统工具.py
退出码：全部通过 0；任一失败 1。
"""
import hashlib
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(BASE, "src", "文件系统工具.light")
TEST = os.path.join("examples", "test_文件系统工具.light")

# A 锚点出现两处（DP 建表 + 回溯），全替换后 LCS 恒空 -> 相同文本也产出全量差异
A_OLD = "如果 前行表[甲] == 后行表[乙]:"
A_NEW = "如果 前行表[甲] == \"@antirun_A\":  # antirun A"
B_OLD = "如果 次数 > 1:"
B_NEW = "如果 次数 > 1000:  # antirun B"
C_OLD = "如果 上限 > 最大上限:"
C_NEW = "如果 上限 > 最大上限 + 1000:  # antirun C"


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
        case("A diff 算法失效(不计算 LCS/逐行退化) -> 红", A_OLD, A_NEW)
        case("B edit 多命中不再要求唯一或 replace_all -> 红", B_OLD, B_NEW)
        case("C read 行范围上界放开(>2000 通过) -> 红", C_OLD, C_NEW)
    finally:
        write_bytes(TARGET, original)

    ok_restore = hashlib.sha256(read_bytes(TARGET)).hexdigest() == digest
    rc_green = run_test()

    ok = ok_restore and rc_green == 0 and all(r for _, r, _ in results)
    print("=== 第14轮 任务1 反跑判据（fs 工具域 文件系统工具）===")
    for name, red, note in results:
        print("%s %s (%s)" % ("PASS" if red else "FAIL", name, note))
    print("%s 字节级恢复校验 (sha256 %s)" % ("PASS" if ok_restore else "FAIL", digest[:12]))
    print("%s 恢复后回归绿 (rc=%d)" % ("PASS" if rc_green == 0 else "FAIL", rc_green))
    print("ALL OK" if ok else "ANTIRUN FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
