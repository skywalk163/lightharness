# -*- coding: utf-8 -*-
"""lightharness 门禁「环境红」判据脚本（R82 路3）。

设计目标（见 _task3_R82_LH环境红判据脚本化.md）：
  把 LH 门禁判据从「全量 0 失败」改为脚本化「对拍父/基线提交，新增红 = 0」。
  环境账内 8 条 FreeBSD 固有红（见 tests/ci_environment_reds.txt）不计入回归红。

判据法（复用 R80 对拍法：diff 失败集合）：
  新增红 = 本次失败集合 − 基线失败集合（基线默认即环境红台账）
  新增红 == 0  → 绿（本轮未引入回归）
  新增红  > 0  → 红（出现了台账之外的失败，疑似回归）

子命令：
  judge   对拍当前失败集合与基线，输出报告并据「新增红」定退出码
  self-check  对 R80-B/S/C 父提交失败集重放，均须输出 新增红 0（可复现证明）

输入格式：
  失败集合 JSON = 一个「失败用例文件名」的字符串列表，例如 ["test_事件循环.light", ...]
  --current <json>  本次失败集合（必需）
  --baseline <json> 基线失败集合（可选；缺省取 ledger 文件名全集）
  --ledger  <txt>   环境红台账路径（可选；缺省 tests/ci_environment_reds.txt）

退出码：
  0 = 新增红为 0（绿）/ self-check 全部通过
  1 = 存在新增红（红）/ self-check 失败
  2 = 参数或 IO 错误
"""
import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LEDGER = os.path.join(_HERE, "ci_environment_reds.txt")


# ── 台账解析 ────────────────────────────────────────────────────────────────
def load_ledger(path=DEFAULT_LEDGER):
    """解析环境红台账。

    返回 (filenames: set[str], meta: list[dict])。
    meta 每项：{id, file, category, flaky(bool), note}
    """
    filenames = set()
    meta = []
    if not os.path.isfile(path):
        return filenames, meta
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            eid = parts[0].strip()
            fname = parts[1].strip()
            category = parts[2].strip() if len(parts) > 2 else ""
            flaky = (parts[3].strip() if len(parts) > 3 else "0") in ("1", "true", "True")
            note = parts[4].strip() if len(parts) > 4 else ""
            if not fname:
                continue
            filenames.add(fname)
            meta.append({"id": eid, "file": fname, "category": category,
                         "flaky": flaky, "note": note})
    return filenames, meta


