# -*- coding: utf-8 -*-
"""验证：启动后大模型配置自动检测 + 配置页弹窗逻辑"""
import os, re, sys, time, urllib.request, subprocess, threading, queue, json

ROOT = r"G:\dswork\duan-light-merge\lightharness"
RUNNER = os.path.join(ROOT, "运行.py")
ENTRY = "examples/运行Web服务器.light"
ENVFILE = os.path.join(ROOT, ".env")

def run_once(name, env_extra, timeout=60):
    env = dict(os.environ)
    env.pop("HARNESS_WEB_MOCK", None)  # 不显式设置 → 走自动检测
    env["HARNESS_WEB_NO_OPEN"] = "1"
    env["HARNESS_WEB_LIFETIME"] = "4"
    env.update(env_extra)
    p = subprocess.Popen(["python", RUNNER, ENTRY], cwd=ROOT, env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                         encoding="utf-8", errors="replace")
    out_q = queue.Queue()
    def rd(stream, q):
        for line in stream: q.put(line)
        q.put(None)
    threading.Thread(target=rd, args=(p.stdout, out_q), daemon=True).start()
    url, out_lines = None, []
    deadline = time.time() + 30
    while time.time() < deadline and url is None:
        try: line = out_q.get(timeout=0.5)
        except queue.Empty: continue
        if line is None: break
        out_lines.append(line)
        if "web 服务已启动:" in line:
            m = re.search(r"(http://127\.0\.0\.1:\d+/\S*)", line)
            if m: url = m.group(1).rstrip()
    # 探测 /api/config
    cfg = None
    root_status = None
    if url:
        try:
            base = url.split("?")[0].rstrip("/")
            with urllib.request.urlopen(base + "/", timeout=5) as r:
                root_status = (r.status, r.read(100).decode("utf-8", "replace"))
        except Exception as e:
            root_status = ("ERR", str(e)[:120])
        try:
            with urllib.request.urlopen(base + "/api/config", timeout=5) as r:
                cfg = json.loads(r.read().decode("utf-8"))
        except Exception as e:
            cfg = {"ERR": str(e)[:160]}
    try:
        rc = p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill(); rc = p.wait()
    while True:
        try:
            l = out_q.get(timeout=0.2)
            if l is None: break
            out_lines.append(l)
        except queue.Empty: break
    print(f"===== {name} =====")
    print("  url:", url)
    print("  GET /:", root_status)
    print("  /api/config:", cfg)
    print("  rc:", rc)
    for l in out_lines:
        l = l.strip()
        if l: print("  out>", l)
    return cfg

# 场景1：有 .env（当前 .env 有 OPENAI_API_KEY）
cfg1 = run_once("有.env", {})
# 场景2：临时移走 .env → 无 .env
bak = ENVFILE + ".bak"
moved = False
if os.path.exists(ENVFILE):
    os.rename(ENVFILE, bak); moved = True
try:
    cfg2 = run_once("无.env", {})
finally:
    if moved and os.path.exists(bak):
        os.rename(bak, ENVFILE)

print("\n================ 判定 ================")
ok = True
def check(name, cond, desc):
    global ok
    print(("PASS" if cond else "FAIL") + f"  {name}: {desc}")
    if not cond: ok = False

check("有env_configured1", cfg1 and cfg1.get("configured") == 1, f"有 .env → configured=1（前端不弹配置页），实际={cfg1 and cfg1.get('configured')}")
check("有env_mock0", cfg1 and cfg1.get("mock") == 0, f"有 .env → mock=0（真实客户端），实际={cfg1 and cfg1.get('mock')}")
check("有env_has_key1", cfg1 and cfg1.get("has_key") == 1, f"有 .env → has_key=1，实际={cfg1 and cfg1.get('has_key')}")
check("无env_服务照常启动", cfg2 is not None and "ERR" not in cfg2, f"无 .env → 服务照常启动（不退出），/api/config 返回={cfg2}")
check("无env_configured0", cfg2 and cfg2.get("configured") == 0, f"无 .env → configured=0（前端弹配置页），实际={cfg2 and cfg2.get('configured')}")
check("无env_mock1", cfg2 and cfg2.get("mock") == 1, f"无 .env → mock=1（占位启动），实际={cfg2 and cfg2.get('mock')}")
check("无env_has_key0", cfg2 and cfg2.get("has_key") == 0, f"无 .env → has_key=0，实际={cfg2 and cfg2.get('has_key')}")
check("env恢复", os.path.exists(ENVFILE) and not os.path.exists(bak), ".env 已恢复原状")

print("\nRESULT:", "ALL PASS" if ok else "HAS FAILURES")
sys.exit(0 if ok else 1)
