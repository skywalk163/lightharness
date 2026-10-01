# 临时脚本：经 GitHub Git Data API 把本地 HEAD~1..HEAD 的增量推到 github（绕过本地代理对 github.com 的 502 拦截）。
# 取 github 当前 HEAD 的 tree 为基座，应用本次提交的变更文件，建新 tree，再以 github 当前 HEAD 为 parent 建 commit，fast-forward ref。
# 仅依赖标准库；token 从 monorepo 根 .env 的 GITHUB_TOKEN 读取。
import os, json, subprocess, urllib.request, urllib.error
from datetime import datetime

REPO = "skywalk163/lightharness"
BRANCH = "main"
REPO_DIR = r"G:/dswork/duan-light-merge/lightharness"
ENV_PATH = r"G:/dswork/duan-light-merge/.env"
API = "https://api.github.com"


def get_token():
    t = os.environ.get("GITHUB_TOKEN")
    if t:
        return t
    if os.path.exists(ENV_PATH):
        for line in open(ENV_PATH, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if line.startswith("GITHUB_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"')
    raise SystemExit("GITHUB_TOKEN not found")


TOKEN = get_token()


def git(*args):
    return subprocess.run(["git"] + list(args), cwd=REPO_DIR,
                          capture_output=True, text=True)


def api(method, path, data=None):
    url = API + path
    headers = {"Authorization": f"Bearer {TOKEN}",
               "Accept": "application/vnd.github+json",
               "User-Agent": "push-delta-script"}
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8") or "{}")
    except Exception as e:
        return -1, {"error": str(e)[:300]}


def iso_from_gitdate(s):
    dt = datetime.strptime(s.strip(), "%Y-%m-%dT%H:%M:%S%z")
    return dt.isoformat()


def main():
    # 1) github 当前 HEAD 及其 tree（a5b424e3，= 归一化 67aea3d）
    st, res = api("GET", f"/repos/{REPO}/git/refs/heads/{BRANCH}")
    if st != 200:
        raise SystemExit(f"读取远端 ref 失败 {st}: {res}")
    remote = res["object"]["sha"]
    st, cres = api("GET", f"/repos/{REPO}/git/commits/{remote}")
    if st != 200:
        raise SystemExit(f"读取远端 commit 失败 {st}: {cres}")
    base_tree = cres["tree"]["sha"]
    print("remote(old):", remote)
    print("base_tree  :", base_tree)

    # 2) HEAD~1..HEAD 的变更文件（仅本次提交的若干文件）
    LOCAL = git("rev-parse", "HEAD").stdout.strip()
    parent = git("rev-parse", "HEAD~1").stdout.strip()
    diff = git("diff", "--name-status", parent, LOCAL).stdout
    entries = []
    for line in diff.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        path = parts[-1]
        mode = git("ls-files", "-s", "--", path).stdout.split()[0] or "100644"
        raw = open(os.path.join(REPO_DIR, path), "rb").read()
        content = raw.replace(b"\r\n", b"\n").decode("utf-8")  # 归一为 LF，与 github 存储一致
        st2, bres = api("POST", f"/repos/{REPO}/git/blobs",
                        {"content": content, "encoding": "utf-8"})
        if st2 != 201:
            raise SystemExit(f"blob 上传失败 {st2}: {bres} for {path}")
        entries.append({"path": path, "mode": mode, "type": "blob", "sha": bres["sha"]})
        print(f"  blob OK: {path} -> {bres['sha'][:10]}")
    print(f"已上传 {len(entries)} 个 blob")

    # 3) 在 base_tree 之上建新 tree
    st3, tres = api("POST", f"/repos/{REPO}/git/trees",
                    {"base_tree": base_tree, "tree": entries})
    if st3 != 201:
        raise SystemExit(f"tree 创建失败 {st3}: {tres}")
    new_tree = tres["sha"]
    print("new_tree   :", new_tree)

    # 4) commit（复用 cb8034c5 的 message / author / committer）
    log = git("log", "-1",
              "--format=%B%x00%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI",
              LOCAL).stdout
    p = log.split("\x00")
    message = p[0]
    author = {"name": p[1], "email": p[2], "date": iso_from_gitdate(p[3])}
    committer = {"name": p[4], "email": p[5], "date": iso_from_gitdate(p[6])}
    st4, comres = api("POST", f"/repos/{REPO}/git/commits",
                      {"message": message, "tree": new_tree,
                       "parents": [remote], "author": author, "committer": committer})
    if st4 != 201:
        raise SystemExit(f"commit 创建失败 {st4}: {comres}")
    new_commit = comres["sha"]
    print("new_commit :", new_commit)

    # 5) fast-forward（force:False）
    st5, rf = api("PATCH", f"/repos/{REPO}/git/refs/heads/{BRANCH}",
                  {"sha": new_commit, "force": False})
    if st5 != 200:
        raise SystemExit(f"ref 更新失败 {st5}: {rf}")
    print("推送成功；远端 main ->", new_commit)


if __name__ == "__main__":
    main()
