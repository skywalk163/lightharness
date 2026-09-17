# -*- coding: utf-8 -*-
"""R55 探针4：0.82 上 light-merge 全量 pytest 收集规模探测（含/不含 slow 标记）。"""
from __future__ import annotations
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
SYNC = ROOT / "lightharness" / "scripts" / "同步0.82.py"
spec = importlib.util.spec_from_file_location("sync082", SYNC)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

cli = mod.connect()
try:
    mod.ensure_shim(cli)
    rd = mod.load_remote_dir()
    print("远端副本", rd)
    for label, extra in [("全量", ""), ("not slow", "-m 'not slow'")]:
        cmd = (f"cd {rd}/light-merge && timeout 600 {mod.PY} -m pytest tests/ --collect-only -q "
               f"-o addopts= -p no:cacheprovider -p no:xdist {extra} 2>&1 | tail -3")
        rc, out = mod.run_remote(cli, cmd, timeout=700, quiet=True)
        print(f"--- {label}: rc={rc}\n{out.strip()}\n")
    # slow 标记用例数
    cmd = (f"cd {rd}/light-merge && {mod.PY} -m pytest tests/ --collect-only -q "
           f"-o addopts= -p no:cacheprovider -p no:xdist -m slow 2>&1 | tail -3")
    rc, out = mod.run_remote(cli, cmd, timeout=700, quiet=True)
    print(f"--- slow: rc={rc}\n{out.strip()}\n")
finally:
    cli.close()
