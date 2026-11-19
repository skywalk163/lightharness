# -*- coding: utf-8 -*-
"""scripts/fetch-deps.ps1 静态契约测试（T-0394）。

背景：README「第一步：一键拉齐三仓」原先只有 Bash 版，Windows 用户被迫装 Git Bash。
本测试钉住三件事：
  1. PowerShell 版脚本存在，且参数与 fetch-deps.sh 一一对应；
  2. 关键行为不退化（三仓平铺、标志物校验、pull --ff-only、冒烟入口、URL 覆盖）；
  3. README 给出 ps1 用法，且不再强迫用户装 Git Bash。

本机有 pwsh / powershell 时实跑 `-DryRun` 断言 rc=0；FreeBSD 等无 pwsh 环境按卡面
约定跳过实跑（不硬装），只跑静态契约。
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PS1 = REPO_ROOT / "scripts" / "fetch-deps.ps1"
SH = REPO_ROOT / "scripts" / "fetch-deps.sh"
README = REPO_ROOT / "README.md"


def _read(path: Path) -> str:
    # ps1 以 UTF-8 BOM 保存（Windows PowerShell 5.1 读中文需要 BOM），utf-8-sig 兼容两种
    return path.read_text(encoding="utf-8-sig")


def _run_powershell(args, cwd, timeout=120):
    exe = shutil.which("pwsh") or shutil.which("powershell")
    if not exe:
        pytest.skip("本机没有 pwsh / powershell，跳过实跑（见卡片「环境说明」）")
    return subprocess.run(
        [exe, "-NoProfile", "-File", str(PS1)] + list(args),
        cwd=str(cwd), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout,
    )


def test_ps1_exists_with_param_block():
    assert PS1.is_file(), "scripts/fetch-deps.ps1 不存在"
    text = _read(PS1)
    assert re.search(r"\bparam\s*\(", text), "缺少 param() 参数块"


@pytest.mark.parametrize("flag", [
    "-Dir", "-Mirror", "-Depth", "-Branch", "-NoPull", "-NoRun", "-DryRun",
])
def test_ps1_declares_flag(flag):
    assert flag in _read(PS1), f"缺少参数 {flag}"


def test_option_parity_with_sh():
    """sh 版每个长选项都要在 ps1 里有对应参数（改名是允许的，漏掉不行）。"""
    mapping = {
        "--dir": "-Dir",
        "--mirror": "-Mirror",
        "--depth": "-Depth",
        "--branch": "-Branch",
        "--no-pull": "-NoPull",
        "--no-run": "-NoRun",
        "--dry-run": "-DryRun",
    }
    sh_text = _read(SH)
    ps1_text = _read(PS1)
    for sh_flag, ps_flag in mapping.items():
        assert sh_flag in sh_text, f"sh 版缺少 {sh_flag}（对齐前提不成立）"
        assert ps_flag in ps1_text, f"ps1 缺少与 {sh_flag} 对应的 {ps_flag}"


def test_ps1_keeps_behavior_contract():
    text = _read(PS1)
    # 三仓平铺
    for repo in ("light", "lightplugin", "lightharness"):
        assert repo in text
    # 已存在仓走 ff-only，不重复克隆
    assert "pull --ff-only" in text
    # 布局标志物
    assert "light/src" in text
    assert "lightplugin/集成" in text
    assert "运行.py" in text
    # 冒烟通过两个环境变量指定依赖根
    assert "LIGHT_MERGE" in text and "LIGHTPLUGIN" in text
    assert "examples/冒烟.light" in text


@pytest.mark.parametrize("env", [
    "LIGHTHARNESS_DEPS_DIR", "LIGHT_REPO", "LIGHTPLUGIN_REPO", "LIGHTHARNESS_REPO",
])
def test_ps1_supports_env_override(env):
    assert env in _read(PS1), f"缺少环境变量支持 {env}"


def test_readme_documents_ps1():
    text = _read(README)
    assert "fetch-deps.ps1" in text, "README 未给出 PowerShell 用法"
    for banned in ("用 Git Bash", "必须用 Git Bash", "需要 Git Bash", "只能 Git Bash"):
        assert banned not in text, f"README 仍在强制 Git Bash：{banned}"


def test_ps1_dry_run_rc0(tmp_path):
    """有 pwsh 时实跑 -DryRun：rc=0、打印三仓 clone 命令、不落盘。"""
    r = _run_powershell(["-DryRun"], tmp_path)
    out = (r.stdout or "") + (r.stderr or "")
    assert r.returncode == 0, f"rc={r.returncode}\n{out}"
    assert "git clone" in out
    assert out.count("git clone") == 3, f"应打印三个仓的克隆命令\n{out}"
    for repo in ("light", "lightplugin", "lightharness"):
        assert repo in out
    assert not (tmp_path / "lightharness-deps").exists(), "-DryRun 不应创建目录"


def test_ps1_help_rc0(tmp_path):
    r = _run_powershell(["-Help"], tmp_path)
    out = (r.stdout or "") + (r.stderr or "")
    assert r.returncode == 0, f"rc={r.returncode}\n{out}"
    assert "-DryRun" in out and "-Mirror" in out
