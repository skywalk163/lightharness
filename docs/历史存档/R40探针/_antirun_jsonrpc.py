# -*- coding: utf-8 -*-
"""
_antirun_jsonrpc.py —— 任务4（SDK 协议域 / NDJSON JSON-RPC 传输层）反跑判据。

对 src/JSONRPC传输.light 做字节级备份 → 定点篡改 → 跑 examples/test_JSONRPC传输.light：
  A：响应帧判别改错（id+method 被提前判为「仅 id → 响应」）→ 测试应红；恢复 → 绿
  B：非法行忽略改抛错（JSON 解析失败行改为向外抛错）→ 测试应红；恢复 → 绿
  C：增量解码半行合并改错（无换行残块被当作完整帧吐出）→ 测试应红；恢复 → 绿
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src", "JSONRPC传输.light")
TEST = os.path.join("examples", "test_JSONRPC传输.light")

env = dict(os.environ)
env["LIGHT_MERGE"] = r"G:\dswork\duan-light-merge\light-merge"


def run_test():
    """跑一次本路新增测试；返回退出码。"""
    p = subprocess.run(
        [sys.executable, "运行.py", TEST],
        cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8",
    )
    return p.returncode, p.stdout, p.stderr


# ---- 三个判据：(名称, 旧文本, 新文本) ----
CASES = [
    (
        "A-响应帧判别改错",
        "  如果 有标识 且 有方法:\n"
        "    返回 \"请求\"\n"
        "  如果 有标识:\n"
        "    返回 \"响应\"\n",
        "  如果 有标识:\n"
        "    返回 \"响应\"\n"
        "  如果 有标识 且 有方法:\n"
        "    返回 \"请求\"\n",
    ),
    (
        "B-非法行忽略改抛错",
        "    尝试:\n"
        "      设 消息 为 解析JSON(行)\n"
        "    捕获 错误:\n"
        "      返回\n",
        "    尝试:\n"
        "      设 消息 为 解析JSON(行)\n"
        "    捕获 错误:\n"
        "      抛出 错误\n",
    ),
    (
        "C-增量半行合并改错",
        "      设 边界 为 查找子串(己.待定, \"\\n\")\n"
        "      如果 边界 < 0:\n"
        "        设 进行 为 假\n",
        "      设 边界 为 查找子串(己.待定, \"\\n\")\n"
        "      如果 边界 < 0:\n"
        "        行表.追加(己.待定)\n"
        "        己.待定 为 \"\"\n"
        "        设 进行 为 假\n",
    ),
]


def main():
    with open(SRC, "rb") as f:
        original = f.read()

    # 先确认基线绿
    base_rc, base_out, _ = run_test()
    print(f"[基线] 未篡改测试 rc={base_rc}")
    assert base_rc == 0, f"基线应绿，实际 rc={base_rc}\n{base_out}"

    results = []
    try:
        for name, old, new in CASES:
            text = original.decode("utf-8")
            assert text.count(old) == 1, f"[{name}] 锚点不唯一或缺失，count={text.count(old)}"
            corrupted = text.replace(old, new)
            with open(SRC, "wb") as f:
                f.write(corrupted.encode("utf-8"))

            bad_rc, bad_out, bad_err = run_test()
            red_ok = bad_rc != 0
            print(f"[{name}] 篡改后测试 rc={bad_rc} （期望非0=红）{'OK' if red_ok else '!!未变红!!'}")

            # 恢复字节
            with open(SRC, "wb") as f:
                f.write(original)
            good_rc, good_out, _ = run_test()
            green_ok = good_rc == 0
            print(f"[{name}] 恢复后测试 rc={good_rc} （期望0=绿）{'OK' if green_ok else '!!未恢复!!'}")

            results.append((name, red_ok, green_ok))
    finally:
        # 兜底恢复
        with open(SRC, "wb") as f:
            f.write(original)

    print("=" * 50)
    all_ok = True
    for name, red_ok, green_ok in results:
        mark = "PASS" if (red_ok and green_ok) else "FAIL"
        if mark == "FAIL":
            all_ok = False
        print(f"  {name}: 红={'是' if red_ok else '否'} 绿={'是' if green_ok else '否'} -> {mark}")

    if not all_ok:
        print("反跑失败！")
        sys.exit(1)
    print("全部反跑判据通过（篡改→红，恢复→绿）")


if __name__ == "__main__":
    main()
