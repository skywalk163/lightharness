# -*- coding: utf-8 -*-
"""_antirun_sesslog.py —— 第 13 轮任务 4 反跑判据（session 日志域）

对象：src/会话日志增量.light（字节级备份 → 变异 → 跑测试 → 断言真红 → 恢复 → 断言真绿）
判据（3/3）：
  A. 水印不再取最大（`如果 通过序号 > 水印:` → `如果 水印 < 0:`，退化为取首个）→ 水印断言红；恢复 → 绿
  B. 线头 seedLength 无条件落键（去掉 `已播种 == 真` 条件）→ 「缺省不落键」断言红；恢复 → 绿
  C. 畸形接受事件不再抛错（格式版本畸形由 `抛出` 改为 `跳过`）→ 「应抛错」断言红；恢复 → 绿
用法：cd lightharness && python _antirun_sesslog.py
退出码：全部判据通过 0（打印 ALL OK）；任一失败 1。
"""
import hashlib
import subprocess
import sys

TARGET = "src/会话日志增量.light"
TEST = "examples/test_会话日志增量.light"


def _nl(data: bytes) -> str:
    """按目标文件实际换行风格（CRLF/LF）生成变异串换行。"""
    return "\r\n" if b"\r\n" in data else "\n"


A_OLD = "    如果 通过序号 > 水印:\n      设 水印 为 通过序号"
A_NEW = "    如果 水印 < 0:\n      设 水印 为 通过序号"
B_OLD = "  如果 取字段(会话头, [\"已播种\", \"isSeeded\"], 假) == 真:\n    结果[\"seedLength\"] 为 取字段(会话头, [\"继承事件数\", \"inheritedEventCount\"], 0)\n"
B_NEW = "  结果[\"seedLength\"] 为 取字段(会话头, [\"继承事件数\", \"inheritedEventCount\"], 0)\n"
C_OLD = (
    "    如果 是安全整数(接受版本) == 假:\n"
    "      抛出 新建 错误(\"session-log-deepseek: malformed acceptance format version at seq \" + 转字符串(此处序号))\n"
)
C_NEW = (
    "    如果 是安全整数(接受版本) == 假:\n"
    "      设 序号 为 序号 + 1\n"
    "      继续\n"
)


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
        write_bytes(TARGET, mutated)
        rc, out = run_test()
        results.append((name, rc != 0, "判红运行 rc=%d" % rc))
        write_bytes(TARGET, original)

    case("A 水印不再取最大（退化为取首个）", A_OLD, A_NEW)
    case("B 线头 seedLength 无条件落键", B_OLD, B_NEW)
    case("C 畸形接受事件不再抛错", C_OLD, C_NEW)

    ok_restore = hashlib.sha256(read_bytes(TARGET)).hexdigest() == digest
    rc_green, out_green = run_test()
    ok_green = rc_green == 0 and "test_会话日志增量 PASS" in out_green

    ok = ok_restore and ok_green and all(r for _, r, _ in results)
    print("=== 第 13 轮任务 4 反跑判据（session 日志域）===")
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
