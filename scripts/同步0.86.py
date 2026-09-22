# -*- coding: utf-8 -*-
"""R85 任务F（批1 基建）—— 0.86（Linux）同步 / 环境探测 / 远程执行 / 门禁跑通。

设计（仿 lightharness/scripts/同步0.82.py，面向 Linux 0.86 做向后兼容泛化）：
  * --host 参数化：默认 192.168.0.86；传 --host 1.2.3.4 可复用同一脚本测别的机器，
    不破坏「不传即 0.86」的既有约定（本脚本只服务 0.86，但机器常量可覆盖）。
  * 多账号依次探活：AI → TRAE → WORKBUDDY → DUMATE（密码键同名前缀 SSH_PASS_*，
    DUMATE 额外试 SSH_PASS_DUMATE2），首个能连通的账号即采用；凭据只从工作区 .env 读，
    值不入档、不落日志、不上传。
  * 打包用 `git ls-files` 取 tracked 树（干净、不含 .venv/垃圾/未跟踪 scratch）。
    --with-git 时额外把 .git 一并带上（远端副本成为真正的 git 工作树）。
  * 远端**不碰系统 Python**：在 /tmp 建用户级 venv 装 pytest + xdist + pytest-timeout
    + psutil，所有 pytest 用该 venv 跑；PATH 注入 venv/bin（同时解决 Linux 上
    可能没有 `python` 命令、只有 `python3` 的问题）。
  * 新增 probe：探测 OS 发行版 / Python 版本 / sudo 可用性 / git 版本 / CPU 核数 /
    内存 → reports/R85_linux_环境探测.json。
  * 新增 test-lm / test-lh：在 0.86 上跑 light-merge / lightharness 全量 pytest，
    拉回 junitxml → 基线 JSON（复用 scripts/回归基线.py 口径）。远端命令一律后台跑+
    轮询（全量可能 10~20 分钟），不阻塞本机。

用法：
    python scripts/同步0.86.py probe
    python scripts/同步0.86.py sync [--with-git]
    python scripts/同步0.86.py verify
    python scripts/同步0.86.py run -- CMD
    python scripts/同步0.86.py test-lm [--mode fast|full] [--timeout-sec N]
    python scripts/同步0.86.py test-lh [--timeout-sec N]
    python scripts/同步0.86.py --host 1.2.3.4 probe
"""
from __future__ import annotations

import argparse
import io
import os
import subprocess
import sys
import tarfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]            # G:/dswork/duan-light-merge
LIGHTHARNESS = ROOT / "lightharness"
LIGHT_MERGE = ROOT / "light-merge"

DEFAULT_HOST = "192.168.0.86"
PORT = 22
REMOTE_BASE = "/tmp"
VENV_DIR = "/tmp/r85-venv"                            # 0.86 用户级 venv（不碰系统 python）
SHIM_DIR = "/tmp/r85-shim"                             # 备用垫片（python/python3 → venv）
REMOTE_DIR_PREFIX = "r85-"
REMOTE_PY = f"{VENV_DIR}/bin/python"                  # 0.86 上跑 pytest / 运行器用的 python


def remote_prefix(remote_dir: str) -> str:
    """远端执行前缀：切到 lightharness、注入 LIGHT_MERGE / venv PATH / 编码。"""
    return (f"cd {remote_dir}/lightharness && export LIGHT_MERGE={remote_dir}/light-merge && "
            f"export PATH={VENV_DIR}/bin:{SHIM_DIR}:$PATH && "
            f"export PYTHONIOENCODING=utf-8 && ")


def ensure_ready(cli) -> str:
    """确保 0.86 远端 venv 就绪（建 venv + 装 pytest 全家桶），返回 venv python 路径。"""
    return ensure_venv(cli)

# ── tracked 树打包排除（沿用 0.82 口径：这些产物 0.86 跑测试用不到，且体积大）──
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
        raise SystemExit(f"[同步0.86] 缺少 .env：{env_path}")
    data: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip().lstrip("@").strip()             # 容忍 @SSH_PASS_DUMATE 这种笔误行
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


