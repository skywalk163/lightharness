# -*- coding: utf-8 -*-
"""_antirun_t2_词法扩展.py —— 第19轮 任务2（词法扩展 L-119/L-120）反跑判据

对象：light-merge/src/lexer.py（字节级备份 -> 变异 -> 跑复现用例 -> 断红 -> 恢复 -> 断绿）
判据（5 项）：
  A=修复后绿：test_L119.light（配[0] 变量名）与 test_L120.light（错误己 整体成词）均 rc=0
  B=边界（词法 token 流，不改源码直接验证）：
      配 情况: 仍为 KEYWORD(配)（匹配语句不受影响）
      打印 真 中 真 仍为 KEYWORD（值字面量不在词尾合并表）
      设 配 为 [1,2] 中 配 仍为 KEYWORD（后随空格不触发下标豁免）
      错误甲 整体 IDENTIFIER（无关键字成分，行为不变）
  C1=变异：单字别名串删除 配 的 compound-safe 登记 -> test_L119 立红（恢复后绿）
  C2=变异：_TRAILING_ALIAS_MERGE 移除 己 -> test_L120 立红（恢复后绿）
恢复放在 try/finally 异常安全路径；恢复后 sha256 逐字节一致。
用法：python lightharness/_antirun_t2_词法扩展.py（BASE 自定位，跨项目定位 light-merge）
退出码：全部通过 0；任一失败 1。
"""
import hashlib
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
LM = os.environ.get("LIGHT_MERGE", os.path.join(ROOT, "light-merge"))
TARGET = os.path.join(LM, "src", "lexer.py")

C1_OLD = "    '配',   # 配置/配对/配位"
C1_NEW = "    # 配 antirun C1"
C2_OLD = "    '遍', '捕', '抛', '终', '返', '己', '设', '承', '宏', '掷',"
C2_NEW = "    '遍', '捕', '抛', '终', '返', '设', '承', '宏', '掷',  # antirun C2"

LIGHT_MERGE_ENV = dict(os.environ, LIGHT_MERGE=LM)


def run_light(rel):
    p = subprocess.run(
        [sys.executable, "运行.py", rel],
        cwd=BASE, capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=LIGHT_MERGE_ENV,
    )
    return p.returncode


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def write_bytes(path, data):
    with open(path, "wb") as f:
        f.write(data)


def mutate_case(name, old, new, rel_test):
    original = read_bytes(TARGET)
    digest = hashlib.sha256(original).hexdigest()
    mutated = original.replace(old.encode("utf-8"), new.encode("utf-8"))
    if mutated == original:
        print("FAIL %s (skip: 变异锚点未命中)" % name)
        return False
    results = []
    try:
        write_bytes(TARGET, mutated)
        rc = run_light(rel_test)
        results.append(("变异后立红", rc != 0, "rc=%d（期望非0）" % rc))
    finally:
        write_bytes(TARGET, original)
    ok_restore = hashlib.sha256(read_bytes(TARGET)).hexdigest() == digest
    results.append(("字节级恢复", ok_restore, digest[:12]))
    ok = all(r for _, r, _ in results)
    for rn, r, note in results:
        print("%s %s (%s)" % ("PASS" if r else "FAIL", rn, note))
    print("%s %s" % ("PASS" if ok else "FAIL", name))
    return ok


def boundary_check():
    """B 判据：直接调 lexer 验证边界场景 token 流。"""
    sys.path.insert(0, os.path.join(LM, "src"))
    from lexer import Lexer
    lx = Lexer()
    checks = []

    def types(src):
        return [(t.type.name, t.value) for t in lx.tokenize(src)]

    t = types("配 情况:")
    checks.append(("配 情况: 配仍为KEYWORD", ("KEYWORD", "配") in t))
    t = types("打印 真")
    checks.append(("打印 真 真仍为KEYWORD", ("KEYWORD", "真") in t))
    t = types("设 配 为 [1,2]")
    checks.append(("设 配 为 配仍为KEYWORD", ("KEYWORD", "配") in t))
    t = types("错误甲")
    checks.append(("错误甲 整体IDENTIFIER", t[0] == ("IDENTIFIER", "错误甲")))
    ok = all(c for _, c in checks)
    for name, c in checks:
        print("%s B=边界 %s" % ("PASS" if c else "FAIL", name))
    return ok


def main():
    original = read_bytes(TARGET)
    digest = hashlib.sha256(original).hexdigest()
    all_ok = True

    # A 判据：修复后绿
    rc1 = run_light(os.path.join("examples", "test_L119.light"))
    rc2 = run_light(os.path.join("examples", "test_L120.light"))
    ok_a = rc1 == 0 and rc2 == 0
    print("%s A=修复后绿 (test_L119 rc=%d, test_L120 rc=%d)" % ("PASS" if ok_a else "FAIL", rc1, rc2))
    all_ok = all_ok and ok_a

    # B 判据：边界 token 流
    all_ok = boundary_check() and all_ok

    # C1/C2 判据：变异立红 + 恢复
    all_ok = mutate_case("C1=变异 配 compound-safe 登记删除 -> test_L119 红", C1_OLD, C1_NEW,
                         os.path.join("examples", "test_L119.light")) and all_ok
    all_ok = mutate_case("C2=变异 _TRAILING_ALIAS_MERGE 移除 己 -> test_L120 红", C2_OLD, C2_NEW,
                         os.path.join("examples", "test_L120.light")) and all_ok

    ok_final = hashlib.sha256(read_bytes(TARGET)).hexdigest() == digest
    print("%s 终态字节级校验 (sha256 %s)" % ("PASS" if ok_final else "FAIL", digest[:12]))
    all_ok = all_ok and ok_final

    print("=== 第19轮 任务2 反跑判据（词法扩展 L-119/L-120）===")
    print("ALL OK" if all_ok else "ANTIRUN FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
