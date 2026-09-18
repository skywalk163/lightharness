# -*- coding: utf-8 -*-
"""R57 任务3：0.82 定向验证（排队执行，一次会话完成）。

步骤：
  1. 核对远端副本状态（lexer.py md5 —— 判断任务1a 修复是否已同步）；
  2. 上传两个新测试文件（纯新增，不覆盖任何既有文件）；
  3. py3.12 定向跑 lightharness/tests/test_R57_复现回归.py（旧 lexer 下预期
     4 场景红=复现取证、3 守卫绿）；
  4. py3.12 定向跑 light-merge/tests/test_R57_L170回归.py（预期绿）。
不跑全量、不清理、不改 src。
"""
from __future__ import annotations
import importlib.util
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
LH = HERE.parent.parent.parent
SYNC = LH / "scripts" / "同步0.82.py"
PY312 = "/usr/local/bin/python3.12"

FILES = [
    (LH / "tests" / "test_R57_复现回归.py",
     "lightharness/tests/test_R57_复现回归.py"),
    (LH.parent / "light-merge" / "tests" / "test_R57_L170回归.py",
     "light-merge/tests/test_R57_L170回归.py"),
]

spec = importlib.util.spec_from_file_location("sync082", SYNC)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def md5b(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def main() -> int:
    print("[local] lexer.py md5 =", md5b(LH.parent / "light-merge/src/lexer.py"))
    cli = mod.connect()
    try:
        mod.ensure_shim(cli)
        rd = mod.load_remote_dir()
        print(f"[remote] 副本 {rd}")

        rc, out = mod.run_remote(
            cli,
            "md5 -q {rd}/light-merge/src/lexer.py; "
            "ls {rd}/light-merge/src/__pycache__/lexer.cpython-312.pyc 2>/dev/null || "
            "echo '(no lexer pyc312)'".format(rd=rd),
            timeout=60, quiet=True)
        print("[remote] lexer md5/pyc:\n" + out)

        # 上传新测试文件
        sftp = cli.open_sftp()
        try:
            for local, rel in FILES:
                rp = f"{rd}/{rel}"
                sftp.put(str(local), rp)
                print(f"[upload] {rel} -> OK")
        finally:
            sftp.close()

        # 3) lightharness 新用例定向跑（py3.12，串行、置空 addopts）
        rc, out = mod.run_remote(
            cli,
            "cd {rd}/lightharness && LIGHT_MERGE={rd}/light-merge PYTHONIOENCODING=utf-8 "
            "{py} -m pytest tests/test_R57_复现回归.py -v --tb=line -o addopts= "
            "-p no:cacheprovider 2>&1 | tail -25; "
            "echo __RC__=${{PIPESTATUS}}".format(rd=rd, py=PY312),
            timeout=600, quiet=True)
        print("[0.82] test_R57_复现回归.py：\n" + out)

        # 4) L-170 用例定向跑
        rc, out = mod.run_remote(
            cli,
            "cd {rd}/light-merge && PYTHONIOENCODING=utf-8 "
            "{py} -m pytest tests/test_R57_L170回归.py -v --tb=short -o addopts= "
            "-p no:cacheprovider 2>&1 | tail -8".format(rd=rd, py=PY312),
            timeout=600, quiet=True)
        print("[0.82] test_R57_L170回归.py：\n" + out)
    finally:
        cli.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