# ---------------------------------------------------------------- SSH
def connect(host: str, port: int = PORT, timeout: int = 30):
    """多账号依次探活，返回 (cli, 账号名, 用户名, 密码)。"""
    import paramiko
    accts, _sudo = load_accounts()
    if not accts:
        raise SystemExit("[同步0.86] .env 无可用的 SSH 账号（SSH_USER_*/SSH_PASS_*）")
    last_err = None
    for acct, user, pwd in accts:
        try:
            cli = paramiko.SSHClient()
            cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            cli.connect(host, port=port, username=user, password=pwd, timeout=timeout,
                        allow_agent=False, look_for_keys=False)
            try:
                cli.get_transport().set_keepalive(30)
            except Exception:
                pass
            print(f"[同步0.86] ✅ 账号 {acct}({user})@{host} 连通")
            return cli, acct, user, pwd
        except Exception as e:                 # 密码错 / 账号锁 / 网络不可达
            last_err = e
            print(f"[同步0.86] ⚠️ 账号 {acct}({user})@{host} 失败：{type(e).__name__}: {e}")
    raise SystemExit(f"[同步0.86] 所有账号均无法连通 {host}（末错：{last_err}）")


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
            raise TimeoutError(f"[同步0.86] 远端命令超时 {timeout}s：{cmd[:120]}")
        time.sleep(0.2)
    rc = chan.recv_exit_status()
    chan.close()
    return rc, buf.getvalue()


