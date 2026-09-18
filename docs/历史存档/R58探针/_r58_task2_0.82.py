# -*- coding: utf-8 -*-
"""R58 任务2 —— 0.82 环境红清账驱动（lunardate/requests/cryptography）

复用 scripts/同步0.82.py 的 connect / run_remote / load_remote_dir，
避免在 bash 里拼远端引号。所有输出重定向到本地文件留痕。

用法：
    python _r58_task2_0.82.py check    # 副本/依赖现状体检
    python _r58_task2_0.82.py install  # pip install 三件套（py3.12）
    python _r58_task2_0.82.py test     # 定向 pytest 4 文件
"""
from __future__ import annotations

import io
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          # duan-light-merge/
LH = Path(__file__).resolve().parents[0]            # lightharness/
sys.path.insert(0, str(LH / "scripts"))

import importlib.util as _ilu                       # noqa: E402

_spec = _ilu.spec_from_file_location("_sync082", LH / "scripts" / "同步0.82.py")
S = _ilu.module_from_spec(_spec)                    # noqa: E402
_spec.loader.exec_module(S)

RD = S.load_remote_dir()
PY312 = "/usr/local/bin/python3.12"


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    cli = S.connect()
    try:
        if mode == "check":
            cmds = [
                f"cd {RD}/light-merge && ls tests/test_datetime.py tests/test_lightpub_bridge.py tests/test_tls_light.py tests/test_async_io_light.py | wc -l",
                f"{PY312} -c \"import importlib.util as u; print({{m: bool(u.find_spec(m)) for m in ['lunardate','requests','cryptography','xdist','pytest_timeout']}})\"",
                f"{PY312} -m pip --version",
            ]
        elif mode == "install":
            cmds = [
                f"{PY312} -m pip install --no-input lunardate requests cryptography 2>&1; echo __PIP_RC__=$?",
                f"{PY312} -c \"import lunardate, requests, cryptography; print('IMPORT_OK')\" 2>&1; echo __IMP_RC__=$?",
            ]
        elif mode == "test":
            out = f"{RD}/_r58_task2_env.xml"
            cmds = [
                f"cd {RD}/light-merge && export PYTHONIOENCODING=utf-8 && "
                f"{PY312} -m pytest tests/test_datetime.py tests/test_lightpub_bridge.py "
                f"tests/test_tls_light.py tests/test_async_io_light.py -q --tb=line -rs 2>&1; echo __RC__=$?",
            ]
        else:
            raise SystemExit(f"未知模式 {mode}")

        for c in cmds:
            print(f"\n===== CMD: {c[:160]} …")
            t0 = time.time()
            rc, out = S.run_remote(cli, c, timeout=1200)
            print(out)
            print(f"===== [rc={rc} elapsed={time.time()-t0:.1f}s]")
        return 0
    finally:
        cli.close()


if __name__ == "__main__":
    sys.exit(main())
