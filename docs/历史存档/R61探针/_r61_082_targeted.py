# -*- coding: utf-8 -*-
"""R61 任务1 —— 0.82 定向验证（只传改动的那 1 个测试文件，不重跑全量）。

为什么需要：1A 改了 `tests/test_pure_light_hook.py`（裸路径 → LIGHT_BLOCKS_DIR + skip），
这是 0.82 门禁会执行到的文件。按 R58 教训（「定向全绿也会漏」），必须在门禁平台
（0.82 / FreeBSD / py3.12）上复核一遍 skip 分支行为。

做法：
  1) 复用 `scripts/同步0.82.py` 的 connect()/load_env()（凭据只从 .env 读）
  2) 把本地改后的 test_pure_light_hook.py 覆盖到**已同步的 R60 副本**（/tmp 草稿树）
  3) 用 /usr/local/bin/python3.12 跑定向用例，取 rc（不接管道）

注意：不传 pyproject / CI yml / blocks_pkg —— 那些不参与 pytest 判定。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path("G:/dswork/duan-light-merge")
LH = ROOT / "lightharness"
LM = ROOT / "light-merge"

REMOTE_DIR = "/tmp/r44-20260918-202728"          # R60 已同步副本
PY = "/usr/local/bin/python3.12"

FILES = ["tests/test_pure_light_hook.py"]

TARGETS = [
    "tests/test_pure_light_hook.py",
    "tests/test_feature_core_light.py::TestBitwiseInBlocks",
]


def _load_sync():
    spec = importlib.util.spec_from_file_location("sync082", LH / "scripts" / "同步0.82.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main() -> int:
    sync = _load_sync()
    cli = sync.connect()
    sftp = cli.open_sftp()

    print("[0.82定向] 远端目录：%s" % REMOTE_DIR)
    rc, out = sync.run_remote(cli, "ls -d %s/light-merge/tests" % REMOTE_DIR, quiet=True)
    print("[0.82定向] 存在性探测 rc=%d out=%s" % (rc, out.strip()[:200]))
    if rc != 0:
        print("[0.82定向] 远端副本不存在 → 放弃（不重同步，全量由路M 统一做）")
        return 2

    for rel in FILES:
        local = LM / rel
        remote = "%s/light-merge/%s" % (REMOTE_DIR, rel)
        sftp.put(str(local), remote)
        print("[0.82定向] 已上传 %s → %s (%d bytes)" % (rel, remote, local.stat().st_size))
    sftp.close()

    for t in TARGETS:
        cmd = ("cd %s/light-merge && export PYTHONIOENCODING=utf-8 && "
               "export PATH=/tmp/r44-shim:$PATH && "
               "%s -m pytest '%s' -q -p no:cacheprovider -o addopts= "
               "> /tmp/r61_082_t.out 2>&1; echo __RC__=$?; tail -6 /tmp/r61_082_t.out"
               % (REMOTE_DIR, PY, t))
        print("\n[0.82定向] 目标：%s" % t)
        rc, out = sync.run_remote(cli, cmd)
        print(out.strip()[-900:])

    cli.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
