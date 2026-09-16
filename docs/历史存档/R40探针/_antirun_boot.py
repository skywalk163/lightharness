# -*- coding: utf-8 -*-
"""
_antirun_boot.py —— 任务5（启动配置域 / boot profile + patch 层组合 + cmdline）反跑判据。

对 src/启动配置.light 做字节级备份 → 定点篡改 → 跑 examples/test_启动配置.light：
  A：composeEntries 顺序反转（layers 倒序叠加）→ 测试应红；恢复 → 绿
  B：profile 目录解析默认路径改错（去掉 profiles 段）→ 测试应红；恢复 → 绿
  C：命令行 --patch 收集改错（覆盖而非追加）→ 测试应红；恢复 → 绿
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src", "启动配置.light")
TEST = os.path.join("examples", "test_启动配置.light")

env = dict(os.environ)
env["LIGHT_MERGE"] = r"G:\\dswork\\duan-light-merge\\light-merge"


def run_test():
    p = subprocess.run(
        [sys.executable, "运行.py", TEST],
        cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8",
    )
    return p.returncode, p.stdout, p.stderr


# ---- 三个判据：(名称, 旧文本, 新文本) ----
CASES = [
    (
        "A-composeEntries顺序反转",
        "  遍历 层 之 layers:\n"
        "    遍历 补丁 之 层:\n"
        "      如果 是字典(补丁) == 假:\n"
        "        抛出 \"each patch must be an object\"\n"
        "      应用补丁(补丁, 顺序表, 索引表)\n"
        "  返回 顺序表\n",
        "  设 反转层 为 []\n"
        "  设 i 为 长(layers) - 1\n"
        "  当 i >= 0:\n"
        "    反转层.追加(layers[i])\n"
        "    设 i 为 i - 1\n"
        "  遍历 层 之 反转层:\n"
        "    遍历 补丁 之 层:\n"
        "      如果 是字典(补丁) == 假:\n"
        "        抛出 \"each patch must be an object\"\n"
        "      应用补丁(补丁, 顺序表, 索引表)\n"
        "  返回 顺序表\n",
    ),
    (
        "B-profile目录解析去掉profiles段",
        "  返回 主目录路径(主目录, [资料夹名, 名称], 配置, 环境)\n",
        "  返回 主目录路径(主目录, [名称], 配置, 环境)\n",
    ),
    (
        "C-patch收集改覆盖非追加",
        "      patches.追加(路径值)\n",
        "      设 patches 为 [路径值]\n",
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
            if not red_ok:
                print(f"  --- stdout ---\n{bad_out[-800:]}")

            # 恢复字节
            with open(SRC, "wb") as f:
                f.write(original)
            good_rc, good_out, _ = run_test()
            green_ok = good_rc == 0
            print(f"[{name}] 恢复后测试 rc={good_rc} （期望0=绿）{'OK' if green_ok else '!!未恢复!!'}")

            results.append((name, red_ok, green_ok))
    finally:
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
