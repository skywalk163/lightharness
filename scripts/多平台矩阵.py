#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第44轮 任务5 —— 跨平台回归门（本机 Windows + 0.82 FreeBSD 统一判据）。

R41 版只做「平台能力探测 + 4 个核心用例 rc 比对」。本轮升级为**回归门**：

* 核心用例集扩充到 R41~R45 的真实链路样例（网络/文件/webhook/bash/LLM往返/agent循环/影子变量告警/子进程）。
* 新增 `--mode pytest`：两平台各跑全量 pytest，比对**失败用例集合**（而非仅 rc），
  避免「都非零退出但失败项不同」被误判为一致。
* 远端执行复用 `scripts/同步0.82.py`（paramiko + 只读 /tmp 副本 + python 垫片），
  不重复实现传输层；`--sync` 可先做一次全量重同步。
* 判据（硬）：两平台每个用例 rc 相等，且（pytest 模式）失败集合相等 → 退出码 0。

用法：
    python scripts/多平台矩阵.py --mode core                # 本机核心用例
    python scripts/多平台矩阵.py --mode core --remote        # 本机 + 0.82 比对
    python scripts/多平台矩阵.py --mode pytest --remote --sync
    python scripts/多平台矩阵.py --mode core --output reports/矩阵.json
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import locale
import os
import platform
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYNC_SCRIPT = ROOT / "scripts" / "同步0.82.py"
PY = "G:/dswork/duan-light-merge/light-merge/.venv/Scripts/python.exe"

# 核心用例：R41 四项 + R41~R43 真实链路（跨平台语义稳定，不含平台专属断言）
CASES = [
    ("cli", "examples/test_CLI命令面.light"),
    ("r39-system-prompt", "examples/test_R39_系统提示.light"),
    ("r39-scope", "examples/test_R39_作用域.light"),
    ("r40-integration", "examples/test_R40_端到端互举.light"),
    ("r41-file-io", "examples/test_R41_真实文件IO.light"),
    ("r41-net-io", "examples/test_R41_真实网络IO.light"),
    ("r42-fetch", "examples/test_R42_真实抓取.light"),
    ("r42-webhook", "examples/test_R42_真实webhook.light"),
    ("r42-bash-cross", "examples/test_R42_bash跨平台.light"),
    ("r42-toolchain", "examples/test_R42_真实工具链.light"),
    ("r43-llm-roundtrip", "examples/test_R43_真实LLM往返.light"),
    ("r43-agent-loop", "examples/test_R43_真实agent循环.light"),
    # R45：影子变量告警载体（stderr 告警 + rc=0）、以及本轮加固的两个子进程用例
    # （不再写死 python，改用运行器注入的 HARNESS_PY）
    ("r45-shadow-warning", "examples/test_R45_影子变量告警.light"),
    ("r45-subprocess-bg", "examples/test_子进程后台.light"),
    ("r45-subprocess-code", "examples/test_子进程码.light"),
]

FAILED_LINE = re.compile(r"^(FAILED|ERROR)\s+(\S+)")


def python_cmd() -> str:
    return os.environ.get("R41_PYTHON") or PY


