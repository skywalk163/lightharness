# _antirun_llm_fix.py —— 第9轮任务2 反跑判据脚本（字节级/内存级备份恢复）
#
# 反跑判据（任务2：LLM 域修复 T3-D1/T3-D2）：
#   A：客户端.light 翻译用量 删 totalTokens 赋值 → totalTokens 断言红；恢复 → 绿
#   B：消息.light 消息构造改回直接引用（删 拷贝内容块表 包裹）→ 脱钩断言红；恢复 → 绿
#
# 内存备份策略（对齐第8轮教训）：运行前把两源文件读入内存，patch 后立跑，
# 最后从内存原式写回还原，全程不重读被污染源文件，规避 运行.py 异步残留清空源文件的竞态。
#
# 用法：python _antirun_llm_fix.py
# 退出码：全部成立 → 0；任一不成立 → 非 0

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIGHT_MERGE = r"G:\dswork\duan-light-merge\light-merge"
os.environ.setdefault("LIGHT_MERGE", LIGHT_MERGE)

CLIENT = os.path.join(HERE, "src", "客户端.light")
MSG = os.path.join(HERE, "src", "消息.light")
TEST = os.path.join(HERE, "examples", "test_修复_LLM.light")


def run_test():
    """运行 test_修复_LLM，返回 (是否通过, 输出)。绿=无'错误'/'断言失败'/'解析错误'。"""
    proc = subprocess.run(
        [sys.executable, "运行.py", TEST],
        cwd=HERE,
        capture_output=True,
        text=True,
    )
    out = proc.stdout + proc.stderr
    failed = ("错误" in out) or ("断言失败" in out) or ("解析错误" in out)
    return (not failed), out


def read_src(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write_src(path, text):
    with open(path, "wb") as f:
        f.write(text.encode("utf-8"))


def check(label, cond):
    status = "✅ 成立" if cond else "❌ 不成立"
    print(f"  [{label}] {status}")
    return cond


def main():
    print("=== 反跑判据：LLM 域修复（T3-D1 totalTokens / T3-D2 消息脱钩）===")

    # 内存备份（运行前读入，全程不重读）
    orig_client = read_src(CLIENT)
    orig_msg = read_src(MSG)
    overall = True

    # 基线：原始应绿
    ok, _ = run_test()
    overall &= check("基线（原始）应绿", ok)

    # ---- A：删 totalTokens 赋值 ----
    pat_a = '  结果["totalTokens"] 为 总计\n'
    if pat_a in orig_client:
        # 连同「设 总计」定义一并去除，确保 totalTokens 桶不出现
        pat_a2 = '  设 总计 为 用量["prompt_tokens"] + 用量["completion_tokens"]\n'
        src_a = orig_client.replace(pat_a, "")
        src_a = src_a.replace(pat_a2, "")
        write_src(CLIENT, src_a)
        ok_a, _ = run_test()
        overall &= check("A（删 totalTokens 赋值）→ 应红", not ok_a)
    else:
        overall &= check("A（删 totalTokens 赋值）→ 应红", False)

    # 恢复 A，再改 B
    write_src(CLIENT, orig_client)

    # ---- B：消息构造改回直接引用（删 拷贝内容块表 包裹）----
    if "拷贝内容块表(内容)" in orig_msg:
        src_b = orig_msg.replace("拷贝内容块表(内容)", "内容")
        write_src(MSG, src_b)
        ok_b, _ = run_test()
        overall &= check("B（消息构造改回直接引用）→ 应红", not ok_b)
    else:
        overall &= check("B（消息构造改回直接引用）→ 应红", False)

    # 恢复 B → 绿
    write_src(MSG, orig_msg)
    ok2, _ = run_test()
    overall &= check("恢复后 → 应绿", ok2)

    # 最终兜底：两源文件均与内存原式一致（防竞态污染）
    write_src(CLIENT, orig_client)
    write_src(MSG, orig_msg)

    print("==== 反跑结果：", "全部成立 ✅" if overall else "存在不成立 ❌", "====")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
