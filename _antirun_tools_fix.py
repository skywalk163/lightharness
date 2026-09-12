#!/usr/bin/env python3
"""
反跑判据 (antirun) — 工具域修复（第9轮任务3）
================================================
对 examples/test_修复_工具.light 中的关键断言做字节级变异，
然后运行测试，验证变异后测试必然失败 (rc != 0)。
每次变异后立即还原原始字节。

变异项 (4):
  A1. S1:  concludesTurn 传播断言 真 → 假（验证传播确实为真）
  A2. S5:  错误路径 concludesTurn 断言 假 → 真（验证错误路径确实为假）
  B1. S9:  未显式传策略默认 exclusive → parallel（验证默认确实为 exclusive）
  B2. S10: 未知工具默认 exclusive → parallel（验证未知工具确实为 exclusive）
"""

import subprocess
import sys
import os

TEST_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "examples", "test_修复_工具.light"
)
RUNNER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "运行.py"
)

# 变异项: (描述, 原始字节片段, 变异字节片段)
# 使用 .encode("utf-8") 避免手写字节字面量
def m(desc, old, new):
    return (desc, old.encode("utf-8"), new.encode("utf-8"))

MUTATIONS = [
    # A1: S1 concludesTurn 传播为真 → 改成期望假，测试应失败
    m(
        "A1 S1: concludesTurn 传播断言 真→假",
        '断言等于(结果1["concludesTurn"], 真, "S1 concludesTurn 传播为真")',
        '断言等于(结果1["concludesTurn"], 假, "S1 concludesTurn 传播为真")',
    ),
    # A2: S5 错误路径 concludesTurn=假 → 改成期望真，测试应失败
    m(
        "A2 S5: 错误路径 concludesTurn 断言 假→真",
        '断言等于(结果5["concludesTurn"], 假, "S5 错误路径 concludesTurn=假")',
        '断言等于(结果5["concludesTurn"], 真, "S5 错误路径 concludesTurn=假")',
    ),
    # B1: S9 未显式传策略默认 exclusive → 改成期望 parallel，测试应失败
    m(
        "B1 S9: 默认策略断言 exclusive→parallel",
        '断言等于(注册表T4.执行策略("implicit"), "exclusive", "S9 未显式传策略默认 exclusive")',
        '断言等于(注册表T4.执行策略("implicit"), "parallel", "S9 未显式传策略默认 exclusive")',
    ),
    # B2: S10 未知工具默认 exclusive → 改成期望 parallel，测试应失败
    m(
        "B2 S10: 未知工具策略断言 exclusive→parallel",
        '断言等于(注册表T4.执行策略("不存在"), "exclusive", "S10 未知工具默认 exclusive")',
        '断言等于(注册表T4.执行策略("不存在"), "parallel", "S10 未知工具默认 exclusive")',
    ),
]


def run_test():
    """运行测试，返回 returncode."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, RUNNER, TEST_FILE],
        capture_output=True,
        timeout=60,
        env=env,
    )
    return proc.returncode


def main():
    # 1. 读取原始字节
    with open(TEST_FILE, "rb") as f:
        original_bytes = f.read()

    print(f"反跑判据: 工具域修复（第9轮任务3）")
    print(f"测试文件: {TEST_FILE}")
    print(f"原始大小: {len(original_bytes)} bytes")
    print(f"变异项数: {len(MUTATIONS)}")
    print()

    all_red = True
    for i, (desc, old_frag, new_frag) in enumerate(MUTATIONS, 1):
        # 2. 验证原始片段存在
        if old_frag not in original_bytes:
            print(f"  [{i}] 跳过: 原始片段未找到 — {desc}")
            all_red = False
            continue

        # 3. 应用变异
        mutated_bytes = original_bytes.replace(old_frag, new_frag, 1)
        with open(TEST_FILE, "wb") as f:
            f.write(mutated_bytes)

        # 4. 运行测试
        rc = run_test()

        # 5. 还原原始字节
        with open(TEST_FILE, "wb") as f:
            f.write(original_bytes)

        # 6. 判定
        if rc != 0:
            print(f"  [{i}] RED (rc={rc}) — {desc}")
        else:
            print(f"  [{i}] GREEN (rc=0) 变异未导致失败! — {desc}")
            all_red = False

    print()
    if all_red:
        print("结果: ALL RED — 反跑判据通过")
        sys.exit(0)
    else:
        print("结果: NOT ALL RED — 反跑判据失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
