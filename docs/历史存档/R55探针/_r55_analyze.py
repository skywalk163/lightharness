# -*- coding: utf-8 -*-
"""R55 探针5：0.82 light-merge 基线失败项归类 + 与 light-merge 自带 CI 基线交叉核对。"""
from __future__ import annotations
import importlib.util
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
LH = ROOT / "lightharness"
BASE = LH / "reports" / "082_lightmerge基线_latest.json"
CI_BASE = ROOT / "light-merge" / "tests" / "ci_baseline_failures.txt"

b = json.loads(BASE.read_text(encoding="utf-8"))
t = b["totals"]
print("== 0.82 light-merge 基线 ==")
print({k: t[k] for k in ("total", "passed", "failed", "failure", "error", "skipped", "xfailed", "duration_sec")})

# 1) 按文件归类
by_file = Counter(f["file"] for f in b["failed"])
print("\n== 失败按文件分布（前 20）==")
for f, n in by_file.most_common(20):
    print(f"  {n:4d}  {f}")

# 2) 按失败原因关键词归类
def cls(msg: str) -> str:
    m0 = msg
    m = m0.lower()
    for kw, label in [
        ("cryptography", "缺可选依赖 cryptography"),
        ("lunardate", "缺可选依赖 lunardate"),
        ("modulenotfounderror", "缺可选依赖（其他模块）"),
        ("importerror", "ImportError"),
        ("nameerror", "NameError（代码生成符号缺失）"),
        ("parseerror", "ParseError（词法/语法）"),
        ("timeoutexpired", "超时"),
        ("filenotfounderror", "文件缺失"),
        ("keyerror", "KeyError"),
        ("valueerror", "ValueError"),
        ("typeerror", "TypeError"),
        ("syntaxerror", "SyntaxError"),
        ("runtimeerror", "RuntimeError"),
    ]:
        if kw in m:
            return label
    if m.startswith("assert ") or "assertionerror" in m:
        return "AssertionError（行为/代码生成不符）"
    return "其他"

by_cls = Counter(cls(f["message"]) for f in b["failed"])
print("\n== 失败按原因归类 ==")
for c, n in by_cls.most_common():
    print(f"  {n:4d}  {c}")

# 3) 与 light-merge 自带 CI 基线交叉核对
# 3) 补出 cid（本轮首份基线写得早，没有 cid 字段 → 从 junitxml 补齐）
import xml.etree.ElementTree as ET
xmls = sorted((LH / "reports").glob("_082_lm_results_*.xml"))
cid_map: dict[str, str] = {}
if xmls:
    for tc in ET.parse(xmls[-1]).getroot().iter("testcase"):
        file_ = tc.get("file") or ""
        ident = f"{file_}::{tc.get('name','')}"
        cid_map[ident] = f"{tc.get('classname','')}::{tc.get('name','')}"

print("\n== 「其他」失败样例（前 10 条原文截断）==")
n = 0
for f in b["failed"]:
    if cls(f["message"]) == "其他":
        print("   ", f["id"][:70], "|", f["message"][:100])
        n += 1
        if n >= 10:
            break

if CI_BASE.exists():
    lines = [l.strip() for l in CI_BASE.read_text(encoding="utf-8", errors="ignore").splitlines()]
    ci_ids = {l for l in lines if l and not l.startswith("#")}
    our_cids = {cid_map.get(f["id"], f["id"]) for f in b["failed"]}
    print(f"\n== 与 light-merge 自带 CI 基线（tests/ci_baseline_failures.txt，{len(ci_ids)} 条）交叉核对 ==")
    print(f"  双方都红：{len(ci_ids & our_cids)}")
    print(f"  只在我们这轮红（CI 基线里没有）：{len(our_cids - ci_ids)}")
    print(f"  只在 CI 基线里红（本轮未跑/已绿）：{len(ci_ids - our_cids)}")
    only = sorted(our_cids - ci_ids)
    print("  本轮独有红（前 15 条）：")
    for i in only[:15]:
        print("    ", i)
    missing = sorted(ci_ids - our_cids)
    if missing:
        print("  CI 基线独有（前 10 条）：")
        for i in missing[:10]:
            print("    ", i)
else:
    print("\n[warn] 找不到 light-merge CI 基线文件")
