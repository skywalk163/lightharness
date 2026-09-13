# -*- coding: utf-8 -*-
"""_antirun_typert.py —— 第 14 轮任务 5 反跑判据（类型系统域）

对象：src/类型系统.light（字节级备份 → 变异 → 跑测试 → 断言真红 → 恢复 → 断言真绿）
判据（3/3）：
  A. 结构相等退化为「仅同一对象」（`如果 甲种 != 乙种:` → `如果 真:`，节点恒不等）→ 相等断言红；恢复 → 绿
  B. union 渲染不再加 ` | ` 分隔（`" | "` → `"|"`）→ 联合渲染断言红；恢复 → 绿
  C. 分析器不再检测重复符号（`抛出 … duplicate symbol …` → `返回 符号`）→ 重复符号应抛错断言红；恢复 → 绿
用法：cd lightharness && python _antirun_typert.py
退出码：全部判据通过 0（打印 ALL OK）；任一失败 1。
安全：恢复一律走 finally，异常退出也不会残留变异（第13轮教训 C 判据变异残留）。
"""
import hashlib
import subprocess
import sys

TARGET = "src/类型系统.light"
TEST = "examples/test_类型系统.light"
PASS_LINE = "test_类型系统 PASS"


def _nl(data: bytes) -> str:
    """按目标文件实际换行风格（CRLF/LF）生成变异串换行。"""
    return "\r\n" if b"\r\n" in data else "\n"


A_OLD = "  如果 甲种 != 乙种:\n    返回 假\n"
A_NEW = "  如果 真:\n    返回 假\n"

B_OLD = '  如果 种类 == "union":\n    返回 连接节点(取字段(节点, ["成员"], []), " | ")\n'
B_NEW = '  如果 种类 == "union":\n    返回 连接节点(取字段(节点, ["成员"], []), "|")\n'

C_OLD = '    抛出 新建 错误("duplicate symbol " + 名 + " in package " + 表["包"])\n'
C_NEW = "    返回 符号\n"


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
        case("A 结构相等退化为仅同一对象", A_OLD, A_NEW)
        case("B union 渲染不加 | 分隔", B_OLD, B_NEW)
        case("C 分析器不再检测重复符号", C_OLD, C_NEW)
    finally:
        write_bytes(TARGET, original)

    ok_restore = hashlib.sha256(read_bytes(TARGET)).hexdigest() == digest
    rc_green, out_green = run_test()
    ok_green = rc_green == 0 and PASS_LINE in out_green

    ok = ok_restore and ok_green and all(r for _, r, _ in results)
    print("=== 第 14 轮任务 5 反跑判据（类型系统域）===")
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
