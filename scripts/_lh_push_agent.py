#!/usr/bin/env python3
"""把 lightharness-fb98 的 agent 登记提交并推到 origin/main。

hive 的 agent 配置是 git 文件（agents/<name>.json）。
MCP 读走 clone，必须 commit+push 才能让 hived 看到。
不 force、不 rebase、不动别人；只是把新增文件提交。
"""
import pathlib
import subprocess

HIVE = "/home/skywalk/dswork/hive"
TARGET = "agents/lightharness-fb98.json"


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    p = subprocess.run(["git", "-C", HIVE, *args], capture_output=True, text=True)
    if check and p.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} 失败:\n{p.stdout}\n{p.stderr}")
    return p


print("=== pre status ===")
print(run("status", "--short").stdout)
print("=== branch ===")
print(run("branch", "--show-current").stdout)
print("=== log -3 ===")
print(run("log", "--oneline", "-3").stdout)
print("=== remote ===")
print(run("remote", "-v").stdout)

print("=== add ===")
print(run("add", TARGET).stdout)

print("=== diff --cached ===")
print(run("diff", "--cached", "--stat").stdout)

print("=== commit ===")
c = run("commit", "-m",
        f"agent: 登记 {TARGET}（lightharness MCP 接入）",
        check=False)
print(c.stdout)
print(c.stderr)

print("=== post status ===")
print(run("status", "--short").stdout)

print("=== push (dry-run) ===")
d = run("push", "--dry-run", "origin", "HEAD:main", check=False)
print(d.stdout)
print(d.stderr)
