#!/usr/bin/env python3
"""一次性收尾：删除临时脚本、提交 MCP 接入材料、推送三个远端。"""
import subprocess
from pathlib import Path

ROOT = Path("/home/skywalk/dswork/lightharness").resolve()
SCRIPTS = ROOT / "scripts"
TEMPS = [
    SCRIPTS / "_lh_enroll.py",
    SCRIPTS / "_lh_push_agent.py",
    SCRIPTS / "_lh_push_agent2.py",
    SCRIPTS / "_lh_enroll.sh",
    Path(__file__).resolve(),  # 本脚本完成后自删
]


def run(*args, check=True):
    print(f"$ {' '.join(args)}")
    p = subprocess.run(args, cwd=str(ROOT), capture_output=True, text=True)
    if p.stdout:
        print(p.stdout.rstrip())
    if p.stderr:
        print(p.stderr.rstrip())
    if check and p.returncode != 0:
        raise SystemExit(f"exit={p.returncode}")
    return p


def verified_target(p: Path) -> Path:
    resolved = p.resolve(strict=False)
    print(f"delete-target: {resolved}")
    if resolved.parent != SCRIPTS:
        raise SystemExit(f"拒绝删除：不在 scripts 目录: {resolved}")
    if not (resolved.name.startswith("_lh_") or resolved.name.startswith("_finish_lh_")):
        raise SystemExit(f"拒绝删除：文件名不匹配: {resolved}")
    return resolved


# 先验证所有删除目标，再删
targets = [verified_target(p) for p in TEMPS]
for p in targets:
    if p.exists():
        p.unlink()
        print(f"removed {p}")
    else:
        print(f"skip missing {p}")

print("=== status before ===")
run("git", "status", "--short", "--untracked-files=all")

add_files = [
    ".gitignore",
    "mcp.example.json",
    "docs/里程碑-2026-11-18-MCP接入成功.md",
    "docs/公告-2026-11-18-MCP生态接入.md",
    "examples/_probe_hive_mcp.light",
]
run("git", "add", "--", *add_files)
print("=== staged ===")
run("git", "diff", "--cached", "--stat")
print("=== staged names ===")
run("git", "diff", "--cached", "--name-status")

msg = "docs: lightharness MCP 实战接入 hive（里程碑与配置模板）"
c = run("git", "commit", "-m", msg, check=False)
if "nothing to commit" in (c.stdout + c.stderr):
    print("nothing to commit")
elif c.returncode != 0:
    raise SystemExit(f"commit failed exit={c.returncode}")

print("=== status after commit ===")
run("git", "status", "--short", "--untracked-files=all")

for remote in ("origin", "gitcode", "github"):
    print(f"=== fetch {remote} ===")
    run("git", "fetch", remote, check=False)
    run("git", "log", "--oneline", "--left-right", f"HEAD...{remote}/main", check=False)

for remote in ("origin", "gitcode", "github"):
    print(f"=== push {remote} ===")
    p = run("git", "push", remote, "HEAD:main", check=False)
    if p.returncode != 0:
        print(f"PUSH_FAILED remote={remote} exit={p.returncode}")
