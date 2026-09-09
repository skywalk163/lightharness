# -*- coding: utf-8 -*-
"""W4 验收脚本：webui 定位三态 + token 反跑 + 浏览器打开行为"""
import os, re, sys, tempfile, time, urllib.request, subprocess, threading, queue

ROOT = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(ROOT, "运行.py")
ENTRY = "examples/运行Web服务器.light"
BASE_ENV = dict(os.environ)
BASE_ENV.setdefault("HARNESS_WEB_MOCK", "1")
BASE_ENV["HARNESS_WEB_NO_OPEN"] = "1"
BASE_ENV["HARNESS_WEB_LIFETIME"] = "3"
BASE_ENV.pop("HARNESS_WEB_UI_DIR", None)  # 防止外层 shell 污染 S2/S4 的"未设置"语义

results = []

def run_launcher(env_extra, name, do_http=True, wait_exit=True, timeout=40):
    env = dict(BASE_ENV); env.update(env_extra)
    p = subprocess.Popen(["python", RUNNER, ENTRY], cwd=ROOT, env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                         encoding="utf-8", errors="replace")
    out_q, err_q = queue.Queue(), queue.Queue()
    def rd(stream, q):
        for line in stream: q.put(line)
        q.put(None)
    threading.Thread(target=rd, args=(p.stdout, out_q), daemon=True).start()
    threading.Thread(target=rd, args=(p.stderr, err_q), daemon=True).start()
    url, out_lines, err_lines = None, [], []
    deadline = time.time() + 30
    while time.time() < deadline and url is None:
        try: line = out_q.get(timeout=0.5)
        except queue.Empty: continue
        if line is None: break
        out_lines.append(line)
        if "web 服务已启动:" in line:
            m = re.search(r"(http://127\.0\.0\.1:\d+/\S+)", line)
            if m: url = m.group(1)
    # drain a bit
    end = time.time() + 1.5
    while time.time() < end:
        try: out_lines.append(out_q.get(timeout=0.2))
        except queue.Empty: pass
    http = None
    if url and do_http:
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                body = r.read().decode("utf-8", "replace")
                http = (r.status, body[:200])
        except Exception as e:
            http = ("ERR", str(e)[:160])
    rc, waited = None, False
    if wait_exit:
        try:
            rc = p.wait(timeout=timeout); waited = True
        except subprocess.TimeoutExpired:
            p.kill(); rc = p.wait(); waited = False
        # 补捞进程退出前的 stdout 尾部（LIFETIME 常驻期间可能仍有输出）
        while True:
            try: out_lines.append(out_q.get(timeout=0.2))
            except queue.Empty: break
    while True:
        try: err_lines.append(err_q.get(timeout=0.2))
        except queue.Empty: break
    joined_out = "".join(l for l in out_lines if l)
    joined_err = "".join(l for l in err_lines if l)
    results.append((name, url, http, rc, waited, joined_out, joined_err))
    print(f"[{name}] url={'YES' if url else 'NO'} http={http} rc={rc} exited={waited}")
    if joined_err.strip(): print(f"    stderr> {joined_err.strip()[:200]}")

# ---- S1: HARNESS_WEB_UI_DIR 指向自定义目录（应优先采用） ----
tmpd = tempfile.mkdtemp(prefix="w4_ui_")
with open(os.path.join(tmpd, "index.html"), "w", encoding="utf-8") as f:
    f.write("<html><body>CUSTOM-UI-OK</body></html>")
run_launcher({"HARNESS_WEB_UI_DIR": tmpd}, "S1_UI_DIR自定义")

# ---- S2: 未设置 UI_DIR → 应落到 lightharness/webui（同级） ----
run_launcher({}, "S2_同级webui")

# ---- S3: UI_DIR 指向不存在目录 → env非空直接采用(契约4优先级①) 不警告 + 静态404 + 服务照常 ----
run_launcher({"HARNESS_WEB_UI_DIR": "Z:\\__nonexist__\\webui"}, "S3_不存在目录")

# ---- S4: 未设置 UI_DIR 且同级/上级 webui 均缺失 → 警告 + 静态404 + 服务照常 ----
_ui_path = os.path.join(ROOT, "webui")
_bak_path = os.path.join(ROOT, "webui.s4bak")
if not os.path.isdir(_ui_path) and os.path.isdir(_bak_path):
    os.rename(_bak_path, _ui_path)  # 上次异常残留，先恢复
if os.path.isdir(_ui_path):
    os.rename(_ui_path, _bak_path)  # 临时移走同级 webui，制造"推导失败"
try:
    run_launcher({}, "S4_推导失败警告")
finally:
    if os.path.isdir(_bak_path):
        os.rename(_bak_path, _ui_path)  # 无条件恢复目录

# ---- 反跑1: 显式设置 HARNESS_WEB_TOKEN → URL 使用该令牌 ----
run_launcher({"HARNESS_WEB_TOKEN": "t0k3n-xYz123"}, "R1_显式令牌")

print("\n================ 判定 ================")
ok = True
def check(name, cond, desc):
    global ok
    print(("PASS" if cond else "FAIL") + f"  {name}: {desc}")
    if not cond: ok = False

def get(name):
    return next(r for r in results if r[0] == name)

s1 = get("S1_UI_DIR自定义"); check("S1", s1[2] and s1[2][0] == 200 and "CUSTOM-UI-OK" in s1[2][1], "自定义 UI_DIR 生效，GET / 返回200且含标记")
s2 = get("S2_同级webui"); check("S2", s2[2] and s2[2][0] == 200, "未设置时落到同级 lightharness/webui，GET / 返回200")
s3 = get("S3_不存在目录")
# 契约4优先级①: env 非空直接采用、不校验目录存在 → 不打印警告，仅静态404
check("S3", s3[2] is not None and s3[2][0] in (404, "ERR"), f"不存在目录→无警告 静态404/不可用 服务仍启动(rc={s3[3]})")
s4 = get("S4_推导失败警告")
s4_all = (s4[5] + s4[6]) if s4[5] or s4[6] else ""
warn4 = "未找到 webui 目录，静态页面不启用" in s4_all
check("S4", s4[2] is not None and s4[2][0] in (404, "ERR") and warn4, f"推导失败→警告({warn4}) 静态404/不可用 服务仍启动(rc={s4[3]})")
check("S4rc", s4[3] == 0 and s4[4], "S4 进程 LIFETIME 正常退出 rc=0")
check("S4restore", os.path.isdir(_ui_path) and not os.path.isdir(_bak_path), "S4 后 webui 目录已恢复、无残留备份")
check("S1rc", s1[3] == 0 and s1[4], "S1 进程 LIFETIME 正常退出 rc=0")
check("S2rc", s2[3] == 0 and s2[4], "S2 进程 LIFETIME 正常退出 rc=0")
check("S3rc", s3[3] == 0 and s3[4], "S3 进程 LIFETIME 正常退出 rc=0")
r1 = get("R1_显式令牌")
check("R1", r1[1] is not None and "token=t0k3n-xYz123" in r1[1], "显式令牌出现在 URL 上")
# 每个 URL 均带 token（认证接入）
for r in results:
    check("token_" + r[0], r[1] is None or "?token=" in r[1], f"{r[0]} URL 带 token 参数")
# NO_OPEN=1 时不得输出浏览器相关提示
for r in results:
    s = r[5] + r[6]
    check("noopen_" + r[0], "自动打开浏览器" not in s and "请手动访问" not in s, f"{r[0]} 未触发浏览器打开提示")

print("\nRESULT:", "ALL PASS" if ok else "HAS FAILURES")
sys.exit(0 if ok else 1)