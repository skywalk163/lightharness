# -*- coding: utf-8 -*-
"""经 GitHub Git Data API 把本地 <release_sha> 的【完整树】同步到 github main。

⚠️ 当前状态（R121 实测）：**本脚本在本机网络下不可用**——它第一步就要
`POST /repos/{repo}/git/blobs` 上传 blob，而该端点在本机代理下**稳定返回 HTTP 500**
（连 5 字节最小 blob 也 500，与编码无关），会卡死在第一步。
另：github 的 git 智能 HTTP 经代理偶发 502，直推也不可靠。
⇒ **请改用 `scripts/push_github_inline.py`**（用 `POST /git/trees` 的 inline content
直接内联改动内容建树 + `base_tree` 合并，绕开坏掉的 blobs 端点，且请求体极小避开 502）。
若将来 blobs 端点恢复（或换网络环境），本脚本仍是「分叉兜底全量同步」的主路径，故保留。

适用场景：github 与本地历史分叉（github 的 commit/tree SHA 在本地对象库里不存在），
无法用 rev-list base..HEAD 增量重放。本脚本直接：
  1) 以 github 当前 HEAD 的 tree 为基座；
  2) 用 git ls-tree -r <release_sha> 取本地树，逐文件与 github 树按 blob SHA 比对；
  3) 仅上传「新增/改动」的 blob（内容取自 git 对象库，已是 LF，CRLF->LF 双保险），
     删除「本地已无」的文件；
  4) 建 tree（base_tree=github HEAD tree）-> 建 commit（parent=github HEAD）-> FF PATCH ref。
最终 github main 的树 == 本地 release 树（内容等价，SHA 因 CRLF/重建而不同）。
可选第 4 参 tag=v0.3.0：同步后顺手建 lightweight tag ref 指向新 HEAD。

用法：
    python _push_github_tree_sync.py <repo_full_name> <repo_dir> <release_sha> [tag=vX.Y.Z]
例：
    python _push_github_tree_sync.py skywalk163/lightharness G:/dswork/duan-light-merge/lightharness 082255c tag=v0.3.0
"""
import os
import sys
import json
import base64
import subprocess
import urllib.request
import urllib.error
from datetime import datetime

ENV_PATH = r"G:/dswork/duan-light-merge/.env"
API = "https://api.github.com"


def get_token():
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


def api(method, path, data=None):
    url = API + path
    headers = {"Authorization": f"Bearer {TOKEN}",
               "Accept": "application/vnd.github+json",
               "User-Agent": "tree-sync"}
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8") or "{}")
    except Exception as e:
        return -1, {"error": str(e)[:300]}


def remote_head(repo, branch="main"):
    st, res = api("GET", f"/repos/{repo}/git/refs/heads/{branch}")
    if st != 200:
        raise SystemExit(f"读取远端 ref 失败 {st}: {res}")
    return res["object"]["sha"]


def fetch_tree_recursive(repo, tree_sha):
    entries = {}
    st, res = api("GET", f"/repos/{repo}/git/trees/{tree_sha}?recursive=1")
    if st != 200:
        raise SystemExit(f"取 tree 失败 {st}: {res}")
    for e in res.get("tree", []):
        if e["type"] == "blob":
            entries[e["path"]] = e["sha"]
    if res.get("truncated"):
        print("WARNING: tree 被截断（>100k 条目），本脚本未做分页，结果可能不全")
    return entries


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
    print(f"github 当前 HEAD = {gh_head[:10]}  tree = {gh_tree[:10]}")
    gh_entries = fetch_tree_recursive(repo, gh_tree)
    print(f"github 树文件数 = {len(gh_entries)}")

    local = git(repo_dir, "ls-tree", "-r", release).stdout
    local_entries = {}
    for line in local.splitlines():
        mode, _, sha, path = line.split(None, 3)
        local_entries[path] = (sha, mode)
    print(f"本地 release 树文件数 = {len(local_entries)}")

    to_upload = {}
    for path, (sha, mode) in local_entries.items():
        if gh_entries.get(path) != sha:
            to_upload[path] = (sha, mode)
    deletes = [p for p in gh_entries if p not in local_entries]
    print(f"待上传(新增/改动) = {len(to_upload)}，待删除 = {len(deletes)}")

    entries = []
    for path in deletes:
        entries.append({"path": path, "mode": "100644", "type": "blob", "sha": None})
        print(f"  del  : {path}")
    for path, (sha, mode) in to_upload.items():
        # 原样上传 git 对象库里的 blob 字节（不归一 CRLF）：
        # 本地树里的 blob SHA 取决于对象库实际存储字节，归一会破坏树等价。
        raw = subprocess.run(["git", "-c", "core.quotePath=false", "cat-file", "blob", sha],
                             cwd=repo_dir, capture_output=True).stdout  # bytes
        b64 = base64.b64encode(raw).decode("ascii")
        st_b, bres = api("POST", f"/repos/{repo}/git/blobs",
                         {"content": b64, "encoding": "base64"})
        if st_b != 201:
            raise SystemExit(f"blob 上传失败 {st_b}: {bres} for {path}")
        entries.append({"path": path, "mode": mode, "type": "blob", "sha": bres["sha"]})
        print(f"  blob : {path} -> {bres['sha'][:10]}")

    st_t, tres = api("POST", f"/repos/{repo}/git/trees",
                     {"base_tree": gh_tree, "tree": entries})
    if st_t != 201:
        raise SystemExit(f"tree 创建失败 {st_t}: {tres}")
    new_tree = tres["sha"]

    log = git(repo_dir, "log", "-1",
              "--format=%B%x00%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI",
              release).stdout
    p = log.split("\x00")
    payload = {
        "message": p[0],
        "tree": new_tree,
        "parents": [gh_head],
        "author": {"name": p[1], "email": p[2], "date": iso_from_gitdate(p[3])},
        "committer": {"name": p[4], "email": p[5], "date": iso_from_gitdate(p[6])},
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
