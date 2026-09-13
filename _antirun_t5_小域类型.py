# -*- coding: utf-8 -*-
"""_antirun_t5_小域类型.py —— 第16轮 任务5（小域类型合并）反跑判据

对象：lightharness/src/小域类型.light（字节级备份 -> 变异 -> 跑本路测试 -> 断红 -> 恢复 -> 断绿）
判据（3 项）：
  A=正常：待办构造->状态转换->过滤输出与预期一致（无变异回归绿验证）
  B=边界：空终端读请求校验不崩溃回默认值（无变异回归绿验证）
  C=变异：待办状态枚举值 in_progress 改错（in-progress）-> 测试立红（恢复后绿）
    （任务书 C 指向 plan/types.ts 的 PlanMode 枚举——上游 plan 域无 PlanMode 枚举
     （实为 PlanProjection/PlanUnitState 形状），取语义等价的待办状态枚举变异，登记 R16-D5）
恢复放在 try/finally 异常安全路径；恢复后 sha256 逐字节一致。
用法：python lightharness/_antirun_t5_小域类型.py（BASE 自定位）
退出码：全部通过 0；任一失败 1。
"""
import hashlib
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(BASE, "src", "小域类型.light")
TEST = os.path.join("examples", "test_小域类型.light")

C_OLD = '"pending", "in_progress", "completed"'
C_NEW = '"pending", "in-progress", "completed"  # antirun C'


def run_test():
    env = dict(os.environ)
    env["LIGHT_MERGE"] = r"G:\dswork\duan-light-merge\light-merge"
    p = subprocess.run(
        [sys.executable, "运行.py", TEST],
        cwd=BASE, capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=env,
    )
    return p.returncode


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def write_bytes(path, data):
    with open(path, "wb") as f:
        f.write(data)


def main():
    original = read_bytes(TARGET)
    digest = hashlib.sha256(original).hexdigest()
    results = []

    def case(name, old, new):
        mutated = original.replace(old.encode("utf-8"), new.encode("utf-8"))
        if mutated == original:
            results.append((name, False, "skip: 变异锚点未命中"))
            return
        write_bytes(TARGET, mutated)
        try:
            rc = run_test()
            results.append((name, rc != 0, "变异后运行 rc=%d（期望非 0，真红）" % rc))
        finally:
            write_bytes(TARGET, original)

    try:
        case("C=变异 待办状态枚举 in_progress 改错 -> 红", C_OLD, C_NEW)
    finally:
        write_bytes(TARGET, original)

    ok_restore = hashlib.sha256(read_bytes(TARGET)).hexdigest() == digest
    # A/B 判据：无变异回归绿即含待办构造-过滤与空终端读请求场景
    rc_green = run_test()

    ok = ok_restore and rc_green == 0 and all(r for _, r, _ in results)
    print("=== 第16轮 任务5 反跑判据（小域类型合并 小域类型）===")
    for name, red, note in results:
        print("%s %s (%s)" % ("PASS" if red else "FAIL", name, note))
    print("%s 字节级恢复校验 (sha256 %s)" % ("PASS" if ok_restore else "FAIL", digest[:12]))
    print("%s A/B 判据（待办构造过滤 + 空终端读请求）回归绿 (rc=%d)" % ("PASS" if rc_green == 0 else "FAIL", rc_green))
    print("ALL OK" if ok else "ANTIRUN FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
