# -*- coding: utf-8 -*-
"""第5轮任务1 反跑判据：_antirun_default_model.py

判据（改反即红）：
  A. 把 src/总入口.light 模型解析链兜底 改回 "deepseek-chat" → test_入口默认模型 必须 rc=1
  B. 把 src/令牌计量.light 单价表去掉 deepseek-flash → test_入口默认模型 必须 rc=1

用法：python _antirun_default_model.py   （退出码 0 = 两项判据均成立）
源文件以字节级备份/恢复，不改 git 状态。
"""
import io
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(ROOT, "运行.py")
TEST = os.path.join(ROOT, "examples", "test_入口默认模型.light")

ENTRY = os.path.join(ROOT, "src", "总入口.light")
METER = os.path.join(ROOT, "src", "令牌计量.light")

FALLBACK_OLD = "  返回 取默认模型()"
FALLBACK_NEW = '  返回 "deepseek-chat"'
PRICE_OLD = '"deepseek-flash": [0.27, 1.10], '
PRICE_NEW = ""


def _read(p):
    with io.open(p, encoding="utf-8", newline="") as f:
        return f.read()


def _write(p, s):
    with io.open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def _run_test():
    r = subprocess.run([sys.executable, RUNNER, TEST],
                       cwd=ROOT, capture_output=True, text=True, timeout=300)
    return r.returncode


def flip(path, old, new, tag):
    """翻转 → 断言红 → 恢复。返回 True 表示判据成立（改反后确实红了）。"""
    backup = _read(path)
    if old not in backup:
        print(f"[{tag}] 失败：未找到目标片段，脚本与源码不同步")
        return False
    try:
        _write(path, backup.replace(old, new, 1))
        rc = _run_test()
        ok = rc != 0
        print(f"[{tag}] 翻转后 rc={rc} → {'判据成立(改反即红)' if ok else '判据不成立(仍绿!)'}")
        return ok
    finally:
        _write(path, backup)
        # 恢复后复核用例回绿
        rc = _run_test()
        print(f"[{tag}] 恢复后 rc={rc} → {'源码已还原' if rc == 0 else '警告: 恢复后仍红!'}")


def main():
    results = [
        flip(ENTRY, FALLBACK_OLD, FALLBACK_NEW, "A 入口兜底改回deepseek-chat"),
        flip(METER, PRICE_OLD, PRICE_NEW, "B 单价表去掉deepseek-flash"),
    ]
    print()
    if all(results):
        print("反跑判据全部成立：2/2 改反即红")
        return 0
    print(f"反跑判据未全过：{sum(results)}/2")
    return 1


if __name__ == "__main__":
    sys.exit(main())
