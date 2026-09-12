# -*- coding: utf-8 -*-
"""_antirun_approval.py —— 第 12 轮任务 6 反跑判据（审批域对照收口，字节级备份/恢复 src）

对象：src/审批.light（字节级备份/恢复）
判据：
  A. never 策略改 ask（请求审批审计 的 never 分支改回 ask 语义）→ never 自动拒绝断言红；恢复 → 绿
  B. 裁决结果集少一种（审批结果词汇 去掉 unavailable）→ 四结果闭集断言红；恢复 → 绿
  C. hasOpenTurn 判定改错（是开轮 的 turn/start 分支改返回 假）→ 开轮断言红；恢复 → 绿
用法：cd lightharness && python _antirun_approval.py
退出码：全部判据通过 0；任一失败 1。
"""
import hashlib
import subprocess
import sys

TARGET = "src/审批.light"
TEST = "examples/test_审批对照.light"


def _b(s: str) -> bytes:
    """按目标文件实际换行（CRLF/LF 兼容）编码变异串。"""
    raw = s.encode("utf-8").replace(b"\n", b"\r\n")
    return raw

A_OLD = '''    如果 己.策略 == 策略从不:
      # never 在任何分派前确定性拒绝（上游 decide:266）
      设 裁决 为 结果拒绝'''
A_NEW = '''    如果 己.策略 == 策略从不:
      # antirun A：never 改 ask 语义（不应通过）
      设 裁决 为 结果允许一次'''
B_OLD = '设 审批结果词汇 为 [结果允许一次, 结果拒绝, 结果撤回, 结果不可用]'
B_NEW = '设 审批结果词汇 为 [结果允许一次, 结果拒绝, 结果撤回]'
C_OLD = '''    如果 类型 == "turn/start":
      返回 真
    如果 类型 == "turn/end":
      返回 假'''
C_NEW = '''    如果 类型 == "turn/start":
      返回 假
    如果 类型 == "turn/end":
      返回 假'''


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
        mutated = original.replace(_b(old), _b(new))
        if mutated == original:
            results.append((name, False, "skip: 变异未命中"))
            return
        write_bytes(TARGET, mutated)
        rc = run_test()
        results.append((name, rc != 0, "判红运行 rc=%d" % rc))
        write_bytes(TARGET, original)

    case("A never 策略改 ask 语义", A_OLD, A_NEW)
    case("B 裁决结果集少 unavailable", B_OLD, B_NEW)
    case("C 开轮判定改错(start→假)", C_OLD, C_NEW)

    ok_restore = hashlib.sha256(read_bytes(TARGET)).hexdigest() == digest
    rc_green = run_test()

    ok = ok_restore and rc_green == 0 and all(r for _, r, _ in results)
    print("=== 第 12 轮任务 6 反跑判据（审批域对照）===")
    for name, red, note in results:
        print("%s %s (%s)" % ("✓" if red else "✗", name, note))
    print("%s 字节级恢复校验 (sha256 %s)" % ("✓" if ok_restore else "✗", digest[:12]))
    print("%s 恢复后回归绿 (rc=%d)" % ("✓" if rc_green == 0 else "✗", rc_green))
    print("=== 结果：%s ===" % ("全部通过" if ok else "存在失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
