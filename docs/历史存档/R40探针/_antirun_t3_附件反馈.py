# -*- coding: utf-8 -*-
"""_antirun_t3_附件反馈.py —— 第 15 轮任务 3 反跑判据（attachment + feedback 域）

对象：src/附件反馈.light（字节级备份 → 变异 → 跑测试 → 断言真红 → 恢复 → 断言真绿）
判据（3/3）：
  A. 图片规范 base64 判据取消（是规范BASE64图片 末句 `返回 是规范base64(数据)` → `返回 真`）
     → "aGk"/"a Gk=" 等非法 base64 被放行 → 断言红；恢复 → 绿
  B. 投影取整退回内建银行家舍入（取整半数上 → 四舍五入）
     → L-125 判别例 投影图片尺寸(8,5,14) 由 4x3 变 4x2（内建与 JS 语义分歧）→ 断言红；恢复 → 绿
  C. 附件错误码表漏码（去掉 "ATTACHMENT_CORRUPT"）
     → 码表长度 17→16、是附件错误码("ATTACHMENT_CORRUPT") 由真变假 → 断言红；恢复 → 绿
用法：cd lightharness && python _antirun_t3_附件反馈.py
退出码：全部判据通过 0（打印 ALL OK）；任一失败 1。
安全：恢复一律走 finally，异常退出也不会残留变异（第13轮教训 C 判据变异残留）。
同时提醒：本脚本原地改 src/，**不得与 运行.py 并行执行**（第14轮教训：并行会读到被改版本导致假红）。
"""
import hashlib
import subprocess
import sys

TARGET = "src/附件反馈.light"
TEST = "examples/test_附件反馈.light"
PASS_LINE = "test_附件反馈 PASS"


def _nl(data: bytes) -> str:
    """按目标文件实际换行风格（CRLF/LF）生成变异串换行。"""
    return "\r\n" if b"\r\n" in data else "\n"


A_OLD = (
    "  如果 字符串长度(数据) == 0:\n"
    "    返回 假\n"
    "  返回 是规范base64(数据)\n"
)
A_NEW = (
    "  如果 字符串长度(数据) == 0:\n"
    "    返回 假\n"
    "  返回 真\n"
)

B_OLD = "段落 取整半数上 接收 x:\n  返回 向下取整(x + 0.5)\n"
B_NEW = "段落 取整半数上 接收 x:\n  返回 四舍五入(x)\n"

C_OLD = '  遍历 码 之 ["INVALID_FILE_BASE64", "INVALID_ATTACHMENT_REF", "ATTACHMENT_CORRUPT",\n'
C_NEW = '  遍历 码 之 ["INVALID_FILE_BASE64", "INVALID_ATTACHMENT_REF",\n'


def run_test():
    p = subprocess.run(
        [sys.executable, "运行.py", TEST],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def write_bytes(path, data):
    with open(path, "wb") as f:
        f.write(data)


def main():
    original = read_bytes(TARGET)
    digest = hashlib.sha256(original).hexdigest()
    nl = _nl(original)
    results = []

    def case(name, old, new):
        old_b = old.replace("\n", nl).encode("utf-8")
        new_b = new.replace("\n", nl).encode("utf-8")
        mutated = original.replace(old_b, new_b)
        if mutated == original:
            results.append((name, False, "skip: 变异未命中"))
            return
        try:
            write_bytes(TARGET, mutated)
            rc, out = run_test()
            results.append((name, rc != 0, "判红运行 rc=%d" % rc))
        finally:
            write_bytes(TARGET, original)

    try:
        case("A 规范 base64 判据取消", A_OLD, A_NEW)
        case("B 投影取整退回银行家舍入", B_OLD, B_NEW)
        case("C 附件错误码表漏 ATTACHMENT_CORRUPT", C_OLD, C_NEW)
    finally:
        write_bytes(TARGET, original)

    ok_restore = hashlib.sha256(read_bytes(TARGET)).hexdigest() == digest
    rc_green, out_green = run_test()
    ok_green = rc_green == 0 and PASS_LINE in out_green

    ok = ok_restore and ok_green and all(r for _, r, _ in results)
    print("=== 第 15 轮任务 3 反跑判据（attachment + feedback 域）===")
    for name, red, note in results:
        print("%s %s (%s)" % ("✓" if red else "✗", name, note))
    print("%s 字节级恢复校验 (sha256 %s)" % ("✓" if ok_restore else "✗", digest[:12]))
    print("%s 恢复后回归绿 (rc=%d，PASS 已打印)" % ("✓" if ok_green else "✗", rc_green))
    if ok:
        print("ALL OK")
    else:
        print("=== 结果：存在失败 ===")
        print((out_green or "")[-600:])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