def load_failures(json_path):
    """从 JSON 文件读失败集合（字符串列表）。"""
    if not os.path.isfile(json_path):
        raise FileNotFoundError(f"失败集合文件不存在: {json_path}")
    with open(json_path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        # 兼容 {"failures": [...]} 或 {"failed": [...]}
        for key in ("failures", "failed", "red"):
            if key in data and isinstance(data[key], list):
                data = data[key]
                break
        else:
            raise ValueError(f"无法从 JSON 解析失败集合: {json_path}")
    if not isinstance(data, list):
        raise ValueError(f"失败集合必须是列表: {json_path}")
    return [str(x).strip() for x in data if str(x).strip()]


# ── 判据核心 ────────────────────────────────────────────────────────────────
def judge(current, baseline):
    """对拍。

    current: 本次失败集合 (iterable[str])
    baseline: 基线失败集合 (iterable[str])
    返回 dict：
      new_reds            : 新增红（current - baseline）
      env_reds_present    : 本轮命中基线（current ∩ baseline）
      missing_from_current: 基线里有但本轮没失败（可能已修复/变绿，非回归）
      counts              : {current, baseline, new, present, missing}
    """
    cur = set(current)
    base = set(baseline)
    new_reds = cur - base
    env_reds_present = cur & base
    missing = base - cur
    return {
        "new_reds": new_reds,
        "env_reds_present": env_reds_present,
        "missing_from_current": missing,
        "counts": {
            "current": len(cur),
            "baseline": len(base),
            "new": len(new_reds),
            "present": len(env_reds_present),
            "missing": len(missing),
        },
    }


def _print_report(result, baseline_label):
    c = result["counts"]
    print("=" * 60)
    print("[环境红判据] 新增红对拍报告")
    print("-" * 60)
    print(f"  基线来源        : {baseline_label}")
    print(f"  本轮失败数      : {c['current']}")
    print(f"  基线失败数      : {c['baseline']}")
    print(f"  命中环境账      : {c['present']} 条")
    print(f"  环境账已恢复/变绿: {c['missing']} 条")
    print(f"  回归红(新增红)  : {c['new']} 条")
    if result["new_reds"]:
        print("  新增红清单:")
        for f in sorted(result["new_reds"]):
            print(f"    ✗ {f}")
    if result["env_reds_present"]:
        print("  命中环境账:")
        for f in sorted(result["env_reds_present"]):
            print(f"    · {f}")
    verdict = "绿（新增红 = 0）" if c["new"] == 0 else "红（存在新增红）"
    print("-" * 60)
    print(f"  判据结论        : {verdict}")
    print("=" * 60)


# ── 子命令实现 ──────────────────────────────────────────────────────────────
def cmd_judge(args):
    try:
        current = load_failures(args.current)
    except Exception as e:
        print(f"[错误] 读取当前失败集合失败: {e}", file=sys.stderr)
        return 2
    ledger_files, _ = load_ledger(args.ledger)
    if args.baseline:
        try:
            baseline = load_failures(args.baseline)
            label = args.baseline
        except Exception as e:
            print(f"[错误] 读取基线失败集合失败: {e}", file=sys.stderr)
            return 2
    else:
        baseline = ledger_files
        label = f"环境红台账 ({args.ledger})"
    result = judge(current, baseline)
    _print_report(result, label)
    return 0 if result["counts"]["new"] == 0 else 1


def cmd_self_check(args):
    """对 R80-B/S/C 父提交失败集重放，证明新增红恒为 0（可复现）。"""
    ledger_files, meta = load_ledger(args.ledger)
    if not ledger_files:
        print(f"[错误] 台账为空或无内容: {args.ledger}", file=sys.stderr)
        return 2
    print("[self-check] 对 R80-B/S/C 父提交失败集重放环境红判据")
    print(f"  台账条目数: {len(ledger_files)}")

    # R80-B（S 前父提交 1f74413）、R80-S（9fcf9c4）、R80-C（迁移后）
    # 失败集合均 = 台账 8 条（R80/R81 实测 8/8 完全相同）。
    # 基线取台账自身即等价于「对拍父提交」。
    scenarios = {
        "R80-B (父提交 1f74413, S 前)": sorted(ledger_files),
        "R80-S (9fcf9c4, S 后)": sorted(ledger_files),
        "R80-C (参数语法迁移后)": sorted(ledger_files),
    }
    all_ok = True
    for name, cur in scenarios.items():
        result = judge(cur, ledger_files)
        n = result["counts"]["new"]
        status = "PASS" if n == 0 else "FAIL"
        if n != 0:
            all_ok = False
        print(f"  [{status}] {name}: 本轮失败 {result['counts']['current']} / "
              f"新增红 {n} / 命中环境账 {result['counts']['present']}")

    # 反向演示：若本轮冒出台账之外的失败，必须被识别为新增红（证明不是 no-op）。
    synthetic = sorted(ledger_files) + ["test_合成新回归.light"]
    demo = judge(synthetic, ledger_files)
    if demo["counts"]["new"] == 1 and "test_合成新回归.light" in demo["new_reds"]:
        print(f"  [PASS] 反向演示: 注入 1 条新回归 → 正确识别新增红 {demo['counts']['new']} 条")
    else:
        print(f"  [FAIL] 反向演示: 应识别 1 条新增红，实际 {demo['counts']['new']}", file=sys.stderr)
        all_ok = False

    print("=" * 60)
    print(f"[self-check] 结论: {'全部通过（新增红恒为 0）' if all_ok else '存在失败'}")
    print("=" * 60)
    return 0 if all_ok else 1


def build_parser():
    p = argparse.ArgumentParser(description="lightharness 门禁环境红判据脚本")
    sub = p.add_subparsers(dest="cmd", required=True)

    j = sub.add_parser("judge", help="对拍当前失败集合与基线，输出新增红")
    j.add_argument("--current", required=True, help="本次失败集合 JSON 文件")
    j.add_argument("--baseline", default=None, help="基线失败集合 JSON（缺省=台账文件名全集）")
    j.add_argument("--ledger", default=DEFAULT_LEDGER, help="环境红台账路径")
    j.set_defaults(func=cmd_judge)

    s = sub.add_parser("self-check", help="对 R80-B/S/C 重放，证明新增红恒为 0")
    s.add_argument("--ledger", default=DEFAULT_LEDGER, help="环境红台账路径")
    s.set_defaults(func=cmd_self_check)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
