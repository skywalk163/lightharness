# -*- coding: utf-8 -*-
"""R65 任务1 探针：直接解析 stdlib/*.light，统计 DeprecationWarning（「接收」废弃语法）数量。

为什么不用 pytest 计数：pytest 的 warnings 汇总会按 (message, category, module, lineno) 去重，
且 stdlib 被每个测试重复编译，计数随测试集漂移，不可比。
改为**每个 .light 精确解析一次**，计数确定、可比、快（秒级）。

用法： python light-merge/_probe_R65_stdlib_warn.py > 改前.txt
"""
from __future__ import annotations

import io
import sys
import warnings
from pathlib import Path

ROOT = Path(r"G:\dswork\duan-light-merge\light-merge")
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from light_parser_v3 import LightParser  # noqa: E402

STDLIB = ROOT / "stdlib"
DEP_MSG = "已废弃"


def main() -> None:
    parser = LightParser()
    files = sorted(STDLIB.glob("*.light"))
    total = 0
    per_file = []
    errs = []
    for p in files:
        try:
            src = io.open(p, encoding="utf-8", newline="").read()
        except (OSError, UnicodeDecodeError) as e:
            errs.append((p.name, f"读取失败 {e}"))
            continue
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                parser.parse(src)
            except BaseException as e:  # noqa: BLE001
                errs.append((p.name, f"{type(e).__name__}: {str(e)[:60]}"))
        n = sum(1 for x in w if issubclass(x.category, DeprecationWarning)
                and DEP_MSG in str(x.message))
        if n:
            per_file.append((n, p.name))
        total += n

    print("=" * 70)
    print("R65：stdlib 旧式「接收」DeprecationWarning 计数（每文件解析一次）")
    print("=" * 70)
    print(f"扫描 .light 文件 {len(files)} 个")
    print(f"**DeprecationWarning 合计 = {total}**")
    print(f"命中文件数 = {len(per_file)}")
    print()
    print("--- Top 25 ---")
    for n, name in sorted(per_file, reverse=True)[:25]:
        print(f"  {n:>5}  {name}")
    if errs:
        print()
        print(f"--- 解析异常 {len(errs)} 个（前 10，仅登记，不影响计数）---")
        for name, msg in errs[:10]:
            print(f"  {name}: {msg}")


if __name__ == "__main__":
    main()
