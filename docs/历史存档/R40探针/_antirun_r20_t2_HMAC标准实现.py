# -*- coding: utf-8 -*-
"""_antirun_r20_t2_HMAC标准实现.py —— 第20轮 任务2（HMAC RFC 2104 标准实现）反跑判据

对象：light-merge/stdlib/哈希.py 与 lightharness/stdlib/哈希.py（双份同步）
判据（4 项）：
  A=对拍全过：
    A1 test_L095.light rc=0（7 组对拍：标准 2 + 边界 5，期望值离线预计算）
    A2 直接 import 两份 哈希.py，7 组对拍逐一致（含空密钥/空消息/长密钥/中文）
  B=其他哈希函数不受影响：MD5/SHA1/SHA256/SHA512/Base64编码 与 Python hashlib/base64 现场对拍
  C=变异：HMAC 改回单轮 PBKDF2 -> test_L095 立红（恢复后绿，双份同步恢复）
恢复放在 try/finally 异常安全路径；恢复后 sha256 双份一致。
用法：python lightharness/_antirun_r20_t2_HMAC标准实现.py（BASE 自定位，跨项目定位 light-merge）
退出码：全部通过 0；任一失败 1。
"""
import base64
import hashlib
import importlib.util
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
LM = os.environ.get("LIGHT_MERGE", os.path.join(ROOT, "light-merge"))
TARGET_LM = os.path.join(LM, "stdlib", "哈希.py")
TARGET_LH = os.path.join(BASE, "stdlib", "哈希.py")

C_OLD = "    return hmac.new(\r\n        key.encode(encoding), text.encode(encoding), hashlib.sha256\r\n    ).hexdigest()"
C_NEW = "    return hashlib.pbkdf2_hmac('sha256', text.encode(encoding), key.encode(encoding), 1).hex()  # antirun C"

CASES = [
    ("密钥", "消息", "51785c6051c3d60392c441ada800662e64a027761ff96d71237c51da0eb25020"),
    ("key", "The quick brown fox jumps over the lazy dog", "f7bc83f430538424b13298e6aa6fb143ef4d59a14946175997479dbc2d1a3cd8"),
    ("", "", "b613679a0814d9ec772f95d778c35fc5ff1697c493715653c6c712144292c5ad"),
    ("", "消息", "41ecea812c250b68b001c3f2392c6468f74c491cc2a6cba5d36d2bbfe61104a0"),
    ("密钥", "", "9cfdadd2b279a7fe32f8060cfdeebe268ba0f00107a7780cd62304e818bd7631"),
    ("k" * 100, "长密钥测试", "67607baa8e6e0344ba7966ff3ce74c37427031b1cee165191d4b8ba680ed2513"),
    ("中文密钥甲乙丙", "中文消息丁戊己", "a19c812ead99e6cb449ba831a32733d2eace7a3b44aa7ac94c72784adf00501c"),
]

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


def load_hash_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check_a2():
    """A2：两份哈希.py 直接对拍 7 用例。"""
    ok = True
    for path, tag in ((TARGET_LM, "light-merge"), (TARGET_LH, "lightharness")):
        mod = load_hash_module(path, "_hash_%s" % tag)
        for key, msg, expect in CASES:
            got = mod.HMAC_SHA256(key, msg)
            if got != expect:
                ok = False
                print("FAIL A2[%s] HMAC(%r,%r)=%s 期望 %s" % (tag, key, msg, got, expect))
    print("%s A2=两份哈希.py 7 组对拍逐一致" % ("PASS" if ok else "FAIL"))
    return ok


def check_b():
    """B 判据：其他哈希函数与 Python 标准库现场对拍。"""
    mod = load_hash_module(TARGET_LM, "_hash_b")
    checks = [
        ("MD5", mod.MD5("abc"), hashlib.md5(b"abc").hexdigest()),
        ("SHA1", mod.SHA1("abc"), hashlib.sha1(b"abc").hexdigest()),
        ("SHA256", mod.SHA256("abc"), hashlib.sha256(b"abc").hexdigest()),
        ("SHA512", mod.SHA512("abc"), hashlib.sha512(b"abc").hexdigest()),
        ("Base64编码", mod.Base64编码("光明"), base64.b64encode("光明".encode()).decode()),
    ]
    ok = all(g == e for _, g, e in checks)
    for name, got, expect in checks:
        if got != expect:
            print("FAIL B %s=%s 期望 %s" % (name, got, expect))
    print("%s B=其他哈希函数不受影响 (MD5/SHA1/SHA256/SHA512/Base64)" % ("PASS" if ok else "FAIL"))
    return ok


def main():
    all_ok = True

    # A1：.light 用例 7 组对拍全过
    rc = run_light(os.path.join("examples", "test_L095.light"))
    print("%s A1=test_L095.light 7 组对拍 rc=0 (rc=%d)" % ("PASS" if rc == 0 else "FAIL", rc))
    all_ok = all_ok and rc == 0

    # A2 / B
    all_ok = check_a2() and all_ok
    all_ok = check_b() and all_ok

    # C：变异立红 + 恢复
    original = read_bytes(TARGET_LM)
    digest = hashlib.sha256(original).hexdigest()
    mutated = original.replace(C_OLD.encode("utf-8"), C_NEW.encode("utf-8"))
    if mutated == original:
        print("FAIL C (skip: 变异锚点未命中)")
        all_ok = False
    else:
        try:
            write_bytes(TARGET_LM, mutated)
            write_bytes(TARGET_LH, mutated)
            rc = run_light(os.path.join("examples", "test_L095.light"))
            ok_red = rc != 0
            print("%s 变异后立红 (test_L095 rc=%d，期望非0)" % ("PASS" if ok_red else "FAIL", rc))
        finally:
            write_bytes(TARGET_LM, original)
            write_bytes(TARGET_LH, original)
        ok_restore = (hashlib.sha256(read_bytes(TARGET_LM)).hexdigest() == digest
                      and hashlib.sha256(read_bytes(TARGET_LM)).hexdigest()
                      == hashlib.sha256(read_bytes(TARGET_LH)).hexdigest())
        print("%s 字节级恢复且双份一致 (sha256 %s)" % ("PASS" if ok_restore else "FAIL", digest[:12]))
        all_ok = all_ok and ok_red and ok_restore

    print("=== 第20轮 任务2 反跑判据（HMAC RFC 2104 标准实现）===")
    print("ALL OK" if all_ok else "ANTIRUN FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
