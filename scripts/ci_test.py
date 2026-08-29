#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lightharness CI 统一测试入口。

职责：
  1. 检查 light-merge 编译器可用性（LIGHT_MERGE 环境变量）
  2. 运行 pytest 全量回归（tests/test_回归.py 参数化遍历 examples/*.light）
  3. 运行核心模块冒烟测试（直接调用 运行.py）
  4. 汇总结果，非零退出码表示失败

用法：
    python scripts/ci_test.py              # 全量
    python scripts/ci_test.py --quick      # 仅 pytest，跳过冒烟

环境变量：
    LIGHT_MERGE   light-merge 编译器根目录（必须，需包含 src/）
"""
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, "运行.py")

# 冒烟测试：核心模块代表性用例
SMOKE_FILES = [
    "examples/test_会话.light",
    "examples/test_代理.light",
    "examples/test_工具.light",
    "examples/test_消息.light",
    "examples/test_流.light",
]


def _log(msg):
    print(f"[CI] {msg}", flush=True)


def check_light_merge():
    """检查 light-merge 编译器是否可用。"""
    lm = os.environ.get("LIGHT_MERGE", "")
    if not lm:
        _log("错误: LIGHT_MERGE 环境变量未设置")
        _log("  示例: set LIGHT_MERGE=G:\\dswork\\duan-light-merge\\light-merge")
        return False
    if not os.path.isdir(os.path.join(lm, "src")):
        _log(f"错误: LIGHT_MERGE={lm} 下找不到 src/ 目录")
        return False
    _log(f"light-merge 编译器: {lm}")
    return True


def run_pytest():
    """运行 pytest 全量回归。"""
    _log("=== 运行 pytest 全量回归 ===")
    t0 = time.time()
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short"],
        cwd=ROOT,
    )
    elapsed = time.time() - t0
    _log(f"pytest 退出码={r.returncode}，耗时 {elapsed:.1f}s")
    return r.returncode == 0


def run_smoke():
    """运行核心模块冒烟测试。"""
    _log("=== 运行核心模块冒烟测试 ===")
    all_ok = True
    for rel in SMOKE_FILES:
        fpath = os.path.join(ROOT, rel)
        if not os.path.isfile(fpath):
            _log(f"  [跳过] {rel} 不存在")
            continue
        t0 = time.time()
        r = subprocess.run(
            [sys.executable, RUNNER, fpath],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=ROOT, timeout=120,
        )
        elapsed = time.time() - t0
        ok = r.returncode == 0
        status = "通过" if ok else "失败"
        _log(f"  [{status}] {rel} ({elapsed:.1f}s)")
        if not ok:
            all_ok = False
            tail = (r.stdout or "")[-800:] + (r.stderr or "")[-800:]
            if tail.strip():
                print(tail, flush=True)
    return all_ok


def main():
    quick = "--quick" in sys.argv
    print("=" * 60, flush=True)
    print("lightharness CI 测试", flush=True)
    print("=" * 60, flush=True)
    _log(f"项目根目录: {ROOT}")
    _log(f"Python: {sys.version.split()[0]}")
    _log(f"模式: {'快速（仅pytest）' if quick else '全量（pytest + 冒烟）'}")

    if not check_light_merge():
        sys.exit(1)

    results = {}
    results["pytest"] = run_pytest()
    if not quick:
        results["smoke"] = run_smoke()

    print()
    print("=" * 60, flush=True)
    _log("=== 结果汇总 ===")
    for name, ok in results.items():
        label = "通过" if ok else "失败"
        _log(f"  {name}: {label}")
    print("=" * 60, flush=True)

    if all(results.values()):
        _log("全部通过")
        sys.exit(0)
    else:
        _log("存在失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
