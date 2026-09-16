# -*- coding: utf-8 -*-
"""_antirun_t6_控制器类型.py —— #109 域：api 控制器类型合并（workspace-files / settings-controller / workspace-controller）反跑判据

对  src/控制器类型.light  做字节级变异注入：变异立红 → 字节级恢复 → 回归判绿。
三判据：
  A) 正常输出：造变更存现 -> 判变更存在 -> 取变更路径 构造判别链路与预期一致；
     变异把 造变更存现 的 "version" 键写坏为 "versio"，用例_文件变更 必须红，恢复后绿。
  B) 边界：空设置对象键枚举不崩溃（返回空列表），判目录打开值(空) 判假；
     变异把 判目录打开真 的 opened 判定 == 真 改 != 真，用例_设置 必须红，恢复后绿。
  C) 变异立红（真实语义）：workspace-files 变更枚举 "directory" 写坏为 "dir"，
     用例_目录项 类型枚举断言必须红，恢复后绿。

输出：三判据逐一判红/判绿，最终 ALL OK 退出码 0。
"""
import hashlib
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "src", "控制器类型.light")
TEST = os.path.join(BASE, "examples", "test_控制器类型.light")


def read_bytes(p):
    with open(p, "rb") as f:
        return f.read()


def write_bytes(p, b):
    with open(p, "wb") as f:
        f.write(b)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def run_test():
    r = subprocess.run(
        [sys.executable, "运行.py", TEST],
        cwd=BASE, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def patch_after(text, anchor, old, new):
    i = text.find(anchor)
    assert i >= 0, "锚点段落未找到: " + anchor
    j = text.find(old, i + len(anchor))
    assert j >= 0, "变异点未找到: " + old
    return text[:j] + new + text[j + len(old):]


def check(label, anchor, old, new):
    orig = read_bytes(SRC)
    h0 = sha(orig)
    # 注入变异（基于字节级精确回滚，保证恢复后 sha256 一致）
    write_bytes(SRC, patch_after(orig.decode("utf-8"), anchor, old, new).encode("utf-8"))
    rc_red, out_red = run_test()
    red = (rc_red != 0)
    # 字节级恢复
    write_bytes(SRC, orig)
    h1 = sha(read_bytes(SRC))
    restored = (h0 == h1)
    rc_green, out_green = run_test()
    green = (rc_green == 0)
    ok = red and restored and green
    print("[%s] %s 变异判红=%s 恢复字节=%s 恢复判绿=%s"
          % ("PASS" if ok else "FAIL", label, red, restored, green))
    if not ok:
        print("  变异输出尾: " + (out_red.strip().splitlines() or [""])[-1][:120])
    return ok


def main():
    ok = True
    ok &= check("A 正常输出:变更构造->判别->取路径",
                "段落 造变更存现", '"version", 版本', '"versio", 版本')
    ok &= check("B 边界:空设置键枚举不崩",
                "段落 判目录打开真", '值["opened"] == 真', '值["opened"] != 真')
    ok &= check("C 变异:目录类型枚举改坏",
                "段落 判目录项类型", '"directory"', '"dir"')
    print("3/3 ALL OK" if ok else "反跑未全过")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())