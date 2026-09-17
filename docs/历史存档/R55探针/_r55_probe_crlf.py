# -*- coding: utf-8 -*-
"""R55 探针7：那 4 个 Windows 红 / FreeBSD 绿的 example，是不是被 CRLF 行尾差异打红的？

做法：把同一个文件内容分别以 CRLF 和 LF 写到 examples/ 下的临时副本（用完删除），
本机同一解释器各跑一次，比 rc。若 LF 版绿、CRLF 版红 → 行尾就是平台差异真因。
"""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
LH = ROOT / "lightharness"
EX = LH / "examples"
PY = ROOT / "light-merge" / ".venv" / "Scripts" / "python.exe"

NAMES = [
    "test_R22_嵌入关键字冗余验证",
    "test_R26_词首并入反向",
    "test_R26_词首并入混合",
    "test_R27_词首并入反向",
]

for n in NAMES:
    src = EX / f"{n}.light"
    raw = src.read_bytes()
    print(f"--- {n}  原始行尾={'CRLF' if b'\r\n' in raw else 'LF'}")

    results = {}
    for label, data in (("原样", raw),
                        ("CRLF", raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")),
                        ("LF", raw.replace(b"\r\n", b"\n"))):
        tmp = EX / f"_tmp_{n}_{label}.light"
        tmp.write_bytes(data)
        try:
            env = os.environ.copy()
            env["LIGHT_MERGE"] = str(ROOT / "light-merge")
            env["PYTHONIOENCODING"] = "utf-8"
            p = subprocess.run([str(PY), "运行.py", f"examples/{tmp.name}"],
                               cwd=str(LH), env=env, capture_output=True,
                               text=True, encoding="utf-8", errors="replace",
                               timeout=180)
            results[label] = p.returncode
            last = [l for l in (p.stdout or "").splitlines() if l.strip()][-1:] or [""]
            print(f"    {label:4s} rc={p.returncode}  {last[0][:70]}")
        finally:
            try:
                tmp.unlink()
            except OSError:
                pass
    print(f"    ==> {results}")
