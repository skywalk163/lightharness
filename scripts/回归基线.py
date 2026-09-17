# -*- coding: utf-8 -*-
"""第55轮 任务2/3/4 —— 回归基线公共库（JUnit XML → 结构化基线 JSON → 基线 diff）。

被两个脚本共用，避免「两处各写一套解析」导致基线口径对不上：

* ``scripts/082全量回归.py``  —— 0.82 上跑 light-merge 全量 pytest（任务2）
* ``scripts/多平台矩阵.py``    —— 本机 lightharness + 0.82 light-merge 跨平台回归门（任务4）

基线判据统一为**新增红**：当前轮失败集合 − 上一轮失败集合 = ∅ 才算通过。
这样「预存失败」不会被误判为回归，符合 R41 以来的 CI 门禁口径
（参考 light-merge 的 ``check_regression.py --baseline``）。

基线 JSON 结构（schema 1）：
    {
      "schema": 1, "generated_at": ..., "round": "R55",
      "target":  {"name","platform","host","remote_dir","cwd"},
      "runner":  {"mode","parallel","timeout_sec","marker","cmd"},
      "totals":  {"total","passed","failed","error","skipped","xfailed","duration_sec"},
      "failed":  [{"id","status","file","message"}],   # failure / error 全量明细
      "skipped": ["id", ...]
    }
只存非通过项明细 + 计数，保证 4000+ 用例的基线文件仍可读、可 diff。
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

SCHEMA = 1

# 计入「红」的状态：failure（断言失败）+ error（fixture/收集/teardown 报错）
RED_STATUSES = ("failure", "error")


# --------------------------------------------------------------- JUnit 解析
def parse_junit(xml_path: Path) -> dict:
    """把 pytest --junitxml 的 XML 解析成统一的 cases/totals 结构。"""
    xml_path = Path(xml_path)
    root = ET.parse(xml_path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))

    cases: list[dict] = []
    duration = 0.0
    for su in suites:
        try:
            duration += float(su.get("time") or 0.0)
        except ValueError:
            pass
        for tc in su.findall("testcase"):
            cases.append(_case_record(tc))

    totals = {"total": len(cases)}
    for st in ("passed", "failure", "error", "skipped", "xfailed", "xpassed"):
        if st == "passed":
            continue
        totals[st] = sum(1 for c in cases if c["status"] == st)
    totals["passed"] = len(cases) - sum(totals[k] for k in ("failure", "error", "skipped", "xfailed", "xpassed"))
    totals["failed"] = totals["failure"] + totals["error"]
    totals["duration_sec"] = round(duration, 3)
    return {"totals": totals, "cases": cases}


def _case_record(tc: ET.Element) -> dict:
    classname = tc.get("classname", "") or ""
    name = tc.get("name", "") or ""
    file_ = tc.get("file") or _classname_to_file(classname)
    ident = f"{file_}::{name}" if file_ else f"{classname}::{name}"

    status = "passed"
    message = ""
    kind = ""
    for tag in ("failure", "error", "skipped"):
        el = tc.find(tag)
        if el is None:
            continue
        kind = el.get("type") or tag
        if tag == "skipped" and "xfail" in (el.get("type") or "").lower():
            status = "xfailed"
        elif tag == "skipped":
            status = "skipped"
        else:
            status = tag
        message = _first_line(el.get("message") or el.text or "")
        break

    try:
        t = float(tc.get("time") or 0.0)
    except ValueError:
        t = 0.0
    return {"id": ident, "file": file_, "classname": classname, "name": name,
            "status": status, "kind": kind, "message": message, "time": round(t, 3)}


def _classname_to_file(classname: str) -> str:
    """``tests.test_lexer.TestFoo`` → ``tests/test_lexer.py::TestFoo`` 退化的粗略还原。

    仅在 XML 没有 ``file`` 属性时才用（pytest 9 的 junitxml 是带 file 的）。
    """
    if not classname:
        return ""
    parts = classname.split(".")
    out: list[str] = []
    for p in parts:
        if not out:
            out.append(p)
        elif p[:1].isupper():          # 类名起点，其后的都归到 classname 部分
            break
        else:
            out.append(p)
    return "/".join(out) + ".py"


def _first_line(text: str, limit: int = 300) -> str:
    line = ""
    for ln in (text or "").splitlines():
        if ln.strip():
            line = ln.strip()
            break
    return line[:limit]


# --------------------------------------------------------------- 基线读写
def make_baseline(parsed: dict, *, name: str, platform: str, runner: dict,
                  host: str = "", remote_dir: str = "", cwd: str = "",
                  round_: str = "R55") -> dict:
    cases = parsed["cases"]
    return {
        "schema": SCHEMA,
        "round": round_,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "target": {"name": name, "platform": platform, "host": host,
                   "remote_dir": remote_dir, "cwd": cwd},
        "runner": runner,
        "totals": parsed["totals"],
        # id = 文件::用例名（跨平台稳定）；cid = classname::name（与 light-merge 自带
        # tests/ci_baseline_failures.txt 同一口径，便于和它的 CI 基线交叉核对）
        "failed": [{"id": c["id"], "cid": f"{c['classname']}::{c['name']}",
                    "status": c["status"], "file": c["file"],
                    "message": c["message"]}
                   for c in cases if c["status"] in RED_STATUSES],
        "skipped": [c["id"] for c in cases if c["status"] in ("skipped", "xfailed")],
    }


def save_baseline(baseline: dict, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")
    return path


def load_baseline(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def red_ids(baseline: dict) -> set[str]:
    return {f["id"] for f in baseline.get("failed", [])}


# --------------------------------------------------------------- 基线对比
def diff_baselines(base: dict | None, new: dict) -> dict:
    """对比两条基线：新增红 / 已修复 / 持平。

    base 为 None（首次跑，无历史基线）时：本轮全部失败视为「预存」而非新增红，
    这样首轮可以通过并把当前状态固化成基线；从第二轮起才真正拦新增红。
    """
    old = red_ids(base) if base else set()
    cur = red_ids(new)
    first = base is None
    new_red = sorted(cur - old)
    return {
        "base_generated_at": (base or {}).get("generated_at"),
        "new_generated_at": new.get("generated_at"),
        "base_total": (base or {}).get("totals", {}).get("total"),
        "new_total": new.get("totals", {}).get("total"),
        "base_failed": len(old),
        "new_failed": len(cur),
        "new_red": new_red,                    # 真正的新增红：判据（首次跑为空）
        "recorded": sorted(cur) if first else [],  # 首次跑：全部失败原样记为基线
        "fixed": sorted(old - cur),            # 已修复
        "unchanged_red": sorted(cur & old),    # 持平的老红
        "first_run": first,
        # 首次跑没有历史可比，本轮失败就是「现状」，不能算新增红，否则门永远第一跑就红
        "ok": first or len(new_red) == 0,
    }


def print_diff_result(d: dict, label: str = "") -> None:
    tag = f"[{label}] " if label else ""
    print(f"{tag}失败数 {d['base_failed']} → {d['new_failed']}"
          f"（{d['base_total']} → {d['new_total']} 用例）")
    if d["first_run"]:
        print(f"{tag}首次跑：{len(d['recorded'])} 条失败记为基线，不判新增红 ✅")
        for i in d["recorded"][:30]:
            print(f"{tag}    ✗ {i}")
        return
    print(f"{tag}新增红 {len(d['new_red'])} ｜ 已修复 {len(d['fixed'])} ｜ 持平 {len(d['unchanged_red'])}")
    if d["fixed"]:
        print(f"{tag}  已修复样例：{d['fixed'][:5]}")
    if d["new_red"]:
        print(f"{tag}  ❌ 新增红清单（前 30 条）：")
        for i in d["new_red"][:30]:
            print(f"{tag}    {i}")
    else:
        print(f"{tag}  ✅ 零新增红（含 {len(d['unchanged_red'])} 条存量失败）")
