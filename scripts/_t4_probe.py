# -*- coding: utf-8 -*-
"""T4 观察工具：SSH 到 1.5 盒子（192.168.1.5），抓 dsh-web 稳定性快照。

用法:
    python _t4_probe.py once <outfile>            # 单次快照（落 JSON）
    python _t4_probe.py watch <outfile> [n] [sec] # 每 sec 秒一次，共 n 次（默认 7 次 / 300s）
    python _t4_probe.py bench <outfile>           # 温缓存抽样（ltbench compiler_bench）
    python _t4_probe.py all <outfile>             # 一次全量快照 + 栅栏 + warm bench
"""
from __future__ import annotations

import io
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[2]          # monorepo 根（含 .env）


def load_env():
    env = {}
    for line in io.open(ROOT / ".env", encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


ENV = load_env()
HOST = ENV.get("15SSH_HOST") or ENV.get("SSH_HOST")
USER = ENV.get("SSH_USER_WORKBUDDY") or "workbuddy"
PASS = ENV.get("SSH_PASS_WORKBUDDY")

LIGHT = {
    "pidchain": (
        "LP=$(sockstat -4l -p 3080 2>/dev/null | awk 'NR>1{print $3}' | head -1); "
        "echo LISTEN_PID=$LP; "
        "echo '--- chain ---'; "
        "ps -o pid,ppid,etime,pcpu,rss,command -p $LP 2>/dev/null; "
        "PP=$(ps -o ppid= -p $LP 2>/dev/null | tr -d ' '); "
        "if [ -n \"$PP\" ]; then ps -o pid,ppid,etime,command -p $PP; "
        "GP=$(ps -o ppid= -p $PP 2>/dev/null | tr -d ' '); "
        "if [ -n \"$GP\" ]; then ps -o pid,ppid,etime,command -p $GP; fi; fi; "
        "echo '--- daemon pidfile ---'; "
        "cat /var/run/dsh_web.pid 2>/dev/null || echo NO_PIDFILE"
    ),
    "sockstat": "sockstat -4l -p 3080 2>/dev/null || echo NO_LISTEN",
    "swap": "swapinfo -h 2>/dev/null || swapinfo",
    "load": "uptime",
    "oom_recent": "dmesg 2>/dev/null | grep -iE 'out of swap|out of memory|killed process' | tail -3 || echo NO_OOM",
    "dsh_log": "for f in /var/log/dsh_web.log /tmp/dsh_web.log; do [ -f \"$f\" ] && echo \"== $f\" && tail -15 \"$f\"; done 2>/dev/null | tail -40",
    "loopback_get": "curl -s -o /dev/null -w 'loopback_root_notoken=%{http_code}\\n' --max-time 10 http://127.0.0.1:3080/; true",
    "landirect": "curl -s -o /dev/null -w 'lan_direct=%{http_code}\\n' --max-time 6 http://192.168.1.5:3080/; echo \"curl_rc=$?\"; true",
}

BENCH = "~/dswork/ltbench/scripts/compiler_bench.py"


def run(client, cmd, timeout=120):
    try:
        _i, o, e = client.exec_command(cmd, timeout=timeout)
        out = o.read().decode("utf-8", "replace")
        err = e.read().decode("utf-8", "replace")
        rc = o.channel.recv_exit_status()
        return {"rc": rc, "out": out.strip(), "err": err.strip()[:1500]}
    except Exception as exc:  # noqa
        return {"rc": -1, "out": "", "err": f"ERR {type(exc).__name__}"}


def connect():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, password=PASS, timeout=30, look_for_keys=False, allow_agent=False)
    return c


def light_snap(client):
    snap = {"ts": datetime.now().astimezone().isoformat(timespec="seconds")}
    for k, cmd in LIGHT.items():
        snap[k] = run(client, cmd, timeout=60)
    return snap


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "once"
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "lightharness/logs/_t4_watch.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)

    if mode == "watch":
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 7
        interval = int(sys.argv[4]) if len(sys.argv) > 4 else 300
        for i in range(n):
            try:
                c = connect()
                try:
                    snap = light_snap(c)
                finally:
                    c.close()
            except Exception as exc:  # noqa
                snap = {"ts": datetime.now().isoformat(), "error": f"{type(exc).__name__}"}
            with io.open(out, "a", encoding="utf-8") as f:
                f.write(json.dumps(snap, ensure_ascii=False) + "\n")
            print(f"[watch {i+1}/{n}] {snap.get('ts')} err={snap.get('error','-')}", flush=True)
            if i < n - 1:
                time.sleep(interval)
        return

    c = connect()
    try:
        snap = {"ts": datetime.now().astimezone().isoformat(timespec="seconds")}
        for k, cmd in LIGHT.items():
            snap[k] = run(c, cmd, timeout=60)
        if mode in ("bench", "all"):
            for nsamples in (("3",) if mode == "all" else (sys.argv[3] if len(sys.argv) > 3 else "3",)):
                snap[f"bench_{nsamples}"] = run(
                    c, f"cd ~/dswork/ltbench && /usr/local/bin/python3 {BENCH} {nsamples} 2>&1 | tail -30",
                    timeout=600,
                )
    finally:
        c.close()
    with io.open(out, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=1)
    print(json.dumps(snap, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
