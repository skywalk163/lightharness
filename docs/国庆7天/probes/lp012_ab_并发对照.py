#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LP-D-012 A/B 对照探针（一条命令可复跑）。

把白天 6c1c31e「三模块新增原生并发 B 入口 + A/B 等价证明」固化成一条命令：
直接驱动 lightharness 自带的 `tests/unit/test_Day3_并发原语A_B.py`（9 个用例，
每个用例把 A 旧路径与 B 新路径放在同一份 .light 里逐项比对），并落盘对照表
（A 旧路径 / B 新路径 / 判定）。

- 通过 = B 相对 A 无回归（A/B 差异不消失）
- 失败 = B 相对 A 有回归，判定 FAIL
- `--break-b`：把测试副本里 B 入口符号改名为不存在的符号，期望 pytest 复红
  （A/B 差异消失），用于证明探针不是恒绿。

用法（任意工作目录）：
    python3 probes/lp012_ab_并发对照.py \
        --repo /path/to/lightharness \
        --light-merge /path/to/light-merge \
        [--reps 2] [--break-b]

退出码：
    0  全部用例通过且多次复跑结论一致（break-b 模式下另需复红确认）
    1  存在 FAIL 用例 / 多次复跑结论不一致
    9  break-b 反跑未复红（探针失效）
    8  探针自身无法运行（缺依赖 / 找不到测试文件）
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

# B 入口符号（src 侧原生并发入口；break-b 反跑时把测试副本里这些符号改名）
BREAK_B_SYMBOLS = [
    "轮询抽", "并发轮询", "具并发执行", "具异步执行", "具登记异步处理",
    "循异步派发", "注册协监听", "注销协监听", "驱动异步",
]

# A/B 对照表（用例名 -> (A 旧路径, B 新路径)）；与 test_Day3 的注释/函数名一致
AB_TABLE = [
    ("任务拉取泵_AB_追加表与溢录表逐项相等",
     "注入式推进器：调用方手写 while + 抽一轮/终抽",
     "原生 B：轮询抽（异步 段落 + 等待）"),
    ("任务拉取泵_并发轮询_多泵各自沉降盆",
     "注入式：逐泵串行驱动",
     "原生 B：并发轮询多泵，各自沉降盆"),
    ("工具执行_AB_并发结果与串行结果逐项相等",
     "注入式：执行工具（同步串行）",
     "原生 B：具并发执行（闸门串行 + 执行体并发）"),
    ("工具执行_异步处理器_经具异步执行生效",
     "注入式：仅同步工具，无异步处理器",
     "原生 B：具登记异步处理 + 具异步执行"),
    ("工具执行_并发执行_拒绝项按请求序对齐",
     "注入式：串行执行，无并发拒绝语义",
     "原生 B：具并发执行，拒绝项按请求序对齐"),
    ("代理循环_AB_协监听并发派发且错误隔离",
     "注入式：派发监听（同步遍历协监听器）",
     "原生 B：循异步派发（并发 + 错误隔离）"),
    ("代理循环_循异步跑一轮_轮内让出点且步骤全终态",
     "注入式：宿主侧手动排空",
     "原生 B：循异步派发轮内让出点，步骤全终态"),
    ("代理_驱动异步与驱动_inbox消费等价",
     "注入式：代理.驱动（同步消费 inbox）",
     "原生 B：代理.驱动异步（inbox 消费语义一致）"),
    ("反向哨兵_同步段落内等待必须报错",
     "同步段落里写 等待（禁止形态）",
     "反向哨兵：必须响亮报错，不能静默通过"),
]


def _run(cmd: list[str], env: dict[str, str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), env=env,
                          capture_output=True, text=True, timeout=600)


def _parse_junit(xml_path: Path) -> dict[str, str]:
    """返回 {用例名(去test_前缀): PASS|FAIL}。"""
    root = ET.parse(str(xml_path)).getroot()
    out: dict[str, str] = {}
    for tc in root.iter("testcase"):
        name = tc.get("name", "")
        if name.startswith("test_"):
            name = name[len("test_"):]
        status = "PASS"
        if tc.find("failure") is not None or tc.find("error") is not None:
            status = "FAIL"
        out[name] = status
    return out


def run_ab(repo: Path, lm: Path, reps: int, workdir: Path,
           test_file: Path, tag: str) -> dict[str, str]:
    """跑 reps 次 pytest 驱动 test_Day3，返回 {用例名: PASS|FAIL}（并校验结论一致）。"""
    pycache = workdir / "pycache"
    pycache.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.update({
        "LIGHT_MERGE": str(lm),
        "PYTHONPATH": os.pathsep.join([str(lm / "src"), str(repo / "tests" / "unit")]),
        "PYTHONPYCACHEPREFIX": str(pycache),
        "PYTHONUTF8": "1",
    })
    result_maps: list[dict[str, str]] = []
    for i in range(reps):
        jxml = workdir / f"junit_{tag}_{i}.xml"
        cmd = [
            sys.executable, "-m", "pytest", str(test_file),
            "-q", "--tb=no", "-rf", "-p", "no:cacheprovider",
            "--no-header", "-o", "addopts=",
            "--junitxml", str(jxml),
        ]
        proc = _run(cmd, env, repo)
        print(f"[{tag}] rep#{i+1}/{reps} rc={proc.returncode}")
        tail = proc.stdout.strip().splitlines()[-3:]
        for line in tail:
            print(f"    {line}")
        if proc.returncode != 0 and " passed" not in proc.stdout:
            print(f"    stderr尾部: {proc.stderr.strip().splitlines()[-2:]}")
        rm = _parse_junit(jxml)
        result_maps.append(rm)
    # 结论一致性校验
    first = result_maps[0]
    consistent = all(rm == first for rm in result_maps[1:])
    print(f"[{tag}] 多次复跑结论一致: {consistent}")
    if not consistent:
        return {}
    return first


