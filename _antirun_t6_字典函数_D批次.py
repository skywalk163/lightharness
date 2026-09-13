# -*- coding: utf-8 -*-
"""_antirun_t6_字典函数_D批次.py —— 第19轮 任务6（字典与函数 L-096 + D批次验收）反跑判据

对象：light-merge/src/code_generator.py（L-096 字典属性访问修复）
判据（7 项）：
  A=修复后绿：test_L096.light（对象.键 属性访问）rc=0；D批次验收用例
    test_L068/L069/L070/L071/L072/L074 rc=0（L-073 捕获后绿 rc=0）
  B=边界（直接调 codegen 验证发射）：
      对象.键      发射 _light_attr_get(对象, '键')
      己.标识 为 值 发射 _light_attr_set(...)（属性赋值不走读取 helper）
      无财.叫()    保持方法调用发射（类实例方法不受影响）
  C1=变异：属性访问发射改回 obj.member 直通 -> test_L096 立红（恢复后绿）
  C2=变异：属性赋值拦截删除（目标也走读取 helper）-> test_会话 立红
    （cannot assign to function call，恢复后绿）
恢复放在 try/finally 异常安全路径；恢复后 sha256 逐字节一致。
用法：python lightharness/_antirun_t6_字典函数_D批次.py（BASE 自定位，跨项目定位 light-merge）
退出码：全部通过 0；任一失败 1。
"""
import hashlib
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
LM = os.environ.get("LIGHT_MERGE", os.path.join(ROOT, "light-merge"))
TARGET = os.path.join(LM, "src", "code_generator.py")

C1_OLD = '                return f"_light_attr_get({obj}, {expr.member!r})"'
C1_NEW = '                return f"{obj}.{mapped_member}"  # antirun C1'
C2_OLD = "            if isinstance(stmt.target, MemberAccess) and not stmt.target.is_method_call:"
C2_NEW = "            if isinstance(stmt.target, MemberAccess) and False and not stmt.target.is_method_call:  # antirun C2"

LIGHT_MERGE_ENV = dict(os.environ, LIGHT_MERGE=LM)


def run_light(rel, expect=0):
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


def mutate_case(name, old, new, rel_test, expect_rc):
    original = read_bytes(TARGET)
    digest = hashlib.sha256(original).hexdigest()
    mutated = original.replace(old.encode("utf-8"), new.encode("utf-8"))
    if mutated == original:
        print("FAIL %s (skip: 变异锚点未命中)" % name)
        return False
    try:
        write_bytes(TARGET, mutated)
        rc = run_light(rel_test)
        ok = rc == expect_rc
        print("%s 变异后 rc=%d（期望 %d）" % ("PASS" if ok else "FAIL", rc, expect_rc))
    finally:
        write_bytes(TARGET, original)
    ok_restore = hashlib.sha256(read_bytes(TARGET)).hexdigest() == digest
    print("%s 字节级恢复 (sha256 %s)" % ("PASS" if ok_restore else "FAIL", digest[:12]))
    ok = ok and ok_restore
    print("%s %s" % ("PASS" if ok else "FAIL", name))
    return ok


def boundary_check():
    """B 判据：直接调 codegen 验证属性访问/赋值发射。"""
    sys.path.insert(0, os.path.join(LM, "src"))
    from light_parser_v3 import LightParser
    from code_generator import PythonCodeGenerator
    checks = []

    parser = LightParser()
    module = parser.parse("段落 主 接收:\n    设 对象 为 {}\n    打印 对象.键\n")
    code = PythonCodeGenerator().generate(module)
    checks.append(("对象.键 发射 _light_attr_get", "_light_attr_get" in code and "_light_attr_get(对象, '键')" in code))

    parser = LightParser()
    module = parser.parse("类 用:\n    段落 初始化 接收:\n        己.标识 为 1\n")
    code = PythonCodeGenerator().generate(module)
    checks.append(("己.标识 为 发射 _light_attr_set", "_light_attr_set(self, '标识', 1)" in code))
    checks.append(("赋值左值不走 _light_attr_get", "_light_attr_get(self, '标识') =" not in code))

    parser = LightParser()
    module = parser.parse("类 狗:\n    段落 叫 接收:\n        打印 \"汪\"\n设 无财 为 新建 狗()\n无财.叫()\n")
    code = PythonCodeGenerator().generate(module)
    checks.append(("方法调用保持原生发射", "无财.叫()" in code))

    ok = all(c for _, c in checks)
    for name, c in checks:
        print("%s B=边界 %s" % ("PASS" if c else "FAIL", name))
    return ok


def main():
    all_ok = True
    ex = "examples"

    # A 判据：修复后绿 + D批次验收状态
    rc96 = run_light(os.path.join(ex, "test_L096.light"))
    print("%s A=修复后绿 test_L096 (rc=%d)" % ("PASS" if rc96 == 0 else "FAIL", rc96))
    all_ok = all_ok and rc96 == 0

    d_ok = True
    for t in ("L068", "L069", "L070", "L071", "L072", "L074"):
        rc = run_light(os.path.join(ex, "test_%s.light" % t))
        if rc != 0:
            d_ok = False
            print("FAIL D批次 test_%s rc=%d（期望 0）" % (t, rc))
    rc73 = run_light(os.path.join(ex, "test_L073.light"))
    if rc73 != 0:
        d_ok = False
        print("FAIL D批次 test_L073 rc=%d（预期捕获后绿，期望 0）" % rc73)
    print("%s A=D批次验收用例状态符合标注 (L068~L074)" % ("PASS" if d_ok else "FAIL"))
    all_ok = all_ok and d_ok

    # B 判据：边界发射验证
    all_ok = boundary_check() and all_ok

    # C1/C2 判据：变异立红 + 恢复
    all_ok = mutate_case("C1=变异 属性访问改回直通 -> test_L096 红",
                         C1_OLD, C1_NEW, os.path.join(ex, "test_L096.light"), 1) and all_ok
    all_ok = mutate_case("C2=变异 属性赋值拦截删除 -> test_会话 红",
                         C2_OLD, C2_NEW, os.path.join(ex, "test_会话.light"), 1) and all_ok

    print("=== 第19轮 任务6 反跑判据（字典与函数 L-096 + D批次验收）===")
    print("ALL OK" if all_ok else "ANTIRUN FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
