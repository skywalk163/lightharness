# -*- coding: utf-8 -*-
"""_antirun_session_fix.py —— 第 9 轮任务 1 反跑判据（会话域修复，字节级备份/恢复 src）

对象：src/会话格式.light + src/会话.light（字节级备份/恢复）
判据：
  A. T2-D5 修复点改回笔误（投影节点0 append 分支 ["系统"]→["system"]）→ 红；恢复 → 绿
  B1. T2-D1 顺序校验失效（如果 旧开始 > 旧结束 → 如果 假）→ start>end 不抛错红；恢复 → 绿
  B2. T2-D1 存在性校验失效（如果 有起点 == 假 → 如果 假）→ 起点不存在不抛错红；恢复 → 绿
  C. T2-D3 版本键改回中文（["major":…,"minor":…] → 头["版本"]）→ 版本还原断言红；恢复 → 绿
用法：cd lightharness && python _antirun_session_fix.py
退出码：全部判据通过 0；任一失败 1。
"""
import hashlib
import subprocess
import sys

FMT = "src/会话格式.light"
FHUI = "src/会话.light"
TEST = "examples/test_修复_会话.light"

A_OLD = '设 当前 为 当前 + 事件项["数据"]["系统"]'
A_NEW = '设 当前 为 当前 + 事件项["数据"]["system"]'
B1_OLD = "如果 旧开始 > 旧结束:"
B1_NEW = "如果 假:  # antirun B1"
B2_OLD = "如果 有起点 == 假:"
B2_NEW = "如果 假:  # antirun B2"
C_OLD = '行["version"] 为 ["major": 头["版本"]["主"], "minor": 头["版本"]["次"]]'
C_NEW = '行["version"] 为 头["版本"]'


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
    originals = {FMT: read_bytes(FMT), FHUI: read_bytes(FHUI)}
    digests = {k: hashlib.sha256(v).hexdigest() for k, v in originals.items()}
    if read_bytes(TEST) is None:
        print("✗ 找不到测试文件: %s" % TEST)
        return 1
    results = []

    def case(name, target, old, new):
        """改反 src 修复点 → 期望红（rc!=0）；随后恢复字节。"""
        mutated = originals[target].replace(old.encode("utf-8"), new.encode("utf-8"))
        if mutated == originals[target]:
            results.append((name, False, "skip: 变异未命中"))
            return
        write_bytes(target, mutated)
        rc = run_test()
        results.append((name, rc != 0, "判红运行 rc=%d" % rc))
        write_bytes(target, originals[target])

    case("A T2-D5 键名改回笔误", FMT, A_OLD, A_NEW)
    case("B1 T2-D1 顺序校验失效", FHUI, B1_OLD, B1_NEW)
    case("B2 T2-D1 存在性校验失效", FHUI, B2_OLD, B2_NEW)
    case("C T2-D3 版本键改回中文", FMT, C_OLD, C_NEW)

    # 恢复校验：字节级还原
    ok_restore = all(hashlib.sha256(read_bytes(k)).hexdigest() == v for k, v in digests.items())
    rc_green = run_test()

    ok = ok_restore and rc_green == 0 and all(r for _, r, _ in results)
    print("=== 第 9 轮任务 1 反跑判据（会话域修复）===")
    for name, red, note in results:
        print("%s %s (%s)" % ("✓" if red else "✗", name, note))
    print("%s 字节级恢复校验" % ("✓" if ok_restore else "✗"))
    print("%s 恢复后回归绿 (rc=%d)" % ("✓" if rc_green == 0 else "✗", rc_green))
    print("=== 结果：%s ===" % ("全部通过" if ok else "存在失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
