#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R41 任务4：标准库多平台回归矩阵（本机执行与结果比对）。"""
from __future__ import annotations
import argparse, hashlib, json, locale, os, platform, socket, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("cli", ["运行.py", "examples/test_CLI命令面.light"]),
    ("r39-system-prompt", ["运行.py", "examples/test_R39_系统提示.light"]),
    ("r39-scope", ["运行.py", "examples/test_R39_作用域.light"]),
    ("r40-integration", ["运行.py", "examples/test_R40_端到端互举.light"]),
]

def python_cmd():
    return os.environ.get("R41_PYTHON") or sys.executable

def normalize(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")

def digest(text):
    return hashlib.sha256(normalize(text).encode("utf-8", "replace")).hexdigest()[:16]

def probe():
    return {
        "os": platform.system(), "release": platform.release(), "machine": platform.machine(),
        "python": platform.python_version(), "shell": os.environ.get("SHELL") or os.environ.get("COMSPEC", ""),
        "path_separator": os.sep, "line_separator": repr(os.linesep),
        "preferred_encoding": locale.getpreferredencoding(False),
        "filesystem_encoding": sys.getfilesystemencoding(), "socket_ipv6": bool(socket.has_ipv6),
        "env_case_sensitive_observed": os.environ.get("Path") != os.environ.get("PATH"),
    }

def run_case(name, args):
    env = os.environ.copy(); env["PYTHONIOENCODING"] = "utf-8"
    t0 = time.monotonic()
    p = subprocess.run([python_cmd(), *args], cwd=ROOT, env=env, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=300)
    output = normalize((p.stdout or "") + (p.stderr or ""))
    return {"name": name, "rc": p.returncode, "elapsed_sec": round(time.monotonic()-t0, 3),
            "output_digest": digest(output), "output_lines": len(output.splitlines()),
            "tail": output.splitlines()[-5:]}

def main(argv=None):
    ap = argparse.ArgumentParser(description="R41 多平台回归矩阵")
    ap.add_argument("--output", default="", help="JSON 结果路径")
    ap.add_argument("--compare", default="", help="另一平台 JSON，比较用例 rc")
    args = ap.parse_args(argv)
    result = {"schema": 1, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
              "root": str(ROOT), "platform": probe(), "cases": []}
    for name, cmd in CASES:
        item = run_case(name, cmd); result["cases"].append(item)
        print(("PASS" if item["rc"] == 0 else "FAIL"), name, "rc=%d" % item["rc"],
              "%.3fs" % item["elapsed_sec"])
    result["ok"] = all(x["rc"] == 0 for x in result["cases"])
    if args.compare:
        other = json.loads(Path(args.compare).read_text(encoding="utf-8"))
        mine = {x["name"]: x["rc"] for x in result["cases"]}
        theirs = {x["name"]: x["rc"] for x in other.get("cases", [])}
        result["comparison"] = {"rc_equal": mine == theirs, "local": mine, "other": theirs}
        result["ok"] = result["ok"] and mine == theirs
        print("COMPARE", "PASS" if mine == theirs else "FAIL")
    if args.output:
        out = Path(args.output); out = out if out.is_absolute() else ROOT / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8", newline="\n")
        print("JSON", out)
    return 0 if result["ok"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
