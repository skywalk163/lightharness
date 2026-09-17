# -*- coding: utf-8 -*-
"""R55 探针2：0.82 pytest 插件 / light-merge 依赖检查。"""
from __future__ import annotations
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
SYNC = ROOT / "lightharness" / "scripts" / "同步0.82.py"

spec = importlib.util.spec_from_file_location("sync082", SYNC)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

CHECK = (
    "import importlib;"
    "import sys;"
    "print('PY', sys.version.split()[0]);"
    "print('EXE', sys.executable);"
    "[print('PLUGIN', m, 'OK' if importlib.util.find_spec(m) else 'MISSING') "
    " for m in ['pytest','xdist','pytest_timeout','_pytest','paramiko','yaml','requests']];"
    "[print('MOD', m, 'OK' if importlib.util.find_spec(m) else 'MISSING') "
    " for m in ['numpy','psutil','PIL','lark','antlr4']]"
)

cli = mod.connect()
try:
    mod.ensure_shim(cli)
    rc, out = mod.run_remote(cli, f"{mod.PY} -c \"{CHECK}\"", timeout=180, quiet=True)
    print("plugins rc=%d\n%s" % (rc, out.strip()))
    rd = mod.load_remote_dir()
    print("\n== 远端副本", rd)
    rc, out = mod.run_remote(cli, f"ls {rd} && ls {rd}/light-merge/tests/test_lexer.py", quiet=True, timeout=120)
    print(out.strip())
    # light-merge 能否被 import（pytest 收集前置条件）
    rc, out = mod.run_remote(
        cli,
        f"cd {rd}/light-merge && {mod.PY} -m pytest tests/test_lexer.py --collect-only -q "
        f"-o addopts='' -p no:cacheprovider 2>&1 | tail -5",
        timeout=300, quiet=True)
    print("\n== collect-only 试跑 rc=%d\n%s" % (rc, out.strip()))
finally:
    cli.close()
