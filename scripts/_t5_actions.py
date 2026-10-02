# -*- coding: utf-8 -*-
"""T5：查 github Actions runs 状态（只读 API，不触发重跑）。

用法： python _t5_actions.py [limit_per_page]
输出： of 各 run 的 job 结论表 + 失败 job 的日志尾部（去 token 化）
"""
from __future__ import annotations

import io
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]


def load_env():
    env = {}
    for line in io.open(ROOT / ".env", encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


ENV = load_env()
TOKEN = ENV.get("GITHUB_TOKEN")
OWNER, REPO = "skywalk163", "light"
API = "https://api.github.com"

SECRET_RE = re.compile(r"(ghp_[A-Za-z0-9]{20,}|ghs_[A-Za-z0-9]{20,}|pypi-[A-Za-z0-9_\-]{20,}|[A-Za-z0-9_\-]{40,}\.[A-Za-z0-9_\-]{20,})")


def get(path, accept="application/vnd.github+json"):
    req = Request(f"{API}{path}", headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": accept,
        "User-Agent": "workbuddy-t5",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urlopen(req, timeout=60) as r:  # noqa: S310
        return json.loads(r.read().decode("utf-8"))


def sanitize(s: str) -> str:
    return SECRET_RE.sub("[REDACTED]", s or "")


def tail_log(owner, repo, job_id, n=40):
    try:
        with urlopen(Request(  # noqa: S310
            f"{API}/repos/{owner}/{repo}/actions/jobs/{job_id}/logs",
            headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json",
                     "User-Agent": "workbuddy-t5"},
        ), timeout=90) as r:
            txt = r.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa
        return f"<日志获取失败: {type(exc).__name__}>"
    lines = [l for l in txt.splitlines() if l.strip()]
    return "\n".join(sanitize(l)[:220] for l in lines[-n:])


def main():
    runs = get(f"/repos/{OWNER}/{REPO}/actions/runs?per_page=15")["workflow_runs"]
    print(f"{'#':<3}{'id':>12}  {'event':<10}{'status':<10}{'concl':<10}{'created':<22}{'head':<28}{'name'}")
    print("-" * 150)
    for r in runs:
        print(f"{r['run_attempt']:<3}{r['id']:>12}  {r['event']:<10}{r['status']:<10}{str(r.get('conclusion')):<10}"
              f"{r['created_at']:<22}{str(r.get('head_branch'))[:26]:<28}{r['name']}")
    print()

    for r in runs[:6]:
        print("=" * 100)
        print(f"RUN {r['id']} · {r['name']} · event={r['event']} · {r['display_title']} · "
              f"{r['created_at']} → {r['updated_at']} · conclusion={r.get('conclusion')}")
        print(f"  head_sha={r['head_sha'][:12]}  html={r['html_url']}")
        jobs = get(f"/repos/{OWNER}/{REPO}/actions/runs/{r['id']}/jobs?per_page=30")["jobs"]
        for j in jobs:
            print(f"  ├─ [{str(j.get('conclusion')):<12}] {j['name']}  (started {j['started_at']} / {j['completed_at']})")
        for j in jobs:
            if j.get("conclusion") in ("failure", "cancelled", "timed_out"):
                print(f"  ▼ job={j['name']} 日志尾部：")
                print("    " + tail_log(OWNER, REPO, j["id"]).replace("\n", "\n    "))


if __name__ == "__main__":
    main()
