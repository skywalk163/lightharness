#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跨平台回归门（本机 Windows + 0.82 FreeBSD 统一判据）。

演进三代：
* R41：平台能力探测 + 4 个核心用例 rc 比对。
* R44：升级为**回归门**——核心用例扩到真实链路样例，并加 `--mode pytest`
       比对两平台**失败用例集合**（而非仅 rc），避免「都非零但失败项不同」被误判一致。
* R55（本轮）：加 `--mode gate`——**双平台回归门**，解决 "light-merge 全量 pytest
       本机跑不完 / xdist 不稳定"（R54 路M 诊断）：
       - 本机侧：只跑 **lightharness** 全量（~1200 用例，串行 6~7 分钟）→ 快门；
       - 0.82 侧：跑 **light-merge** 全量（8106 用例，FreeBSD 串行）→ 基准；
       - 两侧**各自与自己上一份基线**比「新增红」（不是互比，因为两侧套件不同）；
       - 判据：两侧新增红都为 0 才 rc=0。

`--mode gate` 内部复用两份基建，不重复实现：
  * 本机 pytest 由本脚本跑，结果用 `--junitxml` 落盘，交给 `scripts/回归基线.py` 解析；
  * 0.82 light-merge 全量直接调 `scripts/082全量回归.py test`（同步 + 跑 + 拉回 + 存基线）。

用法：
    python scripts/多平台矩阵.py --mode core                # 本机核心用例
    python scripts/多平台矩阵.py --mode core --remote        # 本机 + 0.82 比对
    python scripts/多平台矩阵.py --mode pytest --remote --sync

    python scripts/多平台矩阵.py --mode gate --local-only    # 只跑本机快门
    python scripts/多平台矩阵.py --mode gate --remote        # 本机 + 0.82 双平台门
    python scripts/多平台矩阵.py --mode gate --remote --sync # 先同步再跑
    python scripts/多平台矩阵.py --mode gate --local-xml reports/本机lh_results.xml
                                                            # 复用已跑完的本机结果，不用重跑
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
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
REPORTS = ROOT / "reports"
SYNC_SCRIPT = SCRIPTS / "同步0.82.py"
REG082_SCRIPT = SCRIPTS / "082全量回归.py"
BASE_LIB = SCRIPTS / "回归基线.py"
PY = "G:/dswork/duan-light-merge/light-merge/.venv/Scripts/python.exe"

# gate 模式：本机跑 lightharness（快门），0.82 跑 light-merge（基准）
LOCAL_BASELINE_PREFIX = "本机lh基线_"
LOCAL_LATEST = REPORTS / f"{LOCAL_BASELINE_PREFIX}latest.json"
LOCAL_PYTEST = ["-m", "pytest", "tests/", "-q", "--tb=no", "-rfE",
                "-o", "addopts=", "-p", "no:cacheprovider", "-p", "no:xdist",
                # addopts 被置空后 --timeout 也被清掉了，这里显式加回来：
                # lightharness 的 test_回归.py 有真实网络/服务器类用例，没有单用例
                # 超时保护会整轮 hang 死（R55 实测：跑到 84% 卡住 8 分钟不动）。
                "--timeout", "60"]

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


def load_base_lib():
    """动态加载 回归基线.py（与 082全量回归.py 共用一套解析/对比口径）。"""
    spec = importlib.util.spec_from_file_location("回归基线", BASE_LIB)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------ gate 模式
def local_baselines() -> list[Path]:
    if not REPORTS.exists():
        return []
    return sorted(p for p in REPORTS.glob(f"{LOCAL_BASELINE_PREFIX}*.json")
                  if p.name != LOCAL_LATEST.name)


def _stamp() -> str:
    return time.strftime("%Y-%m-%d-%H%M%S")


