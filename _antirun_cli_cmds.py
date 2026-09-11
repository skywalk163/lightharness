# -*- coding: utf-8 -*-
"""第7轮任务1 反跑判据：_antirun_cli_cmds.py

判据（改反即红）：
  A. 把 dump-config 的「来源」标注常量改错（"内置默认 取默认模型()" → "内置默认"）
     → examples/test_CLI命令面.light 必须 rc!=0（来源标注被断言抓住）
  B. 把未知命令的退出码改 0（删掉 主 里的 抛出，改打印）
     → 子进程 HARNESS_CMD=bogus 跑 CLI 必须 rc!=0 的断言翻红
  C. 把 版本号 常量改错（"0.1.5-lh" → "0.1.5"）→ test_CLI命令面 必须 rc!=0

用法：python _antirun_cli_cmds.py   （退出码 0 = 三项判据均成立）
源文件以字节级备份/恢复，不改 git 状态。
"""
import io
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(ROOT, "运行.py")
ENTRY = os.path.join(ROOT, "src", "总入口.light")
CLI = os.path.join(ROOT, "examples", "运行CLI.light")
TEST = os.path.join(ROOT, "examples", "test_CLI命令面.light")
# 无 .env 的干净 cwd，避免 run 分支碰真实密钥/会话根
CLEAN_CWD = os.path.join(ROOT, "_w3_probe")

# A: 来源标注常量（dump-config 唯一逐字来源文案）
A_OLD = '  返回 "内置默认 取默认模型()"'
A_NEW = '  返回 "内置默认"'
# B: 未知命令必须非零退出（抛异常 → 进程非零）
B_OLD = '    抛出 "未知命令: " + 命令 + "（设 HARNESS_CMD 为 help 查看命令列表）"'
B_NEW = '    打印 "未知命令: " + 命令'
# C: 版本号常量
C_OLD = '设 版本号 为 "0.1.5-lh"'
C_NEW = '设 版本号 为 "0.1.5"'


def _read(p):
    with io.open(p, encoding="utf-8", newline="") as f:
        return f.read()


def _write(p, s):
    with io.open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def _run_test():
    r = subprocess.run([sys.executable, RUNNER, TEST],
                       cwd=ROOT, capture_output=True, text=True, timeout=600)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def _run_bogus_cmd():
    """子进程跑 CLI，HARNESS_CMD=bogus：正常实现必须非零退出。"""
    env = dict(os.environ)
    env["HARNESS_CMD"] = "bogus"
    r = subprocess.run([sys.executable, RUNNER, CLI],
                       cwd=CLEAN_CWD if os.path.isdir(CLEAN_CWD) else ROOT,
                       capture_output=True, text=True, timeout=300, env=env)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def check_cli_test():
    """断言 test_CLI命令面 通过。返回 (期望是否满足, rc, 输出)。"""
    rc, out = _run_test()
    return rc == 0, rc, out


def check_unknown_cmd_nonzero():
    """断言未知命令非零退出。返回 (期望是否满足, rc, 输出)。"""
    rc, out = _run_bogus_cmd()
    return rc != 0, rc, out


def flip(path, old, new, tag, check):
    """翻转 → 跑断言(应失败=改反即红) → 恢复 → 再跑断言(应回绿)。"""
    backup = _read(path)
    if old not in backup:
        print(f"[{tag}] 失败：未找到目标片段，脚本与源码不同步")
        return False
    passed, rc, out = check()
    if not passed:
        print(f"[{tag}] 失败：翻转前断言已红(rc={rc})，基线不可信")
        _write(path, backup)
        return False
    try:
        _write(path, backup.replace(old, new, 1))
        passed_red, rc_red, out_red = check()
        ok = not passed_red
        print(f"[{tag}] 翻转后 rc={rc_red} → {'判据成立(改反即红)' if ok else '判据不成立(仍绿!)'}")
        if not ok:
            print(f"    改反后仍绿的输出尾部: {out_red.strip()[-200:]}")
        return ok
    finally:
        _write(path, backup)
        passed_green, rc_green, _ = check()
        print(f"[{tag}] 恢复后 rc={rc_green} → {'源码已还原并回绿' if passed_green else '警告: 恢复后仍红!'}")


def main():
    if not os.path.isdir(CLEAN_CWD):
        os.makedirs(CLEAN_CWD, exist_ok=True)
    results = [
        flip(ENTRY, A_OLD, A_NEW, "A dump-config来源标注改错", check_cli_test),
        flip(ENTRY, B_OLD, B_NEW, "B 未知命令退出码改0", check_unknown_cmd_nonzero),
        flip(ENTRY, C_OLD, C_NEW, "C 版本号常量改错", check_cli_test),
    ]
    print()
    if all(results):
        print(f"反跑判据全部成立：{sum(results)}/{len(results)} 改反即红")
        return 0
    print(f"反跑判据未全过：{sum(results)}/{len(results)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
