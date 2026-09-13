# -*- coding: utf-8 -*-
"""_antirun_t6_词法安全.py —— 第18轮 任务6（标识符与词法安全工具库）反跑判据

对象：lightharness/src/词法安全.light（字节级备份 -> 变异 -> 跑本路测试 -> 断红 -> 恢复 -> 断绿）
判据（3 项）：
  A=正常：保留字表+是保留字+安全标识符+绕法指南 组合使用（无变异回归绿验证）
  B=边界：标识符可切分检查步数判定、生成安全变量名计数持久（无变异回归绿验证）
  C=变异：单字别名串移除 配 字 -> 保留字表缺 配 -> 是保留字("配置") 断言立红（恢复后绿）
  （注：为 字同时被多字关键字表兜底，单字锚点选仅存在于 L-119 单字表的 配）
恢复放在 try/finally 异常安全路径；恢复后 sha256 逐字节一致。
用法：python lightharness/_antirun_t6_词法安全.py（BASE 自定位）
退出码：全部通过 0；任一失败 1。
"""
import hashlib
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(BASE, "src", "词法安全.light")
TEST = os.path.join("examples", "test_词法安全.light")

C_OLD = '设 单字别名串 为 "若则否是段出导遍对跳过试捕抛终返配己自设为从当空长首末余父常并与且或的到现例步断接承宏引掷跃非真"'
C_NEW = '设 单字别名串 为 "若则否是段出导遍对跳过试捕抛终返己自设为从当空长首末余父常并与且或的到现例步断接承宏引掷跃非真"  # antirun C: 移除 配'


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
        case("C=变异 单字别名串移除 配 字 -> 是保留字(配置) 断言立红 -> 红", C_OLD, C_NEW)
    finally:
        write_bytes(TARGET, original)

    ok_restore = hashlib.sha256(read_bytes(TARGET)).hexdigest() == digest
    # A/B 判据：无变异回归绿即含保留字检查、可切分判定与绕法指南场景
    rc_green = run_test()

    ok = ok_restore and rc_green == 0 and all(r for _, r, _ in results)
    print("=== 第18轮 任务6 反跑判据（标识符与词法安全工具库）===")
    for name, red, note in results:
        print("%s %s (%s)" % ("PASS" if red else "FAIL", name, note))
    print("%s 字节级恢复校验 (sha256 %s)" % ("PASS" if ok_restore else "FAIL", digest[:12]))
    print("%s A/B 判据（保留字检查 + 可切分/生成名持久）回归绿 (rc=%d)" % ("PASS" if rc_green == 0 else "FAIL", rc_green))
    print("ALL OK" if ok else "ANTIRUN FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
