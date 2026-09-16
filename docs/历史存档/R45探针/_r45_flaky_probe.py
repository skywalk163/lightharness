# R45 探针：复现 test_子进程后台 的 flaky
# 复刻 tests/test_回归.py::_run 的条件：cwd=临时目录 + capture_output 管道
import subprocess, tempfile, shutil, sys, os, glob

ROOT = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(ROOT, "运行.py")
CASE = os.path.join(ROOT, "examples", "test_子进程后台.light")
N = int(sys.argv[1]) if len(sys.argv) > 1 else 15

fails = 0
for i in range(1, N + 1):
    workdir = tempfile.mkdtemp(prefix="lightharness_case_")
    try:
        _ex = os.path.join(workdir, "examples")
        os.makedirs(_ex, exist_ok=True)
        for _py in glob.glob(os.path.join(ROOT, "examples", "*.py")):
            shutil.copy2(_py, _ex)
        p = subprocess.run([sys.executable, RUNNER, CASE],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           timeout=300, cwd=workdir)
        tag = "OK " if p.returncode == 0 else "RED"
        print(f"[{tag}] run{i} rc={p.returncode}", flush=True)
        if p.returncode != 0:
            fails += 1
            out = (p.stdout or "") + (p.stderr or "")
            print("---- 输出尾 ----", flush=True)
            print(out[-1200:], flush=True)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

print(f"\n==== 结果：{N} 次中 {fails} 次红 ====")
