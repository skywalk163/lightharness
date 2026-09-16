# _antirun_t3_错误增强.py —— 第18轮任务3 反跑脚本（#118 / R18-D3）
# 判据：A=正常（造结构化错误→抛出→捕获→解析，码/消息/详情 round-trip 一致）→ 测试 PASS
#       B=边界（尝试执行抛出异常的函数返回默认值不传播）→ 测试 PASS
#       C=变异（抛出结构化错误抹掉码字段 → 解析错误码测试立红），恢复后 PASS
# 铁律：BASE 自定位；原地改 src 后 sha256 校验恢复；不落备份文件到仓库。

import os
import hashlib
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(BASE, "src", "错误增强.light")
PY = r"C:\Users\skywalk\.workbuddy\binaries\python\versions\3.13.12\python.exe"
RUNNER = os.path.join(BASE, "运行.py")
TEST = os.path.join(BASE, "examples", "test_错误增强.light")


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def run_test():
    p = subprocess.run([PY, "-u", RUNNER, TEST],
                       cwd=BASE, capture_output=True, text=True, encoding="utf-8")
    return p.returncode, p.stdout + p.stderr


def main():
    with open(TARGET, "rb") as f:
        raw = f.read()
    orig_sha = sha256_of(TARGET)
    original = raw.decode("utf-8")

    # A/B：干净运行（含正常 round-trip + 边界断言）必须通过
    rc, out = run_test()
    if rc != 0:
        print("【A/B 判据】干净运行应 PASS，实际 FAIL")
        print(out[-1500:])
        raise SystemExit(1)
    print("【A/B 判据】干净运行 PASS  OK（正常 round-trip + 边界断言全过）")

    # C：变异——抛出结构化错误抹掉码字段（序列化不含码）
    mutated = original.replace(
        "  设 文本 为 序列化JSON(结构)",
        "  设 文本 为 序列化JSON({\"消息\": 消息, \"详情\": 详情})",
        1,
    )
    if mutated == original:
        print("【C 判据】未找到变异锚点，跳过")
        raise SystemExit(1)
    with open(TARGET, "wb") as f:
        f.write(mutated.encode("utf-8"))

    rc_mut, out_mut = run_test()
    if rc_mut == 0:
        print("【C 判据】变异后测试仍 PASS，未立红！")
        with open(TARGET, "wb") as f:
            f.write(raw)
        raise SystemExit(1)
    print("【C 判据】变异后测试立红  OK（解析错误码断言失败）")

    # 恢复并校验 sha256（二进制保真）
    with open(TARGET, "wb") as f:
        f.write(raw)
    restored_sha = sha256_of(TARGET)
    if restored_sha != orig_sha:
        print("【恢复校验】sha256 不一致！原始=%s 恢复=%s" % (orig_sha, restored_sha))
        raise SystemExit(1)
    print("【恢复校验】sha256 一致  OK（%s）" % restored_sha)

    rc2, out2 = run_test()
    if rc2 != 0:
        print("【恢复后】应为 PASS，实际 FAIL")
        print(out2[-1500:])
        raise SystemExit(1)
    print("【恢复后】PASS  OK")

    print("ANTIRUN T3 ALL OK")


if __name__ == "__main__":
    main()
