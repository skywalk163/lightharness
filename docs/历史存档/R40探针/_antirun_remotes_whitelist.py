# _antirun_remotes_whitelist.py —— 任务2 反跑判据脚本（字节级备份/恢复）
#
# 反跑判据：
#   A：白名单删掉 1 条（approval/request）→ 该条断言红；恢复 → 绿
#   B：某条模式改错（approval/request: waterfall → emit）→ 断言红；恢复 → 绿
#
# 用法：python _antirun_remotes_whitelist.py
# 退出码：全部成立 → 0；任一不成立 → 非 0

import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIGHT_MERGE = r"G:\dswork\duan-light-merge\light-merge"
os.environ.setdefault("LIGHT_MERGE", LIGHT_MERGE)

SRC = os.path.join(HERE, "src", "远端总线.light")
TEST = os.path.join(HERE, "examples", "test_远端白名单.light")
BACKUP = os.path.join(HERE, "_antirun_远端总线.bak")


def run_test():
    """运行 test_远端白名单，返回 (是否通过, 输出)。绿=无'错误'/'断言失败'/'解析错误'。"""
    proc = subprocess.run(
        [sys.executable, "运行.py", TEST],
        cwd=HERE,
        capture_output=True,
        text=True,
    )
    out = proc.stdout + proc.stderr
    failed = ("错误" in out) or ("断言失败" in out) or ("解析错误" in out)
    return (not failed), out


def read_src():
    with open(SRC, encoding="utf-8") as f:
        return f.read()


def write_src(text):
    with open(SRC, "wb") as f:
        f.write(text.encode("utf-8"))


def backup():
    shutil.copyfile(SRC, BACKUP)


def restore():
    if os.path.exists(BACKUP):
        shutil.copyfile(BACKUP, SRC)
        os.remove(BACKUP)


def check(label, cond):
    status = "✅ 成立" if cond else "❌ 不成立"
    print(f"  [{label}] {status}")
    return cond


def main():
    print("=== 反跑判据：远端总线 转发白名单 ===")
    backup()
    try:
        overall = True

        # 基线：原始应绿
        ok, _ = run_test()
        overall &= check("基线（原始）应绿", ok)

        # A：删除 approval/request 一条
        src = read_src()
        # 删掉整行（含尾逗号），并修正前一条尾逗号以避免尾逗号语法错误
        pat = re.compile(r'\s*"approval/request": "waterfall",\n')
        if pat.search(src):
            # 删除目标行，并把上一行 "agent-preset/selected": "emit", 的逗号去掉（成为新尾）
            src_a = src.replace('    "agent-preset/selected": "emit",\n', '    "agent-preset/selected": "emit"\n')
            src_a = src_a.replace('    "approval/request": "waterfall",\n', '')
            write_src(src_a)
            ok_a, _ = run_test()
            overall &= check("A（删 approval/request）→ 应红", not ok_a)
        else:
            overall &= check("A（删 approval/request）→ 应红", False)

        # 恢复后再改 B
        restore()
        backup()
        src = read_src()
        # B：approval/request 模式 waterfall → emit（不改逗号，纯值替换）
        if '"approval/request": "waterfall"' in src:
            src_b = src.replace('"approval/request": "waterfall"', '"approval/request": "emit"')
            write_src(src_b)
            ok_b, _ = run_test()
            overall &= check("B（approval/request 模式改错）→ 应红", not ok_b)
        else:
            overall &= check("B（approval/request 模式改错）→ 应红", False)

        # 恢复 → 绿
        restore()
        ok2, _ = run_test()
        overall &= check("恢复后 → 应绿", ok2)
    finally:
        restore()
        if os.path.exists(BACKUP):
            os.remove(BACKUP)

    print("==== 反跑结果：", "全部成立 ✅" if overall else "存在不成立 ❌", "====")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
