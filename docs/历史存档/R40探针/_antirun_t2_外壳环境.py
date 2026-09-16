# -*- coding: utf-8 -*-
"""_antirun_t2_外壳环境.py —— 第13轮 任务2（shell 环境域）反跑判据

对象：lightharness/src/外壳环境.light（字节级备份 -> 变异 -> 跑本路测试 -> 断红 -> 恢复 -> 断绿）
判据（≥3 项）：
  A. 是保留键 短路返回 假（DSH_HOME 允许被贡献者注册）-> 测试红
  B. 按键序冻结 返回未排序原表（collect 去掉键排序）-> 测试红
  C. 注销闭包不删除贡献者（注销后 collect 仍含键）-> 测试红
恢复后：sha256 逐字节一致 + 回归绿（rc=0），输出 ALL OK。
用法：cd G:\\dswork\\duan-light-merge && python _antirun_t2_外壳环境.py
退出码：全部通过 0；任一失败 1。
"""
import hashlib
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(BASE, "src", "外壳环境.light")
TEST = os.path.join("examples", "test_外壳环境.light")

A_OLD = "段落 是保留键 接收 键:\n  如果 键 == DSH家目录键:"
A_NEW = "段落 是保留键 接收 键:\n  返回 假  # antirun A\n  如果 键 == DSH家目录键:"
B_OLD = "返回 冻结(有序表)"
B_NEW = "返回 冻结(表)  # antirun B"
C_OLD = "字典删除(贡献者表, 名字)"
C_NEW = "设 保留名字 为 名字  # antirun C"


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

    case("A 保留键 DSH_HOME 允许注册 -> 红", A_OLD, A_NEW)
    case("B collect 去掉键排序 -> 红", B_OLD, B_NEW)
    case("C 注销函数不删除贡献者 -> 红", C_OLD, C_NEW)

    ok_restore = hashlib.sha256(read_bytes(TARGET)).hexdigest() == digest
    rc_green = run_test()

    ok = ok_restore and rc_green == 0 and all(r for _, r, _ in results)
    print("=== 第13轮 任务2 反跑判据（shell 环境域 外壳环境）===")
    for name, red, note in results:
        print("%s %s (%s)" % ("PASS" if red else "FAIL", name, note))
    print("%s 字节级恢复校验 (sha256 %s)" % ("PASS" if ok_restore else "FAIL", digest[:12]))
    print("%s 恢复后回归绿 (rc=%d)" % ("PASS" if rc_green == 0 else "FAIL", rc_green))
    print("ALL OK" if ok else "ANTIRUN FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
