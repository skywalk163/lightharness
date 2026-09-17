# -*- coding: utf-8 -*-
"""第55轮 任务2 —— 0.82 全量回归一键化脚本（sync → test → diff → all）。

背景（R54 路M 诊断）：light-merge 全量 pytest 有 4000+ 用例，本机 Windows 上
xdist 并行会 INTERNALERROR、串行又要 1 小时以上，所以**统一去 0.82（FreeBSD）
跑全量**。本脚本把「同步代码 → 远端跑 pytest → 拉回结果 → 对比基线」串成一个命令。

子命令：
    sync    把 lightharness + light-merge 打包上传到 0.82 并解压（复用同步0.82.py）
    test    在 0.82 上跑 light-merge 全量 pytest，产出基线 JSON
    diff    与上一份基线对比，输出新增红 / 已修复 / 持平
    all     sync + test + diff 一条龙（默认入口）

实测要点（本轮踩坑固化，别踩回去）：
  * 0.82 只装了 pytest 9.1.1，**没有 xdist、没有 pytest-timeout**
    → addopts 必须 `-o addopts=` 置空，否则 `-n auto` / `--timeout=60` 直接 ARGERROR。
  * 没有 pytest-timeout 就用 FreeBSD 自带的 `timeout(1)` 兜一层，防止 hang 死。
  * 结果用 pytest 内建的 `--junitxml` 结构化落盘再 sftp 拉回，不靠解析终端文本。
  * 判据沿用 CI 口径：**新增红**（本轮失败集合 − 基线失败集合）为空才算通过。

用法：
    python scripts/082全量回归.py all
    python scripts/082全量回归.py all --mode full          # 连 slow 用例一起跑
    python scripts/082全量回归.py test --parallel           # 0.82 装了 xdist 时可试并行
    python scripts/082全量回归.py test --timeout-sec 3600
    python scripts/082全量回归.py diff
    python scripts/082全量回归.py diff --base reports/082_lightmerge基线_2026-09-17-235900.json
    python scripts/082全量回归.py show                      # 打印最近一份基线摘要
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]                  # lightharness/
SCRIPTS = ROOT / "scripts"
REPORTS = ROOT / "reports"
SYNC_SCRIPT = SCRIPTS / "同步0.82.py"

# 本机跑的东西（local python 用于拉 flame？不需要；远端命令用 mod.PY）
BASELINE_PREFIX = "082_lightmerge基线_"
LATEST = REPORTS / f"{BASELINE_PREFIX}latest.json"

# pytest 参数：addopts 必须置空（远端无 xdist / pytest-timeout 插件）
PYTEST_BASE = ["-m", "pytest", "tests/", "-q", "--tb=no", "-rfE",
               "-o", "addopts=", "-p", "no:cacheprovider"]


def _load_sync_module():
    """动态加载 同步0.82.py（文件名带点，不能常规 import）。"""
    spec = importlib.util.spec_from_file_location("sync082", SYNC_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_base():
    spec = importlib.util.spec_from_file_location("回归基线", SCRIPTS / "回归基线.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BASE = _load_base()


# ------------------------------------------------------------------ 工具
def _stamp() -> str:
    return time.strftime("%Y-%m-%d-%H%M%S")


def list_baselines() -> list[Path]:
    if not REPORTS.exists():
        return []
    return sorted(p for p in REPORTS.glob(f"{BASELINE_PREFIX}*.json")
                  if p.name != LATEST.name)


def has_remote(mod, cli, expr: str) -> bool:
    """远端能力探测：`python -c 'import x'` / `command -v timeout`。"""
    rc, _ = mod.run_remote(cli, expr, timeout=120, quiet=True)
    return rc == 0


def connect(mod):
    cli = mod.connect()
    # 全量跑 30~50 分钟，SSH 空闲被中间设备掐断会前功尽弃 → 开 keepalive
    try:
        cli.get_transport().set_keepalive(30)
    except Exception:      # pragma: no cover
        pass
    return cli


# ------------------------------------------------------------------ sync
def cmd_sync(args) -> int:
    mod = _load_sync_module()
    ns = argparse.Namespace(with_git=getattr(args, "with_git", False))
    return mod.cmd_sync(ns)


# ------------------------------------------------------------------ test
def cmd_test(args) -> int:
    mod = _load_sync_module()
    cli = connect(mod)
    try:
        mod.ensure_shim(cli)
        rd = mod.load_remote_dir()
        print(f"[082全量] 远端副本 {rd}")

        # 1) 能力探测：xdist 是否可用、FreeBSD timeout(1) 是否存在
        parallel = False
        if not args.serial:
            parallel = has_remote(mod, cli, f"{mod.PY} -c 'import xdist'")
        has_timeout = has_remote(mod, cli, "command -v timeout")
        nproc = 1
        _, out = mod.run_remote(cli, "sysctl -n hw.ncpu", quiet=True)
        if out.strip().isdigit():
            nproc = int(out.strip().split()[0])
        print(f"[082全量] 远端能力：xdist={'可用' if parallel else '缺失'}，"
              f"timeout(1)={'可用' if has_timeout else '缺失'}，ncpu={nproc}")

        # 2) 组装 pytest 命令
        xml_remote = f"{rd}/lm_results_{args.mode}.xml"
        pytest_argv = list(PYTEST_BASE) + ["--junitxml", xml_remote]
        if args.mode == "fast":
            pytest_argv += ["-m", "not slow"]
        if parallel:
            pytest_argv += ["-n", "auto", "--dist", "loadscope"]
        else:
            pytest_argv += ["-p", "no:xdist"]
        runner_cmd = f"cd {rd}/light-merge && {mod.PY} " + " ".join(
            _q(a) for a in pytest_argv)
        if has_timeout:
            runner_cmd = f"timeout {args.timeout_sec} sh -c {_q(runner_cmd)}"
        full = (f'export PYTHONIOENCODING=utf-8 && export PATH={mod.SHIM_DIR}:$PATH && '
                f'{runner_cmd}')

        print(f"[082全量] 0.82 执行（mode={args.mode}，串行={not parallel}，"
              f"硬超时={args.timeout_sec}s）：\n  {full}")
        t0 = time.monotonic()
        rc, out = mod.run_remote(cli, full, timeout=args.timeout_sec + 300)
        elapsed = round(time.monotonic() - t0, 1)
        tail = out.strip().splitlines()[-15:]
        print(f"[082全量] 远端 rc={rc}，耗时 {elapsed}s")
        for ln in tail:
            print("   |", ln)

        timed_out = rc == 124 or "TIMEOUT" in out.upper()
        if timed_out:
            print(f"[082全量] ⚠️ 远端 pytest 被硬超时（{args.timeout_sec}s）打断，"
                  f"结果不完整，不写入基线")

        # 3) 拉回 junitxml
        local_xml = REPORTS / f"_082_lm_results_{_stamp()}.xml"
        REPORTS.mkdir(parents=True, exist_ok=True)
        sftp = cli.open_sftp()
        try:
            try:
                sftp.stat(xml_remote)
            except OSError:
                print("[082全量] ❌ 远端没有产出 junitxml，测试未跑到收尾阶段")
                return 2
            sftp.get(xml_remote, str(local_xml))
        finally:
            sftp.close()
        print(f"[082全量] 取回结果 {local_xml.relative_to(ROOT)}")

        parsed = BASE.parse_junit(local_xml)
        baseline = BASE.make_baseline(
            parsed, name="light-merge", platform="0.82 FreeBSD 15.1",
            host=mod.HOST, remote_dir=rd, cwd=f"{rd}/light-merge",
            runner={"mode": args.mode, "parallel": parallel,
                    "timeout_sec": args.timeout_sec,
                    "marker": "not slow" if args.mode == "fast" else "",
                    "cmd": full, "elapsed_sec": elapsed,
                    "pytest_rc": rc, "timed_out": timed_out})

        path = REPORTS / f"{BASELINE_PREFIX}{_stamp()}.json"
        BASE.save_baseline(baseline, path)
        BASE.save_baseline(baseline, LATEST)
        print(f"[082全量] 基线写入 {path.relative_to(ROOT)}（同步更新 latest）")

        t = baseline["totals"]
        print("[082全量] 摘要：共 %d 用例，通过 %d，失败 %d（failure %d / error %d），"
              "跳过 %d，xfail %d，pytest 自报耗时 %.1fs"
              % (t["total"], t["passed"], t["failed"], t["failure"], t["error"],
                 t["skipped"], t["xfailed"], t["duration_sec"]))
        if baseline["failed"]:
            print("[082全量] 失败清单（前 20 条）：")
            for f in baseline["failed"][:20]:
                print("   ✗", f["id"], "—", f["message"][:120])
        return 0
    finally:
        cli.close()


def _q(s: str) -> str:
    """给 shell 参数加单引号（参数里没有单引号，够用）。"""
    return "'" + s.replace("'", "'\\''") + "'"


# ------------------------------------------------------------------ diff
def cmd_diff(args) -> int:
    history = list_baselines()
    if not history:
        print("[082全量] 没有历史基线，先跑 test")
        return 1

    if args.base:
        base = BASE.load_baseline(Path(args.base))
        new_path = Path(args.new) if args.new else LATEST
    else:
        if len(history) < 2:
            print(f"[082全量] 只有一份基线（{history[-1].name}），无可比对的历史。"
                  f"首次跑不判新增红。")
            return 0
        base = BASE.load_baseline(history[-2])
        new_path = history[-1]
    new = BASE.load_baseline(new_path)

    print(f"[082全量] 对比：{new_path.name}  ⟵  {args.base or history[-2].name}")
    d = BASE.diff_baselines(base, new)
    BASE.print_diff_result(d, label="082全量")

    out = {"diff": d, "new_baseline": str(new_path),
           "base_baseline": str(args.base or history[-2])}
    rp = REPORTS / f"082_diff_{_stamp()}.json"
    REPORTS.mkdir(parents=True, exist_ok=True)
    rp.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                  encoding="utf-8", newline="\n")
    print(f"[082全量] 对比报告 {rp.relative_to(ROOT)}")
    return 0 if d["ok"] else 1


# ------------------------------------------------------------------ show
def cmd_show(args) -> int:
    history = list_baselines()
    if not history:
        print("[082全量] 尚无基线")
        return 1
    for p in (history[-3:] if args.recent else history):
        b = BASE.load_baseline(p)
        t = b["totals"]
        print("%s  共%d 通过%d 失败%d 跳过%d  %.0fs  %s"
              % (p.name, t["total"], t["passed"], t["failed"], t["skipped"],
                 t["duration_sec"], b.get("runner", {}).get("mode", "")))
    if args.dump:
        print(json.dumps(BASE.load_baseline(history[-1]), ensure_ascii=False, indent=2))
    return 0


# ------------------------------------------------------------------ all
def cmd_all(args) -> int:
    if not args.no_sync:
        print("=" * 60)
        print("[082全量] 步骤 1/3  sync")
        rc = cmd_sync(args)
        if rc != 0:
            print("[082全量] ❌ sync 失败 rc=%d" % rc)
            return rc
    print("=" * 60)
    print("[082全量] 步骤 2/3  test")
    t0 = time.monotonic()
    before = list_baselines()
    rc = cmd_test(args)
    elapsed = time.monotonic() - t0
    print(f"[082全量] test 总耗时 {elapsed:.0f}s")
    if rc != 0:
        return rc
    print("=" * 60)
    print("[082全量] 步骤 3/3  diff")
    after = list_baselines()
    d = None
    if before and len(after) > len(before):
        # 用本次跑之前的最后一份做基线
        prev = BASE.load_baseline(before[-1])
        cur = BASE.load_baseline(after[-1])
        d = BASE.diff_baselines(prev, cur)
        print(f"[082全量] 对比：{after[-1].name}  ⟵  {before[-1].name}")
        BASE.print_diff_result(d, label="082全量")
    else:
        print("[082全量] 首次跑（此前无基线），本轮失败全部计入基线，不判新增红")
    ok = (rc == 0) and (d is None or d["ok"])
    print("=" * 60)
    print("[082全量] 门：" + ("PASS ✅" if ok else "FAIL ❌"))
    return 0 if ok else 1


# ------------------------------------------------------------------ CLI
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="R55 0.82 light-merge 全量回归一键化")
    sub = ap.add_subparsers(dest="sub", required=True)

    def common(p):
        p.add_argument("--mode", choices=["fast", "full"], default="fast",
                       help="fast=-m 'not slow'（默认，跳过慢用例）；full=全量")
        p.add_argument("--parallel", action="store_true",
                       help="0.82 上有 xdist 时启用 -n auto（默认：探测到才用）")
        p.add_argument("--serial", action="store_true", help="强制串行")
        p.add_argument("--timeout-sec", type=int, default=2700,
                       help="远端硬超时秒数（默认 2700 = 45min）")
        return p

    p = sub.add_parser("sync", help="打包并同步到 0.82")
    p.add_argument("--with-git", action="store_true", help="连 .git 一起同步")
    p.set_defaults(fn=cmd_sync)

    p = common(sub.add_parser("test", help="0.82 上跑 light-merge 全量 pytest"))
    p.set_defaults(fn=cmd_test)

    p = sub.add_parser("diff", help="与上一份基线对比")
    p.add_argument("--base", help="显式指定基线 JSON")
    p.add_argument("--new", help="本轮基线 JSON（默认 latest）")
    p.set_defaults(fn=cmd_diff)

    p = sub.add_parser("show", help="列出基线摘要")
    p.add_argument("--recent", action="store_true", help="只看最近 3 份")
    p.add_argument("--dump", action="store_true", help="打印最新一份完整 JSON")
    p.set_defaults(fn=cmd_show)

    p = common(sub.add_parser("all", help="sync + test + diff"))
    p.add_argument("--no-sync", action="store_true", help="跳过同步（复用现有远端副本）")
    p.set_defaults(fn=cmd_all)
    return ap


def main() -> int:
    args = build_parser().parse_args()
    for k in ("mode", "parallel", "serial", "timeout_sec"):
        if not hasattr(args, k):
            setattr(args, k, None)
    args.timeout_sec = args.timeout_sec or 2700
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
