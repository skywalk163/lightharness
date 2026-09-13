# -*- coding: utf-8 -*-
"""_antirun_t4_字符串哈希.py —— 第19轮 任务4（字符串与哈希 L-086/L-095）反跑判据

对象：light-merge/src/parser_expr.py（L-086 插值判定修复）
      light-merge/stdlib/哈希.py 与 lightharness/stdlib/哈希.py（L-095 HMAC 标准实现，双份同步）
判据（6 项）：
  A=修复后绿：test_L086.light（正则 {1,4} 可用）与 test_L095.light（HMAC 对拍）均 rc=0
  B=边界（直接调 parser_expr._parse_string_interpolation）：
      "{甲}" 仍解析为插值（Identifier 部件）
      "[0-9a-f]{1,4}" 不触发插值（返回 None）
      "{名:格式}" 格式说明符插值不受影响
  C1=变异：parser_expr 的 {数字,数字} 字面量规则判据破坏 -> test_L086 立红（恢复后绿）
  C2=变异：哈希.py HMAC 改回单轮 PBKDF2 -> test_L095 立红（恢复后绿，双份同步恢复）
恢复放在 try/finally 异常安全路径；恢复后 sha256 逐字节一致。
用法：python lightharness/_antirun_t4_字符串哈希.py（BASE 自定位，跨项目定位 light-merge）
退出码：全部通过 0；任一失败 1。
"""
import hashlib
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
LM = os.environ.get("LIGHT_MERGE", os.path.join(ROOT, "light-merge"))
TARGET_PARSER = os.path.join(LM, "src", "parser_expr.py")
TARGET_HASH_LM = os.path.join(LM, "stdlib", "哈希.py")
TARGET_HASH_LH = os.path.join(BASE, "stdlib", "哈希.py")

C1_OLD = "if re.match(r'^\\d+\\s*,\\s*\\d+$', expr_text):"
C1_NEW = "if re.match(r'^\\d+\\s*,\\s*\\d+NEVER$', expr_text):  # antirun C1"
C2_OLD = "    return hmac.new(\r\n        key.encode(encoding), text.encode(encoding), hashlib.sha256\r\n    ).hexdigest()"
C2_NEW = "    return hashlib.pbkdf2_hmac('sha256', text.encode(encoding), key.encode(encoding), 1).hex()  # antirun C2"

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


def mutate_case(name, target, old, new, rel_test, extra_restore=None):
    original = read_bytes(target)
    digest = hashlib.sha256(original).hexdigest()
    mutated = original.replace(old.encode("utf-8"), new.encode("utf-8"))
    if mutated == original:
        print("FAIL %s (skip: 变异锚点未命中)" % name)
        return False
    try:
        write_bytes(target, mutated)
        if extra_restore:
            write_bytes(extra_restore, mutated)
        rc = run_light(rel_test)
        ok_red = rc != 0
        print("%s 变异后立红 (%s rc=%d，期望非0)" % ("PASS" if ok_red else "FAIL", rel_test, rc))
    finally:
        write_bytes(target, original)
        if extra_restore:
            write_bytes(extra_restore, original)
    ok_restore = hashlib.sha256(read_bytes(target)).hexdigest() == digest
    print("%s 字节级恢复 (%s sha256 %s)" % ("PASS" if ok_restore else "FAIL", os.path.basename(target), digest[:12]))
    ok = ok_red and ok_restore
    print("%s %s" % ("PASS" if ok else "FAIL", name))
    return ok


def boundary_check():
    """B 判据：直接调 _parse_string_interpolation 验证边界。"""
    sys.path.insert(0, os.path.join(LM, "src"))
    from light_parser_v3 import LightParser
    checks = []
    p = LightParser()
    node = p._parse_string_interpolation("值:{甲}", 1, 1)
    ok_interp = node is not None and any(type(x).__name__ == "Identifier" for x in node.parts if not isinstance(x, str))
    checks.append(("{甲} 仍为插值", ok_interp))
    node = p._parse_string_interpolation("[0-9a-f]{1,4}", 1, 1)
    checks.append(("{1,4} 不触发插值", node is None))
    node = p._parse_string_interpolation("值:{甲:.2f}", 1, 1)
    ok_fmt = node is not None
    checks.append(("{甲:.2f} 格式插值不受影响", ok_fmt))
    ok = all(c for _, c in checks)
    for name, c in checks:
        print("%s B=边界 %s" % ("PASS" if c else "FAIL", name))
    return ok


def main():
    all_ok = True

    # A 判据：修复后绿
    rc1 = run_light(os.path.join("examples", "test_L086.light"))
    rc2 = run_light(os.path.join("examples", "test_L095.light"))
    ok_a = rc1 == 0 and rc2 == 0
    print("%s A=修复后绿 (test_L086 rc=%d, test_L095 rc=%d)" % ("PASS" if ok_a else "FAIL", rc1, rc2))
    all_ok = all_ok and ok_a

    # B 判据：边界插值判定
    all_ok = boundary_check() and all_ok

    # C1 判据：L-086 变异立红
    all_ok = mutate_case("C1=变异 {数字,数字} 字面量规则破坏 -> test_L086 红",
                         TARGET_PARSER, C1_OLD, C1_NEW,
                         os.path.join("examples", "test_L086.light")) and all_ok

    # C2 判据：L-095 HMAC 改回 PBKDF2 立红（双份同步变异/恢复）
    all_ok = mutate_case("C2=变异 HMAC 改回单轮PBKDF2 -> test_L095 红",
                         TARGET_HASH_LM, C2_OLD, C2_NEW,
                         os.path.join("examples", "test_L095.light"),
                         extra_restore=TARGET_HASH_LH) and all_ok

    # 终态双份哈希一致校验
    ok_final = (hashlib.sha256(read_bytes(TARGET_HASH_LM)).hexdigest()
                == hashlib.sha256(read_bytes(TARGET_HASH_LH)).hexdigest())
    print("%s 终态双份哈希.py 一致校验" % ("PASS" if ok_final else "FAIL"))
    all_ok = all_ok and ok_final

    print("=== 第19轮 任务4 反跑判据（字符串与哈希 L-086/L-095）===")
    print("ALL OK" if all_ok else "ANTIRUN FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
