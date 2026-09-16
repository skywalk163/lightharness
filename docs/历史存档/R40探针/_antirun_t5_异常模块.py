# _antirun_t5_异常模块.py —— 第19轮任务5 反跑脚本（L-093 跨模块未捕获异常位置块归因）
# 判据：A=修复后（未捕获的跨模块异常，顶层 formatter 位置块精确指向真实抛出模块
#           载体模块.light:6，片段指向「返回 1 除以 分母」）
#       B=边界（单模块未捕获异常仍正确归因于自身入口文件，不被跨模块修复误伤）
#       C=变异（禁用 frame.filename 重编译归因分支 → 位置块回退入口，不再含
#            「载体模块.light:6」）→ 恢复后 A 判据重新 PASS
# 铁律：BASE 自定位；变异落点在 light-merge/src/enhanced_errors.py，原地改后 sha256 校验恢复；
#       不落备份到仓库；未捕获用例以临时文件写入 examples/ 后即时删除（不污染 CI 用例集合）。

import os
import sys
import hashlib
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
LIGHT_MERGE = os.path.normpath(os.path.join(BASE, "..", "light-merge"))
ERRMOD = os.path.join(LIGHT_MERGE, "src", "enhanced_errors.py")
PY = r"C:\Users\skywalk\.workbuddy\binaries\python\versions\3.13.12\python.exe"
RUNNER = os.path.join(BASE, "运行.py")
EXAMPLES = os.path.join(BASE, "examples")

# C 变异锚点：L-093 核心修复——就 frame.filename 重编译真实 .light 模块做 py→light 映射
ANCHOR = "if ffile.endswith('.light') and os.path.isfile(ffile):"
ANCHOR_OFF = "if False and ffile.endswith('.light') and os.path.isfile(ffile):  # L093-mutation"


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def run_src(src, name):
    """在 examples/ 下写临时未捕获用例并运行（保证 载体模块 解析同探针），结束即删。"""
    tmp = os.path.join(EXAMPLES, "_tmp_t5_%s.light" % name)
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
    with open(ERRMOD, "rb") as f:
        raw = f.read()
    orig_sha = sha256_of(ERRMOD)
    original = raw.decode("utf-8")
    if ANCHOR not in original:
        print("【前置检查】未找到变异锚点：%s" % ANCHOR)
        raise SystemExit(1)

    # ===== A 判据：未捕获跨模块异常，位置块指向真实抛点 载体模块.light:6 =====
    a_src = (
        "段落 主:\n"
        "    从 载体模块 导入 触发\n"
        "    打印(触发())\n"
    )
    rc_a, out_a = run_src(a_src, "uncaught")
    if rc_a == 0:
        print("【A 判据】未捕获跨模块异常应 rc!=0，实际 PASS：")
        print(out_a[-1500:])
        raise SystemExit(1)
    if "载体模块.light:6" not in out_a:
        print("【A 判据】位置块未指向 载体模块.light:6（修复未生效）：")
        print(out_a[-2000:])
        raise SystemExit(1)
    if "返回 1 除以 分母" not in out_a:
        print("【A 判据】位置块片段未指向真实抛点语句「返回 1 除以 分母」：")
        print(out_a[-2000:])
        raise SystemExit(1)
    print("【A 判据】未捕获跨模块异常位置块指向 载体模块.light:6  OK（片段=返回 1 除以 分母）")

    # ===== B 判据：单模块未捕获异常仍正确归因于自身入口文件 =====
    b_src = (
        "段落 主:\n"
        "    设 分母 为 0\n"
        "    打印(1 除以 分母)\n"
    )
    rc_b, out_b = run_src(b_src, "self")
    if rc_b == 0:
        print("【B 判据】单模块未捕获异常应 rc!=0，实际 PASS：")
        print(out_b[-1500:])
        raise SystemExit(1)
    if "载体模块" in out_b:
        print("【B 判据】单模块异常不应出现跨模块标注「载体模块」，实际：")
        print(out_b[-2000:])
        raise SystemExit(1)
    if "除零" not in out_b and "division by zero" not in out_b:
        print("【B 判据】单模块异常位置块 message 应含除零语义，实际：")
        print(out_b[-2000:])
        raise SystemExit(1)
    print("【B 判据】单模块未捕获异常仍正确归因于自身  OK（无跨模块误伤）")

    # ===== C 判据：禁用 frame.filename 重编译归因 → 位置块回退入口，不再含 载体模块.light:6 =====
    mutated = original.replace(ANCHOR, ANCHOR_OFF, 1)
    if mutated == original:
        print("【C 判据】变异失败：锚点替换无效")
        raise SystemExit(1)
    try:
        with open(ERRMOD, "wb") as f:
            f.write(mutated.encode("utf-8"))
        rc_mut, out_mut = run_src(a_src, "mut")
    finally:
        # 无论结果先恢复，避免污染仓库
        with open(ERRMOD, "wb") as f:
            f.write(raw)
    restored_sha = sha256_of(ERRMOD)
    if restored_sha != orig_sha:
        print("【恢复校验】sha256 不一致！原始=%s 恢复=%s" % (orig_sha, restored_sha))
        raise SystemExit(1)

    if "载体模块.light:6" in out_mut:
        print("【C 判据】变异后位置块仍指向 载体模块.light:6（修复分支未被禁用！）：")
        print(out_mut[-2000:])
        raise SystemExit(1)
    print("【C 判据】变异后位置块回退入口（不再含 载体模块.light:6）  OK（证明修复必要）")

    print("【恢复校验】sha256 一致  OK（%s）" % restored_sha)

    # 恢复后再次确认 A 判据 PASS
    rc_a2, out_a2 = run_src(a_src, "uncaught")
    if rc_a2 == 0 or "载体模块.light:6" not in out_a2:
        print("【恢复后】A 判据应 PASS，实际 FAIL：")
        print(out_a2[-2000:])
        raise SystemExit(1)
    print("【恢复后】A 判据 PASS  OK")

    print("ANTIRUN T5 ALL OK")


if __name__ == "__main__":
    main()
