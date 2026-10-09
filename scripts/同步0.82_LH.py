# -*- coding: utf-8 -*-
"""R128-B —— lightharness 在 0.82（FreeBSD 15.1）上的全量 pytest 基线工具。

背景：R110 遗留至今，LH 从未在 0.82 建立过全量基线（此前 0.82 上的基线都是
      light-merge 的 `082_lightmerge基线_*`）。本脚本以 0.86（Linux）的
      `scripts/同步0.86.py` 为蓝本，面向 FreeBSD 0.82 做适配，一次性把
      probe / sync / verify / run / test-lh 打通。

相对 0.86 蓝本的改动点（0.82 特化）：
  1. 主机常量：DEFAULT_HOST=192.168.0.82，远端目录前缀 `r128-`，
     venv `/tmp/r128-venv`，shim `/tmp/r128-shim`。
  2. 远端 python：0.82 上**优先自建 venv**（`/tmp/r128-venv/bin/python`），
     缺失时退回 `/usr/local/bin/python3.12`。
     ⚠️ 0.82 系统只有 python3.11 / python3.12 两个解释器，且**没有 `python` 命令**；
     `tests/test_回归.py:241` 硬编码 `['python', RUNNER, f]` 起子进程，
     故必须把 shim 目录放在 PATH 最前面（`python` → venv python 3.12）。
  3. venv 用 `--system-site-packages` 建：0.82 系统 python3.12 已装好
     xdist/timeout/psutil/lunardate/antlr4==4.13.2（psutil 在 FreeBSD 无 wheel，
     纯新建 venv 要现场编译，慢且易失败），只额外 `pip install pytest==9.1.1`
     与本机 Windows 基线口径对齐（系统自带的是 8.4.2）。
  4. 打包三仓：lightharness + light-merge + **lightplugin**。
     lightplugin 缺失时 `运行.py:_lightplugin_paths()` **静默返回空表**，
     表现为 `No module named '生产挂载'` 连片红 34 条（0.86 踩过的坑）。
  5. 远端执行前缀注入 `export LIGHT_MERGE=<rd>/light-merge`：
     `运行.py:58` 的默认值是硬编码 Windows 路径 `G:\\dswork\\...`，不注入会 sys.exit(1)。
  6. 打包口径 = `git ls-files` tracked 树 + EXCLUDE 排除表。
     ⚠️ tracked 树不含未跟踪文件；且**当前工作树有未提交改动**（R127/R128），
     故每次 sync/test 都在产物里落一份「树版本」（三仓 HEAD 短 SHA + porcelain 摘要）。

R128-B 第二轮补齐（三段式收口）：
  7. `diff` 子命令：新增红 / 已修复 / 持平，判据 = 新增红为空。
  8. `cleanup` 子命令：清 0.82 /tmp 陈旧同步树（R125-A1：全目录递归会抢 stdlib → 假红）。
  9. addopts 是否置空**按所选解释器实测插件**决定（不写死）：
     `probe_caps()` 实测 xdist / pytest-timeout / FreeBSD timeout(1)，
     有 xdist → 保留 addopts 并显式补 `-n <jobs> --dist loadscope`；
     无 xdist → `-o addopts=` + `-p no:xdist`（否则 `-n/--timeout` ARGERROR）；
     无 pytest-timeout → 只靠 FreeBSD `timeout(1)` 兜硬超时。

用法：
    python scripts/同步0.82_LH.py probe
    python scripts/同步0.82_LH.py sync [--with-git]
    python scripts/同步0.82_LH.py verify
    python scripts/同步0.82_LH.py run -- CMD
    python scripts/同步0.82_LH.py test-lh [--jobs N] [--timeout-case N] [--timeout-sec N]
    # 连通性冒烟（小子集，不写 latest）
    python scripts/同步0.82_LH.py test-lh --select tests/unit/test_support.py \
        --jobs 2 --timeout-case 180 --timeout-sec 900 --poll 15 --round R128-B-smoke
    # 首轮全量（A 线完成后）
    python scripts/同步0.82_LH.py test-lh --jobs 4 --timeout-sec 5400 --round R128-B
    python scripts/同步0.82_LH.py diff [--prefix R128_LH_0.82基线_]
    python scripts/同步0.82_LH.py cleanup --keep-latest --yes
"""
from __future__ import annotations

import argparse
import io
import os
import re
import subprocess
import sys
import tarfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]            # G:/dswork/duan-light-merge
LIGHTHARNESS = ROOT / "lightharness"
LIGHT_MERGE = ROOT / "light-merge"
# R112-R1：lightplugin 是第 4 个独立仓，`运行.py:_lightplugin_paths()` 在目录缺失时
# 静默返回空表 ⇒ `No module named '生产挂载'` 连片红。远端落点 `{rd}/lightplugin`
# 正是 `运行.py` 的默认解析点（ROOT/../lightplugin），无需额外环境变量。
LIGHTPLUGIN = ROOT / "lightplugin"

DEFAULT_HOST = "192.168.0.82"
PORT = 22
REMOTE_BASE = "/tmp"
VENV_DIR = "/tmp/r128-venv"                           # 0.82 用户级 venv（不碰系统 python）
SHIM_DIR = "/tmp/r128-shim"                           # python/python3 → venv python
# ⚠️ 用 `r128-b-` 而非裸 `r128-`：R128-B 首轮用裸前缀时，远端副本
# `/tmp/r128-20261009-003837` 在 pytest 跑到 86% 时被**外部删除**（venv/shim 仍在，
# 只有同步副本没了，符合「别的清理动作命中 /tmp/r128-2*」的特征），导致整轮作废。
# 加线别标记 `b` 后不再与 `r128-2026*` 这类通配清理相撞。
REMOTE_DIR_PREFIX = "r128-b-"
SYSTEM_PY = "/usr/local/bin/python3.12"               # venv 不可用时的兜底解释器

