# -*- coding: utf-8 -*-
"""R62 任务1 实测：同步包打包前后体积/文件数对比（不上传，只本地打包测量）。

用法： python lightharness/_probe_R62_syncsize.py
"""
from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path

ROOT = Path(r"G:\dswork\duan-light-merge")
SCRIPT = ROOT / "lightharness" / "scripts" / "同步0.82.py"


def load():
    spec = importlib.util.spec_from_file_location("sync082", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def measure(m, out: Path, label: str, old: bool):
    if old:
        m.EXCLUDE_DIR_PREFIXES = ()
        m.EXCLUDE_REL_PREFIXES = ()
    t0 = time.time()
    n = m.build_tarball(out)
    dt = time.time() - t0
    mb = out.stat().st_size / 1024 / 1024
    print(f"{label:<10} 文件 {n:>6}  体积 {mb:>8.2f} MB  耗时 {dt:>6.1f}s")
    return n, mb, dt


def main() -> None:
    # ⚠️ 每次测量都 **重新加载模块**：第一次为「改前」会把两个排除表清空，
    # 若不重载，第二次「改后」会沿用被清空的旧值 → 测出两组完全相同的假数据。
    print("=" * 70)
    print("R62 任务1：同步包体积实测")
    print("=" * 70)
    m_old = load()
    n0, mb0, dt0 = measure(m_old, ROOT / "_r62_sync_before.tar.gz", "改前", old=True)
    m_new = load()
    n1, mb1, dt1 = measure(m_new, ROOT / "_r62_sync_after.tar.gz", "改后", old=False)
    print("-" * 70)
    print(f"文件数 {n0} → {n1}  ({n1 - n0:+d}, {(n1/n0-1)*100:+.1f}%)")
    print(f"体积   {mb0:.2f}MB → {mb1:.2f}MB  ({mb1 - mb0:+.2f}MB, {(mb1/mb0-1)*100:+.1f}%)")
    print(f"耗时   {dt0:.1f}s → {dt1:.1f}s")
    print(f"验收线 tar.gz ≤ 35MB：{'PASS' if mb1 <= 35 else 'FAIL'}")
    for f in (before, after):
        try:
            f.unlink()
        except OSError:
            pass


if __name__ == "__main__":
    main()
