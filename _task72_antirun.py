# -*- coding: utf-8 -*-
"""
反跑验证脚本（对齐任务书门禁：源被改反 → 测试立红 rc≠0；还原 → 复绿）。
- 不写 /tmp（此前踩过 windows python /tmp 不存在的坑），绿色原文全程驻留内存。
- 5 个独立单点破坏，逐一轮换应用，确认每个对应 反跑_ 断言变红。
- 末尾把 预设.light 还原为绿色原文并跑一次复绿确认。
"""
import subprocess, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "预设.light")
RUN = os.path.join(HERE, "运行.py")
PY = "C:/Users/skywalk/.workbuddy/binaries/python/versions/3.13.12/python.exe"

with open(SRC, "r", encoding="utf-8") as f:
    ORIG = f.read()

# 5 个独立单点破坏（old -> new），每个对应一个 反跑_ 断言
BREAKS = [
    ("标识合法 首字符闸",
     '  如果 (标识[0] == "-"): 返回 假',
     '  如果 (标识[0] == "X"): 返回 假'),
    ("条目列表问题 空名闸",
     '或 名 == ""):',
     '或 名 == "BREAK"):'),
    ("扫描根排序 比较方向",
     '      如果 (应前(b, a) == 真): 设 结果 为 交换元素(结果, i, j)',
     '      如果 (应前(a, b) == 真): 设 结果 为 交换元素(结果, i, j)'),
    ("在纤维内 未命中闸",
     '    如果 (字典包含键(纤维表, 当前) == 假): 返回 假',
     '    如果 (字典包含键(纤维表, 当前) == 假): 返回 真'),
    ("预设投影应用 selected 推进",
     '  如果 (动作["type"] == "agent-preset/selected"): 返回 动作["data"]["agentPreset"]',
     '  如果 (动作["type"] == "agent-preset/BREAK"): 返回 动作["data"]["agentPreset"]'),
]

def run_test():
    p = subprocess.run([PY, RUN, "examples/test_预设.light"],
                       cwd=HERE, capture_output=True, text=True, encoding="utf-8")
    out = (p.stdout or "") + (p.stderr or "")
    rc = p.returncode
    label = ""
    for line in out.splitlines():
        if "断言失败[" in line:
            label = line.split("断言失败[", 1)[1].split("]", 1)[0]
            break
    return rc, label, out.strip()

print("=" * 60)
print("BASELINE 先确认绿色原文")
rc, label, out = run_test()
print(f"  rc={rc}  label={label}  通过={'--- 测试预设 通过 ---' in out}")
assert rc == 0 and "--- 测试预设 通过 ---" in out, "绿色基线居然没过，脚本中止"

results = []
for name, old, new in BREAKS:
    broken = ORIG.replace(old, new, 1)
    assert broken != ORIG, f"破坏点未命中：{name}"
    with open(SRC, "w", encoding="utf-8") as f:
        f.write(broken)
    rc, label, out = run_test()
    ok = (rc != 0) and (label != "")
    results.append((name, rc, label, ok))
    print(f"[破坏] {name:24s} rc={rc} 首个失败断言={label}  {'OK红' if ok else 'XX未红'}")
    with open(SRC, "w", encoding="utf-8") as f:
        f.write(ORIG)

# 最终复绿确认
rc, label, out = run_test()
green_ok = (rc == 0) and ("--- 测试预设 通过 ---" in out)
print("=" * 60)
print(f"FINAL 还原后复绿: rc={rc} 通过={'--- 测试预设 通过 ---' in out}")
print("=" * 60)
print("反跑汇总（应全部 OK红）:")
allred = True
for name, rc, label, ok in results:
    print(f"  {'OK' if ok else 'XX'} {name:24s} -> {label}")
    allred = allred and ok
print("=" * 60)
print("结论:", "5 组独立破坏全部立红 + 还原复绿" if (allred and green_ok) else "存在未达标项，见上")
sys.exit(0 if (allred and green_ok) else 1)
