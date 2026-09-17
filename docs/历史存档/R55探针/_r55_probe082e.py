# -*- coding: utf-8 -*-
"""R55 探针6：本机 lightharness 的失败项，搬到 0.82 上跑一遍，看是平台专属还是共有。"""
from __future__ import annotations
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
SYNC = ROOT / "lightharness" / "scripts" / "同步0.82.py"
spec = importlib.util.spec_from_file_location("sync082", SYNC)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# 本机这 7 条红对应的命令：3 条 pytest 用例 + 4 个 example
PYTEST_IDS = [
    "tests/test_R31_EMBED表保留+flaky修复_token.py::test_fanhui_embedded_scan_triggered",
    "tests/test_R31_EMBED表保留+flaky修复_token.py::test_fanhui_return_value_merged",
    "tests/test_R32_OPERATOR+MERGE_WHOLE精简_token.py::test_deleted_return_code_still_merged",
]
EXAMPLES = [
    "test_R22_嵌入关键字冗余验证", "test_R26_词首并入反向",
    "test_R26_词首并入混合", "test_R27_词首并入反向",
]

cli = mod.connect()
try:
    mod.ensure_shim(cli)
    rd = mod.load_remote_dir()
    pre = (f"cd {rd}/lightharness && export LIGHT_MERGE={rd}/light-merge && "
           f"export PATH={mod.SHIM_DIR}:$PATH && export PYTHONIOENCODING=utf-8 && ")

    print("=== A. 3 条 pytest 用例在 0.82 ===")
    rc, out = mod.run_remote(
        cli,
        pre + f"{mod.PY} -m pytest " + " ".join("'%s'" % i for i in PYTEST_IDS)
        + " -q --tb=line -o addopts= -p no:cacheprovider -p no:xdist 2>&1 | tail -20",
        timeout=600, quiet=True)
    print(f"rc={rc}\n{out.strip()}\n")

    print("=== B. 4 个 example 在 0.82（rc 应为 0 才绿）===")
    for e in EXAMPLES:
        rc, out = mod.run_remote(
            cli, pre + f"{mod.PY} 运行.py examples/{e}.light 2>&1 | tail -6",
            timeout=300, quiet=True)
        tail = " / ".join(l for l in out.strip().splitlines() if l.strip())[-180:]
        print(f"  {e}: rc={rc} | {tail}")
finally:
    cli.close()
