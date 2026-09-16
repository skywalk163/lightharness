# -*- coding: utf-8 -*-
"""R39 任务1+2 反跑：src/作用域.light 的两套单元测试判据有效性验证。

纪律（对齐 lightharness-debug-playbook「反跑判据」节）：
  - 变异写在仓库根目录临时文件（_red_tmp_*.light），绝不放 examples/（避免被 test_回归 收进去）
  - 变异后必须 rc=1 且报出预期关键词；还原（删除临时文件）后原用例必须 rc=0
  - 反跑与正常用例执行严格串行（本脚本内串行完成）
  - 只读原文件、只写根目录临时文件；不碰 src/ 与 examples/
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = r"G:\dswork\duan-light-merge\light-merge\.venv\Scripts\python.exe"

T1 = os.path.join(ROOT, "examples", "test_R39_作用域.light")
T2 = os.path.join(ROOT, "examples", "test_R39_作用域存储.light")

# (临时文件名, 基准文件, [(原名, 变异后)], 期望 rc, 期望输出关键词, 判据名)
CASES = [
    (
        "_red_tmp_r39_t1_value.light",
        T1,
        [('断言相等(作用域相等(键甲, 键乙), 假, "02 异键不等")',
          '断言相等(作用域相等(键甲, 键乙), 真, "02 异键不等")')],
        1, ["断言失败", "断言错误"],
        "T1-值反：异键不等的期望值改反 → 必须红",
    ),
    (
        "_red_tmp_r39_t1_throw.light",
        T1,
        [("    绑定父作用域(代理, 另一预设)\n",
          "    绑定父作用域(建作用域键(\"fresh\"), 另一预设)\n")],
        1, ["应抛错未抛"],
        "T1-抛反：一次性绑定改为不抛（换新键）→ 必须红",
    ),
    (
        "_red_tmp_r39_t2_value.light",
        T2,
        [('断言相等(推进游标(旧游标)["完成"], 真, "05d 旧游标已失效（跨代不可见）")',
          '断言相等(推进游标(旧游标)["完成"], 假, "05d 旧游标已失效（跨代不可见）")')],
        1, ["断言失败", "断言错误"],
        "T2-值反：排空换代后旧游标失效期望值改反 → 必须红",
    ),
    (
        "_red_tmp_r39_t2_throw.light",
        T2,
        [('    抛组.附着(代理上下文, 动作抛错, "store.action", 假)',
          '    抛组.附着(代理上下文, 动作保留, "store.action", 假)')],
        1, ["应抛错未抛"],
        "T2-抛反：动作失败改为不抛（换正常动作）→ 必须红",
    ),
]


def run(path):
    p = subprocess.run([PY, "运行.py", path], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main():
    ok = True

    # ---- 阶段0：基准必须 rc=0 ----
    for f in (T1, T2):
        rc, out = run(f)
        tag = "BASELINE-GREEN" if rc == 0 else "BASELINE-RED"
        print("[%s] rc=%d  %s" % (tag, rc, os.path.basename(f)))
        if rc != 0:
            ok = False
            print(out[:1200])

    # ---- 阶段1：逐条变异 → 必须 rc!=0 且报预期关键词 ----
    for name, base, subs, want_rc, want_kw, label in CASES:
        src = open(base, encoding="utf-8").read()
        mutated = src
        for old, new in subs:
            if old not in mutated:
                print("[MUTATE-MISS] %s —— 未找到锚点：%r" % (label, old[:60]))
                ok = False
                break
            mutated = mutated.replace(old, new, 1)
        else:
            tmp = os.path.join(ROOT, name)
            with open(tmp, "w", encoding="utf-8", newline="") as fh:
                fh.write(mutated)
            try:
                rc, out = run(tmp)
                hit = any(k in out for k in want_kw)
                good = (rc != 0) and hit
                print("[%s] rc=%d kw=%s  %s" % ("PASS" if good else "FAIL", rc, hit, label))
                if not good:
                    ok = False
                    print(out[:1200])
            finally:
                os.remove(tmp)

    # ---- 阶段2：还原后基准必须仍 rc=0（确认未污染）----
    for f in (T1, T2):
        rc, _ = run(f)
        print("[%s] rc=%d  还原复跑 %s" % ("RESTORE-GREEN" if rc == 0 else "RESTORE-RED",
                                          rc, os.path.basename(f)))
        if rc != 0:
            ok = False

    print("\nR39 任务1+2 反跑判据：%s" % ("ALL PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
