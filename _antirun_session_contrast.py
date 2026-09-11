# -*- coding: utf-8 -*-
"""_antirun_session_contrast.py —— 第 8 轮任务 2 反跑判据（会话/持久化行为对照）

对象：examples/test_行为对照_会话持久化.light（测试文件自身，字节级备份/恢复；不碰 src）
判据：
  A. 编解码断言字段值改反（5d 标识保留 "hdr1"→"hdrX"）→ 红；恢复 → 绿
  B. 迁移断言改反（8c 链内版本推进 "3.0"→"2.0"）→ 红；恢复 → 绿
  C. 整节删除（§2 节点0 投影五条断言）→ 输出缺失 → 红；恢复 → 绿
用法：cd lightharness && python _antirun_session_contrast.py
退出码：全部判据通过 0；任一失败 1。
"""
import hashlib
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "examples", "test_行为对照_会话持久化.light")
TMP_ROOT = os.path.join(HERE, "_contrast_r8t2_tmp")

A_OLD = '行甲["id"], "hdr1"'
A_NEW = '行甲["id"], "hdrX"'
B_OLD = '["版本"]) == "3.0"'
B_NEW = '["版本"]) == "2.0"'
C_MARK = "================= §2"
C_END = "================= §3"


def run():
    p = subprocess.run(
        [sys.executable, "运行.py", "examples/test_行为对照_会话持久化.light"],
        cwd=HERE, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def write_bytes(data):
    with open(TARGET, "wb") as f:
        f.write(data)


def read_bytes():
    with open(TARGET, "rb") as f:
        return f.read()


def cleanup_tmp():
    if os.path.isdir(TMP_ROOT):
        shutil.rmtree(TMP_ROOT, ignore_errors=True)


def main():
    if not os.path.exists(TARGET):
        print("✗ 找不到测试文件: %s" % TARGET)
        return 1
    original = read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    results = []

    def case(name, mutate, expect_red_by):
        """mutate(bytes)->bytes；expect_red_by(rc, out)->True 表示判为红"""
        write_bytes(mutate(original))
        rc, out = run()
        red = expect_red_by(rc, out)
        results.append((name, red, rc))
        write_bytes(original)

    # ---- A. 编解码断言字段值改反 ----
    case("A 编解码断言改反(5d)",
         lambda b: b.replace(A_OLD.encode("utf-8"), A_NEW.encode("utf-8"), 1),
         lambda rc, out: rc != 0)

    # ---- B. 迁移断言改反 ----
    case("B 迁移断言改反(8c)",
         lambda b: b.replace(B_OLD.encode("utf-8"), B_NEW.encode("utf-8"), 1),
         lambda rc, out: rc != 0)

    # ---- C. 整节删除（§2 五条断言消失）----
    def drop_section(b):
        text = b.decode("utf-8")
        start = text.index(C_MARK)
        end = text.index(C_END)
        return text[:start].encode("utf-8") + text[end:].encode("utf-8")

    case("C 整节删除(§2)",
         drop_section,
         lambda rc, out: ("✓ 2b" not in out))

    # ---- 恢复校验：字节级还原 ----
    restored = read_bytes()
    same = hashlib.sha256(restored).hexdigest() == digest
    cleanup_tmp()

    ok = same and all(r for _, r, _ in results)
    print("=== 第 8 轮任务 2 反跑判据 ===")
    for name, red, rc in results:
        print("%s %s (判红运行 rc=%s)" % ("✓" if red else "✗", name, rc))
    print("%s 字节级恢复校验 (sha256 %s)" % ("✓" if same else "✗", digest[:12]))
    print("=== 结果：%s ===" % ("全部通过" if ok else "存在失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