# FreeBSD 无 /proc，probe 走 sysctl
PROBES = {
    "uname": "uname -a",
    "kernel": "uname -r",
    "arch": "uname -m",
    "os_release": "freebsd-version -ku 2>/dev/null || uname -sr",
    "cpu_cores": "sysctl -n hw.ncpu",
    "cpu_model": "sysctl -n hw.model",
    "mem_total_mb": "sysctl -n hw.physmem | awk '{print int($1/1048576)}'",
    "loadavg": "sysctl -n vm.loadavg",
    "disk_free_tmp": "df -h /tmp | tail -1",
    "python312_version": f"{SYSTEM_PY} -V 2>&1 || echo NONE",
    "python311_version": "/usr/local/bin/python3.11 -V 2>&1 || echo NONE",
    "python_cmd": "command -v python || echo NONE",
    "python3_cmd": "command -v python3 || echo NONE",
    "git_version": "git --version 2>&1 || echo NONE",
    "clang_version": "cc --version 2>&1 | head -2 || echo NONE",
    "shell": "echo $SHELL",
}

# ── tracked 树打包排除（沿用 0.86/0.82 口径：这些产物远端跑测试用不到且体积大）──
EXCLUDE_REL_PREFIXES = (
    ("docs", "历史存档"),        # lightharness：历史探针档案
    ("demo_video",),             # light-merge：Cinematic_*.mp4
    ("2026-09-11-d613c31d",),    # light-merge：历史任务输出目录
    ("light_verify.tar.gz",),    # light-merge：未跟踪打包产物
    ("data", "finetune"),        # lightharness：微调语料
    ("sessions",),               # lightharness：会话日志
    (".ci",),                    # light-merge：仅 report_local.xml
    ("light.egg-info",),         # light-merge：git 未跟踪
)
EXCLUDE_DIR_PREFIXES = ("_taskR11B_test_", "_082_lm_results_")

INCLUDE_GIT = False


# ---------------------------------------------------------------- 凭据
def _parse_env() -> dict:
    env_path = ROOT / ".env"
    if not env_path.exists():
        raise SystemExit(f"[同步0.82_LH] 缺少 .env：{env_path}")
    data: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip().lstrip("@").strip()             # 容忍 @SSH_PASS_DUMATE 笔误行
        data[k] = v.strip().strip('"').strip("'")
    return data


def load_accounts():
    """按优先级返回 [(账号名, 用户名, 密码), ...] + sudo 密码。"""
    d = _parse_env()
    order = ["AI", "TRAE", "WORKBUDDY", "DUMATE"]
    accts = []
    for a in order:
        u = d.get(f"SSH_USER_{a}")
        p = d.get(f"SSH_PASS_{a}") or d.get(f"SSH_PASS_{a}2")
        if u and p:
            accts.append((a, u, p))
    sudo = d.get("SUDO_PASS", "")
    return accts, sudo


def _key_files() -> list[str]:
    home = Path.home() / ".ssh"
    return [str(home / n) for n in ("id_rsa", "id_ed25519")
            if (home / n).exists()]


# ---------------------------------------------------------------- SSH
def connect(host: str, port: int = PORT, timeout: int = 30):
    """多账号依次探活：每个账号先试**公钥免密**（0.82 上 ai 已实测免密），
    再试 .env 密码。返回 (cli, 账号名, 用户名)。"""
    import paramiko

    accts, _sudo = load_accounts()
    override_user = os.environ.get("SSH_USER", "").strip()
    override_pass = os.environ.get("SSH_PASS", "").strip()
    if override_user:
        accts = [("ENV", override_user, override_pass)] + list(accts)
    if not accts:
        raise SystemExit("[同步0.82_LH] .env 无可用的 SSH 账号（SSH_USER_*/SSH_PASS_*）")

    keys = _key_files()
    last_err = None
    for acct, user, pwd in accts:
        # 1) 公钥免密
        if keys:
            try:
                cli = paramiko.SSHClient()
                cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                cli.connect(host, port=port, username=user, timeout=timeout,
                            allow_agent=False, look_for_keys=False,
                            key_filename=keys)
                try:
                    cli.get_transport().set_keepalive(30)
                except Exception:
                    pass
                print(f"[同步0.82_LH] ✅ 账号 {acct}({user})@{host} 连通（公钥）")
                return cli, acct, user
            except Exception as e:
                last_err = e
                print(f"[同步0.82_LH] ⚠️ {acct}({user}) 公钥失败：{type(e).__name__}: {e}")
        # 2) 密码
        if pwd:
            try:
                cli = paramiko.SSHClient()
                cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                cli.connect(host, port=port, username=user, password=pwd,
                            timeout=timeout, allow_agent=False, look_for_keys=False)
                try:
                    cli.get_transport().set_keepalive(30)
                except Exception:
                    pass
                print(f"[同步0.82_LH] ✅ 账号 {acct}({user})@{host} 连通（密码）")
                return cli, acct, user
            except Exception as e:
                last_err = e
                print(f"[同步0.82_LH] ⚠️ {acct}({user}) 密码失败：{type(e).__name__}: {e}")
    raise SystemExit(f"[同步0.82_LH] 所有账号均无法连通 {host}（末错：{last_err}）")


def run_remote(cli, cmd: str, timeout: int = 300, quiet: bool = False):
    """远端执行，增量回显 + 超时保护。返回 (rc, 全部输出)。"""
    chan = cli.get_transport().open_session()
    chan.settimeout(timeout)
    chan.exec_command(cmd)
    buf = io.StringIO()
    t0 = time.time()
    while True:
        if chan.recv_ready():
            chunk = chan.recv(65536).decode("utf-8", "replace")
            buf.write(chunk)
            if not quiet:
                sys.stdout.write(chunk)
                sys.stdout.flush()
        if chan.exit_status_ready():
            while chan.recv_ready():
                chunk = chan.recv(65536).decode("utf-8", "replace")
                buf.write(chunk)
                if not quiet:
                    sys.stdout.write(chunk)
                    sys.stdout.flush()
            break
        if time.time() - t0 > timeout:
            chan.close()
            raise TimeoutError(f"[同步0.82_LH] 远端命令超时 {timeout}s：{cmd[:120]}")
        time.sleep(0.2)
    rc = chan.recv_exit_status()
    chan.close()
    return rc, buf.getvalue()


