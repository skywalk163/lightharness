# _task73_antirun.py —— C 线 #73 反跑验证
# 规则：绿色原文驻留内存；每次从原文重做单点破坏写入 src/交互命令.light，
#       运行 examples/test_交互命令.light，确认 rc != 0（变红），随后立即还原。
#       末尾复绿确认 rc == 0。全程不使用 /tmp。
import subprocess, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "交互命令.light")
TEST = os.path.join(HERE, "examples", "test_交互命令.light")
RUNNER = os.path.join(HERE, "运行.py")

# 绿色原文（驻留内存，永不改）
ORIGINAL = open(SRC, encoding="utf-8").read()

# 5 个独立单点破坏： (编号, 标签, 旧串, 新串)
MUTATIONS = [
    ("①解析命令末尾返回改空",
     '  返回 {"name":名, "rawInput":余}',
     '  返回 空'),
    ("②推导预设首命中改返回custom",
     '    如果 (规格["sandbox"] == 沙箱 且 规格["approval"] == 审批): 返回 名',
     '    如果 (规格["sandbox"] == 沙箱 且 规格["approval"] == 审批): 返回 自定义预设'),
    ("③有效权限预设逆序改从0",
     '  设 i 为 长 - 1',
     '  设 i 为 0'),
    ("④校验提问请求空问题闸删",
     '  如果 (字典包含键(请求, "questions") == 假): 抛出 新建 错误("EMPTY_QUESTIONS")\n'
     '  设 问题表 为 请求["questions"]\n'
     '  如果 (是列表(问题表) == 假 或 列表长度(问题表) == 0): 抛出 新建 错误("EMPTY_QUESTIONS")',
     '  设 问题表 为 []\n'
     '  如果 (字典包含键(请求, "questions") == 真): 设 问题表 为 请求["questions"]\n'
     '  如果 (假): 抛出 新建 错误("EMPTY_QUESTIONS")'),
    ("⑤校验命令生命周期重复run闸删",
     '      如果 (列表包含(已见运行, id) == 真): 失败("command/run repeats commandId " + id)',
     '      如果 (假): 失败("command/run repeats commandId " + id)'),
]

def run_test():
    p = subprocess.run([sys.executable, RUNNER, TEST],
                       cwd=HERE, capture_output=True, text=True)
    return p.returncode

def restore():
    open(SRC, "w", encoding="utf-8").write(ORIGINAL)

results = []
try:
    for tag, old, new in MUTATIONS:
        mutated = ORIGINAL.replace(old, new, 1)
        if mutated == ORIGINAL:
            results.append((tag, "FAIL-未命中目标串", None))
            continue
        open(SRC, "w", encoding="utf-8").write(mutated)
        rc = run_test()
        red = (rc != 0)
        results.append((tag, "RED" if red else "FAIL-仍绿", rc))
        restore()  # 立即还原
finally:
    restore()  # 任何异常也还原

# 末尾复绿确认
rc_green = run_test()
print("=== 反跑结果 ===")
all_red = True
for tag, status, rc in results:
    print(f"  {tag}: {status} (rc={rc})")
    if status != "RED":
        all_red = False
print(f"=== 复绿确认: rc={rc_green} ({'GREEN-OK' if rc_green == 0 else 'GREEN-FAIL'}) ===")
if all_red and rc_green == 0:
    print("SCRIPT_RC=0  # 5/5 全红 + 还原复绿")
    sys.exit(0)
else:
    print("SCRIPT_RC=1  # 反跑未达标")
    sys.exit(1)
