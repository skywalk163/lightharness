# -*- coding: utf-8 -*-
"""_antirun_goalround.py —— 第 13 轮任务 3 反跑判据（goal 轮驱动域）

对象：src/目标轮驱动.light（字节级备份 → 变异 → 跑测试 → 断言真红 → 恢复 → 断言真绿）
判据（3/3）：
  A. 轮号改 roundsStarted（`设 轮 为 已开 + 1` → `设 轮 为 已开`）→ 轮号断言红；恢复 → 绿
  B. 轮次上限不再阻止（round-limit 分支改判 `已开 > 上限` 并改写等待动作）→ 阻止断言红；恢复 → 绿
  C. 提示缺收尾标记（去掉 prompt 末尾 `</goal_round>`）→ 收尾断言红；恢复 → 绿
用法：cd lightharness && python _antirun_goalround.py
退出码：全部判据通过 0（打印 ALL OK）；任一失败 1。
"""
import hashlib
import subprocess
import sys

TARGET = "src/目标轮驱动.light"
TEST = "examples/test_目标轮驱动.light"


def _nl(data: bytes) -> str:
    """按目标文件实际换行风格（CRLF/LF）生成变异串换行。"""
    return "\r\n" if b"\r\n" in data else "\n"


A_OLD = "  设 轮 为 已开 + 1\n"
A_NEW = "  设 轮 为 已开\n"
B_OLD = (
    "  如果 已开 >= 上限:\n"
    "    返回 {\"动作\": \"block\", \"码\": 码轮次上限, \"消息\": \"目标达到配置上限 \" + 转字符串(上限) + \" 轮\", \"目标引用\": 取目标引用(目标)}\n"
)
B_NEW = (
    "  如果 已开 > 上限:\n"
    "    返回 {\"动作\": \"wait\"}\n"
)
C_OLD = " + \"\\n\" + 目标轮尾标记"
C_NEW = " + \"\""


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

    case("A 轮号改 roundsStarted", A_OLD, A_NEW)
    case("B 轮次上限不再阻止", B_OLD, B_NEW)
    case("C 提示缺 </goal_round> 收尾", C_OLD, C_NEW)

    ok_restore = hashlib.sha256(read_bytes(TARGET)).hexdigest() == digest
    rc_green, out_green = run_test()
    ok_green = rc_green == 0 and "test_目标轮驱动 PASS" in out_green

    ok = ok_restore and ok_green and all(r for _, r, _ in results)
    print("=== 第 13 轮任务 3 反跑判据（goal 轮驱动域）===")
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
