# -*- coding: utf-8 -*-
"""
第 8 轮 任务3 反跑判据脚本（LLM 消息/请求行为对照）

判据：
  A 请求体字段 —— 改反 客户端.组装请求 的 model 字段（删除 model 键），
       → 节C「C 请求体 model 字段」断言应红；还原后复绿。
  B token 分桶 —— 改反 令牌估算.聚合单次用量 的未缓存输入求和（每桶 +1），
       → 节F「F 未缓存输入=160」断言应红；还原后复绿。

说明：运行.py 退出后会有异步残留进程短暂清空 .light 源文件（竞态），
故本脚本全程用【内存中的干净备份】做 patch/restore，绝不重新读取
可能被污染的源文件，最后 finally 用内存备份还原，无 .bak 残留。
"""
import os, sys, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
TEST = os.path.join(ROOT, "examples", "test_行为对照_LLM.light")
客户端 = os.path.join(ROOT, "src", "客户端.light")
令牌估算 = os.path.join(ROOT, "src", "令牌估算.light")

# 判据 A：删除组装请求 的 model 键
PATCH_A_OLD = '    设 请求 为 ["model": 己.模型名, "messages": 消息表, "stream": 真]'
PATCH_A_NEW = '    设 请求 为 ["messages": 消息表, "stream": 真]'

# 判据 B：未缓存输入求和每桶 +1（破坏分桶正确性）
PATCH_B_OLD = '    设 输入 为 输入 + 用量["输入"]'
PATCH_B_NEW = '    设 输入 为 输入 + 用量["输入"] + 1'


def run_test():
    """返回是否通过（bool）。"""
    p = subprocess.run(
        [sys.executable, "运行.py", TEST],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
    )
    out = (p.stdout or "") + (p.stderr or "")
    return ("测试通过" in out) or ("PASS" in out) or ("通过 ---" in out)


def write_src(path, content):
    open(path, "w", encoding="utf-8").write(content)


def restore_all(orig):
    write_src(客户端, orig["client"])
    write_src(令牌估算, orig["token"])


def main():
    # 仅在最开始读取一次干净源码（此时无竞态污染）
    orig = {
        "client": open(客户端, encoding="utf-8").read(),
        "token": open(令牌估算, encoding="utf-8").read(),
    }
    assert orig["client"].count(PATCH_A_OLD) == 1, "A 补丁目标不唯一"
    assert orig["token"].count(PATCH_B_OLD) == 1, "B 补丁目标不唯一"

    results = []

    # 0) 基线：必须绿
    ok = run_test()
    results.append(("基线（未改）", ok, True))
    print(f"[基线] {'绿' if ok else '红(异常!)'}")

    try:
        # A) 改反 model 字段 → 期望红（用内存备份 patch，不重读源文件）
        write_src(客户端, orig["client"].replace(PATCH_A_OLD, PATCH_A_NEW))
        ok_a = run_test()
        results.append(("A 删 model 键", ok_a, False))
        print(f"[A 删 model 键] {'红(符合预期)' if not ok_a else '绿(判据失效!)'}")

        # 还原 A → 期望绿
        write_src(客户端, orig["client"])
        ok_ar = run_test()
        results.append(("A 还原", ok_ar, True))
        print(f"[A 还原] {'绿' if ok_ar else '红(异常!)'}")

        # B) 改反 token 分桶求和 → 期望红
        write_src(令牌估算, orig["token"].replace(PATCH_B_OLD, PATCH_B_NEW))
        ok_b = run_test()
        results.append(("B 破坏分桶求和", ok_b, False))
        print(f"[B 破坏分桶求和] {'红(符合预期)' if not ok_b else '绿(判据失效!)'}")

        # 还原 B → 期望绿
        write_src(令牌估算, orig["token"])
        ok_br = run_test()
        results.append(("B 还原", ok_br, True))
        print(f"[B 还原] {'绿' if ok_br else '红(异常!)'}")

    finally:
        # 双保险：无论是否异常都用内存备份还原两个源文件
        restore_all(orig)

    # 汇总
    print("\n==== 反跑判据汇总 ====")
    all_ok = True
    for name, got, expect in results:
        ok_flag = (got == expect)
        all_ok = all_ok and ok_flag
        verdict = "✅" if ok_flag else "❌"
        print(f"  {verdict} {name}: 得到={'绿' if got else '红'} 期望={'绿' if expect else '红'}")
    print("\n结论:", "全部反跑判据成立 ✅" if all_ok else "存在失效判据 ❌")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
