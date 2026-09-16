# _antirun_t1_词法核心.py —— 第19轮任务1 反跑脚本（L-084 / L-092 / L-137）
# 判据：A=修复后绿（3个复现用例 rc=0）
#       B=边界（独立`为`/`返回`仍作关键字；`为了`/`行为`/`作为`/`成为`/`认为`作整体标识符）
#       C=变异（撤掉本轮新增的嵌入最大匹配分支）→ L-084 立红（证明修复必要），
#                         L-092/L-137 仍绿（证明由既有复合词硬化独立保护，作回归用例）
# 铁律：BASE 自定位；变异落点在 light-merge/src/lexer.py，原地改后 sha256 校验恢复；不落备份到仓库。

import os
import sys
import hashlib
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
LIGHT_MERGE = os.path.normpath(os.path.join(BASE, "..", "light-merge"))
LEXER = os.path.join(LIGHT_MERGE, "src", "lexer.py")
PY = r"C:\Users\skywalk\.workbuddy\binaries\python\versions\3.13.12\python.exe"
RUNNER = os.path.join(BASE, "运行.py")

TEST_L084 = os.path.join(BASE, "examples", "test_L084.light")
TEST_L092 = os.path.join(BASE, "examples", "test_L092.light")
TEST_L137 = os.path.join(BASE, "examples", "test_L137.light")

# 变异锚点（任务1 新增的嵌入最大匹配集合定义）
ANCHOR = "_EMBED_MAX_MATCH_KEYWORDS = frozenset({'为', '返回', '尝试'})"
ANCHOR_OFF = "_EMBED_MAX_MATCH_KEYWORDS = frozenset()"


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def run_test(test_path):
    env = dict(os.environ)
    env["LIGHT_MERGE"] = LIGHT_MERGE
    p = subprocess.run([PY, "-u", RUNNER, test_path],
                       cwd=BASE, capture_output=True, text=True, encoding="utf-8", env=env)
    return p.returncode, p.stdout + p.stderr


def run_src(src, label):
    """在 lightharness 根目录写临时边界用例并运行，结束后删除。"""
    tmp = os.path.join(BASE, "_tmp_t1_boundary.light")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(src)
    try:
        env = dict(os.environ)
        env["LIGHT_MERGE"] = LIGHT_MERGE
        p = subprocess.run([PY, "-u", RUNNER, tmp],
                           cwd=BASE, capture_output=True, text=True, encoding="utf-8", env=env)
        return p.returncode, p.stdout + p.stderr
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def main():
    with open(LEXER, "rb") as f:
        raw = f.read()
    orig_sha = sha256_of(LEXER)
    original = raw.decode("utf-8")
    if ANCHOR not in original:
        print("【前置检查】未找到变异锚点：%s" % ANCHOR)
        raise SystemExit(1)

    # ===== A 判据：干净运行 3 用例必须全绿 =====
    for name, t in (("L-084", TEST_L084), ("L-092", TEST_L092), ("L-137", TEST_L137)):
        rc, out = run_test(t)
        if rc != 0:
            print("【A 判据】%s 应 PASS，实际 FAIL：" % name)
            print(out[-1500:])
            raise SystemExit(1)
        print("【A 判据】%s PASS  OK" % name)
    print("【A 判据】3 用例全绿  OK")

    # ===== B 判据：边界用例 =====
    b_src = (
        "段落 主:\n"
        "    设 为了 为 1\n"          # 为在开头，整串标识符
        "    设 行为 为 2\n"          # 为在词尾，整串标识符
        "    设 作为 为 3\n"          # 为在中间，整串标识符
        "    设 成为 为 4\n"
        "    设 认为 为 5\n"
        "    设 甲 为 10\n"           # 独立 为 仍作赋值关键字
        "    段落 取 接收 值:\n"      # 独立 返回 仍作返回关键字
        "        返回 值\n"
        "    打印(为了)\n"            # 期望 1
        "    打印(行为)\n"            # 期望 2
        "    打印(作为)\n"            # 期望 3
        "    打印(成为)\n"            # 期望 4
        "    打印(认为)\n"            # 期望 5
        "    打印(甲)\n"              # 期望 10
        "    打印(取(99))\n"          # 期望 99
    )
    rc_b, out_b = run_src(b_src, "边界")
    if rc_b != 0:
        print("【B 判据】边界用例应 PASS，实际 FAIL：")
        print(out_b[-2000:])
        raise SystemExit(1)
    print("【B 判据】边界用例 PASS  OK（独立 为/返回 仍作关键字；为了/行为/作为/成为/认为 作整体标识符）")

    # ===== C 判据：撤掉本轮修复分支 =====
    mutated = original.replace(ANCHOR, ANCHOR_OFF, 1)
    if mutated == original:
        print("【C 判据】变异失败：锚点替换无效")
        raise SystemExit(1)
    with open(LEXER, "wb") as f:
        f.write(mutated.encode("utf-8"))

    rc084m, _ = run_test(TEST_L084)
    rc092m, _ = run_test(TEST_L092)
    rc137m, _ = run_test(TEST_L137)

    # 恢复（无论 C 判据结果都先恢复，避免污染仓库）
    with open(LEXER, "wb") as f:
        f.write(raw)
    restored_sha = sha256_of(LEXER)
    if restored_sha != orig_sha:
        print("【恢复校验】sha256 不一致！原始=%s 恢复=%s" % (orig_sha, restored_sha))
        raise SystemExit(1)

    ok = True
    if rc084m == 0:
        print("【C 判据】L-084 变异后仍 PASS，未立红！")
        ok = False
    else:
        print("【C 判据】L-084 变异后立红  OK（证明本轮修复必要）")
    if rc092m != 0:
        print("【C 判据】L-092 变异后意外 FAIL（本应由既有硬化独立保护）")
        ok = False
    else:
        print("【C 判据】L-092 变异后仍绿  OK（既有复合词硬化独立保护，作回归用例）")
    if rc137m != 0:
        print("【C 判据】L-137 变异后意外 FAIL（本应由既有硬化独立保护）")
        ok = False
    else:
        print("【C 判据】L-137 变异后仍绿  OK（既有复合词硬化独立保护，作回归用例）")

    if not ok:
        raise SystemExit(1)

    print("【恢复校验】sha256 一致  OK（%s）" % restored_sha)

    # 恢复后再次确认 3 用例全绿
    for name, t in (("L-084", TEST_L084), ("L-092", TEST_L092), ("L-137", TEST_L137)):
        rc, _ = run_test(t)
        if rc != 0:
            print("【恢复后】%s 应为 PASS，实际 FAIL" % name)
            raise SystemExit(1)
    print("【恢复后】3 用例全绿  OK")

    print("ANTIRUN T1 ALL OK")


if __name__ == "__main__":
    main()
