# -*- coding: utf-8 -*-
"""_antirun_title.py —— 第 14 轮任务 6 反跑判据（会话标题域）

对象：src/会话标题族.light（字节级备份 → 变异 → 跑测试 → 断言真红 → 恢复 → 断言真绿）
判据（3/3）：
  A. 标题比较不规范化（`标题同值` 退化为原始串比较）→ 6a/6b（首尾/内部空白折叠）红；恢复 → 绿
  B. 事件不变量不再校验「messageSeqs 空 ⟺ source.kind=user」配对（配对判据恒假）→ 6n/6p 红；恢复 → 绿
  C. 系统提示不再注入目标词数/汉字数（第 4 行退化为静态文案）→ 3d 红；恢复 → 绿
用法：cd lightharness && python _antirun_title.py
退出码：全部判据通过 0（打印 ALL OK）；任一失败 1。
安全：恢复一律走 finally，异常退出也不会残留变异（第13轮教训 C 判据变异残留）。
"""
import hashlib
import subprocess
import sys

TARGET = "src/会话标题族.light"
TEST = "examples/test_会话标题族.light"
PASS_LINE = "test_会话标题族 PASS"


def _nl(data: bytes) -> str:
    """按目标文件实际换行风格（CRLF/LF）生成变异串换行。"""
    return "\r\n" if b"\r\n" in data else "\n"


# A 规范化在标题比较中失效
A_OLD = "  返回 规范化会话标题(甲, 安全整数上限) == 规范化会话标题(乙, 安全整数上限)\n"
A_NEW = "  返回 甲 == 乙\n"

# B 不变量配对判据被短路（序号数 与 source.kind 不再配对校验）
B_OLD = "  如果 (序号数 == 0) != 用户改:\n"
B_NEW = "  如果 假:\n"

# C 系统提示第 4 行不再注入 targetWords / targetCjkCharacters
C_OLD = (
    '  列表追加(行表, "Aim for about " + 转字符串(配置["targetWords"]) + '
    '" words in non-CJK languages or " + 转字符串(配置["targetCjkCharacters"]) + " CJK characters.")\n'
)
C_NEW = '  列表追加(行表, "Aim for about some words in non-CJK languages or some CJK characters.")\n'


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
        case("A 标题比较不规范化", A_OLD, A_NEW)
        case("B 不变量不再校验 messageSeqs ⟺ user 配对", B_OLD, B_NEW)
        case("C 系统提示不再注入目标词数/汉字数", C_OLD, C_NEW)
    finally:
        write_bytes(TARGET, original)

    ok_restore = hashlib.sha256(read_bytes(TARGET)).hexdigest() == digest
    rc_green, out_green = run_test()
    ok_green = rc_green == 0 and PASS_LINE in out_green

    ok = ok_restore and ok_green and all(r for _, r, _ in results)
    print("=== 第 14 轮任务 6 反跑判据（会话标题域）===")
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
