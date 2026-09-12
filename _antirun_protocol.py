# _antirun_protocol.py —— 反跑判据（任务5 代码运行时协议）
# 字节级备份/恢复 src/代码运行时协议.light；逐项变异使测试变红，还原后变绿，并校验文件完全还原。
# 用法：python _antirun_protocol.py
import os
import subprocess
import sys

这里 = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(这里, "src", "代码运行时协议.light")
test = os.path.join(这里, "examples", "test_代码运行时协议.light")
运行 = os.path.join(这里, "运行.py")
py = r"C:\Users\skywalk\.workbuddy\binaries\python\versions\3.13.12\python.exe"

备份 = open(src, encoding="utf-8").read()


def 跑(label):
    结果 = subprocess.run([py, 运行, test], capture_output=True, text=True, cwd=这里)
    print(f"  [{label}] rc={结果.returncode}")
    return 结果.returncode


def 写(text):
    open(src, "w", encoding="utf-8").write(text)


print("=== 反跑：代码运行时协议 ===")

# ---- A：放宽字段名册必填校验 → 缺字段不再被拒 → 红 ----
print("A 变异：放宽必填校验（返回 假 → 返回 真）")
a_src = 备份.replace(
    "    如果 字典包含键(帧, 字段) == 假:\n      返回 假",
    "    如果 字典包含键(帧, 字段) == 假:\n      返回 真",
)
assert a_src != 备份, "A 变异未生效（文本未变）"
写(a_src)
a_rc = 跑("A变异")

# 还原 A
写(备份)

# ---- B：无损检测失效（非无损 永不置真）→ 含非无损值不再被拒 → 红 ----
print("B 变异：无损检测失效（设 非无损 为 真 → 为 假）")
b_src = 备份.replace(
    "      如果 非有限(当前) == 真:\n        设 非无损 为 真\n      否则:\n        如果 是负零(当前) == 真:\n          设 非无损 为 真",
    "      如果 非有限(当前) == 真:\n        设 非无损 为 假\n      否则:\n        如果 是负零(当前) == 真:\n          设 非无损 为 假",
)
assert b_src != 备份, "B 变异未生效（文本未变）"
写(b_src)
b_rc = 跑("B变异")

# 还原 B
写(备份)

# ---- C：截断标记改词 → 标记字符串不符 → 红 ----
print("C 变异：截断标记改词")
c_src = 备份.replace(
    "[dsh-code-runtime-python] log capture truncated at ",
    "[dsh] truncated at ",
)
assert c_src != 备份, "C 变异未生效（文本未变）"
写(c_src)
c_rc = 跑("C变异")

# 还原 C
写(备份)

# ---- 还原后复跑 + 字节级校验 ----
g_rc = 跑("还原后复跑")
还原文本 = open(src, encoding="utf-8").read()
if 还原文本 != 备份:
    print("❌ 文件未完全还原！")
    sys.exit(2)

print("字节级还原校验: OK")
a红 = (a_rc != 0)
b红 = (b_rc != 0)
c红 = (c_rc != 0)
g绿 = (g_rc == 0)
print(f"判据: A红={a红} B红={b红} C红={c红} 还原绿={g绿}")
if a红 and b红 and c红 and g绿:
    print("✅ 反跑成立 (3/3 变异红，还原绿)")
    sys.exit(0)
else:
    print("❌ 反跑不成立")
    sys.exit(1)