def normalize(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def digest(text: str) -> str:
    return hashlib.sha256(normalize(text).encode("utf-8", "replace")).hexdigest()[:16]


def probe() -> dict:
    return {
        "os": platform.system(), "release": platform.release(), "machine": platform.machine(),
        "python": platform.python_version(),
        "shell": os.environ.get("SHELL") or os.environ.get("COMSPEC", ""),
        "path_separator": os.sep, "line_separator": repr(os.linesep),
        "preferred_encoding": locale.getpreferredencoding(False),
        "filesystem_encoding": sys.getfilesystemencoding(),
        "socket_ipv6": bool(socket.has_ipv6),
    }


# ----------------------------------------------------------------- 远端
def load_sync_module():
    """动态加载 同步0.82.py（文件名含点，不能常规 import）。"""
    spec = importlib.util.spec_from_file_location("sync082", SYNC_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_local(args, timeout=600) -> dict:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    t0 = time.monotonic()
    p = subprocess.run([python_cmd(), *args], cwd=ROOT, env=env, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=timeout)
    out = normalize((p.stdout or "") + (p.stderr or ""))
    return {"rc": p.returncode, "elapsed_sec": round(time.monotonic() - t0, 3),
            "output_digest": digest(out), "output_lines": len(out.splitlines()),
            "tail": out.splitlines()[-5:], "raw": out}


def run_remote(mod, cli, remote_dir: str, args, timeout=1800) -> dict:
    cmd = " ".join(args)
    full = (f"cd {remote_dir}/lightharness && export LIGHT_MERGE={remote_dir}/light-merge && "
            f"export PATH={mod.SHIM_DIR}:$PATH && export PYTHONIOENCODING=utf-8 && {cmd}")
    t0 = time.monotonic()
    rc, out = mod.run_remote(cli, full, timeout=timeout, quiet=True)
    out = normalize(out)
    return {"rc": rc, "elapsed_sec": round(time.monotonic() - t0, 3),
            "output_digest": digest(out), "output_lines": len(out.splitlines()),
            "tail": out.splitlines()[-5:], "raw": out}


def parse_failures(raw: str) -> list[str]:
    ids = []
    for line in raw.splitlines():
        m = FAILED_LINE.match(line.strip())
        if m:
            ids.append(m.group(2))
    return sorted(ids)


# ----------------------------------------------------------------- 主流程
def main() -> int:
    ap = argparse.ArgumentParser(description="R44 跨平台回归门")
    ap.add_argument("--mode", choices=["core", "pytest"], default="core")
    ap.add_argument("--remote", action="store_true", help="同时跑 0.82 并比对")
    ap.add_argument("--sync", action="store_true", help="比对前先全量重同步 0.82")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--output", default="")
    args = ap.parse_args()

    result = {"schema": 2, "round": "R44", "mode": args.mode,
              "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
              "local_platform": probe(), "local": {}, "remote": {}, "gate": {}}

    # 本机
    print(f"=== 本机（{platform.system()} {platform.release()}）mode={args.mode} ===")
    if args.mode == "core":
        cases = {}
        for name, path in CASES:
            r = run_local(["运行.py", path], timeout=args.timeout)
            r.pop("raw", None)
            cases[name] = r
            print(("PASS" if r["rc"] == 0 else "FAIL"), name, "rc=%d" % r["rc"], "%.2fs" % r["elapsed_sec"])
        result["local"] = {"cases": cases,
                           "all_rc_zero": all(c["rc"] == 0 for c in cases.values())}
    else:
        r = run_local(["-m", "pytest", "tests/", "-q", "-p", "no:cacheprovider", "--tb=no"],
                      timeout=args.timeout)
        failed = parse_failures(r["raw"])
        result["local"] = {"rc": r["rc"], "elapsed_sec": r["elapsed_sec"],
                           "failed": failed, "failed_count": len(failed),
                           "tail": r["tail"]}
        print("本机 pytest rc=%d，失败 %d：%s" % (r["rc"], len(failed), failed))

    # 0.82
    if args.remote:
        mod = load_sync_module()
        print("=== 0.82（FreeBSD 15.1）===")
        cli = mod.connect()
        try:
            mod.ensure_shim(cli)
            remote_dir = mod.load_remote_dir()
            if args.sync:
                print("[门] 先做全量重同步…")
                rc, _ = mod.run_remote(cli, "true", quiet=True)
                # 同步需在本地打包上传，交由子命令完成
                subprocess.run([python_cmd(), str(SYNC_SCRIPT), "sync"], cwd=ROOT, check=False)
                remote_dir = mod.load_remote_dir()
            print(f"[门] 远端副本 {remote_dir}")
            if args.mode == "core":
                cases = {}
                for name, path in CASES:
                    r = run_remote(mod, cli, remote_dir, [mod.PY, "运行.py", path], timeout=args.timeout)
                    r.pop("raw", None)
                    cases[name] = r
                    print(("PASS" if r["rc"] == 0 else "FAIL"), name, "rc=%d" % r["rc"], "%.2fs" % r["elapsed_sec"])
                result["remote"] = {"cases": cases,
                                    "all_rc_zero": all(c["rc"] == 0 for c in cases.values())}
            else:
                r = run_remote(mod, cli, remote_dir,
                               [mod.PY, "-m", "pytest", "tests/", "-q", "-p", "no:cacheprovider", "--tb=no"],
                               timeout=args.timeout)
                failed = parse_failures(r["raw"])
                result["remote"] = {"rc": r["rc"], "elapsed_sec": r["elapsed_sec"],
                                    "failed": failed, "failed_count": len(failed),
                                    "tail": r["tail"]}
                print("0.82 pytest rc=%d，失败 %d：%s" % (r["rc"], len(failed), failed))
        finally:
            cli.close()

    # 判据
    gate = {"rc_equal": None, "failures_equal": None, "ok": False}
    if args.remote:
        if args.mode == "core":
            lr = {k: v["rc"] for k, v in result["local"]["cases"].items()}
            rr = {k: v["rc"] for k, v in result["remote"]["cases"].items()}
            gate["rc_equal"] = lr == rr
            gate["local_rc"] = lr
            gate["remote_rc"] = rr
            gate["ok"] = bool(gate["rc_equal"]) and result["local"]["all_rc_zero"]
        else:
            lf = result["local"]["failed"]
            rf = result["remote"]["failed"]
            gate["failures_equal"] = lf == rf
            gate["ok"] = bool(gate["failures_equal"])
        print("=== 门 ===", "PASS ✅" if gate["ok"] else "FAIL ❌")
    else:
        gate["ok"] = (result["local"].get("all_rc_zero", False) if args.mode == "core"
                      else result["local"].get("rc", 1) == 0)
        print("=== 门（仅本机）===", "PASS ✅" if gate["ok"] else "FAIL ❌")
    result["gate"] = gate

    if args.output:
        out = Path(args.output)
        out = out if out.is_absolute() else ROOT / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8", newline="\n")
        print("JSON", out)
    return 0 if gate["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
