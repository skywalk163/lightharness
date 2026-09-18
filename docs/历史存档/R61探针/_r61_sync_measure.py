# -*- coding: utf-8 -*-
"""R61 任务1B —— 拆分提速量化：sync 打包体量 / 组成拆解（只读，不联网、不上传）。

复用 `lightharness/scripts/同步0.82.py` 的 build_tarball / _should_skip，
保证口径与路M 真实 sync 完全一致（同一排除表、同一 tarfile 参数 compresslevel=1）。

输出：
  * 实测 tar.gz 文件数 / 字节数 / 打包耗时
  * 按子树拆解（light-merge / lightharness）文件数与原始字节
  * lighting 仓（拆分出去的部分）文件数与字节数 —— 即「本仓不再承担」的体量
"""
from __future__ import annotations

import importlib.util
import os
import sys
import time
from pathlib import Path

ROOT = Path("G:/dswork/duan-light-merge")
LIGHT_MERGE = ROOT / "light-merge"
LIGHTHARNESS = ROOT / "lightharness"
LIGHTING = ROOT / "lighting"


def _load_sync():
    p = LIGHTHARNESS / "scripts" / "同步0.82.py"
    spec = importlib.util.spec_from_file_location("sync082", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _walk_stats(base: Path, skip=None):
    n = 0
    size = 0
    for p in base.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(base)
        if skip is not None and skip(rel):
            continue
        try:
            size += p.stat().st_size
        except OSError:
            continue
        n += 1
    return n, size


def main() -> int:
    sync = _load_sync()
    out = ROOT / "_r61_sync_probe.tar.gz"

    print("[1B] 打包口径：", "EXCLUDE_DIRS =", sorted(sync.EXCLUDE_DIRS))
    print("[1B] 排除后缀：", sorted(sync.EXCLUDE_SUFFIX), " 含 .git：", sync.INCLUDE_GIT)

    t0 = time.monotonic()
    n = sync.build_tarball(out)
    elapsed = time.monotonic() - t0
    size = out.stat().st_size
    print("\n===== 打包实测（拆分后，R61）=====")
    print("文件数            : %d" % n)
    print("tar.gz 字节       : %d  (%.2f MB)" % (size, size / 1024 / 1024))
    print("原始字节（未压缩）: 见下方子树拆解")
    print("打包耗时          : %.1f s" % elapsed)

    print("\n===== 子树拆解（同一排除表）=====")
    for name, base in (("light-merge", LIGHT_MERGE), ("lightharness", LIGHTHARNESS)):
        cn, cs = _walk_stats(base, sync._should_skip)
        print("%-13s: %6d 文件  %8.2f MB（入包）" % (name, cn, cs / 1024 / 1024))
        an, as_ = _walk_stats(base)
        print("%-13s: %6d 文件  %8.2f MB（全量，含被排除项）" % ("  ↑全量", an, as_ / 1024 / 1024))

    if LIGHTING.exists():
        ln, ls = _walk_stats(LIGHTING)
        print("%-13s: %6d 文件  %8.2f MB（**已拆出本仓**，不再计入 sync 体量）"
              % ("lighting", ln, ls / 1024 / 1024))
        print("  → 拆分减少的入包文件数（按 tar.gz 原始字节估）: %.2f MB"
              % (ls / 1024 / 1024))

    out.unlink(missing_ok=True)
    print("\n[1B] 探针 tarball 已删除：%s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
