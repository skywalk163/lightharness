# -*- coding: utf-8 -*-
"""R55 探针3：0.82 pytest 插件清单（逐条单测，避免 stderr 丢失掩盖细节）。"""
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
    for cmd in [
        f"{mod.PY} -m pytest --version 2>&1 | head -20",
        f"{mod.PY} -m pip list 2>/dev/null | grep -iE 'pytest|xdist|timeout|forked|paramiko|numpy|psutil|pillow'",
        f"{mod.PY} -c 'import xdist; print(\"xdist\", xdist.__version__)'",
        f"{mod.PY} -c 'import pytest_timeout; print(\"timeout ok\")'",
    ]:
        rc, out = mod.run_remote(cli, cmd, timeout=180, quiet=True)
        print(f"### rc={rc} :: {cmd[:70]}\n{out.strip()}\n")
finally:
    cli.close()
