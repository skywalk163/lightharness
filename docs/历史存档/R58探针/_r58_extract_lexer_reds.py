# -*- coding: utf-8 -*-
"""R58 任务1：从 R57 存量红明细中抽出「词法层」16 条工作底表。只读。"""
import json, io, sys, os

ROOT = r"G:\dswork\duan-light-merge\lightharness"
SRC = os.path.join(ROOT, "reports", "_task4_R57_存量红明细_072454.json")
OUT = os.path.join(ROOT, "_r58_lexer_reds.txt")

d = json.load(open(SRC, encoding="utf-8"))
print("meta:", json.dumps(d["meta"], ensure_ascii=False)[:600])

rows = []
for r in d["baseline_reds"]:
    cat = str(r.get("category", ""))
    if cat.startswith("词法层"):
        rows.append(r)

lines = []
lines.append("总 baseline_reds=%d  其中词法层=%d" % (len(d["baseline_reds"]), len(rows)))
lines.append("")
for i, r in enumerate(rows, 1):
    lines.append("### [%02d] %s" % (i, r.get("id", "")))
    for k, v in r.items():
        if k == "id":
            continue
        sv = str(v).replace("\n", " | ")
        if len(sv) > 900:
            sv = sv[:900] + " …(截断)"
        lines.append("    %s: %s" % (k, sv))
    lines.append("")

txt = "\n".join(lines)
io.open(OUT, "w", encoding="utf-8").write(txt)
print(txt[:12000])
print("\n--- written ->", OUT)
