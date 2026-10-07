# -*- coding: utf-8 -*-
"""经 GitHub Git Data API 把本地 <release_sha> 的树同步到 github main —— **`git/blobs` 端点不可用时的通道**。

为什么需要这个脚本（R121 实测确认，非臆测）
-----------------------------------------
github 与本地历史分叉（github 的 commit/tree SHA 在本地对象库里不存在），本来靠
`_push_github_tree_sync.py`（先 POST /git/blobs 传 blob，再 POST /git/trees 建树）走 API 同步。
但本机网络下：

  * `POST /repos/{repo}/git/blobs` **稳定返回 HTTP 500**（连 5 字节最小 blob 也 500，
    与 base64/utf-8 编码无关）⇒ 原 tree_sync **完全不可用**，卡在第一步；
  * github 的 `git` 智能 HTTP 经代理**偶发 502**（`CONNECT tunnel failed, response 502`），
    直推不可靠；
  * `api.github.com` 的 GET、`POST /git/trees`、`POST /git/commits`、`PATCH ref` 均正常。

本脚本据此改走两条绕行设计：

  1. **inline content 代替 blob 上传**：`POST /git/trees` 的条目可以直接带 `content`
     （而不用先传 blob 拿 SHA），从而**完全绕开坏掉的 blobs 端点**。
  2. **只提交「改动项 + 删除项」**：带 `base_tree=github HEAD tree`，未变文件由 base_tree
     合并，请求体极小（R121 实到 1 个文件），**避开大包触发的代理 502**。
     （第一版曾把 2281 个文件全部内联进一个 tree POST → 代理 502；必须只提交改动项。）

另加两处健壮性（都是踩过的坑）：
  * `fetch_tree` 对 `IncompleteRead` 重试 —— 大递归树偶发读断，会解析出**残缺树**，
    导致 2281 个文件被误判为「已改」并连带触发二进制 blob 上传；
  * API 层对 5xx 与 `IncompleteRead` 重试 + 退避。

限制
----
  * 只支持**文本文件**走 inline；若改动项含二进制，脚本会明确报错退出
    （此时应改用 git 协议直推，或等 blobs 端点恢复后用 `_push_github_tree_sync.py`）。
  * 结果仍是**内容等价**（github 树与本地树 blob 一致），github 的 commit SHA 与本地不同
    是通道固有差异，不强推、不 force。

用法
----
    python scripts/push_github_inline.py <repo_full_name> <repo_dir> <release_sha> [tag=vX.Y.Z]

例：
    python scripts/push_github_inline.py skywalk163/light G:/dswork/duan-light-merge/light-merge ef009b890

凭据：`GITHUB_TOKEN` 取环境变量，或 monorepo 根 `.env`（与 `_push_github_tree_sync.py` 同口径）。
"""
from __future__ import annotations

import base64
import http.client
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

ENV_PATH = r"G:/dswork/duan-light-merge/.env"
API = "https://api.github.com"
UA = "gh-inline-sync"


