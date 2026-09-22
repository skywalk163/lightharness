# -*- coding: utf-8 -*-
"""R85 任务F 批1（4）—— 0.86 Linux 跨平台 CLI 命令面验证。

复用 lightharness/scripts/跨平台CLI验证.sh 的 4 个命令面断言（version / help /
dump-config / unknown），但改在 0.86（Linux）远端副本上实测，验证命令面跨平台一致。

用法：
    python scripts/跨平台CLI验证_0.86.py
    python scripts/跨平台CLI验证_0.86.py --host 192.168.0.86
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def main() -> int:
    ap = argparse.ArgumentParser(description="0.86 跨平台 CLI 命令面验证")
    ap.add_argument("--host", default="192.168.0.86")
    ap.add_argument("--port", type=int, default=22)
    args = ap.parse_args()

    import importlib.util
    spec = importlib.util.spec_from_file_location("s86", str(ROOT / "scripts" / "同步0.86.py"))
    s86 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(s86)

    cli, *_ = s86.connect(args.host, args.port)
    rd = s86.load_remote_dir()
    prefix = s86.remote_prefix(rd)
    vpy = s86.REMOTE_PY
    # 与 跨平台CLI验证.sh 同口径：HARNESS_MODEL 固定，HARNESS_CMD 驱动运行器
    checks = [
        ("version", "0.1.5-lh"),
        ("help", "lightharness CLI 用法"),
        ("dump-config", "r41-cross-platform-model"),
    ]
    all_ok = True
    try:
        # version / help / dump-config
        for cmd, expected in checks:
            full = (prefix +
                    f'export HARNESS_MODEL=r41-cross-platform-model && '
                    f'export HARNESS_CMD={cmd} && '
                    f'{vpy} 运行.py examples/运行CLI.light 2>&1')
            rc, out = s86.run_remote(cli, full, timeout=300, quiet=True)
            ok = expected in out
            all_ok = all_ok and ok
            print(f"{'PASS' if ok else 'FAIL'} {cmd:<12} rc={rc} "
                  f"(期望包含 {expected!r}: {'命中' if ok else '未命中'})")
            if not ok:
                # 打印尾部便于排查
                for ln in out.strip().splitlines()[-8:]:
                    print("      |", ln)
        # unknown
        full = (prefix +
                f'export HARNESS_CMD=bogus && '
                f'{vpy} 运行.py examples/运行CLI.light 2>&1')
        rc, out = s86.run_remote(cli, full, timeout=300, quiet=True)
        ok = ("未知命令" in out) and (rc != 0)
        all_ok = all_ok and ok
        print(f"{'PASS' if ok else 'FAIL'} {'unknown':<12} rc={rc} "
              f"(期望包含 '未知命令' 且 rc≠0: {'命中' if ok else '未命中'})")
        if not ok:
            for ln in out.strip().splitlines()[-8:]:
                print("      |", ln)
    finally:
        cli.close()

    print("=== 0.86 CLI 命令面 ===", "PASS ✅" if all_ok else "FAIL ❌")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
