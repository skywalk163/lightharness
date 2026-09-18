# -*- coding: utf-8 -*-
"""R62 任务1 探针：统计两仓大文件/大目录构成（>1MB 文件 + 按顶层/二级目录聚合体积）。

只读脚本，不删除任何文件。
用法： python lightharness/_probe_R62_bulk.py
"""
from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"G:\dswork\duan-light-merge")
REPOS = ["light-merge", "lightharness"]
SKIP_PARTS = {".git", "__pycache__", ".venv", "venv", ".pytest_cache", ".mypy_cache",
              "node_modules", "build", "dist", ".idea", ".vscode"}


def walk(repo: Path):
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in SKIP_PARTS]
        for f in filenames:
            p = Path(dirpath) / f
            try:
                st = p.stat()
            except OSError:
                continue
            yield p, st.st_size


def human(n: int) -> str:
    return f"{n/1024/1024:.2f}MB"


def main() -> None:
    big_files: list[tuple[int, str]] = []
    dir_bytes: dict[str, dict[str, list]] = {r: defaultdict(lambda: [0, 0]) for r in REPOS}

    for r in REPOS:
        repo = ROOT / r
        if not repo.exists():
            print(f"[!] 缺失 {repo}")
            continue
        for p, sz in walk(repo):
            rel = p.relative_to(repo)
            parts = rel.parts
            # 聚合：二级目录（顶层若只有一层则用它）
            key = "/".join(parts[:2]) if len(parts) > 1 else (parts[0] if parts else ".")
            d = dir_bytes[r][key]
            d[0] += sz
            d[1] += 1
            if sz >= 1024 * 1024:
                big_files.append((sz, f"{r}/{rel.as_posix()}"))

    print("=" * 78)
    print("【A】≥1MB 单文件清单（按体积降序 Top 40）")
    print("=" * 78)
    big_files.sort(reverse=True)
    for sz, name in big_files[:40]:
        print(f"{human(sz):>10}  {name}")
    print(f"\n≥1MB 文件总数 = {len(big_files)}，合计 {human(sum(s for s, _ in big_files))}")

    print()
    print("=" * 78)
    print("【B】目录聚合（≥1MB，按体积降序 Top 40，键=二级目录）")
    print("=" * 78)
    rows = []
    for r in REPOS:
        for k, (sz, cnt) in dir_bytes[r].items():
            if sz >= 1024 * 1024:
                rows.append((sz, f"{r}/{k}", cnt))
    rows.sort(reverse=True)
    for sz, name, cnt in rows[:40]:
        print(f"{human(sz):>10}  {cnt:>7} 文件  {name}")

    print()
    print("=" * 78)
    print("【C】_taskR11B_test_* 前缀目录统计")
    print("=" * 78)
    for r in REPOS:
        repo = ROOT / r
        for d in sorted(os.listdir(repo)) if repo.exists() else []:
            full = repo / d
            if full.is_dir() and d.startswith("_taskR11B_test_"):
                tot = 0
                cnt = 0
                for p, sz in walk(full):
                    tot += sz
                    cnt += 1
                print(f"{human(tot):>10}  {cnt:>6} 文件  {r}/{d}")


if __name__ == "__main__":
    main()
