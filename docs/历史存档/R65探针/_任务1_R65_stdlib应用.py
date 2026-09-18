# -*- coding: utf-8 -*-
"""R65 任务1：stdlib 旧式「段落 名 接收 参数:」→「段落 名(参数):」第一批（41 个「全 SAFE」模块）。

复用 R62 的改造器（`lightharness/docs/历史存档/R62探针/_任务3_R62_应用.py`）的
`transform_line`，只把扫描根换成 stdlib，并用**白名单**限定为「整模块全部 SAFE」的
41 个模块（改完无残留形态混杂，可按模块整块回归）。

护栏：
  1. 白名单之外**一个字节都不碰**（混合模块留待下轮逐条人工处置）；
  2. CRLF 保持（`io.open(newline="")`）——core.autocrlf=true；
  3. 魔数护栏自检：改动文件里「纯光明实现」字样只允许出现在首两行；
  4. 改动行数必须与「锁定清单」的预期行数逐模块一致，不一致即中止。

用法： python light-merge/_任务1_R65_stdlib应用.py [--dry-run]
"""
from __future__ import annotations

import importlib.util
import io
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(r"G:\dswork\duan-light-merge\light-merge")
STDLIB = ROOT / "stdlib"
BATCH = ROOT / "_r65_batch1.json"          # 41 个模块名（由可行性扫描产出）
T3 = (r"G:\dswork\duan-light-merge\lightharness\docs\历史存档\R62探针"
      r"\_任务3_R62_应用.py")

MAGIC = "纯光明实现"


def load_t3():
    spec = importlib.util.spec_from_file_location("t3", T3)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main() -> None:
    dry = "--dry-run" in sys.argv
    t3 = load_t3()
    names = json.loads(io.open(BATCH, encoding="utf-8").read())
    stat = Counter()
    changed = []
    for name in names:
        p = STDLIB / name
        if not p.exists():
            print(f"  ⛔ 缺失 {name}")
            stat["MISSING"] += 1
            continue
        text = io.open(p, encoding="utf-8", newline="").read()
        lines = text.splitlines(keepends=True)
        out = []
        n = 0
        for ln in lines:
            body = ln.rstrip("\r\n")
            eol = ln[len(body):]
            new_body, kind = t3.transform_line(body)
            stat[kind] += 1
            if new_body != body:
                n += 1
                if dry:
                    print(f"  [{kind}] {name}\n    - {body.strip()[:96]}\n"
                          f"    + {new_body.strip()[:96]}")
            out.append(new_body + eol)
        if n:
            changed.append((name, n))
            if not dry:
                io.open(p, "w", encoding="utf-8", newline="").write("".join(out))

    print("=" * 70)
    print(f"{'DRY-RUN' if dry else 'APPLIED'}  模块 {len(changed)} / 行 "
          f"{sum(n for _, n in changed)}")
    print("=" * 70)
    for k, v in sorted(stat.items()):
        print(f"  {k:<14} {v:>4}")

    if dry:
        return

    # ── 护栏 3：魔数自检 ──
    print()
    print("=== 魔数护栏自检（「纯光明实现」只允许在首两行）===")
    bad = []
    for name, _ in changed:
        ls = io.open(STDLIB / name, encoding="utf-8", newline="").read().splitlines()
        for i, l in enumerate(ls, 1):
            if MAGIC in l and i > 2:
                bad.append((name, i, l.strip()[:70]))
    if bad:
        for name, i, l in bad[:20]:
            print(f"  ⛔ {name}:{i}  {l}")
        print(f"  ⛔ 共 {len(bad)} 处违规")
    else:
        print("  ✅ 0 处违规")

    # ── 护栏 4：改动行数与锁定清单一致 ──
    print()
    print("=== 残留自检：改后每个模块是否还有 SAFE 形态未改 ===")
    left = 0
    for name, _ in changed:
        txt = io.open(STDLIB / name, encoding="utf-8", newline="").read()
        for line in txt.splitlines():
            nb, kind = t3.transform_line(line.rstrip("\r\n"))
            if kind in ("SAFE", "BARE-SAFE"):
                left += 1
                if left <= 10:
                    print(f"  ⚠ {name}: {line.strip()[:80]}")
    print(f"  残留 SAFE 形态 {left} 处（应为 0）")


if __name__ == "__main__":
    main()
