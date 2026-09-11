#!/usr/bin/env python3
"""
反跑判据 (antirun) — 代理循环行为对照
=====================================
对 examples/test_行为对照_代理循环.light 中的关键断言做字节级变异，
然后运行测试，验证变异后测试必然失败 (rc != 0)。
每次变异后立即还原原始字节。

变异项 (>= 2):
  1. S5:  max-tokens 种类 "max-tokens" → "completed"
  2. S8:  客户端异常种类 "error" → "completed"
  3. S16: 并行工具调用数 2 → 99
  4. S18: 轮次开始事件数 1 → 99
"""

import subprocess
import sys
import os

TEST_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "examples", "test_行为对照_代理循环.light"
)
RUNNER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "运行.py"
)

# 变异项: (描述, 原始字节片段, 变异字节片段)
MUTATIONS = [
    (
        "S5: max-tokens 种类断言 max-tokens → completed",
        b'\xe6\x96\xad\xe8\xa8\x80\xe7\x9b\xb8\xe7\xad\x89(\xe7\xbb\x93\xe6\x9e\x9c5["\xe7\xa7\x8d\xe7\xb1\xbb"], "max-tokens"',
        b'\xe6\x96\xad\xe8\xa8\x80\xe7\x9b\xb8\xe7\xad\x89(\xe7\xbb\x93\xe6\x9e\x9c5["\xe7\xa7\x8d\xe7\xb1\xbb"], "completed"',
    ),
    (
        "S8: 客户端异常种类断言 error → completed",
        b'\xe6\x96\xad\xe8\xa8\x80\xe7\x9b\xb8\xe7\xad\x89(\xe7\xbb\x93\xe6\x9e\x9c8["\xe7\xa7\x8d\xe7\xb1\xbb"], "error"',
        b'\xe6\x96\xad\xe8\xa8\x80\xe7\x9b\xb8\xe7\xad\x89(\xe7\xbb\x93\xe6\x9e\x9c8["\xe7\xa7\x8d\xe7\xb1\xbb"], "completed"',
    ),
    (
        "S16: 并行工具调用数 2 → 99",
        b'\xe6\x96\xad\xe8\xa8\x80\xe7\x9b\xb8\xe7\xad\x89(\xe9\x95\xbf\xe5\xba\xa6(\xe5\xb7\xa5\xe5\x85\xb7\xe8\xb0\x83\xe7\x94\xa8\xe8\xa1\xa8), 2,',
        b'\xe6\x96\xad\xe8\xa8\x80\xe7\x9b\xb8\xe7\xad\x89(\xe9\x95\xbf\xe5\xba\xa6(\xe5\xb7\xa5\xe5\x85\xb7\xe8\xb0\x83\xe7\x94\xa8\xe8\xa1\xa8), 99,',
    ),
    (
        "S18: 轮次开始事件数 1 → 99",
        b'\xe6\x96\xad\xe8\xa8\x80\xe7\x9b\xb8\xe7\xad\x89(\xe9\x95\xbf\xe5\xba\xa6(\xe8\xbd\xae\xe6\xac\xa1\xe5\xbc\x80\xe5\xa7\x8b\xe8\xa1\xa8), 1,',
        b'\xe6\x96\xad\xe8\xa8\x80\xe7\x9b\xb8\xe7\xad\x89(\xe9\x95\xbf\xe5\xba\xa6(\xe8\xbd\xae\xe6\xac\xa1\xe5\xbc\x80\xe5\xa7\x8b\xe8\xa1\xa8), 99,',
    ),
]


def run_test():
    """运行测试，返回 (returncode, stdout+stderr)."""
    proc = subprocess.run(
        [sys.executable, RUNNER, TEST_FILE],
        capture_output=True,
        timeout=60,
    )
    return proc.returncode, ""


def main():
    # 1. 读取原始字节
    with open(TEST_FILE, "rb") as f:
        original_bytes = f.read()

    print(f"反跑判据: 代理循环行为对照")
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
        rc, output = run_test()

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
