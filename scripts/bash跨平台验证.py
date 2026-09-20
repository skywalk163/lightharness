#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R42 任务3：验证 bash 工具在不同平台的真实行为。

用法:
  python scripts/bash跨平台验证.py --root .. --out reports/R42_bash_<platform>.json
  python3.11 scripts/bash跨平台验证.py --root .. --out reports/R42_bash_freebsd.json

只验证工具行为，不修改 src/工具_bash.light 或光合编译器。
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="..", help="lightharness 根目录")
    parser.add_argument("--out", required=True, help="输出 JSON 路径")
    parser.add_argument("--light-merge", default=r"G:\dswork\duan-light-merge\light-merge", help="light-merge 根目录")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    light_merge = Path(args.light_merge)
    out = Path(args.out)
    if not out.is_absolute():
        out = (root / out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    light_code = f'''
从 {light_merge.as_posix()}/src/工具_bash.light 导入 执行bash
从 {light_merge.as_posix()}/stdlib/系统.light 导入 取根目录, 判断Windows, 取环境变量
从 {light_merge.as_posix()}/stdlib/外部命令.light 导入 读环境变量

设 工作目录 为 取根目录()
设 正 为 执行bash({{"command": "pwd"}})
设 echo值 为 "R42-" + 取环境变量("COMPUTERNAME", "POSIX")
设 echo结果 为 执行bash({{"command": "echo " + echo值}})
设 dir命令 为 "dir" 如果 判断Windows() 否则 "ls -la"
设 dir结果 为 执行bash({{"command": dir命令}})
设 反向 为 执行bash({{"command": "cd .. && pwd"}})
设 输出 为 格式化JSON([
  "root": 工作目录,
  "is_windows": 判断Windows(),
  "shell": 读环境变量("SHELL", 读环境变量("COMSPEC", "")),
  "cwd": 正,
  "echo": echo结果,
  "dir_cmd": dir命令,
  "dir": dir结果,
  "cd_escape": 反向
], True)
打印 输出
'''
    code_file = root / "examples" / "test_R42_bash跨平台.light"
    code_file.parent.mkdir(parents=True, exist_ok=True)
    code_file.write_text(light_code, encoding="utf-8")

    t0 = time.perf_counter()
    runner = root / "运行.py"
    if not runner.exists() and (light_merge / "运行.py").exists():
        runner = light_merge / "运行.py"
    proc = subprocess.run([sys.executable, str(runner), str(code_file)], cwd=str(root), capture_output=True, text=True, encoding="utf-8", timeout=120)
    elapsed = round(time.perf_counter() - t0, 3)
    raw = {
        "平台": platform.system(),
        "内核": platform.release(),
        "架构": platform.machine(),
        "python": sys.version.split()[0],
        "cwd": str(root),
        "light_merge": str(light_merge),
        "code": str(code_file),
        "returncode": proc.returncode,
        "elapsed": elapsed,
        "stdout_tail": proc.stdout[-1500:],
        "stderr_tail": proc.stderr[-1500:],
    }
    try:
        decoded = json.loads(proc.stdout.strip().splitlines()[-1])
        raw["stdout_json"] = decoded
        raw["checks"] = {
            "pwd_ok": decoded["cwd"]["退出码"] == 0,
            "echo_ok": decoded["echo"]["退出码"] == 0,
            "dir_ok": decoded["dir"]["退出码"] == 0,
            "cd_escape_blocked": decoded["cd_escape"]["退出码"] == -1 and "禁止切换到项目根目录之外" in decoded["cd_escape"]["错误"],
        }
        raw["checks"]["all_pass"] = all(v for v in raw["checks"].values())
    except Exception as exc:
        raw["checks"] = {"parse_stdout_json": False, "error": repr(exc), "all_pass": False}
    out.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(raw, ensure_ascii=False, indent=2))
    return 0 if raw["checks"].get("all_pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
