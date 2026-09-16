# -*- coding: utf-8 -*-
"""第44轮 任务1 —— 0.82 全量重同步（打包 → SFTP 上传 → 解压 → 校验）

背景：R43 的 /tmp/r43-* 是当时快照；本轮按任务书要求做**全量重同步**（非增量），
      拿到干净副本供任务2 做跨平台完整 pytest 对比。

设计要点（踩坑固化）：
  * 不用 Git-Bash tar（GNU 1.35 把 `C:\\` 当远程主机，exit 128）→ 改用 Python `tarfile`。
  * 不用 `--force-local`（FreeBSD bsdtar 不认）。
  * 0.82 无 `python`/`python3` 命令（`test_回归.py` 子进程硬编码 `['python', 运行器, …]`）
    → 远端建 /tmp/r44-shim/python{,3} 垫片，经 PATH 注入。**R43 首轮 402 failed 即垫片初版
    参数被置空所致**，本轮用 `exec ... "$@"` 正确转发参数。
  * 运行需同时有 lightharness 与 light-merge（`LIGHT_MERGE` 指向后者）→ 两个都打包。
  * 凭据只从工作区 `.env` 读（SSH_USER_AI / SSH_PASS_AI），值不入档、不落日志。

用法：
    python scripts/同步0.82.py sync        # 打包+上传+解压+建垫片+校验 examples 数量
    python scripts/同步0.82.py verify      # 只校验远端副本
    python scripts/同步0.82.py run -- CMD  # 远端执行（自动注入 LIGHT_MERGE/PATH 垫片）
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import tarfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # G:/dswork/duan-light-merge
LIGHTHARNESS = ROOT / "lightharness"
LIGHT_MERGE = ROOT / "light-merge"

HOST = "192.168.0.82"                                # 0.82（.env 的 SSH_HOST 是门禁机 .88，不可复用）
PORT = 22
REMOTE_BASE = "/tmp"
SHIM_DIR = "/tmp/r44-shim"
PY = "/usr/local/bin/python3.11"

EXCLUDE_DIRS = {
    ".git", "__pycache__", ".venv", "venv", ".pytest_cache", ".mypy_cache",
    "node_modules", "build", "dist", ".idea", ".vscode",
}
EXCLUDE_SUFFIX = {".pyc", ".pyo", ".pyd", ".so", ".dylib"}

# --with-git 时把 .git 一并带上：远端副本就成了真正的 git 工作树，
# `tests/test_R21_词法确定性_超集.py` 里 `git archive HEAD` 才不会退化成 skip
# （第45轮：0.82 已装 git 2.54.0，但 /tmp 副本此前没有 .git，2 条用例只能跳过）。
INCLUDE_GIT = False


# ---------------------------------------------------------------- 凭据
def load_env() -> tuple[str, str]:
    env_path = ROOT / ".env"
    if not env_path.exists():
        raise SystemExit(f"[同步0.82] 缺少 .env：{env_path}")
    data: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip().strip('"').strip("'")
    user = data.get("SSH_USER_AI", "")
    pwd = data.get("SSH_PASS_AI", "")
    if not user or not pwd:
        raise SystemExit("[同步0.82] .env 缺 SSH_USER_AI / SSH_PASS_AI")
    return user, pwd


# ---------------------------------------------------------------- 打包
def _should_skip(path: Path) -> bool:
    for part in path.parts:
        if part == ".git":
            if INCLUDE_GIT:
                continue          # --with-git：保留 .git，其余排除照旧
            return True
        if part in EXCLUDE_DIRS:
            return True
    if path.suffix in EXCLUDE_SUFFIX:
        return True
    return False


def build_tarball(out_path: Path) -> int:
    """把 lightharness/ 与 light-merge/ 打成一个 tar.gz（顶层即这两个目录名）。"""
    n = 0
    with tarfile.open(out_path, "w:gz", compresslevel=1) as tf:  # 1=最快，体积换时间
        for base in (LIGHTHARNESS, LIGHT_MERGE):
            if not base.exists():
                print(f"[同步0.82] 警告：缺失 {base}，跳过")
                continue
            arc_root = base.name
            for p in base.rglob("*"):
                rel = p.relative_to(base)
                if _should_skip(rel):
                    continue
                if p.is_dir():
                    continue
                try:
                    tf.add(p, arcname=str(Path(arc_root) / rel).replace("\\", "/"))
                    n += 1
                except (OSError, PermissionError) as e:
                    print(f"[同步0.82] 跳过（无法读取）：{p} -> {e}")
    return n


# ---------------------------------------------------------------- SSH
def connect():
    import paramiko

    user, pwd = load_env()
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(HOST, port=PORT, username=user, password=pwd, timeout=30,
                allow_agent=False, look_for_keys=False)
    return cli


def run_remote(cli, cmd: str, timeout: int = 3000, quiet: bool = False):
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
            # 排空残余
            while chan.recv_ready():
                chunk = chan.recv(65536).decode("utf-8", "replace")
                buf.write(chunk)
                if not quiet:
                    sys.stdout.write(chunk)
                    sys.stdout.flush()
            break
        if time.time() - t0 > timeout:
            chan.close()
            raise TimeoutError(f"[同步0.82] 远端命令超时 {timeout}s：{cmd[:120]}")
        time.sleep(0.2)
    rc = chan.recv_exit_status()
    chan.close()
    return rc, buf.getvalue()


def ensure_shim(cli) -> None:
    """建 python/python3 垫片（R43 教训：必须 exec ... "$@" 转发参数）。"""
    rc, _ = run_remote(cli, f'mkdir -p {SHIM_DIR} && '
                            f'printf "#!/bin/sh\\nexec {PY} \\"\\$@\\"\\n" > {SHIM_DIR}/python && '
                            f'cp {SHIM_DIR}/python {SHIM_DIR}/python3 && '
                            f'chmod +x {SHIM_DIR}/python {SHIM_DIR}/python3 && '
                            f'{SHIM_DIR}/python -V', quiet=True)
    if rc != 0:
        raise SystemExit("[同步0.82] 垫片创建/自检失败")
    print(f"[同步0.82] 垫片就绪 {SHIM_DIR}/python -> {PY}")


# ---------------------------------------------------------------- 子命令
def cmd_sync(args) -> int:
    global INCLUDE_GIT
    INCLUDE_GIT = getattr(args, "with_git", False)
    ts = time.strftime("%Y%m%d-%H%M%S")
    remote_dir = f"{REMOTE_BASE}/r44-{ts}"
    tar_path = ROOT / "_r44_sync.tar.gz"

    print(f"[同步0.82] 打包中（排除 {sorted(EXCLUDE_DIRS)}"
          f"{'，但包含 .git' if INCLUDE_GIT else ''}）…")
    t0 = time.time()
    n = build_tarball(tar_path)
    size_mb = tar_path.stat().st_size / 1024 / 1024
    print(f"[同步0.82] 打包完成：{n} 文件，{size_mb:.1f} MB，耗时 {time.time()-t0:.1f}s")

    cli = connect()
    try:
        ensure_shim(cli)
        sftp = cli.open_sftp()
        try:
            sftp.mkdir(remote_dir)
        except OSError:
            pass
        remote_tar = f"{remote_dir}/sync.tar.gz"
        print(f"[同步0.82] 上传 → {remote_tar}")
        t1 = time.time()
        sftp.put(str(tar_path), remote_tar)
        print(f"[同步0.82] 上传完成，耗时 {time.time()-t1:.1f}s")
        sftp.close()

        print("[同步0.82] 远端解压…")
        rc, out = run_remote(cli, f"cd {remote_dir} && tar -xzf sync.tar.gz && rm -f sync.tar.gz && "
                                  f"ls -d {remote_dir}/lightharness {remote_dir}/light-merge")
        if rc != 0:
            raise SystemExit(f"[同步0.82] 解压失败 rc={rc}")
        print(out.strip())

        # --with-git：把副本标为 git 安全目录，并确认 HEAD 可用
        # （否则 `git archive HEAD` 会因 dubious ownership 失败 → 用例退化成 skip）
        if INCLUDE_GIT:
            run_remote(cli, f"git config --global --add safe.directory {remote_dir}/lightharness",
                       quiet=True)
            rc, out = run_remote(cli, f"git -C {remote_dir}/lightharness rev-parse --short HEAD",
                                 quiet=True)
            print(f"[同步0.82] 远端 git HEAD = {out.strip() or '(不可用)'}")

        cnt = verify_examples(cli, remote_dir)
        print(f"[同步0.82] 远端 examples 数量 = {cnt}")

        # 落一个指针文件，供后续任务复用同一副本（写到 reports/ 稳定位置，
        # 避免像 R44 首轮那样写在仓库根的临时文件里被移档后导致 run/verify 失效）
        ptr = ROOT / "lightharness" / "reports" / "同步0.82_远程目录.txt"
        ptr.parent.mkdir(parents=True, exist_ok=True)
        ptr.write_text(remote_dir, encoding="utf-8")
        print(f"[同步0.82] ✅ 完成：远程副本 {remote_dir}（指针 {ptr.relative_to(ROOT)}）")
        return 0
    finally:
        cli.close()
        try:
            tar_path.unlink()
        except OSError:
            pass


def verify_examples(cli, remote_dir: str) -> int:
    rc, out = run_remote(cli, f"ls {remote_dir}/lightharness/examples/*.light | wc -l", quiet=True)
    return int(out.strip().split()[-1]) if rc == 0 else -1


def local_examples_count() -> int:
    """本机 examples/*.light 数量（远端校验的期望值，动态取以免新增用例后误判）。"""
    d = ROOT / "lightharness" / "examples"
    try:
        return len([f for f in os.listdir(d) if f.endswith(".light")])
    except OSError:
        return 402


def cmd_verify(args) -> int:
    cli = connect()
    try:
        rd = load_remote_dir()
        cnt = verify_examples(cli, rd)
        want = local_examples_count()
        print(f"[同步0.82] 副本 {rd} examples = {cnt}（本机 {want}）")
        rc, out = run_remote(cli, f"cd {rd}/lightharness && uname -a && {PY} -V", quiet=True)
        print(out.strip())
        return 0 if cnt == want else 1
    finally:
        cli.close()


def cmd_run(args) -> int:
    cli = connect()
    try:
        rd = load_remote_dir()
        cmd = " ".join(args.cmd)
        full = (f'cd {rd}/lightharness && export LIGHT_MERGE={rd}/light-merge && '
                f'export PATH={SHIM_DIR}:$PATH && {cmd}')
        print(f"[同步0.82] 远端执行：{full}")
        rc, _ = run_remote(cli, full, timeout=args.timeout)
        print(f"[同步0.82] rc={rc}")
        return rc
    finally:
        cli.close()


def load_remote_dir() -> str:
    """取最近一次 sync 的远程副本路径。

    查找顺序（便于历史副本被清理/记录文件被移档时仍可用）：
      1) 环境变量 R44_REMOTE_DIR（临时覆盖用）
      2) reports/同步0.82_远程目录.txt（sync 写入的稳定位置）
      3) 旧位置 lightharness/_r44_remote_dir.txt（R44 首轮遗留，可能已被移档）
    """
    env = os.environ.get("R44_REMOTE_DIR", "").strip()
    if env:
        return env
    for rel in ("lightharness/reports/同步0.82_远程目录.txt",
                "lightharness/_r44_remote_dir.txt"):
        p = ROOT / rel
        if p.exists():
            v = p.read_text(encoding="utf-8").strip()
            if v:
                return v
    raise SystemExit("[同步0.82] 未知远程副本路径，请先执行 sync（或用 R44_REMOTE_DIR 环境变量指定）")


def main() -> int:
    ap = argparse.ArgumentParser(description="0.82 全量重同步与远程执行")
    sub = ap.add_subparsers(dest="sub", required=True)

    sub.add_parser("verify", help="校验远端副本").set_defaults(fn=cmd_verify)
    p_sync = sub.add_parser("sync", help="打包+上传+解压+校验")
    p_sync.add_argument("--with-git", action="store_true",
                        help="连 .git 一起同步（远端副本成为真正的 git 工作树，"
                             "使依赖 `git archive HEAD` 的用例真正跑起来而不是跳过）")
    p_sync.set_defaults(fn=cmd_sync)
    p_run = sub.add_parser("run", help="远端执行命令")
    p_run.add_argument("cmd", nargs=argparse.REMAINDER)
    p_run.add_argument("--timeout", type=int, default=3000)
    p_run.set_defaults(fn=cmd_run)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
