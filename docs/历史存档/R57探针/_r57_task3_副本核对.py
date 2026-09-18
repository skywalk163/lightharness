# -*- coding: utf-8 -*-
"""R57 任务3 前置核对（只读）：0.82 副本一致性检查。

背景：R56 坐实 4 例 example 红在 0.82 稳定复现，但本机 HEAD=3e0de022 同一批
example 用 py3.10/3.12/3.13/3.14 全部 rc=0。本探针只读核对：
  1. 远端副本路径与 light-merge/src/lexer.py 的 md5（对照本机）；
  2. 远端 src/__pycache__ 是否存在（陈旧 pyc 陷阱）；
  3. 用真 rc（不接管道）复跑 1 条 R56 记录为红的 example；
  4. 远端 lexer.py 的 mtime/size。
不做任何修改、不跑 pytest。
"""
from __future__ import annotations
import hashlib
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
LH = HERE.parent.parent.parent          # .../lightharness/docs/历史存档/R57探针 -> lightharness
SYNC = LH / "scripts" / "同步0.82.py"
LM_LOCAL = LH.parent / "light-merge"

spec = importlib.util.spec_from_file_location("sync082", SYNC)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

LOCAL_FILES = [
    "light-merge/src/lexer.py",
    "light-merge/src/parser_stmt.py",
    "lightharness/examples/test_R22_嵌入关键字冗余验证.light",
    "lightharness/examples/test_R26_词首并入反向.light",
    "lightharness/examples/test_R26_词首并入混合.light",
    "lightharness/examples/test_R27_词首并入反向.light",
]


def md5_local(rel: str) -> str:
    p = LH.parent / rel
    return hashlib.md5(p.read_bytes()).hexdigest() if p.exists() else "(missing)"


def main() -> int:
    print("[local] md5 基准：")
    for rel in LOCAL_FILES:
        print(f"   {md5_local(rel)}  {rel}")

    cli = mod.connect()
    try:
        mod.ensure_shim(cli)
        rd = mod.load_remote_dir()
        print(f"\n[remote] 副本 {rd}")
        rc, out = mod.run_remote(
            cli,
            "cd {rd} && for f in light-merge/src/lexer.py light-merge/src/parser_stmt.py "
            "lightharness/examples/test_R22_嵌入关键字冗余验证.light "
            "lightharness/examples/test_R26_词首并入反向.light "
            "lightharness/examples/test_R26_词首并入混合.light "
            "lightharness/examples/test_R27_词首并入反向.light; do "
            "if [ -f \"$f\" ]; then echo \"$(md5 -q \"$f\")  $f\"; else echo \"(missing)  $f\"; fi; done; "
            "echo '--- pycache ---'; "
            "ls light-merge/src/__pycache__ 2>/dev/null | head -5 || echo '(no pycache)'; "
            "echo '--- lexer.py stat ---'; stat -f '%m %z' light-merge/src/lexer.py".format(rd=rd),
            timeout=120, quiet=True)
        print(out)

        print("[remote] 复跑 test_R22（真 rc，不接管道）：")
        rc, out = mod.run_remote(
            cli,
            "cd {rd}/lightharness && LIGHT_MERGE={rd}/light-merge PYTHONIOENCODING=utf-8 "
            "/usr/local/bin/python3.12 运行.py examples/test_R22_嵌入关键字冗余验证.light "
            "> /tmp/o_r57t3 2>&1; echo __RC__=$?; tail -6 /tmp/o_r57t3".format(rd=rd),
            timeout=180, quiet=True)
        print(out)
    finally:
        cli.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
