# -*- coding: utf-8 -*-
"""R57 收口复核：在 0.82 上独立验证 phase9(测试断言工具) 16 条的当前状态。
只做定向 pytest，不跑全量。"""
import io, os, sys, time
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parent
ENV = ROOT / ".env"
if not ENV.exists() or "SSH_USER_AI" not in ENV.read_text(encoding="utf-8", errors="replace"):
    ENV = ROOT.parent / ".env"  # SSH 凭据在项目根 .env

def load_env():
    data = {}
    for line in ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip().strip('"').strip("'")
    return data

def main():
    env = load_env()
    user = env.get("SSH_USER_AI", "")
    pwd = env.get("SSH_PASS_AI", "")
    if not user or not pwd:
        print("[失败] .env 缺 SSH_USER_AI / SSH_PASS_AI")
        return 2
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect("192.168.0.82", port=22, username=user, password=pwd, timeout=20)
    print(f"[已连] 192.168.0.82 ({user})")

    def run(cmd, timeout=300):
        print(f"$ {cmd}")
        stdin, stdout, stderr = cli.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", "replace")
        err = stderr.read().decode("utf-8", "replace")
        rc = stdout.channel.recv_exit_status()
        return rc, out, err

    # 1. 列出 /tmp 下相关副本，确认存在哪些
    rc, out, err = run("ls -d /tmp/r57-directed /tmp/r44-* 2>/dev/null")
    print(out.strip())
    print("----")

    # 2. 找最新的副本（含 light-merge 目录）
    rc, out, err = run("ls -dt /tmp/r57-directed /tmp/r44-* 2>/dev/null | head -5")
    copies = [l.strip() for l in out.splitlines() if l.strip()]
    print("[副本候选]", copies)
    if not copies:
        print("[失败] 无副本")
        return 2
    target = None
    for c in copies:
        rc2, out2, _ = run(f"test -d {c}/light-merge && echo yes || echo no")
        if out2.strip() == "yes":
            target = c
            break
    if not target:
        print("[失败] 未找到含 light-merge 的副本")
        return 2
    print(f"[选定副本] {target}")

    # 3. 确认副本 lexer 是否为修复版（md5 与本机工作树对比）
    local_md5 = None
    try:
        import hashlib
        local_md5 = hashlib.md5((ROOT.parent / "light-merge" / "src" / "lexer.py").read_bytes()).hexdigest()
    except Exception as e:
        print("[提示] 本机 lexer.md5 读取失败:", e)
    rc, out, _ = run(f"md5 -q {target}/light-merge/src/lexer.py 2>/dev/null || md5sum {target}/light-merge/src/lexer.py | cut -d' ' -f1")
    remote_md5 = out.strip().splitlines()[-1].strip() if out.strip() else "?"
    print(f"[lexer] 本机 {local_md5} | 0.82 {remote_md5} | {'一致' if local_md5 and local_md5 == remote_md5 else '不一致(副本旧版)'}")

    # 4. 定向跑 phase9（串行，置空 addopts 避免 -n auto 干扰；--timeout 显式补回）
    phase9_cmd = (
        f"cd {target}/light-merge && export PYTHONIOENCODING=utf-8 && "
        f"/usr/local/bin/python3.12 -m pytest tests/test_stdlib_phase9.py -q --tb=line "
        f"-p no:xdist -p no:cacheprovider -o addopts= --timeout=60 2>&1 | tail -25"
    )
    t0 = time.time()
    rc, out, err = run(phase9_cmd, timeout=600)
    print(f"[phase9 定向] rc={rc} 耗时 {time.time()-t0:.1f}s")
    print(out[-2500:])

    # 5. 若文件存在则顺带看收集规模
    rc, out, err = run(f"cd {target}/light-merge && /usr/local/bin/python3.12 -m pytest tests/test_stdlib_phase9.py --collect-only -q -p no:cacheprovider 2>&1 | tail -5")
    print("[collect-only]")
    print(out[-800:])
    cli.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())
