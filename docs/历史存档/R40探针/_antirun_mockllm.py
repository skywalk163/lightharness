# -*- coding: utf-8 -*-
"""
_task6 反跑判据（_antirun_mockllm.py）
=====================================
对 src/mock大模型服务器.light 做字节级备份/恢复，逐项注入「错误实现」，
跑 examples/test_mock大模型服务器.light，断言：注入后变红（rc != 0），
恢复后变绿（rc == 0）。

判据：
  A 行为消费顺序改错（FIFO → LIFO）：消费脚本 取序列[光标] 改为 序列[末-光标]。
  B SSE [DONE] 结尾去掉：完成帧体 返回 "data: [DONE]\\n\\n" 改为 返回 ""。
  C 随机权重种子忽略：播种随机.构造 己.状态 = 种子 % M 改为 己.状态 = 0。

用法：python _antirun_mockllm.py
退出码 0 = 三判据全部红→恢复→绿；非 0 = 有判据未按预期反转。
"""
import os
import sys
import shutil
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src", "mock大模型服务器.light")
TEST = ["python", "运行.py", "examples/test_mock大模型服务器.light"]

# (名称, 原始片段, 注入片段)。片段必须在源文件中唯一出现一次。
CASES = [
    (
        "A_FIFO改LIFO",
        "设 选中 为 己.序列[索引]",
        "设 选中 为 己.序列[长(己.序列) - 1 - 索引]",
    ),
    (
        "B_去掉DONE",
        '返回 "data: [DONE]\\n\\n"',
        '返回 ""',
    ),
    (
        "C_忽略随机种子",
        "己.状态 为 种子 % 4294967296",
        "己.状态 为 0",
    ),
]


def run_test():
    """跑测试，返回 (rc, 是否通过, stderr文本)。"""
    env = dict(os.environ)
    env["LIGHT_MERGE"] = r"G:\dswork\duan-light-merge\light-merge"
    proc = subprocess.run(
        TEST, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    return proc.returncode, (proc.returncode == 0), (proc.stdout or "") + (proc.stderr or "")


def main():
    if not os.path.isfile(SRC):
        print(f"找不到源文件: {SRC}")
        return 2

    original = open(SRC, "rb").read()  # 字节级备份
    tmp_bak = SRC + ".antirun.bak"
    with open(tmp_bak, "wb") as f:
        f.write(original)

    failures = []
    try:
        for name, old, new in CASES:
            text = original.decode("utf-8")
            cnt = text.count(old)
            if cnt != 1:
                failures.append(f"[{name}] 锚点片段出现 {cnt} 次（期望 1），未执行注入")
                continue
            mutated = text.replace(old, new, 1)

            # 注入
            with open(SRC, "w", encoding="utf-8", newline="") as f:
                f.write(mutated)
            rc_red, ok_red, _ = run_test()

            # 恢复（字节级）
            with open(SRC, "wb") as f:
                f.write(original)
            rc_green, ok_green, proc_green_err = run_test()

            status = "OK"
            if ok_red:
                status = "FAIL(注入后仍绿，未反到红)"
                failures.append(name + " 注入后未变红")
            if not ok_green:
                status = "FAIL(恢复后仍红)"
                failures.append(name + " 恢复后未变绿")
                print("    [恢复后仍红] stderr 尾段:")
                print(proc_green_err)
            print(f"  {name}: 注入后 rc={rc_red} (红={not ok_red}), 恢复后 rc={rc_green} (绿={ok_green}) -> {status}")
    finally:
        # 兜底字节级恢复
        with open(SRC, "wb") as f:
            f.write(original)
        if os.path.exists(tmp_bak):
            os.remove(tmp_bak)

    print("-" * 50)
    if failures:
        print("反跑未全部达标：")
        for x in failures:
            print("  -", x)
        return 1
    print("三判据全部 红→恢复→绿 通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
