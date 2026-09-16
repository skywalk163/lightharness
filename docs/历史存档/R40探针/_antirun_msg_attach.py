# -*- coding: utf-8 -*-
"""第11轮 任务1（消息/附件域）反跑判据脚本。

判据（≥2 项，均字节级备份/恢复 src）：
  A. src/消息.light：System 词表角色名改错（"system"→"System"）
     → examples/test_消息_System.light 应红（rc!=0）；恢复后应绿（rc==0）。
  B. src/附件准入.light：去掉通用文件空串「非规范 base64 容错」（accept→reject，严格解码）
     → examples/test_附件_通用文件.light 应红（rc!=0）；恢复后应绿（rc==0）。

脚本仅在临时字节副本上做精确字符串替换，跑用例前必改、跑完必恢复（finally 兜底）。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(ROOT, "运行.py")
LIGHT_MERGE = r"G:\dswork\duan-light-merge\light-merge"

MSG = os.path.join(ROOT, "src", "消息.light")
ATTACH = os.path.join(ROOT, "src", "附件准入.light")

TEST_SYS = os.path.join(ROOT, "examples", "test_消息_System.light")
TEST_FILE = os.path.join(ROOT, "examples", "test_附件_通用文件.light")


def run_case(path):
    env = dict(os.environ)
    env["LIGHT_MERGE"] = LIGHT_MERGE
    p = subprocess.run(
        [sys.executable, RUNNER, path],
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
    )
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def check(name, path, old, new, test_path, expect_label):
    """对 path 做 old→new 字节替换，跑 test_path：先期望红，恢复后期望绿。"""
    print("=" * 60)
    print(f"[{name}] 注入缺陷：{expect_label}")
    with open(path, "rb") as f:
        original = f.read()
    old_b, new_b = old.encode("utf-8"), new.encode("utf-8")
    assert original.count(old_b) == 1, f"[{name}] 目标串不唯一（count={original.count(old_b)}），中止"
    try:
        corrupted = original.replace(old_b, new_b, 1)
        with open(path, "wb") as f:
            f.write(corrupted)
        rc_red, out_red = run_case(test_path)
        if rc_red == 0:
            print(f"  注入后仍绿（rc=0）——反跑无效！输出尾:\n{out_red[-400:]}")
            return False
        print(f"  注入后红（rc={rc_red}）✓ 符合预期")
    finally:
        with open(path, "wb") as f:
            f.write(original)
        print(f"  已字节级恢复 {os.path.basename(path)}")

    rc_green, out_green = run_case(test_path)
    if rc_green != 0:
        print(f"  恢复后仍红（rc={rc_green}）——恢复失败！输出尾:\n{out_green[-400:]}")
        return False
    print(f"  恢复后绿（rc=0）✓ 反跑通过")
    return True


def main():
    results = []

    # A：System 词表角色名 "system" → "System"
    results.append(("A", check(
        "A", MSG,
        '"role": "system"', '"role": "System"',
        TEST_SYS, "System 词表角色名改错",
    )))

    # B：通用文件空串容错 accept → reject（严格解码）
    results.append(("B", check(
        "B", ATTACH,
        '解码校验(数据, "accept", "INVALID_FILE_BASE64")',
        '解码校验(数据, "reject", "INVALID_FILE_BASE64")',
        TEST_FILE, "去掉文件空串 base64 容错",
    )))

    print("=" * 60)
    passed = sum(1 for _, ok in results if ok)
    for tag, ok in results:
        print(f"  判据 {tag}: {'PASS' if ok else 'FAIL'}")
    print(f"反跑汇总：{passed}/{len(results)} 通过")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
