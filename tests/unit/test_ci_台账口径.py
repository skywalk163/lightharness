# -*- coding: utf-8 -*-
"""CI 台账口径判据（T-0524）。

判据卫生的目标：两份台账都必须是「有据可查的豁免」，不是垃圾桶。
本文件钉住四件事，任何一条不满足即红：

1. 字段自洽：编号格式（E-xx / F-xx）、类别/平台取值合法、处置非空、编号不重复；
2. 取证字段：每条必须有「日期（YYYY-MM-DD）+ 测量依据（命令或全量/单跑等测量动作）
   + 结果摘要（rc=/通过/恒绿/passed）」。缺失即视为「先登记再说」，直接红；
3. 条目不虚指：引用的用例文件必须真实存在；同一 (文件, 平台) 不得重复登记；
   环境红台账与 flaky 台账不得对同一 (文件, freebsd) 双登记；
4. 口径不串门：环境红台账只收平台能力差异，flaky 台账只收「隔离恒绿 + 全量偶发红」。
   已知的确定性挂死用例（T-0524 实测，见 flaky_registry.txt 复核节）不得登记为 flaky
   —— 那是真缺陷，登记即「提前转绿」。

解析口径刻意与 tests/test_回归.py、tests/ci_judge_env_reds.py 保持一致：
制表符分隔、# 开头与空行为注释。日期允许落在条目自身或它所在段落的标题注释里
（历史条目按段落记账，例如 F-03~F-09 统一记在「T-0178 F 路登记（2026-10-28）」节下）。
"""
import importlib.util
import os
import re

TESTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(TESTS_DIR)
EXAMPLES = os.path.join(REPO, "examples")
ENV_LEDGER = os.path.join(TESTS_DIR, "ci_environment_reds.txt")
FLAKY_REGISTRY = os.path.join(TESTS_DIR, "flaky_registry.txt")

DATE_RE = re.compile(r"20\d{2}-\d{2}-\d{2}")
# 测量依据：显式命令，或等价的测量动作词（历史条目按动作记账）
EVIDENCE_CMD_RE = re.compile(
    r"(运行\.py|pytest|python3?|单跑|直跑|隔离|串行全量|全量|复跑|xdist)"
)
# 结果摘要：必须能看出「测出了什么」
EVIDENCE_RESULT_RE = re.compile(r"(rc\s*[=:]\s*\d|rc=|通过|恒绿|passed|全绿|绿)")

PLATFORMS = {"windows", "freebsd", "linux"}

# T-0524 实测为「断言全过但进程不退出」的确定性挂死（非并发假红、非环境差异）。
# 根因：src/web服务器.light 的 排队唤醒循环（T-0490 引入）无停止标志，
#       Web服务端.停止() 只停服务端不停唤醒线程 ⇒ 进程退不出 ⇒ 全量超时判红。
# 证据链见 tests/flaky_registry.txt 的「T-0524 复核」节。
DETERMINISTIC_HANG_CASES = {
    "test_R41_真实IO端到端.light",
    "test_R41_真实网络IO.light",
    "test_流式推流E2E.light",
    "test_web路由.light",
    "test_会话模型选择.light",
}


def _parse(path):
    """按段落解析台账。

    返回 [(section_title, fields)]：section_title 为条目上方最近的「带日期注释」行，
    供历史条目继承取证日期；fields 为制表符拆分后的字段列表。
    """
    rows = []
    section = ""
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            s = line.strip()
            if not s:
                continue
            if s.startswith("#"):
                if DATE_RE.search(s):
                    section = s
                continue
            fields = [p.strip() for p in line.split("\t")]
            if len(fields) < 2 or not fields[1]:
                continue
            rows.append((section, fields))
    return rows


def _text(fields):
    return " ".join(fields[2:])


def _has_evidence(section, fields):
    """条目自身或所属段落里，同时具备 日期 / 测量依据 / 结果摘要。"""
    blob = section + " " + _text(fields)
    return bool(
        DATE_RE.search(blob)
        and EVIDENCE_CMD_RE.search(blob)
        and EVIDENCE_RESULT_RE.search(blob)
    )


def _target_file(name):
    """把台账里的「文件名」还原成仓内相对路径；返回 None 表示无法判定。"""
    bare = name.split("::")[0].strip().replace("\\", "/")
    if not bare:
        return None
    if "/" in bare or bare.startswith("tests"):
        return bare
    return "examples/" + bare


def _load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── 1. 环境红台账 ─────────────────────────────────────────────────────────
def test_环境红台账字段与取证齐全():
    rows = _parse(ENV_LEDGER)
    assert rows, "环境红台账不能为空（空台账等于放弃环境差异豁免）"
    problems = []
    for section, f in rows:
        while len(f) < 5:
            f.append("")
        eid, fname, category, flaky, note = f[0], f[1], f[2], f[3], " ".join(f[4:])
        if not re.fullmatch(r"E-\d{2}", eid):
            problems.append(f"{eid or '?'} 编号格式应为 E-xx")
        if not category:
            problems.append(f"{eid} 缺类别")
        if flaky not in ("0", "1"):
            problems.append(f"{eid} flaky 列应为 0/1，实际 {flaky!r}")
        if not note:
            problems.append(f"{eid} 缺现象/说明")
        if not _has_evidence(section, f):
            problems.append(f"{eid} 缺取证（日期 + 测量依据 + 结果摘要）")
    assert not problems, "环境红台账不合口径:\n  - " + "\n  - ".join(problems)


