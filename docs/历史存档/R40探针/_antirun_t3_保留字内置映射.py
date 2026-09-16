# _antirun_t3_保留字内置映射.py —— 第19轮任务3 反跑脚本（L-087 / L-101 / L-143）
# 判据：A=修复后（L-087 绿；L-101/L-143 报明确保留字提示，满足"明确提示"验收分支，非静默失败）
#       B=边界（L-087 不赋值时回退真实 cwd；L-101/L-143 作前缀整体标识符可正常）
#       C=变异（撤掉 _shadows_builtin 遮蔽 → L-087 语义立红 rc!=0）→ 恢复后绿
# 铁律：BASE 自定位；变异落点在 light-merge/src/code_generator.py，原地改后 sha256 校验恢复；不落备份到仓库。

import os
import hashlib
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
LIGHT_MERGE = os.path.normpath(os.path.join(BASE, "..", "light-merge"))
CODEGEN = os.path.join(LIGHT_MERGE, "src", "code_generator.py")
PY = r"C:\Users\skywalk\.workbuddy\binaries\python\versions\3.13.12\python.exe"
RUNNER = os.path.join(BASE, "运行.py")

TEST_L087 = os.path.join(BASE, "examples", "test_L087.light")
TEST_L101 = os.path.join(BASE, "examples", "test_L101.light")
TEST_L143 = os.path.join(BASE, "examples", "test_L143.light")

# C 变异锚点：_shadows_builtin 的局部变量判定（置 False → 内置映射恒胜，遮蔽失效）
ANCHOR = "and name in self._local_variables"
ANCHOR_OFF = "and False  # T3-mutation"


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
    tmp = os.path.join(BASE, "_tmp_t3_boundary.light")
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
    with open(CODEGEN, "rb") as f:
        raw = f.read()
    orig_sha = sha256_of(CODEGEN)
    original = raw.decode("utf-8")
    if ANCHOR not in original:
        print("【前置检查】未找到变异锚点：%s" % ANCHOR)
        raise SystemExit(1)

    # ===== A 判据 =====
    rc087, out087 = run_test(TEST_L087)
    if rc087 != 0 or "/tmp" not in out087:
        print("【A 判据】L-087 应 PASS 且输出 /tmp，实际 FAIL：")
        print(out087[-1500:])
        raise SystemExit(1)
    print("【A 判据】L-087 PASS  OK（用户变量遮蔽内置映射，输出 /tmp）")

    rc101, out101 = run_test(TEST_L101)
    if rc101 == 0 or "保留关键字" not in out101:
        print("【A 判据】L-101 应报明确保留字提示（rc!=0 且含'保留关键字'），实际：")
        print(out101[-1500:])
        raise SystemExit(1)
    print("【A 判据】L-101 明确提示  OK（rc!=0，报'回调是保留关键字'）")

    rc143, out143 = run_test(TEST_L143)
    if rc143 == 0 or "保留关键字" not in out143:
        print("【A 判据】L-143 应报明确保留字提示（rc!=0 且含'保留关键字'），实际：")
        print(out143[-1500:])
        raise SystemExit(1)
    print("【A 判据】L-143 明确提示  OK（rc!=0，报'作用域是保留关键字'）")

    # ===== B 判据：边界 =====
    # B1：L-087 不赋值时回退真实 cwd（内置映射仍可用）
    rc_b1, out_b1 = run_src("段落 主:\n    打印 当前目录\n", "B1")
    cwd = os.getcwd()
    if rc_b1 != 0 or out_b1.strip() == "/tmp" or cwd.replace("\\", "/") not in out_b1.replace("\\", "/"):
        print("【B 判据】B1 不赋值时 当前目录 应回退真实 cwd，实际：")
        print(out_b1[-1000:])
        raise SystemExit(1)
    print("【B 判据】B1 回退真实 cwd  OK（内置映射未被破坏）")

    # B2：L-101/L-143 作前缀整体标识符可正常（保留字按整 token 判定，非子串）
    rc_b2, out_b2 = run_src(
        "段落 主:\n"
        "    设 回调处理器 为 空\n"
        "    打印 回调处理器\n"
        "    设 作用域表 为 {}\n"
        "    打印 作用域表\n",
        "B2")
    if rc_b2 != 0:
        print("【B 判据】B2 保留字前缀整体标识符应正常，实际 FAIL：")
        print(out_b2[-1500:])
        raise SystemExit(1)
    print("【B 判据】B2 前缀整体标识符  OK（回调处理器/作用域表 作整体标识符）")

    # ===== C 判据：撤掉遮蔽逻辑 → L-087 语义立红 =====
    mutated = original.replace(ANCHOR, ANCHOR_OFF, 1)
    if mutated == original:
        print("【C 判据】变异失败：锚点替换无效")
        raise SystemExit(1)
    try:
        with open(CODEGEN, "wb") as f:
            f.write(mutated.encode("utf-8"))
        rc_mut, out_mut = run_test(TEST_L087)
    finally:
        # 无论结果先恢复，避免污染仓库
        with open(CODEGEN, "wb") as f:
            f.write(raw)
    restored_sha = sha256_of(CODEGEN)
    if restored_sha != orig_sha:
        print("【恢复校验】sha256 不一致！原始=%s 恢复=%s" % (orig_sha, restored_sha))
        raise SystemExit(1)

    if rc_mut == 0:
        print("【C 判据】L-087 变异后仍 PASS，遮蔽逻辑未生效（未立红）！")
        print(out_mut[-1500:])
        raise SystemExit(1)
    print("【C 判据】L-087 变异后立红  OK（断言 当前目录==/tmp 失败 → 证明遮蔽必要）")

    print("【恢复校验】sha256 一致  OK（%s）" % restored_sha)

    # 恢复后再次确认 L-087 绿
    rc2, out2 = run_test(TEST_L087)
    if rc2 != 0 or "/tmp" not in out2:
        print("【恢复后】L-087 应为 PASS，实际 FAIL")
        print(out2[-1500:])
        raise SystemExit(1)
    print("【恢复后】L-087 PASS  OK")

    print("ANTIRUN T3 ALL OK")


if __name__ == "__main__":
    main()