def _q(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


# ---------------------------------------------------------------- 后台执行
def run_remote_bg(cli, cmd: str, logfile: str, timeout: int = 60):
    """后台启动命令（nohup … &），输出重定向到 logfile，返回 pid。"""
    wrapper = f"nohup sh -c {_q(cmd)} > {logfile} 2>&1 & echo $!"
    rc, out = run_remote(cli, wrapper, timeout=timeout, quiet=True)
    if rc != 0:
        raise SystemExit(f"[同步0.82_LH] 后台启动失败 rc={rc}：{out}")
    return out.strip().split()[-1]


def poll_remote(cli, logfile: str, pid: str, interval: int = 30, max_wait: int = 3600,
                watch_dir: str = ""):
    """轮询后台任务。返回 (rc 字符串, 尾部日志)。

    watch_dir：每轮额外查该目录是否还在。R128-B 首轮正是副本目录在 pytest 跑到
    86% 时被外部删除、整轮结果作废却无从察觉，故把「副本还在不在」变成显式观测点。
    """
    deadline = time.time() + max_wait
    last = ""
    while time.time() < deadline:
        watch = (f"test -d {watch_dir} && echo __DIR_OK__ || echo __DIR_GONE__; "
                 if watch_dir else "")
        rc, out = run_remote(
            cli,
            f"if kill -0 {pid} 2>/dev/null; then echo __RUNNING__; else echo __DONE__; fi; "
            f"{watch}"
            f"echo __TAIL__; tail -n 30 {logfile}",
            timeout=60, quiet=True)
        last = out
        if watch_dir and "__DIR_GONE__" in out:
            print(f"[同步0.82_LH] ❌ 副本目录 {watch_dir} 在测试期间消失（外部删除/清理）")
            return "DIR_GONE", out
        if "__DONE__" in out:
            _, code = run_remote(
                cli, f"grep -m1 'R128_EXIT=' {logfile} 2>/dev/null || echo R128_EXIT=unknown",
                timeout=60, quiet=True)
            m = [l for l in code.splitlines() if l.startswith("R128_EXIT=")]
            return (m[0].split("=", 1)[1].strip() if m else "unknown"), out
        time.sleep(interval)
    return "TIMEOUT", last


# ---------------------------------------------------------------- 树版本
def tree_info() -> dict:
    """三仓的被测代码身份（HEAD 短 SHA + 工作区脏摘要）。

    `git ls-files` 只打 tracked 树，**未跟踪文件不进包**；工作树的未提交改动
    会随 tarfile.add 进包。故必须记录，否则「远端跑的和本机不一样」无从察觉。
    """
    out = {}
    for label, base in (("lightharness", LIGHTHARNESS),
                        ("light-merge", LIGHT_MERGE),
                        ("lightplugin", LIGHTPLUGIN)):
        rec: dict = {"path": str(base)}
        if not base.is_dir():
            rec["error"] = "目录不存在"
            out[label] = rec
            continue
        try:
            h = subprocess.run(["git", "-C", str(base), "rev-parse", "--short", "HEAD"],
                               capture_output=True, text=True, timeout=20)
            rec["head"] = h.stdout.strip() or "(不可用)"
            s = subprocess.run(["git", "-C", str(base), "status", "--porcelain"],
                               capture_output=True, text=True, timeout=20)
            lines = [l for l in (s.stdout or "").splitlines() if l.strip()]
            rec["dirty_count"] = len(lines)
            rec["dirty_preview"] = lines[:10]
            rec["untracked"] = [l[3:] for l in lines if l.startswith("??")]
        except (OSError, subprocess.SubprocessError) as e:
            rec["error"] = f"{type(e).__name__}: {e}"
        out[label] = rec
    return out


def print_tree_info(info: dict) -> None:
    for label, rec in info.items():
        print(f"[同步0.82_LH] 被测 {label}: HEAD={rec.get('head')} "
              f"脏={rec.get('dirty_count')} 未跟踪={len(rec.get('untracked') or [])}"
              + (f" 错误={rec['error']}" if rec.get("error") else ""))


# ---------------------------------------------------------------- 打包
def _should_skip(rel: Path) -> bool:
    parts = tuple(rel.parts)
    for pref in EXCLUDE_REL_PREFIXES:
        if parts[:len(pref)] == pref:
            return True
    for part in parts:
        if any(part.startswith(p) for p in EXCLUDE_DIR_PREFIXES):
            return True
    return False


def build_tarball(out_path: Path) -> int:
    n = 0
    with tarfile.open(out_path, "w:gz", compresslevel=1) as tf:
        for base in (LIGHTHARNESS, LIGHT_MERGE, LIGHTPLUGIN):
            if not base.exists():
                print(f"[同步0.82_LH] 警告：缺失 {base}，跳过")
                continue
            arc_root = base.name
            # ⚠️ 必须 `-c core.quotePath=false`：git 默认把中文路径转义成八进制，
            # 导致下方 p.exists() 恒 False → 中文名文件被静默跳过（0.86 踩过）。
            res = subprocess.run(["git", "-c", "core.quotePath=false", "-C", str(base),
                                  "ls-files"],
                                 capture_output=True, text=True, encoding="utf-8")
            if res.returncode != 0:
                print(f"[同步0.82_LH] ⚠️ {base.name} 非 git 仓或 ls-files 失败："
                      f"{res.stderr.strip()[:120]}")
                continue
            tracked = [l for l in res.stdout.splitlines() if l]
            missed = 0
            for rel in tracked:
                rp = Path(rel)
                if _should_skip(rp):
                    continue
                p = base / rel
                if not p.exists():
                    missed += 1
                    continue
                tf.add(p, arcname=f"{arc_root}/{rel}".replace("\\", "/"))
                n += 1
            print(f"[同步0.82_LH]   {base.name}: tracked {len(tracked)} → 入包 {n}，"
                  f"工作树已删 {missed}")
            untracked = [l[3:] for l in (subprocess.run(
                ["git", "-c", "core.quotePath=false", "-C", str(base),
                 "status", "--porcelain"],
                capture_output=True, text=True, encoding="utf-8").stdout or "").splitlines()
                if l.startswith("??")]
            if untracked:
                preview = ", ".join(untracked[:5]) + ("…" if len(untracked) > 5 else "")
                print(f"[同步0.82_LH]   ⚠️ {base.name} 有 {len(untracked)} 个未跟踪文件"
                      f"不入包（如属测试依赖请先 commit）：{preview}")
            if INCLUDE_GIT:
                git_dir = base / ".git"
                if git_dir.is_dir():
                    tf.add(git_dir, arcname=f"{arc_root}/.git".replace("\\", "/"))
                    n += 1
    return n


# ---------------------------------------------------------------- venv + shim
def ensure_venv(cli) -> str:
    """建 /tmp/r128-venv（--system-site-packages + pytest 9.1.1），返回 venv python。

    0.82 的 FreeBSD 无 psutil/numpy 等 manylinux wheel，纯新建 venv 现场编译既慢又
    易失败；系统 python3.12 已带 xdist 3.8.0 / pytest-timeout 2.4.0 / psutil 7.2.2 /
    lunardate 0.3.0 / antlr4-python3-runtime 4.13.2 / requests / cryptography /
    aiohttp，故用 --system-site-packages 继承，只补装 pytest==9.1.1 与本机
    Windows 基线（pytest 9.1.1）对齐。
    """
    rc, out = run_remote(cli, f"test -x {VENV_DIR}/bin/python && echo OK || echo NEED",
                         quiet=True)
    if "OK" not in out:
        rc, out = run_remote(cli, f"rm -rf {VENV_DIR} && {SYSTEM_PY} -m venv "
                                  f"--system-site-packages {VENV_DIR} && echo VENV_OK",
                             timeout=600, quiet=True)
        if rc != 0 or "VENV_OK" not in out:
            raise SystemExit(f"[同步0.82_LH] venv 创建失败 rc={rc}：{out.strip()[:300]}")
    pip = f"{VENV_DIR}/bin/pip"
    # pytest：系统 8.4.2 → venv 内装 9.1.1（与 Windows 基线同版本口径）
    rc, out = run_remote(cli, f"{pip} install -q pytest==9.1.1", timeout=900, quiet=True)
    if rc != 0:
        print(f"[同步0.82_LH] ⚠️ pip install pytest==9.1.1 返回 rc={rc}：{out.strip()[:300]}")
    rc, out = run_remote(cli, f"{pip} install -q pytest-xdist==3.8.0 pytest-timeout==2.4.0 "
                              f"psutil==7.2.2 lunardate==0.3.0 "
                              f"antlr4-python3-runtime==4.13.2", timeout=900, quiet=True)
    if rc != 0:
        print(f"[同步0.82_LH] ⚠️ pip install 依赖组返回 rc={rc}：{out.strip()[:300]}")
    # shim：0.82 没有 `python` 命令，而 test_回归.py 硬编码 ['python', …]
    vpy = f"{VENV_DIR}/bin/python"
    run_remote(cli,
               f"mkdir -p {SHIM_DIR} && "
               f'printf "#!/bin/sh\\nexec {vpy} \\"\\$@\\"\\n" > {SHIM_DIR}/python && '
               f"cp {SHIM_DIR}/python {SHIM_DIR}/python3 && "
               f"chmod +x {SHIM_DIR}/python {SHIM_DIR}/python3", quiet=True)
    rc, ver = run_remote(cli, f"{vpy} -V && {vpy} -c "
                              f"'import pytest,xdist,pytest_timeout,psutil,lunardate,antlr4;"
                              f"print(\"plugins\",pytest.__version__)'", quiet=True)
    print(f"[同步0.82_LH] venv 就绪：{vpy}（{ver.strip()}）")
    return vpy


def remote_python(cli) -> str:
    """远端 python 解析：优先 venv python，缺失兜底 /usr/local/bin/python3.12。"""
    rc, out = run_remote(cli, f"test -x {VENV_DIR}/bin/python && echo OK || echo NO",
                         quiet=True)
    if rc == 0 and "OK" in out:
        return f"{VENV_DIR}/bin/python"
    return SYSTEM_PY


def has_remote(cli, expr: str) -> bool:
    """远端能力探测（`python -c 'import x'` / `command -v timeout`），rc=0 才算有。"""
    rc, _ = run_remote(cli, expr, timeout=180, quiet=True)
    return rc == 0


def probe_caps(cli, vpy: str) -> dict:
    """按**所选解释器**实测插件能力，决定 addopts 是否置空 / 是否并行 / 超时谁兜。

    ⚠️ 这是本脚本最关键的自适应点，不允许写死：
      * 有 xdist  → 保留被测仓自带 addopts，并显式补 `-n <jobs> --dist loadscope`；
      * 无 xdist  → addopts 里的 `-n`/`--timeout` 会直接 ARGERROR，必须
                    `-o addopts=` 置空 + `-p no:xdist`；
      * 有 pytest-timeout → 显式 `--timeout N`；否则只能靠 FreeBSD `timeout(1)` 兜硬超时。
    """
    caps = {
        "python": vpy,
        "xdist": has_remote(cli, f"{vpy} -c 'import xdist'"),
        "pytest_timeout": has_remote(cli, f"{vpy} -c 'import pytest_timeout'"),
        "bsd_timeout": has_remote(cli, "command -v timeout"),
    }
    rc, out = run_remote(cli, "sysctl -n hw.ncpu", timeout=60, quiet=True)
    caps["ncpu"] = int(out.strip().split()[0]) if out.strip().isdigit() else 1
    rc, out = run_remote(cli, f"{vpy} -c 'import pytest;print(pytest.__version__)'",
                         timeout=120, quiet=True)
    caps["pytest"] = out.strip() or "(未知)"
    return caps


def build_pytest_argv(caps: dict, *, jobs: int, case_timeout: int,
                      xml_remote: str, select: list[str] | None = None) -> list[str]:
    """按能力组装 pytest 参数（空 select = 全量 tests/）。"""
    argv = ["-m", "pytest", "-q", "--tb=no", "-rfE", "-p", "no:cacheprovider",
            "--junitxml", xml_remote]
    argv += list(select) if select else ["tests/"]
    if caps["xdist"]:
        # 保留被测仓自带 addopts（LH pytest.ini: --timeout=60 -n 4），
        # 显式补 -n/--dist 双保险（jobs 不超过远端核数）
        argv += ["-n", str(max(1, min(jobs, caps["ncpu"]))), "--dist", "loadscope"]
    else:
        argv += ["-o", "addopts=", "-p", "no:xdist"]
    if caps["pytest_timeout"]:
        argv += ["--timeout", str(case_timeout)]
    return argv


def remote_prefix(remote_dir: str, sub: str = "lightharness") -> str:
    """远端执行前缀：切目录 + 注入 LIGHT_MERGE / PATH（shim 在最前）/ 编码。"""
    return (f"cd {remote_dir}/{sub} && export LIGHT_MERGE={remote_dir}/light-merge && "
            f"export PATH={SHIM_DIR}:{VENV_DIR}/bin:$PATH && "
            f"export PYTHONIOENCODING=utf-8 && ")


# ---------------------------------------------------------------- 子命令
def cmd_probe(args) -> int:
    cli, acct, user = connect(args.host, args.port)
    try:
        info: dict = {"host": args.host, "port": args.port, "account_used": acct,
                      "username": user, "probed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                      "note": "FreeBSD 15.1-STABLE；禁 ICMP，探活只能 ssh"}
        for key, cmd in PROBES.items():
            _, out = run_remote(cli, cmd, timeout=60, quiet=True)
            info[key] = out.strip()
        # venv 就绪情况
        _, out = run_remote(cli, f"test -x {VENV_DIR}/bin/python && "
                                 f"{VENV_DIR}/bin/python -c 'import pytest;print(pytest.__version__)' "
                                 f"|| echo NOT_BUILT", timeout=120, quiet=True)
        info["venv_pytest"] = out.strip()
        print("[同步0.82_LH] 环境探测：")
        for k, v in info.items():
            print(f"   {k}: {v}")
        info["tree"] = tree_info()
        print_tree_info(info["tree"])
        out_path = LIGHTHARNESS / "reports" / "R128_LH_0.82环境探测.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(json_dumps(info).encode("utf-8"))
        print(f"[同步0.82_LH] ✅ 环境探测写入 {out_path.relative_to(ROOT)}")
        return 0
    finally:
        cli.close()


def cmd_sync(args) -> int:
    global INCLUDE_GIT
    INCLUDE_GIT = getattr(args, "with_git", False)
    ti = tree_info()
    print_tree_info(ti)
    ts = time.strftime("%Y%m%d-%H%M%S")
    remote_dir = f"{REMOTE_BASE}/{REMOTE_DIR_PREFIX}{ts}"
    tar_path = ROOT / "_r128_lh_sync.tar.gz"

    print("[同步0.82_LH] 打包（git tracked 树；三仓 lightharness+light-merge+lightplugin"
          f"{'；含 .git' if INCLUDE_GIT else ''}）…")
    t0 = time.time()
    n = build_tarball(tar_path)
    size_mb = tar_path.stat().st_size / 1024 / 1024
    print(f"[同步0.82_LH] 打包完成：{n} 文件，{size_mb:.1f} MB，耗时 {time.time()-t0:.1f}s")

    cli, *_ = connect(args.host, args.port)
    try:
        ensure_venv(cli)
        sftp = cli.open_sftp()
        try:
            sftp.mkdir(remote_dir)
        except OSError:
            pass
        remote_tar = f"{remote_dir}/sync.tar.gz"
        print(f"[同步0.82_LH] 上传 → {remote_tar}")
        t1 = time.time()
        sftp.put(str(tar_path), remote_tar)
        print(f"[同步0.82_LH] 上传完成，耗时 {time.time()-t1:.1f}s")
        sftp.close()

        print("[同步0.82_LH] 远端解压…")
        rc, out = run_remote(cli,
                             f"cd {remote_dir} && tar -xzf sync.tar.gz && rm -f sync.tar.gz && "
                             f"ls -d {remote_dir}/lightharness {remote_dir}/light-merge "
                             f"{remote_dir}/lightplugin", timeout=600)
        if rc != 0:
            raise SystemExit(f"[同步0.82_LH] 解压失败 rc={rc}")
        print(out.strip())

        if INCLUDE_GIT:
            for sub in ("lightharness", "light-merge", "lightplugin"):
                run_remote(cli, f"git config --global --add safe.directory {remote_dir}/{sub}",
                           quiet=True)
                _, o = run_remote(cli, f"git -C {remote_dir}/{sub} rev-parse --short HEAD",
                                  quiet=True)
                print(f"[同步0.82_LH] {sub} 远端 git HEAD = {o.strip() or '(不可用)'}")

        ptr = LIGHTHARNESS / "reports" / "同步0.82_LH_远程目录.txt"
        ptr.parent.mkdir(parents=True, exist_ok=True)
        ptr.write_bytes(remote_dir.encode("utf-8"))
        tp = LIGHTHARNESS / "reports" / "同步0.82_LH_树版本.json"
        tp.write_bytes(json_dumps({"remote_dir": remote_dir,
                                   "synced_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                                   "tree": ti}).encode("utf-8"))
        print(f"[同步0.82_LH] ✅ 完成：远程副本 {remote_dir}"
              f"（指针 {ptr.relative_to(ROOT)}）")
        return 0
    finally:
        cli.close()
        try:
            tar_path.unlink()
        except OSError:
            pass


def cmd_verify(args) -> int:
    cli, *_ = connect(args.host, args.port)
    try:
        rd = load_remote_dir()
        vpy = remote_python(cli)
        rc, out = run_remote(cli,
                             f"ls -d {rd}/lightharness {rd}/light-merge {rd}/lightplugin && "
                             f"ls {rd}/lightplugin/集成/生产挂载.light && "
                             f"ls {rd}/lightharness/examples/*.light | wc -l && "
                             f"ls {rd}/lightharness/tests/test_*.py | wc -l && "
                             f"{vpy} -V", quiet=True)
        print(out.strip())
        # 冒烟：运行.py 能否起来（验证 LIGHT_MERGE + lightplugin 注入正确）
        rc2, out2 = run_remote(cli, remote_prefix(rd) +
                               f"{vpy} 运行.py --help 2>&1 | head -5; echo SMOKERC=$?",
                               timeout=300, quiet=True)
        print(f"[同步0.82_LH] 运行.py 冒烟 rc={rc2}：{out2.strip()[:200]}")
        return 0 if rc == 0 else 1
    finally:
        cli.close()


def cmd_run(args) -> int:
    cli, *_ = connect(args.host, args.port)
    try:
        rd = load_remote_dir()
        vpy = remote_python(cli)
        cmd_parts = list(args.cmd)
        if cmd_parts and cmd_parts[0] == "--":
            cmd_parts = cmd_parts[1:]
        # ⚠️ 每个参数单独加引号：`-c "<含空格的代码>"` 不括起来会被远端 sh
        # 拆成多个词 → rc=2「命令找不到」。代价：本通道不解释管道/重定向等元字符。
        cmd = " ".join(_q(a) for a in cmd_parts)
        full = remote_prefix(rd) + cmd
        print(f"[同步0.82_LH] 远端执行（py={vpy}）：{full}")
        rc, _ = run_remote(cli, full, timeout=args.timeout)
        print(f"[同步0.82_LH] rc={rc}")
        return rc
    finally:
        cli.close()


def _load_base_lib():
    import importlib.util
    spec = importlib.util.spec_from_file_location("回归基线", LIGHTHARNESS / "scripts" / "回归基线.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cmd_test_lh(args) -> int:
    """0.82 上跑 lightharness pytest（全量 or 子集冒烟）。

    `--select` 给空 = 全量 `tests/`（首轮基线用）；给了就是子集（连通性冒烟用）。
    ⚠️ 子集结果**不写 latest 指针**（latest 只代表全量基线），落独立前缀，
       否则一次冒烟就把首轮全量基线顶掉，后续 diff 全是假信号。
    """
    select = [s for s in (args.select or []) if s]
    subset = bool(select)
    cli, *_ = connect(args.host, args.port)
    try:
        ensure_venv(cli)
        rd = load_remote_dir()
        vpy = remote_python(cli)
        caps = probe_caps(cli, vpy)
        print(f"[同步0.82_LH] 解释器 {vpy}：pytest={caps['pytest']} "
              f"xdist={'可用' if caps['xdist'] else '缺失'} "
              f"pytest-timeout={'可用' if caps['pytest_timeout'] else '缺失'} "
              f"timeout(1)={'可用' if caps['bsd_timeout'] else '缺失'} ncpu={caps['ncpu']}")
        argv = build_pytest_argv(caps, jobs=args.jobs,
                                 case_timeout=args.timeout_case,
                                 xml_remote=f"{rd}/lh_results.xml", select=select)
        if args.marker:
            argv += ["-m", args.marker]
        xml_remote = f"{rd}/lh_results.xml"
        logfile = f"{rd}/lh_test.log"
        inner = (f"export LIGHT_MERGE={rd}/light-merge && "
                 f"export PATH={SHIM_DIR}:{VENV_DIR}/bin:$PATH && "
                 f"export PYTHONIOENCODING=utf-8 && cd {rd}/lightharness && "
                 f"{vpy} " + " ".join(_q(a) for a in argv))
        if caps["bsd_timeout"]:
            cmd = f"timeout {args.timeout_sec} sh -c {_q(inner)}; echo R128_EXIT=$? >> {logfile}"
        else:
            cmd = f"{inner}; echo R128_EXIT=$? >> {logfile}"
        print(f"[同步0.82_LH] {'后台' if args.bg else '前台'}启动 LH {'子集' if subset else '全量'}："
              f"{' '.join(select) if subset else 'tests/'}（jobs={args.jobs}，"
              f"用例超时 {args.timeout_case}s，硬超时 {args.timeout_sec}s）")
        print(f"[同步0.82_LH]   命令：{' '.join(argv)}")
        if args.bg:
            pid = run_remote_bg(cli, cmd, logfile)
            print(f"[同步0.82_LH] pid={pid}，轮询中（每 {args.poll}s）…")
            code, tail = poll_remote(cli, logfile, pid, interval=args.poll,
                                     max_wait=args.timeout_sec + 600)
            print(f"[同步0.82_LH] LH 退出码={code}（unknown = 后台标记行未落到日志，"
                  f"需人工核对 {logfile}）")
            for ln in tail.splitlines()[-25:]:
                print("   |", ln)
        else:
            # 默认前台：SSH 已开 keepalive(30s)，不会因空闲被掐；退出码真实可靠
            # （后台模式实测 R128_EXIT 标记行偶发丢失 → 退出码 unknown）
            t0 = time.monotonic()
            rc, tail = run_remote(cli, cmd, timeout=args.timeout_sec + 300)
            elapsed = round(time.monotonic() - t0, 1)
            m = [l for l in tail.splitlines() if l.startswith("R128_EXIT=")]
            code = m[-1].split("=", 1)[1].strip() if m else str(rc)
            print(f"[同步0.82_LH] LH 退出码={code}（本机耗时 {elapsed}s）")
            for ln in tail.splitlines()[-25:]:
                print("   |", ln)
        sftp = cli.open_sftp()
        try:
            sftp.stat(xml_remote)
        except OSError:
            print("[同步0.82_LH] ❌ 远端无 junitxml，LH 未跑到收尾")
            sftp.close()
            return 2
        local_xml = LIGHTHARNESS / "reports" / f"R128_lh_results_{_stamp()}.xml"
        sftp.get(xml_remote, str(local_xml))
        sftp.close()
        print(f"[同步0.82_LH] 取回 junitxml → {local_xml.name}")
        base = _load_base_lib()
        parsed = base.parse_junit(local_xml)
        if parsed["totals"]["total"] == 0:
            print("[同步0.82_LH] ❌ junitxml 里 0 用例：收集阶段就没跑起来（参数/路径错？）")
            return 3
        baseline = base.make_baseline(
            parsed, name="lightharness", platform="0.82 FreeBSD 15.1-STABLE",
            host=args.host, remote_dir=rd, cwd=f"{rd}/lightharness",
            runner={"mode": "subset" if subset else "full",
                    "parallel": caps["xdist"], "target": "lightharness",
                    "cmd": " ".join(argv), "python": vpy, "pytest_rc": code,
                    "jobs": args.jobs, "case_timeout": args.timeout_case,
                    "addopts_cleared": not caps["xdist"],
                    "select": select, "caps": caps},
            round_=args.round)
        baseline["tree"] = tree_info()
        prefix = args.out_prefix or ("R128_LH_0.82冒烟_" if subset
                                     else "R128_LH_0.82基线_")
        path = LIGHTHARNESS / "reports" / f"{prefix}{_stamp()}.json"
        base.save_baseline(baseline, path)
        if not subset:
            base.save_baseline(baseline,
                               LIGHTHARNESS / "reports" / "R128_LH_0.82基线_latest.json")
        print(f"[同步0.82_LH] 基线写入 {path.name}（round={args.round}"
              f"{'，子集不更新 latest' if subset else ''}）")
        t = baseline["totals"]
        print(f"[同步0.82_LH] 摘要：共{t['total']} 通过{t['passed']} 失败{t['failed']} "
              f"跳过{t['skipped']} 错误{t['error']} xfail{t['xfailed']} "
              f"耗时{t['duration_sec']}s")
        if baseline["failed"]:
            print(f"[同步0.82_LH] 失败明细（前 {min(40, len(baseline['failed']))}）：")
            for f in baseline["failed"][:40]:
                print("   ✗", f["id"], "—", (f["message"] or "")[:160])
        return 0
    finally:
        cli.close()


def _list_baselines(prefix: str) -> list[Path]:
    """按 **mtime** 排序（不能按文件名：任务名插在中间会造成基线顺序错乱 → 假 PASS）。"""
    rep = LIGHTHARNESS / "reports"
    if not rep.exists():
        return []
    return sorted((p for p in rep.glob(f"{prefix}*.json")
                   if not p.name.endswith("latest.json")),
                  key=lambda p: p.stat().st_mtime)


def cmd_diff(args) -> int:
    """与基线对比，输出新增红 / 已修复 / 持平。判据 = 新增红为空。"""
    base = _load_base_lib()
    prefix = args.prefix
    history = _list_baselines(prefix)
    if args.base:
        base_path = Path(args.base)
        new_path = Path(args.new) if args.new else history[-1] if history else None
    else:
        if len(history) < 2:
            print(f"[同步0.82_LH] 前缀 {prefix} 只有 {len(history)} 份基线，无可比对的历史"
                  f"（首次跑不判新增红）")
            return 0
        base_path, new_path = history[-2], history[-1]
    if new_path is None:
        print("[同步0.82_LH] 没有可比对的新基线，先跑 test-lh")
        return 1
    b = base.load_baseline(base_path)
    n = base.load_baseline(new_path)
    print(f"[同步0.82_LH] 对比：{new_path.name}  ⟵  {base_path.name}")
    d = base.diff_baselines(b, n)
    base.print_diff_result(d, label="同步0.82_LH")
    rp = LIGHTHARNESS / "reports" / f"R128_LH_0.82_diff_{_stamp()}.json"
    rp.write_bytes(json_dumps({"diff": d, "base": str(base_path),
                               "new": str(new_path)}).encode("utf-8"))
    print(f"[同步0.82_LH] 对比报告 {rp.name}")
    return 0 if d["ok"] else 1


def cmd_cleanup(args) -> int:
    """清理 0.82 上的陈旧同步树（R125-A1：/tmp 里的空壳 .light 会被全目录递归
    抢在 canonical stdlib 前 → 假红；跑门前 /tmp 必须只留当前副本）。"""
    cli, *_ = connect(args.host, args.port)
    try:
        rc, out = run_remote(cli, f"ls -d {REMOTE_BASE}/{REMOTE_DIR_PREFIX}* 2>/dev/null",
                             timeout=120, quiet=True)
        # ⚠️ 只认「同步树」= r128-<8位日期>-<6位时间>；同前缀的 r128-venv / r128-shim
        #    是长期复用件（删了要重建 venv、shim 也丢），必须排除
        pat = re.compile(rf"^{re.escape(REMOTE_BASE)}/{re.escape(REMOTE_DIR_PREFIX)}"
                         r"\d{8}-\d{6}$")
        dirs = [d for d in out.split() if d.strip() and pat.match(d.strip())]
        if not dirs:
            print(f"[同步0.82_LH] {REMOTE_BASE} 下无同步树副本"
                  f"（{REMOTE_DIR_PREFIX}<YYYYMMDD>-<HHMMSS>）")
            return 0
        keep = ""
        if args.keep_latest:
            keep = load_remote_dir() if (LIGHTHARNESS / "reports"
                                         / "同步0.82_LH_远程目录.txt").exists() else ""
        rm = [d for d in dirs if d != keep]
        print(f"[同步0.82_LH] /tmp 副本 {len(dirs)} 个，保留 {keep or '(无)'}，待删 {len(rm)}")
        for d in rm:
            print(f"[同步0.82_LH]   将删 {d}")
        if not rm:
            return 0
        if not args.yes:
            print("[同步0.82_LH] 加 --yes 才真删（安全阀）")
            return 0
        for d in rm:
            rc2, o2 = run_remote(cli, f"rm -rf {_q(d)} && echo OK || echo FAIL",
                                 timeout=300, quiet=True)
            print(f"[同步0.82_LH]   rm {d} → {o2.strip()}")
        _, out = run_remote(cli, f"ls -d {REMOTE_BASE}/{REMOTE_DIR_PREFIX}* 2>/dev/null || echo 空",
                            timeout=120, quiet=True)
        print(f"[同步0.82_LH] 清理后剩余：{out.strip()}")
        return 0
    finally:
        cli.close()


def cmd_test_lm(args) -> int:
    """0.82 上跑 light-merge 全量 pytest（LH 依赖 LM 编译器树，顺带保留）。"""
    cli, *_ = connect(args.host, args.port)
    try:
        ensure_venv(cli)
        rd = load_remote_dir()
        vpy = remote_python(cli)
        xml_remote = f"{rd}/lm_results.xml"
        argv = ["-m", "pytest", "tests/", "-q", "--tb=no", "-rfE",
                "-p", "no:cacheprovider", "--junitxml", xml_remote,
                "--timeout", str(args.timeout_case), "-n", str(args.jobs),
                "--dist", "loadscope"]
        logfile = f"{rd}/lm_test.log"
        inner = (f"export PATH={SHIM_DIR}:{VENV_DIR}/bin:$PATH && "
                 f"export PYTHONIOENCODING=utf-8 && cd {rd}/light-merge && "
                 f"{vpy} " + " ".join(_q(a) for a in argv))
        cmd = f"timeout {args.timeout_sec} sh -c {_q(inner)}; echo R128_EXIT=$? >> {logfile}"
        print(f"[同步0.82_LH] 后台启动 LM 全量（硬超时 {args.timeout_sec}s）…")
        pid = run_remote_bg(cli, cmd, logfile)
        code, tail = poll_remote(cli, logfile, pid, interval=args.poll,
                                 max_wait=args.timeout_sec + 600)
        print(f"[同步0.82_LH] LM 退出码={code}")
        for ln in tail.splitlines()[-20:]:
            print("   |", ln)
        local_xml = LIGHTHARNESS / "reports" / f"R128_lm_results_{_stamp()}.xml"
        sftp = cli.open_sftp()
        try:
            sftp.stat(xml_remote)
        except OSError:
            print("[同步0.82_LH] ❌ 远端无 junitxml，LM 未跑到收尾")
            sftp.close()
            return 2
        sftp.get(xml_remote, str(local_xml))
        sftp.close()
        base = _load_base_lib()
        parsed = base.parse_junit(local_xml)
        baseline = base.make_baseline(
            parsed, name="light-merge", platform="0.82 FreeBSD 15.1-STABLE",
            host=args.host, remote_dir=rd, cwd=f"{rd}/light-merge",
            runner={"mode": "full", "parallel": True, "target": "light-merge",
                    "cmd": " ".join(argv), "python": vpy, "pytest_rc": code},
            round_=args.round)
        baseline["tree"] = tree_info()
        path = LIGHTHARNESS / "reports" / f"R128_LM_0.82基线_{_stamp()}.json"
        base.save_baseline(baseline, path)
        t = baseline["totals"]
        print(f"[同步0.82_LH] LM 摘要：共{t['total']} 通过{t['passed']} 失败{t['failed']} "
              f"跳过{t['skipped']} 错误{t['error']}")
        return 0
    finally:
        cli.close()


# ---------------------------------------------------------------- 工具
def json_dumps(obj) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def _stamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def load_remote_dir() -> str:
    env = os.environ.get("R128_REMOTE_DIR", "").strip()
    if env:
        return env
    p = LIGHTHARNESS / "reports" / "同步0.82_LH_远程目录.txt"
    if p.exists():
        v = p.read_bytes().decode("utf-8", "replace").strip()
        if v:
            return v
    raise SystemExit("[同步0.82_LH] 未知远程副本路径，请先执行 sync（或设 R128_REMOTE_DIR）")


# ---------------------------------------------------------------- CLI
def main() -> int:
    ap = argparse.ArgumentParser(description="R128-B：lightharness 0.82(FreeBSD) 全量基线")
    ap.add_argument("--host", default=DEFAULT_HOST, help=f"目标机（默认 {DEFAULT_HOST}）")
    ap.add_argument("--port", type=int, default=PORT)
    sub = ap.add_subparsers(dest="sub", required=True)

    sub.add_parser("probe", help="环境探测 → reports/R128_LH_0.82环境探测.json").set_defaults(fn=cmd_probe)
    p_sync = sub.add_parser("sync", help="打包三仓+上传+解压+建 venv")
    p_sync.add_argument("--with-git", action="store_true", help="连 .git 一起同步")
    p_sync.set_defaults(fn=cmd_sync)
    sub.add_parser("verify", help="校验远端副本（含 运行.py 冒烟）").set_defaults(fn=cmd_verify)
    p_run = sub.add_parser("run", help="远端执行命令")
    p_run.add_argument("cmd", nargs=argparse.REMAINDER)
    p_run.add_argument("--timeout", type=int, default=3000)
    p_run.set_defaults(fn=cmd_run)

    p_lh = sub.add_parser("test-lh", help="0.82 上跑 lightharness pytest（全量/子集）")
    p_lh.add_argument("--select", nargs="*", default=None,
                      help="pytest 目标子集（空 = 全量 tests/）。例：--select tests/unit/test_support.py。"
                           "⚠️ 给了 select 就是子集冒烟，结果落 冒烟_ 前缀且不更新 latest")
    p_lh.add_argument("--marker", default="", help="追加 -m 标记过滤（如 'not slow'）")
    p_lh.add_argument("--jobs", type=int, default=4, help="xdist worker 数（0.82 hw.ncpu=8）")
    p_lh.add_argument("--timeout-case", type=int, default=120, help="单用例超时秒（FreeBSD 更慢）")
    p_lh.add_argument("--timeout-sec", type=int, default=5400, help="整轮硬超时秒")
    p_lh.add_argument("--poll", type=int, default=60, help="仅 --bg 模式生效：轮询间隔秒")
    p_lh.add_argument("--bg", action="store_true",
                      help="后台+轮询（默认前台；后台模式的 R128_EXIT 标记行偶发丢失）")
    p_lh.add_argument("--round", default="R128-B")
    p_lh.add_argument("--out-prefix", default="")
    p_lh.set_defaults(fn=cmd_test_lh)

    p_d = sub.add_parser("diff", help="与基线对比（判据 = 新增红为空）")
    p_d.add_argument("--prefix", default="R128_LH_0.82基线_",
                     help="基线文件名前缀（默认全量基线；冒烟用 R128_LH_0.82冒烟_）")
    p_d.add_argument("--base", default="", help="显式指定基线 JSON（默认倒数第二份）")
    p_d.add_argument("--new", default="", help="本轮基线（默认最新一份）")
    p_d.set_defaults(fn=cmd_diff)

    p_c = sub.add_parser("cleanup", help="清理 0.82 /tmp 上的陈旧同步树")
    p_c.add_argument("--yes", action="store_true", help="真删（不加只列清单）")
    p_c.add_argument("--keep-latest", action="store_true",
                     help="保留当前指针指向的副本（默认全删）")
    p_c.set_defaults(fn=cmd_cleanup)

    p_lm = sub.add_parser("test-lm", help="0.82 上跑 light-merge 全量 pytest")
    p_lm.add_argument("--jobs", type=int, default=4)
    p_lm.add_argument("--timeout-case", type=int, default=120)
    p_lm.add_argument("--timeout-sec", type=int, default=5400)
    p_lm.add_argument("--poll", type=int, default=60)
    p_lm.add_argument("--round", default="R128-B")
    p_lm.set_defaults(fn=cmd_test_lm)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