def get_token() -> str:
    t = os.environ.get("GITHUB_TOKEN")
    if t:
        return t.strip().strip('"').strip("'")
    if os.path.exists(ENV_PATH):
        for line in open(ENV_PATH, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if line.startswith("GITHUB_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("GITHUB_TOKEN not found")


TOKEN = get_token()


def git(repo_dir, *args):
    return subprocess.run(["git", "-c", "core.quotePath=false"] + list(args),
                          cwd=repo_dir, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def api(method, path, data=None, retries=4):
    """API 调用：对 5xx / IncompleteRead 重试 + 退避；4xx 直接返回。"""
    url = API + path
    headers = {"Authorization": f"Bearer {TOKEN}",
               "Accept": "application/vnd.github+json",
               "User-Agent": UA}
    body = json.dumps(data).encode("utf-8") if data is not None else None
    last_err = None
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(url, data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as e:
            code = e.code
            try:
                err = json.loads(e.read().decode("utf-8") or "{}")
            except Exception:
                err = {}
            if code >= 500:
                last_err = f"HTTP {code}: {err}"
                time.sleep(3 * attempt)
                continue
            return code, err
        except (http.client.IncompleteRead, urllib.error.URLError) as e:
            last_err = str(e)[:200]
            time.sleep(3 * attempt)
            continue
    return -1, {"error": f"重试耗尽: {last_err}"}


def remote_head(repo, branch="main"):
    st, res = api("GET", f"/repos/{repo}/git/refs/heads/{branch}")
    if st != 200:
        raise SystemExit(f"读取远端 ref 失败 {st}: {res}")
    return res["object"]["sha"]


def fetch_tree(repo, tree_sha):
    """递归拉树；对 IncompleteRead/5xx 重试，确保拿全（残缺树会误判大量改动）。"""
    entries = {}
    last_err = None
    for attempt in range(1, 7):
        st, res = api("GET", f"/repos/{repo}/git/trees/{tree_sha}?recursive=1")
        if st == 200:
            for e in res.get("tree", []):
                if e["type"] == "blob":
                    entries[e["path"]] = (e["sha"], e["mode"])
            if res.get("truncated"):
                print("WARNING: tree 被截断（>100k 条目），本脚本未分页，结果可能不全")
            return entries
        last_err = f"HTTP {st}: {res}"
        print(f"  fetch_tree 重试 {attempt}/6（{last_err[:80]}）")
        time.sleep(2 * attempt)
    raise SystemExit(f"取 tree 失败（重试耗尽）：{last_err}")


def iso_from_gitdate(s):
    return datetime.strptime(s.strip(), "%Y-%m-%dT%H:%M:%S%z").isoformat()


def main():
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    repo, repo_dir, release = sys.argv[1], sys.argv[2], sys.argv[3]
    tag_arg = None
    if len(sys.argv) == 5 and sys.argv[4].startswith("tag="):
        tag_arg = sys.argv[4].split("=", 1)[1]

    if git(repo_dir, "cat-file", "-t", release).stdout.strip() != "commit":
        raise SystemExit(f"release {release} 不是本地 commit")

    gh_head = remote_head(repo)
    st_c, cres = api("GET", f"/repos/{repo}/git/commits/{gh_head}")
    if st_c != 200:
        raise SystemExit(f"读取远端 commit 失败 {st_c}: {cres}")
    gh_tree = cres["tree"]["sha"]
    gh_entries = fetch_tree(repo, gh_tree)
    print(f"github HEAD={gh_head[:10]} tree={gh_tree[:10]} 文件数={len(gh_entries)}")

    local = git(repo_dir, "ls-tree", "-r", release).stdout
    local_entries = {}
    for line in local.splitlines():
        mode, _, sha, path = line.split(None, 3)
        local_entries[path] = (sha, mode)
    print(f"本地 release 文件数={len(local_entries)}")

    changed = [p for p in local_entries
               if gh_entries.get(p) is None or gh_entries.get(p)[0] != local_entries[p][0]]
    deletes = [p for p in gh_entries if p not in local_entries]
    print(f"待改/增={len(changed)}：{changed[:10]}{' …' if len(changed) > 10 else ''}")
    print(f"待删={len(deletes)}")

    if not changed and not deletes:
        print("无改动，跳过")
        return

    entries = []
    for p in deletes:
        entries.append({"path": p, "mode": "100644", "type": "blob", "sha": None})

    for p in changed:
        sha, mode = local_entries[p]
        raw = subprocess.run(["git", "-c", "core.quotePath=false", "cat-file", "blob", sha],
                             cwd=repo_dir, capture_output=True).stdout
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise SystemExit(
                f"二进制文件 {p} 无法走 inline 通道（blobs 端点 500）。"
                f"请改用 git 协议直推，或等 blobs 端点恢复后用 _push_github_tree_sync.py")
        entries.append({"path": p, "mode": mode, "type": "blob", "content": content})
        print(f"  inline: {p} ({len(content)} chars)")
    # 未变文件交 base_tree 合并，不重复提交（避免大包触发代理 502）

    st_t, tres = api("POST", f"/repos/{repo}/git/trees",
                     {"base_tree": gh_tree, "tree": entries})
    if st_t != 201:
        raise SystemExit(f"tree 创建失败 {st_t}: {tres}")
    new_tree = tres["sha"]

    log = git(repo_dir, "log", "-1",
              "--format=%B%x00%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI", release).stdout
    f = log.split("\x00")
    payload = {
        "message": f[0],
        "tree": new_tree,
        "parents": [gh_head],
        "author": {"name": f[1], "email": f[2], "date": iso_from_gitdate(f[3])},
        "committer": {"name": f[4], "email": f[5], "date": iso_from_gitdate(f[6])},
    }
    st_k, comres = api("POST", f"/repos/{repo}/git/commits", payload)
    if st_k != 201:
        raise SystemExit(f"commit 创建失败 {st_k}: {comres}")
    new_commit = comres["sha"]

    st_r, rf = api("PATCH", f"/repos/{repo}/git/refs/heads/main",
                   {"sha": new_commit, "force": False})
    if st_r != 200:
        raise SystemExit(f"ref 更新失败 {st_r}: {rf}")
    print(f"PUSHED: github main {gh_head[:8]} -> {new_commit[:10]}")
    print(f"NEW_GH_HEAD={new_commit}")

    if tag_arg:
        st_tg, tgres = api("POST", f"/repos/{repo}/git/refs",
                           {"ref": f"refs/tags/{tag_arg}", "sha": new_commit})
        if st_tg != 201:
            raise SystemExit(f"tag 创建失败 {st_tg}: {tgres}")
        print(f"TAGGED: refs/tags/{tag_arg} -> {new_commit[:10]}")
    print("DONE")


if __name__ == "__main__":
    main()