def _q(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


# ---------------------------------------------------------------- 后台执行（长任务不阻塞本机）
def run_remote_bg(cli, cmd: str, logfile: str, timeout: int = 60):
    """后台启动命令（nohup … &），输出重定向到 logfile，返回 pid。"""
    wrapper = f"nohup sh -c {_q(cmd)} > {logfile} 2>&1 & echo $!"
    rc, out = run_remote(cli, wrapper, timeout=timeout, quiet=True)
    if rc != 0:
        raise SystemExit(f"[同步0.86] 后台启动失败 rc={rc}：{out}")
    pid = out.strip().split()[-1]
    return pid


def poll_remote(cli, logfile: str, pid: str, interval: int = 30, max_wait: int = 3600):
    """轮询后台任务：每 interval 秒查一次，最多 max_wait 秒。返回 (rc, 全部尾部日志)。"""
    deadline = time.time() + max_wait
    last = ""
    while time.time() < deadline:
        rc, out = run_remote(
            cli,
            f"if kill -0 {pid} 2>/dev/null; then echo __RUNNING__; else echo __DONE__; fi; "
            f"echo __TAIL__; tail -n 30 {logfile}",
            timeout=60, quiet=True)
        last = out
        if "__DONE__" in out:
            # 取退出码
            _, code = run_remote(
                cli, f"grep -m1 'R85_EXIT=' {logfile} 2>/dev/null || echo R85_EXIT=unknown",
                timeout=60, quiet=True)
            m = [l for l in code.splitlines() if l.startswith("R85_EXIT=")]
            exit_code = m[0].split("=", 1)[1].strip() if m else "unknown"
            return exit_code, out
        time.sleep(interval)
    return "TIMEOUT", last


# ---------------------------------------------------------------- 打包（git tracked 树）
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
        for base in (LIGHTHARNESS, LIGHT_MERGE):
            if not base.exists():
                print(f"[同步0.86] 警告：缺失 {base}，跳过")
                continue
            arc_root = base.name
            # tracked 文件（干净，不含 .venv / 未跟踪 scratch）
            res = subprocess.run(["git", "-C", str(base), "ls-files"],
                                  capture_output=True, text=True, encoding="utf-8")
            tracked = [l for l in res.stdout.splitlines() if l]
            for rel in tracked:
                rp = Path(rel)
                if _should_skip(rp):
                    continue
                p = base / rel
                if not p.exists():
                    continue
                tf.add(p, arcname=f"{arc_root}/{rel}".replace("\\", "/"))
                n += 1
            # --with-git：把 .git 一并带上（远端成为真正 git 工作树）
            if INCLUDE_GIT:
                git_dir = base / ".git"
                if git_dir.is_dir():
                    tf.add(git_dir, arcname=f"{arc_root}/.git".replace("\\", "/"))
                    n += 1
                    print(f"[同步0.86] 含 .git：{git_dir}")
    return n


# ---------------------------------------------------------------- venv + shim
def ensure_venv(cli) -> str:
    """在 0.86 建 /tmp 用户级 venv（含 pytest + xdist + timeout + psutil）。
    返回 venv python 绝对路径。"""
    # 1) 探测系统 python3
    rc, out = run_remote(cli, "command -v python3 || command -v python", quiet=True)
    py3 = (out.strip().splitlines() or [""])[0].strip() or "/usr/bin/python3"
    print(f"[同步0.86] 远端 python3 = {py3}")

    # 2) 建 venv（失败则尝试 sudo 装 python3-venv，再失败退回 virtualenv）
    rc, out = run_remote(cli, f"test -x {VENV_DIR}/bin/python && echo OK || echo NEED",
                         quiet=True)
    if "OK" not in out:
        rc, out = run_remote(cli, f"{py3} -m venv {VENV_DIR} && echo VENV_OK", quiet=True)
        if rc != 0 or "VENV_OK" not in out:
            print(f"[同步0.86] venv 创建失败，尝试 sudo 装 python3-venv：{out.strip()[:200]}")
            accts, sudo = load_accounts()
            _sudo = sudo or (accts[0][2] if accts else "")
            run_remote(cli,
                       f"echo {_q(_sudo)} | sudo -S apt-get install -y python3-venv "
                       f">/dev/null 2>&1; {py3} -m venv {VENV_DIR}",
                       timeout=300, quiet=True)
            rc, out = run_remote(cli, f"test -x {VENV_DIR}/bin/python && echo OK || echo NO",
                                 quiet=True)
            if "OK" not in out:
                raise SystemExit("[同步0.86] 无法在 0.86 创建 venv（请检查 python3-venv 或 virtualenv）")

    # 3) 装依赖
    pip = f"{VENV_DIR}/bin/pip"
    run_remote(cli, f"{pip} install -q --upgrade pip", timeout=300, quiet=True)
    pkgs = "pytest pytest-xdist pytest-timeout psutil"
    rc, out = run_remote(cli, f"{pip} install -q {pkgs}", timeout=600, quiet=True)
    if rc != 0:
        print(f"[同步0.86] ⚠️ venv 依赖安装返回 rc={rc}：{out.strip()[:300]}")
    # 4) 建备用 shim（python/python3 → venv python），防止子进程裸调 `python` 找不到
    vpy = f"{VENV_DIR}/bin/python"
    run_remote(cli,
               f"mkdir -p {SHIM_DIR} && "
               f'printf "#!/bin/sh\\nexec {vpy} \\"\\$@\\"\\n" > {SHIM_DIR}/python && '
               f"cp {SHIM_DIR}/python {SHIM_DIR}/python3 && "
               f"chmod +x {SHIM_DIR}/python {SHIM_DIR}/python3", quiet=True)
    print(f"[同步0.86] venv 就绪：{vpy}")
    return vpy


# ---------------------------------------------------------------- 子命令
def cmd_probe(args) -> int:
    cli, acct, user, pwd = connect(args.host, args.port)
    try:
        info: dict = {"host": args.host, "port": args.port, "account_used": acct,
                      "username": user, "probed_at": time.strftime("%Y-%m-%d %H:%M:%S")}
        probes = {
            "uname": "uname -a",
            "os_release": "cat /etc/os-release 2>/dev/null | head -8 || true",
            "kernel": "uname -r",
            "python3_version": "python3 -V 2>&1 || echo NONE",
            "python_version": "python -V 2>&1 || echo NONE",
            "git_version": "git --version 2>&1 || echo NONE",
            "cpu_cores": "nproc 2>/dev/null || grep -c ^processor /proc/cpuinfo",
            "mem_total_mb": "free -m 2>/dev/null | awk '/Mem:/{print $2}' || echo NONE",
            "arch": "uname -m",
        }
        for key, cmd in probes.items():
            rc, out = run_remote(cli, cmd, timeout=60, quiet=True)
            info[key] = out.strip()
        # sudo 可用性（用 sudo 密码试 sudo -S true）
        accts, sudo = load_accounts()
        _sudo = sudo or pwd
        rc, out = run_remote(cli, f"echo {_q(_sudo)} | sudo -S true >/dev/null 2>&1 && echo SUDO_OK || echo SUDO_NO",
                             timeout=60, quiet=True)
        info["sudo_available"] = bool("SUDO_OK" in out)
        info["sudo_note"] = out.strip()
        # 编译器/解释器探测（0.86 上能否 import xdist/timeout，门禁用）
        rc_x, out_x = run_remote(cli, "python3 -c 'import xdist, pytest_timeout; print(\"PLUGINS_OK\")' 2>&1 || echo NONE",
                                 timeout=60, quiet=True)
        info["pytest_plugins_system"] = out_x.strip()
        print("[同步0.86] 环境探测完成：")
        for k, v in info.items():
            print(f"   {k}: {v}")
        # 落地 JSON（二进制写，避免 CRLF 隐患）
        out_path = LIGHTHARNESS / "reports" / "R85_linux_环境探测.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(json_dumps(info).encode("utf-8"))
        print(f"[同步0.86] ✅ 环境探测写入 {out_path.relative_to(ROOT)}")
        return 0
    finally:
        cli.close()


def cmd_sync(args) -> int:
    global INCLUDE_GIT
    INCLUDE_GIT = getattr(args, "with_git", False)
    ts = time.strftime("%Y%m%d-%H%M%S")
    remote_dir = f"{REMOTE_BASE}/{REMOTE_DIR_PREFIX}{ts}"
    tar_path = ROOT / "_r85_sync.tar.gz"

    print(f"[同步0.86] 打包（git tracked 树；路径排除 "
          f"{['/'.join(p) for p in EXCLUDE_REL_PREFIXES]}"
          f"{'；含 .git' if INCLUDE_GIT else ''}）…")
    t0 = time.time()
    n = build_tarball(tar_path)
    size_mb = tar_path.stat().st_size / 1024 / 1024
    print(f"[同步0.86] 打包完成：{n} 文件，{size_mb:.1f} MB，耗时 {time.time()-t0:.1f}s")

    cli, *_ = connect(args.host, args.port)
    try:
        sftp = cli.open_sftp()
        try:
            sftp.mkdir(remote_dir)
        except OSError:
            pass
        remote_tar = f"{remote_dir}/sync.tar.gz"
        print(f"[同步0.86] 上传 → {remote_tar}")
        t1 = time.time()
        sftp.put(str(tar_path), remote_tar)
        print(f"[同步0.86] 上传完成，耗时 {time.time()-t1:.1f}s")
        sftp.close()

        print("[同步0.86] 远端解压…")
        rc, out = run_remote(cli,
                             f"cd {remote_dir} && tar -xzf sync.tar.gz && rm -f sync.tar.gz && "
                             f"ls -d {remote_dir}/lightharness {remote_dir}/light-merge")
        if rc != 0:
            raise SystemExit(f"[同步0.86] 解压失败 rc={rc}")
        print(out.strip())

        if INCLUDE_GIT:
            for sub in ("lightharness", "light-merge"):
                run_remote(cli, f"git config --global --add safe.directory {remote_dir}/{sub}",
                           quiet=True)
                rc, out = run_remote(cli, f"git -C {remote_dir}/{sub} rev-parse --short HEAD",
                                     quiet=True)
                print(f"[同步0.86] {sub} git HEAD = {out.strip() or '(不可用)'}")

        ensure_venv(cli)

        # 落指针文件（reports 稳定位置）
        ptr = LIGHTHARNESS / "reports" / "同步0.86_远程目录.txt"
        ptr.parent.mkdir(parents=True, exist_ok=True)
        ptr.write_bytes(remote_dir.encode("utf-8"))
        print(f"[同步0.86] ✅ 完成：远程副本 {remote_dir}（指针 {ptr.relative_to(ROOT)}）")
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
        rc, out = run_remote(cli,
                             f"ls -d {rd}/lightharness {rd}/light-merge && "
                             f"ls {rd}/lightharness/examples/*.light | wc -l", quiet=True)
        print(out.strip())
        return 0 if rc == 0 else 1
    finally:
        cli.close()


def cmd_run(args) -> int:
    cli, *_ = connect(args.host, args.port)
    try:
        rd = load_remote_dir()
        # argparse REMAINDER 会把用户显式的 `--` 也收进列表，去掉头部的 `--`
        cmd_parts = list(args.cmd)
        if cmd_parts and cmd_parts[0] == "--":
            cmd_parts = cmd_parts[1:]
        cmd = " ".join(cmd_parts)
        full = (f'cd {rd}/lightharness && export LIGHT_MERGE={rd}/light-merge && '
                f'export PATH={VENV_DIR}/bin:{SHIM_DIR}:$PATH && '
                f'export PYTHONIOENCODING=utf-8 && {cmd}')
        print(f"[同步0.86] 远端执行：{full}")
        rc, _ = run_remote(cli, full, timeout=args.timeout)
        print(f"[同步0.86] rc={rc}")
        return rc
    finally:
        cli.close()


def _load_base_lib():
    import importlib.util
    spec = importlib.util.spec_from_file_location("回归基线", LIGHTHARNESS / "scripts" / "回归基线.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cmd_test_lm(args) -> int:
    """0.86 上跑 light-merge 全量 pytest（venv 带 xdist/timeout，保留 addopts）。"""
    cli, *_ = connect(args.host, args.port)
    try:
        ensure_venv(cli)
        rd = load_remote_dir()
        vpy = f"{VENV_DIR}/bin/python"
        xml_remote = f"{rd}/lm_results_{args.mode}.xml"
        argv = ["-m", "pytest", "tests/", "-q", "--tb=no", "-rfE",
                "-p", "no:cacheprovider", "--junitxml", xml_remote]
        if args.mode == "fast":
            argv += ["-m", "not slow"]
        # LM addopts 自带 -n auto --timeout=60；venv 已装插件 → 保留并行+超时
        argv += ["-n", "auto", "--dist", "loadscope"]
        logfile = f"{rd}/lm_test.log"
        cmd = (f"cd {rd}/light-merge && export PATH={VENV_DIR}/bin:$PATH && "
               f"export PYTHONIOENCODING=utf-8 && "
               f"{vpy} " + " ".join(_q(a) for a in argv) +
               f"; echo R85_EXIT=$? >> {logfile}")
        print(f"[同步0.86] 后台启动 LM 全量（mode={args.mode}，超时 {args.timeout_sec}s）…")
        pid = run_remote_bg(cli, cmd, logfile)
        print(f"[同步0.86] pid={pid}，轮询中…")
        code, tail = poll_remote(cli, logfile, pid, interval=args.poll, max_wait=args.timeout_sec + 600)
        print(f"[同步0.86] LM 退出={code}")
        for ln in tail.splitlines()[-20:]:
            print("   |", ln)
        # 拉回 junitxml
        local_xml = LIGHTHARNESS / "reports" / f"R85_lm_results_{_stamp()}.xml"
        sftp = cli.open_sftp()
        try:
            sftp.stat(xml_remote)
        except OSError:
            print("[同步0.86] ❌ 远端无 junitxml，LM 未跑到收尾")
            return 2
        sftp.get(xml_remote, str(local_xml))
        sftp.close()
        base = _load_base_lib()
        parsed = base.parse_junit(local_xml)
        baseline = base.make_baseline(
            parsed, name="light-merge", platform=f"0.86 Linux",
            host=args.host, remote_dir=rd, cwd=f"{rd}/light-merge",
            runner={"mode": args.mode, "parallel": True, "cmd": " ".join(argv),
                    "pytest_rc": code})
        path = LIGHTHARNESS / "reports" / f"R85_lm基线_{_stamp()}.json"
        base.save_baseline(baseline, path)
        base.save_baseline(baseline, LIGHTHARNESS / "reports" / "R85_lm基线_latest.json")
        t = baseline["totals"]
        print(f"[同步0.86] LM 摘要：共{t['total']} 通过{t['passed']} 失败{t['failed']} "
              f"跳过{t['skipped']} 错误{t['error']}")
        if baseline["failed"]:
            for f in baseline["failed"][:20]:
                print("   ✗", f["id"], "—", f["message"][:120])
        return 0
    finally:
        cli.close()


def cmd_test_lh(args) -> int:
    """0.86 上跑 lightharness 全量 pytest（venv 带 xdist/timeout）。"""
    cli, *_ = connect(args.host, args.port)
    try:
        ensure_venv(cli)
        rd = load_remote_dir()
        vpy = f"{VENV_DIR}/bin/python"
        xml_remote = f"{rd}/lh_results.xml"
        # LH pytest.ini addopts=--timeout=60 -n auto；venv 有插件 → 保留并行+超时，
        # 与 CI/Windows 同口径比对失败集合。
        argv = ["-m", "pytest", "tests/", "-q", "--tb=no", "-rfE",
                "-p", "no:cacheprovider", "--junitxml", xml_remote,
                "-n", "auto", "--dist", "loadscope", "--timeout", "60"]
        logfile = f"{rd}/lh_test.log"
        cmd = (f"cd {rd}/lightharness && export LIGHT_MERGE={rd}/light-merge && "
               f"export PATH={VENV_DIR}/bin:{SHIM_DIR}:$PATH && "
               f"export PYTHONIOENCODING=utf-8 && "
               f"{vpy} " + " ".join(_q(a) for a in argv) +
               f"; echo R85_EXIT=$? >> {logfile}")
        print(f"[同步0.86] 后台启动 LH 全量（超时 {args.timeout_sec}s）…")
        pid = run_remote_bg(cli, cmd, logfile)
        print(f"[同步0.86] pid={pid}，轮询中…")
        code, tail = poll_remote(cli, logfile, pid, interval=args.poll, max_wait=args.timeout_sec + 600)
        print(f"[同步0.86] LH 退出={code}")
        for ln in tail.splitlines()[-20:]:
            print("   |", ln)
        local_xml = LIGHTHARNESS / "reports" / f"R85_lh_results_{_stamp()}.xml"
        sftp = cli.open_sftp()
        try:
            sftp.stat(xml_remote)
        except OSError:
            print("[同步0.86] ❌ 远端无 junitxml，LH 未跑到收尾")
            return 2
        sftp.get(xml_remote, str(local_xml))
        sftp.close()
        base = _load_base_lib()
        parsed = base.parse_junit(local_xml)
        baseline = base.make_baseline(
            parsed, name="lightharness", platform=f"0.86 Linux",
            host=args.host, remote_dir=rd, cwd=f"{rd}/lightharness",
            runner={"mode": "full", "parallel": True, "cmd": " ".join(argv),
                    "pytest_rc": code})
        path = LIGHTHARNESS / "reports" / f"R85_lh基线_{_stamp()}.json"
        base.save_baseline(baseline, path)
        base.save_baseline(baseline, LIGHTHARNESS / "reports" / "R85_lh基线_latest.json")
        t = baseline["totals"]
        print(f"[同步0.86] LH 摘要：共{t['total']} 通过{t['passed']} 失败{t['failed']} "
              f"跳过{t['skipped']} 错误{t['error']}")
        if baseline["failed"]:
            for f in baseline["failed"][:20]:
                print("   ✗", f["id"], "—", f["message"][:120])
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
    env = os.environ.get("R85_REMOTE_DIR", "").strip()
    if env:
        return env
    p = LIGHTHARNESS / "reports" / "同步0.86_远程目录.txt"
    if p.exists():
        v = p.read_bytes().decode("utf-8", "replace").strip()
        if v:
            return v
    raise SystemExit("[同步0.86] 未知远程副本路径，请先执行 sync（或设 R85_REMOTE_DIR）")


# ---------------------------------------------------------------- CLI
def main() -> int:
    ap = argparse.ArgumentParser(description="R85 0.86(Linux) 同步/探测/远程执行/门禁")
    ap.add_argument("--host", default=DEFAULT_HOST, help=f"目标机（默认 {DEFAULT_HOST}）")
    ap.add_argument("--port", type=int, default=PORT)
    sub = ap.add_subparsers(dest="sub", required=True)

    sub.add_parser("probe", help="环境探测 → reports/R85_linux_环境探测.json").set_defaults(fn=cmd_probe)
    p_sync = sub.add_parser("sync", help="打包+上传+解压+建 venv")
    p_sync.add_argument("--with-git", action="store_true", help="连 .git 一起同步")
    p_sync.set_defaults(fn=cmd_sync)
    sub.add_parser("verify", help="校验远端副本").set_defaults(fn=cmd_verify)
    p_run = sub.add_parser("run", help="远端执行命令")
    p_run.add_argument("cmd", nargs=argparse.REMAINDER)
    p_run.add_argument("--timeout", type=int, default=3000)
    p_run.set_defaults(fn=cmd_run)

    p_lm = sub.add_parser("test-lm", help="0.86 上跑 light-merge 全量 pytest")
    p_lm.add_argument("--mode", choices=["fast", "full"], default="fast")
    p_lm.add_argument("--timeout-sec", type=int, default=2400)
    p_lm.add_argument("--poll", type=int, default=30)
    p_lm.set_defaults(fn=cmd_test_lm)

    p_lh = sub.add_parser("test-lh", help="0.86 上跑 lightharness 全量 pytest")
    p_lh.add_argument("--timeout-sec", type=int, default=2400)
    p_lh.add_argument("--poll", type=int, default=30)
    p_lh.set_defaults(fn=cmd_test_lh)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