def _stream_proc(cmd, cwd, env, timeout, label="proc"):
    """Popen 逐行转发子进程 stdout/stderr 到本机终端，返回 (rc, 全部输出文本)。

    解决 gate 长任务（本机 6~7 分钟、0.82 全量 25~45 分钟）原来
    capture_output=True 把输出憋到结束才吐、长跑期间完全看不到进度的问题。
    超时保护保留：超 timeout 秒 kill 子进程并返回 rc=124。PYTHONUNBUFFERED=1
    强制子进程无缓冲，保证逐行实时可见（否则 Python 对管道块缓冲会攒批）。
    """
    env = dict(env if env is not None else os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    p = subprocess.Popen(
        cmd, cwd=cwd, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        bufsize=1, text=True, encoding="utf-8", errors="replace",
    )
    buf = []

    def _pump():
        try:
            while True:
                line = p.stdout.readline()
                if not line:
                    break
                sys.stdout.write(line)
                sys.stdout.flush()
                buf.append(line)
        except Exception:
            pass

    thr = threading.Thread(target=_pump, daemon=True)
    thr.start()
    try:
        rc = p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        try:
            p.wait(timeout=30)
        except subprocess.TimeoutExpired:
            pass
        rc = 124
    thr.join(timeout=10)
    return rc, "".join(buf)


def gate_local(args, result: dict, base_lib) -> bool:
    """本机快门：lightharness 全量 pytest（串行）→ 基线 → 与上一份比新增红。"""
    REPORTS.mkdir(parents=True, exist_ok=True)
    history_before = local_baselines()

    if getattr(args, "local_xml", ""):
        xml = Path(args.local_xml)
        xml = xml if xml.is_absolute() else ROOT / xml
        print(f"[本机] 复用已有 junitxml：{xml}")
        elapsed = None
        rc = None
    else:
        xml = REPORTS / f"_本机lh_results_{_stamp()}.xml"
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env.setdefault("LIGHT_MERGE", str(ROOT.parent / "light-merge"))
        t0 = time.monotonic()
        print(f"[本机] lightharness 全量 pytest（串行，超时 {args.timeout}s）…")
        rc, out = _stream_proc([python_cmd(), *LOCAL_PYTEST, "--junitxml", str(xml)],
                               cwd=ROOT, env=env, timeout=args.timeout, label="本机")
        elapsed = round(time.monotonic() - t0, 1)
        tail = normalize(out).strip().splitlines()[-5:]
        print(f"[本机] pytest rc={rc}，耗时 {elapsed}s")
        for ln in tail:
            print("   |", ln)
        if rc == 124:
            print(f"[本机] ⚠️ 本机 pytest 超时 {args.timeout}s（已 kill）")
        if not xml.exists():
            print("[本机] ❌ 没有产出 junitxml")
            result["local"] = {"error": "no junitxml", "ok": False}
            return False

    parsed = base_lib.parse_junit(xml)
    b = base_lib.make_baseline(
        parsed, name="lightharness", platform=f"本机 {platform.system()} {platform.release()}",
        cwd=str(ROOT),
        runner={"mode": "full", "parallel": False, "cmd": " ".join(LOCAL_PYTEST),
                "elapsed_sec": elapsed, "pytest_rc": rc})
    path = REPORTS / f"{LOCAL_BASELINE_PREFIX}{_stamp()}.json"
    base_lib.save_baseline(b, path)
    base_lib.save_baseline(b, LOCAL_LATEST)
    print(f"[本机] 基线写入 {path.name}")

    t = b["totals"]
    print("[本机] 摘要：共 %d 用例，通过 %d，失败 %d，跳过 %d，pytest 自报 %.0fs"
          % (t["total"], t["passed"], t["failed"], t["skipped"], t["duration_sec"]))

    prev = None
    if history_before:
        prev = base_lib.load_baseline(history_before[-1])
    d = base_lib.diff_baselines(prev, b)
    base_lib.print_diff_result(d, label="本机")
    result["local"] = {"baseline": str(path), "totals": t, "diff": d,
                       "ok": bool(d["ok"]), "first_run": prev is None}
    return bool(d["ok"])


def gate_remote(args, result: dict, base_lib, cli=None, sync_mod=None) -> bool:
    """0.82 基准：调 082全量回归.py test 跑 light-merge 全量，再比新增红。"""
    # R57 任务3（G8）：透传 --py（默认仍 3.12）。此前门远端腿写死默认解释器，
    # 想用 3.11 对照跑（无 xdist、串行口径）只能绕过门脚本手工调 082全量回归.py。
    cmd = [python_cmd(), str(REG082_SCRIPT), "test", "--mode", args.mode_082,
           "--py", args.py_082,
           "--timeout-sec", str(args.remote_timeout)]
    print("[0.82] 调用：%s" % " ".join(Path(c).name if Path(c).exists() else c for c in cmd))
    t0 = time.monotonic()
    # ⚠️ 必须按 mtime 排序，不能按文件名：R56 任务4 产出的对拍基线叫
    # `082_lightmerge基线_R53回退_<ts>.json`，字面序 'R' > '2' → 它排在所有
    # `..._2026-*` 之后，按名字取「最后一个」会拿到它，于是门拿同一份基线自比 → **假 PASS**。
    def _by_mtime():
        return sorted((q for q in REPORTS.glob("082_lightmerge基线_*.json")
                       if q.name != "082_lightmerge基线_latest.json"),
                      key=lambda p: p.stat().st_mtime)

    before = _by_mtime()
    rc, out = _stream_proc(cmd, cwd=ROOT, env=os.environ.copy(),
                           timeout=args.remote_timeout + 600, label="0.82")
    elapsed = round(time.monotonic() - t0, 1)
    tail = normalize(out or "").strip().splitlines()[-8:]
    for ln in tail:
        print("   |", ln)
    after = _by_mtime()
    if before and after and before[-1].name == after[-1].name:
        # 兜底断言：跑完了却没多出新基线，说明取基线的逻辑又出问题，别再给假 PASS
        print(f"[0.82] ❌ 没有产出新基线（最新仍是 {after[-1].name}）")
        result["remote"] = {"ok": False, "rc": rc, "elapsed_sec": elapsed,
                            "reason": "no new baseline produced"}
        return False
    if rc != 0 or len(after) <= len(before):
        print(f"[0.82] ❌ 全量回归未产出新基线（rc={rc}，耗时 {elapsed}s）")
        result["remote"] = {"ok": False, "rc": rc, "elapsed_sec": elapsed}
        return False

    cur = base_lib.load_baseline(after[-1])
    prev = base_lib.load_baseline(before[-1]) if before else None
    d = base_lib.diff_baselines(prev, cur)
    print(f"[0.82] 对比：{after[-1].name}  ⟵  {before[-1].name if before else '(无历史)'}")
    base_lib.print_diff_result(d, label="0.82")
    t = cur["totals"]
    result["remote"] = {"baseline": str(after[-1]), "totals": t, "diff": d,
                        "ok": bool(d["ok"]), "elapsed_sec": elapsed,
                        "first_run": prev is None}
    return bool(d["ok"])


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
def run_legacy(args, result: dict) -> bool:
    """R44 起的老行为（core / pytest 两平台互比），本轮原样保留以向后兼容。"""
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
    return bool(gate["ok"])


def run_gate(args, result: dict) -> bool:
    """R55 双平台回归门：本机 lightharness（快门）+ 0.82 light-merge（基准）。

    两侧套件不同，所以**各自与自己上一份基线**比新增红，不互比失败集合。
    """
    base_lib = load_base_lib()
    REPORTS.mkdir(parents=True, exist_ok=True)
    print("=== 跨平台回归门 gate（本机 lightharness + 0.82 light-merge）===")
    t0 = time.monotonic()
    lok = gate_local(args, result, base_lib)
    rok = True
    if not args.local_only:
        if args.sync:
            print("[门] 先同步 0.82…")
            rc = subprocess.run([python_cmd(), str(SYNC_SCRIPT), "sync"],
                                cwd=ROOT, check=False).returncode
            if rc != 0:
                print(f"[门] ❌ 同步失败 rc={rc}")
                result["gate"] = {"ok": False, "reason": "sync failed"}
                return False
        rok = gate_remote(args, result, base_lib)
    ok = lok and rok
    result["gate"] = {"local_ok": lok, "remote_ok": rok, "ok": ok,
                      "elapsed_sec": round(time.monotonic() - t0, 1),
                      "judge": "两侧各自与自身上一份基线比新增红，均为 0 才通过"}
    print("=== 门 ===", "PASS ✅" if ok else "FAIL ❌",
          f"（本机 {'✅' if lok else '❌'} ｜ 0.82 {'✅' if rok else '❌'}，"
          f"总耗时 {result['gate']['elapsed_sec']:.0f}s）")
    return ok


def write_report(args, result: dict) -> Path | None:
    if not args.output:
        return None
    out = Path(args.output)
    out = out if out.is_absolute() else ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8", newline="\n")
    print("JSON", out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="R55 跨平台回归门（core / pytest / gate）")
    ap.add_argument("--mode", choices=["core", "pytest", "gate"], default="core")
    ap.add_argument("--remote", action="store_true", help="同时跑 0.82 并比对")
    ap.add_argument("--sync", action="store_true", help="比对前先全量重同步 0.82")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--output", default="")
    # gate 模式专用
    ap.add_argument("--local-only", action="store_true", help="gate：只跑本机快门")
    ap.add_argument("--remote-timeout", type=int, default=2700,
                    help="gate：0.82 侧硬超时秒数（默认 2700，与 --timeout 分开，"
                         "因为两侧套件规模差 6 倍）")
    ap.add_argument("--local-xml", default="",
                    help="gate：复用已跑完的本机 junitxml，跳过本机重跑")
    ap.add_argument("--mode-082", choices=["fast", "full"], default="fast",
                    help="gate：0.82 侧 fast（-m 'not slow'）/ full")
    ap.add_argument("--py", dest="py_082", default="/usr/local/bin/python3.12",
                    help="gate：0.82 侧解释器（默认 /usr/local/bin/python3.12，带 xdist；"
                         "传 3.11 时 082全量回归.py 会按其口径置空 addopts 串行跑）。"
                         "R57 任务3（G8）：门远端腿此前写死默认值，不透传此参数。")
    args = ap.parse_args()

    result = {"schema": 3, "round": "R55", "mode": args.mode,
              "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
              "local_platform": probe(), "local": {}, "remote": {}, "gate": {}}

    ok = run_gate(args, result) if args.mode == "gate" else run_legacy(args, result)
    write_report(args, result)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
