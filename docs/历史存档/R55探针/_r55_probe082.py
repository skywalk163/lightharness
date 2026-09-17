# -*- coding: utf-8 -*-
"""R55 探针：0.82 环境可用性检查（一次性，用完删除）。"""
from __future__ import annotations
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
SYNC = ROOT / "lightharness" / "scripts" / "同步0.82.py"

spec = importlib.util.spec_from_file_location("sync082", SYNC)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

cli = mod.connect()
try:
    mod.ensure_shim(cli)
    for cmd, label in [
        ("uname -a", "uname"),
        (f"{mod.PY} -V", "pyver"),
        (f"{mod.PY} -c 'import pytest,xdist,pytest_timeout;print(\"pytest\",pytest.__version__,\"xdist ok\",\"timeout ok\")'",
         "plugins"),
        ("ls -dt /tmp/r44-* 2>/dev/null | head -5", "remote_dirs"),
        ("nproc; sysctl -n hw.ncpu", "ncpu"),
    ]:
        rc, out = mod.run_remote(cli, cmd, timeout=120, quiet=True)
        print(f"--- {label} rc={rc}\n{out.strip()}\n")
finally:
    cli.close()
