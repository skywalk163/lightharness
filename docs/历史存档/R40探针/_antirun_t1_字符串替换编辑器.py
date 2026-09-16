# -*- coding: utf-8 -*-
"""_antirun_t1_字符串替换编辑器.py —— 第13轮 任务1（fs 编辑器域）反跑判据

对象：lightharness/src/字符串替换编辑器.light（字节级备份 -> 变异 -> 跑本路测试 -> 断红 -> 恢复 -> 断绿）
判据（≥3 项）：
  A. 渲染视图行 6 位右对齐改 4 位（视图行号宽度语义被破坏）-> 测试红
  B. str_replace 多命中歧义条件放宽（不再抛 FS_AMBIGUOUS_EDIT）-> 测试红
  C. insert_line 上界放开（> 总行数可通过）-> 测试红
恢复后：sha256 逐字节一致 + 回归绿（rc=0），输出 ALL OK。
用法：cd G:\\dswork\\duan-light-merge && python _antirun_t1_字符串替换编辑器.py
退出码：全部通过 0；任一失败 1。
"""
import hashlib
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(BASE, "src", "字符串替换编辑器.light")
TEST = os.path.join("examples", "test_字符串替换编辑器.light")

A_OLD = '字符串对齐右(转字符串(行号), 6, " ")'
A_NEW = '字符串对齐右(转字符串(行号), 4, " ")  # antirun A'
B_OLD = "如果 列表长度(命中表) > 1:"
B_NEW = "如果 列表长度(命中表) > 1000:  # antirun B"
C_OLD = "如果 行 > 总行数:"
C_NEW = "如果 行 > 总行数 + 1000:  # antirun C"


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
        rc = run_test()
        results.append((name, rc != 0, "变异后运行 rc=%d（期望非 0，真红）" % rc))
        write_bytes(TARGET, original)

    case("A 视图行号 6 位右对齐改 4 位 -> 红", A_OLD, A_NEW)
    case("B str_replace 多命中不再抛歧义 -> 红", B_OLD, B_NEW)
    case("C insert_line 上界放开(>总行数通过) -> 红", C_OLD, C_NEW)

    ok_restore = hashlib.sha256(read_bytes(TARGET)).hexdigest() == digest
    rc_green = run_test()

    ok = ok_restore and rc_green == 0 and all(r for _, r, _ in results)
    print("=== 第13轮 任务1 反跑判据（fs 编辑器域 字符串替换编辑器）===")
    for name, red, note in results:
        print("%s %s (%s)" % ("PASS" if red else "FAIL", name, note))
    print("%s 字节级恢复校验 (sha256 %s)" % ("PASS" if ok_restore else "FAIL", digest[:12]))
    print("%s 恢复后回归绿 (rc=%d)" % ("PASS" if rc_green == 0 else "FAIL", rc_green))
    print("ALL OK" if ok else "ANTIRUN FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
