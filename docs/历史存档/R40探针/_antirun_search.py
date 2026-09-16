# -*- coding: utf-8 -*-
"""_antirun_search.py —— 第 14 轮任务 4 反跑判据（搜索提供商域）

对象：src/搜索提供商.light（字节级备份 → 变异 → 跑测试 → 断言真红 → 恢复 → 断言真绿）
判据（3/3）：
  A. 响应归一不再提取 url（`设 来源 为 {"url": 地址}` → `设 来源 为 {}`）→ 取 url 断言红；恢复 → 绿
  B. 参数校验 limit 上界放开（去掉 `"maximum": 100`）→ limit=101 应报错的取下标断言红；恢复 → 绿
  C. 错误映射 401 不再映射为 API_KEY_MISSING（改返回 PROVIDER_ERROR）→ 401 映射断言红；恢复 → 绿
用法：cd lightharness && python _antirun_search.py
退出码：全部判据通过 0（打印 ALL OK）；任一失败 1。
安全：恢复一律走 finally，异常退出也不会残留变异（第13轮教训 C 判据变异残留）。
"""
import hashlib
import subprocess
import sys

TARGET = "src/搜索提供商.light"
TEST = "examples/test_搜索提供商.light"
PASS_LINE = "test_搜索提供商 PASS"


def _nl(data: bytes) -> str:
    """按目标文件实际换行风格（CRLF/LF）生成变异串换行。"""
    return "\r\n" if b"\r\n" in data else "\n"


A_OLD = '      设 来源 为 {"url": 地址}\n'
A_NEW = "      设 来源 为 {}\n"

B_OLD = '  属性["limit"] 为 {"type": "integer", "minimum": 1, "maximum": 100}\n'
B_NEW = '  属性["limit"] 为 {"type": "integer", "minimum": 1}\n'

C_OLD = "  如果 状态 == 401:\n    返回 码缺密钥\n"
C_NEW = "  如果 状态 == 401:\n    返回 码提供商错误\n"


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
        case("A 响应归一不再提取 url", A_OLD, A_NEW)
        case("B 参数校验 limit 上界放开", B_OLD, B_NEW)
        case("C 401 不再映射为 API_KEY_MISSING", C_OLD, C_NEW)
    finally:
        write_bytes(TARGET, original)

    ok_restore = hashlib.sha256(read_bytes(TARGET)).hexdigest() == digest
    rc_green, out_green = run_test()
    ok_green = rc_green == 0 and PASS_LINE in out_green

    ok = ok_restore and ok_green and all(r for _, r, _ in results)
    print("=== 第 14 轮任务 4 反跑判据（搜索提供商域）===")
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
