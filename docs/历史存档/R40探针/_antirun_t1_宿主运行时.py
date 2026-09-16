# -*- coding: utf-8 -*-
"""_antirun_t1_宿主运行时.py —— 第17轮 任务1（宿主运行时与插件生命周期原型）反跑判据

对象：lightharness/src/宿主运行时.light（字节级备份 -> 变异 -> 跑本路测试 -> 断红 -> 恢复 -> 断绿）
判据（3 项）：
  A=正常：注册 2 个依赖插件->加载全部->服务可获取->停止全部，输出与预期一致（无变异回归绿验证）
  B=边界：注册依赖循环的插件->加载全部应报错不崩溃（错误被捕获记录）（无变异回归绿验证）
  C=变异：拓扑排序退化为按注册顺序装载 -> 拓扑序断言与钩子顺序断言立红（恢复后绿）
恢复放在 try/finally 异常安全路径；恢复后 sha256 逐字节一致。
用法：python lightharness/_antirun_t1_宿主运行时.py（BASE 自定位）
退出码：全部通过 0；任一失败 1。
"""
import hashlib
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(BASE, "src", "宿主运行时.light")
TEST = os.path.join("examples", "test_宿主运行时.light")

C_OLD = ("段落 拓扑排序插件 接收 插件表:\n"
         "  # 依赖缺失检测")
C_NEW = ("段落 拓扑排序插件 接收 插件表:\n"
         "  返回 字典键列表(插件表)  # antirun C：不排序，直接按注册顺序\n"
         "  # 依赖缺失检测")


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
        case("C=变异 拓扑排序退化为注册顺序 -> 红", C_OLD, C_NEW)
    finally:
        write_bytes(TARGET, original)

    ok_restore = hashlib.sha256(read_bytes(TARGET)).hexdigest() == digest
    # A/B 判据：无变异回归绿即含依赖插件装载与依赖循环报错场景
    rc_green = run_test()

    ok = ok_restore and rc_green == 0 and all(r for _, r, _ in results)
    print("=== 第17轮 任务1 反跑判据（宿主运行时与插件生命周期原型）===")
    for name, red, note in results:
        print("%s %s (%s)" % ("PASS" if red else "FAIL", name, note))
    print("%s 字节级恢复校验 (sha256 %s)" % ("PASS" if ok_restore else "FAIL", digest[:12]))
    print("%s A/B 判据（依赖插件装载 + 依赖循环报错）回归绿 (rc=%d)" % ("PASS" if rc_green == 0 else "FAIL", rc_green))
    print("ALL OK" if ok else "ANTIRUN FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