def test_环境红台账编号唯一():
    rows = _parse(ENV_LEDGER)
    ids = [f[0] for _, f in rows]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    assert not dup, f"环境红台账编号重复: {dup}"


# ── 2. flaky 台账 ─────────────────────────────────────────────────────────
def test_flaky台账字段与取证齐全():
    rows = _parse(FLAKY_REGISTRY)
    assert rows, "flaky 台账不能为空（至少含已登记的环境偶发条目）"
    problems = []
    for section, f in rows:
        while len(f) < 5:
            f.append("")
        fid, fname, plat, note, action = f[0], f[1], f[2], f[3], " ".join(f[4:])
        if not re.fullmatch(r"F-\d{2}", fid):
            problems.append(f"{fid or '?'} 编号格式应为 F-xx")
        if plat not in PLATFORMS:
            problems.append(f"{fid} 平台取值非法: {plat!r}（应为 windows/freebsd/linux）")
        if not note:
            problems.append(f"{fid} 缺现象/取证记录")
        if not action:
            problems.append(f"{fid} 缺处置")
        if not _has_evidence(section, f):
            problems.append(f"{fid} 缺取证（日期 + 测量依据 + 结果摘要）")
    assert not problems, "flaky 台账不合口径:\n  - " + "\n  - ".join(problems)


def test_flaky台账编号唯一且同用例子平台不重复():
    rows = _parse(FLAKY_REGISTRY)
    ids = [f[0] for _, f in rows]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    assert not dup, f"flaky 台账编号重复: {dup}"
    keys = [(f[1], f[2]) for _, f in rows]
    dup_keys = sorted({k for k in keys if keys.count(k) > 1})
    assert not dup_keys, f"同一用例同一平台重复登记: {dup_keys}"


# ── 3. 条目不虚指、不双登记 ────────────────────────────────────────────────
def test_台账引用文件真实存在():
    missing = []
    for path in (ENV_LEDGER, FLAKY_REGISTRY):
        for _, f in _parse(path):
            rel = _target_file(f[1])
            if rel is None:
                continue
            if not os.path.exists(os.path.join(REPO, rel)):
                missing.append(f"{os.path.basename(path)}: {f[0]} → {f[1]}（找不到 {rel}）")
    assert not missing, "台账引用了不存在的用例:\n  - " + "\n  - ".join(missing)


def test_环境红与flaky不得双登记():
    env_files = {f[1] for _, f in _parse(ENV_LEDGER)}
    flaky_fbsd = {f[1] for _, f in _parse(FLAKY_REGISTRY) if f[2] == "freebsd"}
    overlap = sorted(env_files & flaky_fbsd)
    assert not overlap, (
        "同一用例同时进了环境红台账和 freebsd flaky 台账，口径串门: " + ", ".join(overlap)
    )


# ── 4. 口径不串门：确定性挂死不得当 flaky ──────────────────────────────────
def test_确定性挂死用例不得登记为flaky():
    """T-0524 复核：这 5 条是「断言全过、进程退不出」的真缺陷，不是并发假红。

    若将来 src/web服务器.light 的唤醒线程被加上停止标志（进程能正常退出）后，
    确实出现了「隔离恒绿 + 全量偶发红」，再按取证口径登记，并同步更新本条判据。
    """
    registered = {f[1] for _, f in _parse(FLAKY_REGISTRY)}
    leaked = sorted(DETERMINISTIC_HANG_CASES & registered)
    assert not leaked, (
        "确定性挂死用例被登记为 flaky（等于把真缺陷提前转绿）: "
        + ", ".join(leaked)
        + "；先修 src/web服务器.light 的退出路径，再谈豁免"
    )


# ── 5. 解析口径与既有判据/判据脚本一致 ────────────────────────────────────
def test_三处解析口径一致():
    """台账是同一份机器可解析文件，三处读者必须看到同一集合。"""
    judge = _load_module(os.path.join(TESTS_DIR, "ci_judge_env_reds.py"), "ci_judge_env_reds_t0524")
    judge_files, judge_meta = judge.load_ledger(ENV_LEDGER)
    mine = {f[1] for _, f in _parse(ENV_LEDGER)}
    assert judge_files == mine, (
        f"ci_judge_env_reds.load_ledger 与环境红台账解析不一致: "
        f"仅脚本={sorted(judge_files - mine)} 仅本判据={sorted(mine - judge_files)}"
    )
    assert len(judge_meta) == len(mine), "环境红台账条目数与判据脚本解析条数不一致"

    regression = _load_module(os.path.join(TESTS_DIR, "test_回归.py"), "test_regression_t0524")
    assert regression.ENV_RED_LEDGER == mine, "test_回归._load_env_red_ledger 解析结果不一致"
    assert all(len(f) >= 4 for _, f in _parse(FLAKY_REGISTRY)), (
        "flaky 台账存在少于 4 字段的条目，test_回归._load_flaky_registry 会静默跳过它"
    )
