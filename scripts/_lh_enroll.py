#!/usr/bin/env python3
"""登记 lightharness-fb98 到 hive 协调仓并换发 MCP token。"""
import json
import pathlib
import subprocess
import sys

HIVE = pathlib.Path("/home/skywalk/dswork/hive")
AGENT = "lightharness-fb98"
TARGET = HIVE / "agents" / f"{AGENT}.json"

sys.path.insert(0, str(HIVE))
import mcp_auth

# 清掉误登记
mistake = HIVE / "agents" / "lightharness.json"
if mistake.exists():
    mistake.unlink()
    print(f"removed stray: {mistake}")
n = mcp_auth.revoke("lightharness")
print(f"revoke lightharness: {n} token")

# 登记 agent
cfg = {
    "name": AGENT,
    "host": "fb98",
    "command": "",
    "mode": "manual",
    "manual": True,
    "abilities": ["code", "docs", "verify", "python", "pytest"],
    "capabilities": ["freebsd", "python", "pytest", "compiler"],
    "repos": {
        "hive": str(HIVE),
        "light": "/home/skywalk/dswork/light",
        "lightharness": "/home/skywalk/dswork/lightharness",
        "lighthive": "/home/skywalk/dswork/lighthive",
        "lightplugin": "/home/skywalk/dswork/lightplugin",
        "lightprism": "/home/skywalk/dswork/lightprism",
    },
    "launch": "",
    "worktrees": "/home/skywalk/.hive/wt",
    "max_concurrency": 1,
    "created": "2026-11-18T21:25:00+08:00",
}
TARGET.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("written:", TARGET)

# enroll token
token = mcp_auth.enroll(AGENT, "worker")
mcp = pathlib.Path("/home/skywalk/dswork/lightharness/mcp.json")
mcp.write_text(json.dumps({
    "mcpServers": [{
        "name": "hive",
        "transport": "http",
        "url": "http://192.168.0.88:8790/mcp",
        "headers": {"Authorization": f"Bearer {token}"},
    }]
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
mcp.chmod(0o600)
print(f"token_len={len(token)}  mcp.json updated")
print(subprocess.run(["git","-C",str(HIVE),"status","--short"], capture_output=True, text=True).stdout)
