# -*- coding: utf-8 -*-
"""任务1 反跑判据（第6轮·压缩E5 浮点除法切片修复）。

判据目标：src/压缩E5.light 段落「修剪工具结果」的
    设 头部长 为 整数((长 * 70) / 100)
是修好「光明 / 为浮点除法 → float 作切片下标报 slice indices must be integers」的必要条件。

- A（红判据）：去掉 整数() 改回 (长 * 70) / 100 → test_压缩E5 必须红；恢复后必须绿。
- B（能力记录，非红判据）：改成 (长 * 70) // 100 → 光明支持整数除法 //（实测 int，截断语义），
  测试仍绿。仅用于登记 L-080 时记录「// 已支持，可用」，不是本次采用的写法。

用法：python _antirun_compresse5.py
字节级改写 src/压缩E5.light，退出前总是恢复原字节；另留 .bak_antirun 备份至本次执行结束。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src", "压缩E5.light")
BAK = SRC + ".bak_antirun"
TEST = "examples/test_压缩E5.light"

BASE = "设 头部长 为 整数((长 * 70) / 100)"
MUT_A = "设 头部长 为 (长 * 70) / 100"        # 回归缺陷：float 切片下标
MUT_B = "设 头部长 为 (长 * 70) // 100"       # 等价写法：// 整数除法


def run_test():
    env = dict(os.environ, LIGHT_MERGE=r"G:\dswork\duan-light-merge\light-merge")
    r = subprocess.run([sys.executable, "运行.py", TEST], cwd=ROOT, env=env,
                       capture_output=True, text=True)
    return r.returncode


def read_bytes():
    with open(SRC, "rb") as f:
        return f.read()


def write_bytes(data):
    with open(SRC, "wb") as f:
        f.write(data)


def main():
    orig = read_bytes()
    text = orig.decode("utf-8-sig")
    assert text.count(BASE) == 1, "基线未唯一命中（命中 %d 次）：修复是否已落地？" % text.count(BASE)
    assert run_test() == 0, "基线用例应先绿，否则反跑判据无意义"

    # 字节级备份
    with open(BAK, "wb") as f:
        f.write(orig)

    results = []
    try:
        # ---- A：去掉 整数() → 必须红 ----
        write_bytes(orig.replace(BASE.encode("utf-8"), MUT_A.encode("utf-8")))
        rc_a = run_test()
        write_bytes(orig)
        rc_a_back = run_test()
        results.append(("A 去掉整数()改回浮点除法", rc_a, rc_a_back))

        # ---- B：改成 // → 光明支持整数除法，测试仍绿（等价写法记录） ----
        write_bytes(orig.replace(BASE.encode("utf-8"), MUT_B.encode("utf-8")))
        rc_b = run_test()
        write_bytes(orig)
        rc_b_back = run_test()
        results.append(("B 改成 // 整数除法（等价写法）", rc_b, rc_b_back))
    finally:
        write_bytes(orig)
        try:
            os.remove(BAK)
        except OSError:
            pass

    ok = True
    print("==== 任务1 反跑判据（压缩E5 浮点除法切片） ====")
    for name, rc_mut, rc_back in results:
        if name.startswith("A"):
            passed = rc_mut == 1 and rc_back == 0
            expect = "改反 rc=1(红) / 恢复 rc=0(绿)"
        else:
            passed = rc_mut == 0 and rc_back == 0
            expect = "改反 rc=0(绿, // 等价可用) / 恢复 rc=0(绿)"
        ok = ok and passed
        print("%-34s 改反 rc=%d  恢复 rc=%d  期望 %s  → %s"
              % (name, rc_mut, rc_back, expect, "PASS" if passed else "FAIL"))

    print("==== %s（%d/%d） ====" % ("全部通过" if ok else "存在不通过",
                                    sum(1 for _, m, b in results
                                        if (m == 1 and b == 0) or (m == 0 and b == 0)),
                                    len(results)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