def do_break_b(repo: Path, lm: Path, test_file: Path, workdir: Path) -> bool:
    """复制测试文件把 B 入口符号改名，期望 pytest 复红。返回是否复红。"""
    src_text = test_file.read_text(encoding="utf-8")
    broken = src_text
    hit = []
    for sym in BREAK_B_SYMBOLS:
        if re.search(rf"(?<![\u4e00-\u9fffA-Za-z0-9_]){re.escape(sym)}(?![\u4e00-\u9fffA-Za-z0-9_])", broken):
            hit.append(sym)
            broken = re.sub(rf"(?<![\u4e00-\u9fffA-Za-z0-9_]){re.escape(sym)}(?![\u4e00-\u9fffA-Za-z0-9_])",
                            sym + "_不存在", broken)
    if not hit:
        print("[break-b] 未命中任何 B 入口符号，反跑无法进行 → 复红失败")
        return False
    print(f"[break-b] 命中并改名符号: {hit}")
    tmp_file = workdir / "test_Day3_breakB_副本.py"
    tmp_file.write_text(broken, encoding="utf-8")
    pycache = workdir / "pycache_breakb"
    pycache.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.update({
        "LIGHT_MERGE": str(lm),
        "PYTHONPATH": os.pathsep.join([str(lm / "src"), str(repo / "tests" / "unit")]),
        "PYTHONPYCACHEPREFIX": str(pycache),
        "PYTHONUTF8": "1",
    })
    cmd = [
        sys.executable, "-m", "pytest", str(tmp_file),
        "-q", "--tb=no", "-rf", "-p", "no:cacheprovider",
        "--no-header", "-o", "addopts=",
    ]
    proc = _run(cmd, env, repo)
    tail = proc.stdout.strip().splitlines()[-4:]
    for line in tail:
        print(f"    {line}")
    red = proc.returncode != 0
    print(f"[break-b] 复红确认: {red} (rc={proc.returncode})")
    return red


def main() -> int:
    ap = argparse.ArgumentParser(
        description="LP-D-012 A/B 对照探针：驱动 test_Day3_并发原语A_B.py 输出对照表",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
               "  python3 lp012_ab_并发对照.py --repo ../.. --light-merge /path/light-merge --reps 2\n"
               "  python3 lp012_ab_并发对照.py --repo ../.. --light-merge /path/light-merge --break-b\n")
    ap.add_argument("--repo", type=Path, required=True,
                    help="lightharness 仓库根（含 运行.py 与 tests/unit/）")
    ap.add_argument("--light-merge", type=Path, required=True,
                    help="light-merge 仓根（含 src/ 与 cli/light.py）")
    ap.add_argument("--reps", type=int, default=2, help="复跑次数（默认 2）")
    ap.add_argument("--break-b", action="store_true",
                    help="反跑：改名 B 入口符号，期望复红")
    args = ap.parse_args()

    repo: Path = args.repo.resolve()
    lm: Path = args.light_merge.resolve()
    test_file = repo / "tests" / "unit" / "test_Day3_并发原语A_B.py"
    for p, name in [(repo, "repo"), (lm, "light-merge"), (test_file, "test_Day3")]:
        if not p.exists():
            print(f"[探针] 找不到 {name}: {p}")
            return 8

    workdir = Path(tempfile.mkdtemp(prefix="lp012_ab_", dir=tempfile.gettempdir()))
    t0 = time.time()
    try:
        print("=" * 70)
        print("LP-D-012 A/B 对照探针（test_Day3_并发原语A_B.py 一条命令复跑）")
        print(f"lightharness : {repo}")
        print(f"light-merge  : {lm}")
        print(f"测试文件     : {test_file}")
        print("=" * 70)

        rm = run_ab(repo, lm, args.reps, workdir, test_file, "ab")
        if not rm:
            print("[探针] 多次复跑结论不一致 → rc=1")
            return 1

        n_pass = sum(1 for v in rm.values() if v == "PASS")
        n_fail = len(rm) - n_pass
        print()
        print("=" * 70)
        print("A/B 对照表（A 旧路径 / B 新路径 / 判定）")
        print("=" * 70)
        for case, a_desc, b_desc in AB_TABLE:
            status = rm.get(case)
            mark = "PASS" if status == "PASS" else ("FAIL" if status == "FAIL" else "未见")
            print(f"  [{mark}] {case}")
            print(f"        A: {a_desc}")
            print(f"        B: {b_desc}")
        print("=" * 70)
        print(f"用例总数={len(rm)} 通过={n_pass} 失败={n_fail} 耗时={time.time()-t0:.1f}s")

        if n_fail > 0:
            print("[探针] 存在 FAIL → rc=1")
            return 1

        if args.break_b:
            red = do_break_b(repo, lm, test_file, workdir)
            if not red:
                print("[探针] break-b 未复红 → 探针失效 rc=9")
                return 9
            print("[探针] break-b 复红确认，A/B 探针有效 → rc=0")
        return 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())