#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""编辑日志.py —— 「编辑前后」日志 schema v1（JSONL，一行一条）。

为什么存在
----------
`light ai check` 的报错归档里 `source_hash` 是对**出错那一刻**的源码算的：
代码没改则现跑仍失败，代码改好后 hash 变了又永远关联不上那条记录。
所以 LightPrism 的修复样本（`<V:ERR=…>` → `<V:PASS>` 配对）只能来自
**记录了编辑动作 + 编辑前后各一次 check** 的日志。格式定义见
`docs/编辑日志格式.md`。

本文件是纯标准库、单文件可跑的写入 / 校验 / 回放实现，也被
`scripts/安全替换.py` 动态加载后调用（构建记录、append）。

用法：
    python scripts/编辑日志.py --self-test
    python scripts/编辑日志.py validate <path>
    python scripts/编辑日志.py dump --json [--outcome fixed] [--since ...] [--until ...]
    python scripts/编辑日志.py record <json-file|->

不变量（写死，不许绕过）：
    * `outcome` 只能由 check_before / check_after 推导，人手填的不算数；
    * `file` 只落 repo 相对路径，绝对路径进不了日志；
    * append-only：同一 (file_hash_before, file_hash_after, ts) 不写第二次；
    * 校验遇到非法行报行号，绝不静默跳过。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import secrets
import socket
import sys
import tempfile
from pathlib import Path

SCHEMA_VERSION = 1
EDIT_KINDS = ("FR", "RW", "PATCH")
OUTCOMES = ("fixed", "still_failing", "regressed", "unknown")
MAX_DIFF_CHARS = 20000  # 超过就截断，并在 diff.truncated 标记
DEDUP_KEYS = ("file_hash_before", "file_hash_after", "ts")

# 必填字段：缺任何一个都是非法记录（「语义不许少」）。
STR_FIELDS = (
    "event_id", "ts", "repo", "file", "file_hash_before", "file_hash_after",
    "edit_kind", "outcome", "light_version", "backend",
)
NULLABLE_STR_FIELDS = ("session_id", "task_id", "agent")
NULLABLE_OBJ_FIELDS = ("check_before", "check_after")
HASH_RE = re.compile(r"^[0-9a-f]{16}$")
# 绝对路径特征：Windows 盘符 / UNC / POSIX 根目录下的典型家目录与临时目录
_PATH_RE = re.compile(
    r"(?<![\w/\\])(?:[A-Za-z]:[\\/][^\s\"'<>|]+|\\\\[^\s\"'<>|]+"
    r"|/(?:home|Users|tmp|usr|var|opt|root|mnt)[^\s\"'<>|]*)"
)


# --------------------------------------------------------------------------
# 基础工具
# --------------------------------------------------------------------------
def _setup_stdout() -> None:
    """Windows 控制台默认 cp936 时中文输出会炸；尽力切成 UTF-8。"""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except (AttributeError, OSError, ValueError):
        pass


def normalize_newlines(text: str) -> str:
    """与 light 报错归档同口径：换行归一化。"""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def file_hash(text: str) -> str:
    """换行归一化后 sha256(...)[:16]，与 light 归档同口径。"""
    return hashlib.sha256(normalize_newlines(text).encode("utf-8")).hexdigest()[:16]


def now_iso() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def make_event_id() -> str:
    """<hostname>-<microsecond>-<rand>，多节点合流时用于去重。"""
    return "%s-%d-%s" % (
        socket.gethostname(), time_microseconds(), secrets.token_hex(4))


def time_microseconds() -> int:
    import time
    return int(time.time() * 1_000_000)


def mask_paths(text: str) -> str:
    """diff / 诊断消息里的本机绝对路径打码，避免泄露目录结构。"""
    if not text:
        return text
    out = _PATH_RE.sub("<PATH>", text)
    for base in (Path.home(), Path(tempfile.gettempdir())):
        for cand in {str(base), str(base).replace("\\", "/"),
                     os.path.normpath(str(base))}:
            if not cand:
                continue
            out = out.replace(cand + "\\", "<HOST_PATH>/")
            out = out.replace(cand + "/", "<HOST_PATH>/")
    return out


def relative_file(path: str | os.PathLike, repo_root: str | os.PathLike | None = None) -> str:
    """把任意路径收敛成 repo 相对路径；落在 repo 外时只保留文件名。

    绝不把 `/tmp/xxx` 或 `C:\\Users\\...` 这类绝对路径写进日志。
    """
    p = Path(path)
    if repo_root:
        try:
            rel = p.resolve().relative_to(Path(repo_root).resolve())
            if ".." not in rel.parts:
                return rel.as_posix()
        except (ValueError, OSError):
            pass
    return p.name


def is_relative_file(value: str) -> bool:
    """schema 层的相对路径判据：`/` 开头、盘符、UNC、`..` 穿越一律拒绝。"""
    if not value or not isinstance(value, str):
        return False
    if value.startswith(("/", "\\")):
        return False
    if re.match(r"^[A-Za-z]:[\\/]", value):
        return False
    parts = re.split(r"[\\/]", value)
    if ".." in parts:
        return False
    return True


# --------------------------------------------------------------------------
# outcome：唯一推导入口
# --------------------------------------------------------------------------
def derive_outcome(check_before: dict | None, check_after: dict | None) -> str:
    """由前后 check 推导 outcome。任一缺失 / ok 非 bool → unknown。

        false → true   fixed
        false → false  still_failing
        true  → false  regressed
        true  → true   unknown（既没坏也没修，不算修复样本）
    """
    if not isinstance(check_before, dict) or not isinstance(check_after, dict):
        return "unknown"
    b, a = check_before.get("ok"), check_after.get("ok")
    if not isinstance(b, bool) or not isinstance(a, bool):
        return "unknown"
    if not b and a:
        return "fixed"
    if not b and not a:
        return "still_failing"
    if b and not a:
        return "regressed"
    return "unknown"


def parse_check_json(stdout: str, returncode: int) -> dict | None:
    """解析 `light ai check --run --json --no-corpus` 的输出。

    取 stdout 中最后一个合法的结果 JSON，再取**首条 error 级诊断**。
    退出码 2（用法/文件错误）或解析不出结果时返回 None —— 不许猜。
    """
    if returncode not in (0, 1):
        return None
    data = None
    for line in reversed((stdout or "").splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except (ValueError, TypeError):
            continue
        if isinstance(obj, dict) and "ok" in obj and "diagnostics" in obj:
            data = obj
            break
    if data is None:
        return None
    first = None
    for d in data.get("diagnostics") or []:
        if isinstance(d, dict) and d.get("severity") == "error":
            first = d
            break
    return {
        "ok": bool(data.get("ok")),
        "code": first.get("code") if first else None,
        "severity": first.get("severity") if first else None,
        "stage": first.get("stage") if first else None,
        "message": mask_paths(str(first.get("message"))) if first and first.get("message") else None,
    }


# --------------------------------------------------------------------------
# schema 校验
# --------------------------------------------------------------------------
def validate_record(rec: object) -> list[str]:
    """返回错误列表（空 = 合法）。每条错误都带字段名，便于报行号时定位。"""
    if not isinstance(rec, dict):
        return ["记录必须是 JSON 对象"]
    errs: list[str] = []
    required = (("schema_version",), STR_FIELDS, NULLABLE_STR_FIELDS,
                NULLABLE_OBJ_FIELDS, ("diff",))
    for group in required:
        for key in group:
            if key not in rec:
                errs.append("缺少必填字段: %s" % key)
    if errs:
        return errs  # 缺字段时后续类型检查没有意义

    if type(rec["schema_version"]) is not int or rec["schema_version"] != SCHEMA_VERSION:
        errs.append("schema_version 必须是整数 %d" % SCHEMA_VERSION)
    for key in STR_FIELDS:
        if not isinstance(rec[key], str):
            errs.append("%s 必须是字符串" % key)
    for key in NULLABLE_STR_FIELDS:
        if rec[key] is not None and not isinstance(rec[key], str):
            errs.append("%s 必须是字符串或 null" % key)
    for key in NULLABLE_OBJ_FIELDS:
        v = rec[key]
        if v is not None and not isinstance(v, dict):
            errs.append("%s 必须是对象或 null" % key)

    if isinstance(rec["ts"], str):
        try:
            parsed = _dt.datetime.fromisoformat(rec["ts"])
        except ValueError:
            errs.append("ts 不是合法 ISO8601: %r" % rec["ts"])
        else:
            if parsed.tzinfo is None:
                errs.append("ts 必须带时区")
    for key in ("file_hash_before", "file_hash_after"):
        if isinstance(rec[key], str) and not HASH_RE.match(rec[key]):
            errs.append("%s 必须是 sha256 前 16 位小写十六进制" % key)
    if isinstance(rec["file"], str) and not is_relative_file(rec["file"]):
        errs.append("file 必须是 repo 相对路径（拒绝绝对路径 / .. 穿越）: %r" % rec["file"])
    if rec["edit_kind"] not in EDIT_KINDS:
        errs.append("edit_kind 只接受 %s: %r" % ("/".join(EDIT_KINDS), rec["edit_kind"]))
    if rec["outcome"] not in OUTCOMES:
        errs.append("outcome 只接受 %s: %r" % ("/".join(OUTCOMES), rec["outcome"]))
    derived = derive_outcome(rec["check_before"], rec["check_after"])
    if rec["outcome"] != derived:
        errs.append("outcome 与 check 推导不一致: 声明 %r，推导 %r（不许手填）"
                    % (rec["outcome"], derived))

    diff = rec["diff"]
    if not isinstance(diff, dict):
        errs.append("diff 必须是对象")
    else:
        has_unified = "unified" in diff
        has_pair = "before" in diff and "after" in diff
        if not (has_unified or has_pair):
            errs.append("diff 必须含 unified，或同时含 before 与 after")
        for key in ("unified", "before", "after"):
            if key in diff and not isinstance(diff[key], str):
                errs.append("diff.%s 必须是字符串" % key)
        if "truncated" in diff and not isinstance(diff["truncated"], bool):
            errs.append("diff.truncated 必须是布尔值")

    for key in NULLABLE_OBJ_FIELDS:
        chk = rec[key]
        if not isinstance(chk, dict):
            continue
        if not isinstance(chk.get("ok"), bool):
            errs.append("%s.ok 必须是布尔值" % key)
        for field in ("code", "severity", "stage", "message"):
            if field in chk and chk[field] is not None and not isinstance(chk[field], str):
                errs.append("%s.%s 必须是字符串或 null" % (key, field))
    return errs


# --------------------------------------------------------------------------
# 构建记录
# --------------------------------------------------------------------------
def build_record(*, repo: str, file: str, edit_kind: str,
                 before_text: str | None = None, after_text: str | None = None,
                 file_hash_before: str | None = None,
                 file_hash_after: str | None = None,
                 diff: dict | None = None,
                 check_before: dict | None = None, check_after: dict | None = None,
                 ts: str | None = None, event_id: str | None = None,
                 session_id: str | None = None, task_id: str | None = None,
                 agent: str | None = None, light_version: str = "",
                 backend: str = "", **extra) -> dict:
    """组装一条记录并校验。outcome 恒由 check 推导，忽略传入的 outcome。

    `before_text` / `after_text` 给定时自动算 hash 并生成 `{before, after}` diff；
    超长时截断并标 `truncated`。两者都给定时不必再传 diff / hash。
    """
    hb = file_hash_before if file_hash_before is not None else (
        file_hash(before_text) if before_text is not None else None)
    ha = file_hash_after if file_hash_after is not None else (
        file_hash(after_text) if after_text is not None else None)
    if diff is None and before_text is not None and after_text is not None:
        b = mask_paths(normalize_newlines(before_text))
        a = mask_paths(normalize_newlines(after_text))
        truncated = len(b) > MAX_DIFF_CHARS or len(a) > MAX_DIFF_CHARS
        diff = {"before": b[:MAX_DIFF_CHARS],
                "after": a[:MAX_DIFF_CHARS],
                "truncated": truncated}
    if diff is None:
        diff = {"unified": ""}
    rec = {
        "schema_version": SCHEMA_VERSION,
        "event_id": event_id or make_event_id(),
        "ts": ts or now_iso(),
        "session_id": session_id,
        "task_id": task_id,
        "agent": agent,
        "repo": repo,
        "file": file,
        "file_hash_before": hb,
        "file_hash_after": ha,
        "edit_kind": edit_kind,
        "diff": diff,
        "check_before": check_before,
        "check_after": check_after,
        "outcome": derive_outcome(check_before, check_after),
        "light_version": light_version,
        "backend": backend,
    }
    rec.update(extra)
    errs = validate_record(rec)
    if errs:
        raise ValueError("非法编辑日志记录: " + "; ".join(errs))
    return rec


# --------------------------------------------------------------------------
# 写入 / 校验 / 回放
# --------------------------------------------------------------------------
def log_dir() -> Path:
    d = os.environ.get("LIGHTHARNESS_EDIT_LOG_DIR")
    return Path(d) if d else Path.home() / ".lightharness" / "edits"


def log_path(ts: str | None = None) -> Path:
    month = (ts or now_iso())[:7]
    return log_dir() / ("%s.jsonl" % month)


def _dedup_key(rec: dict) -> tuple:
    return tuple(rec.get(k) for k in DEDUP_KEYS)


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def record(rec: dict, path: str | os.PathLike | None = None, *,
           check: bool = True) -> dict | None:
    """append 一条记录；重复键返回 None（不写第二次）。

    `check=False` 仅供内部自测构造非法行使用；正常路径永远先校验。
    """
    if check:
        errs = validate_record(rec)
        if errs:
            raise ValueError("拒绝写入非法记录: " + "; ".join(errs))
    p = Path(path) if path else log_path(rec.get("ts"))
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = _read_lines(p)
    key = _dedup_key(rec)
    for no, line in enumerate(lines, 1):
        if not line.strip():
            raise ValueError("日志 %s 第 %d 行为空，拒绝追加" % (p, no))
        try:
            old = json.loads(line)
        except ValueError as exc:
            raise ValueError("日志 %s 第 %d 行 JSON 非法，拒绝追加: %s" % (p, no, exc))
        if not isinstance(old, dict):
            raise ValueError("日志 %s 第 %d 行不是对象，拒绝追加" % (p, no))
        if _dedup_key(old) == key:
            return None  # append-only：不写第二次
    with open(p, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
        f.flush()
    return rec


def validate(path: str | os.PathLike) -> tuple[int, list[str]]:
    """逐行校验，返回 (合法行数, 错误列表)。非法行一律带行号。"""
    p = Path(path)
    errs: list[str] = []
    good = 0
    if not p.exists():
        return 0, ["文件不存在: %s" % p]
    for no, line in enumerate(_read_lines(p), 1):
        if not line.strip():
            errs.append("第 %d 行: 空行（JSONL 一行一条）" % no)
            continue
        try:
            rec = json.loads(line)
        except ValueError as exc:
            errs.append("第 %d 行: JSON 解析失败: %s" % (no, exc))
            continue
        sub = validate_record(rec)
        if sub:
            errs.extend("第 %d 行: %s" % (no, e) for e in sub)
        else:
            good += 1
    return good, errs


def iter_paths(path: str | os.PathLike | None = None) -> list[Path]:
    if path:
        return [Path(path)]
    d = log_dir()
    if not d.is_dir():
        return []
    return sorted(d.glob("*.jsonl"))


def dump(path: str | os.PathLike | None = None, *, outcome: str | None = None,
         since: str | None = None, until: str | None = None,
         limit: int | None = None) -> list[dict]:
    """按 outcome / 时间过滤回放；非法行抛 ValueError（不静默跳过）。"""
    since_dt = _dt.datetime.fromisoformat(since) if since else None
    until_dt = _dt.datetime.fromisoformat(until) if until else None
    out: list[dict] = []
    for p in iter_paths(path):
        if not p.exists():
            raise ValueError("文件不存在: %s" % p)
        good, errs = validate(p)
        if errs:
            raise ValueError("%s 含非法行，拒绝回放: %s" % (p, "; ".join(errs[:5])))
        for line in _read_lines(p):
            if not line.strip():
                continue
            rec = json.loads(line)
            if outcome and rec.get("outcome") != outcome:
                continue
            ts = rec.get("ts")
            if (since_dt or until_dt) and isinstance(ts, str):
                cur = _dt.datetime.fromisoformat(ts)
                if since_dt and cur < since_dt:
                    continue
                if until_dt and cur > until_dt:
                    continue
            out.append(rec)
    out.sort(key=lambda r: (r.get("ts") or "", r.get("event_id") or ""))
    if limit is not None:
        out = out[:limit]
    return out


# --------------------------------------------------------------------------
# 自测（不依赖外部文件）
# --------------------------------------------------------------------------
def self_test() -> int:
    import contextlib
    import io

    checks: list[tuple[str, bool]] = []

    def chk(name: str, cond: bool) -> None:
        checks.append((name, bool(cond)))

    base_checks = {
        "fixed": ({"ok": False, "code": "L3001", "severity": "error",
                   "stage": "运行", "message": "索引错误"},
                  {"ok": True, "code": None, "severity": None,
                   "stage": None, "message": None}),
        "still_failing": ({"ok": False, "code": "L3001", "severity": "error",
                           "stage": "运行", "message": "索引错误"},
                          {"ok": False, "code": "L3001", "severity": "error",
                           "stage": "运行", "message": "索引错误"}),
        "regressed": ({"ok": True, "code": None, "severity": None,
                       "stage": None, "message": None},
                      {"ok": False, "code": "L0000", "severity": "error",
                       "stage": "语法检查", "message": "语法错误"}),
        "unknown": (None, None),
    }
    for expected, (b, a) in base_checks.items():
        chk("outcome 推导: %s" % expected, derive_outcome(b, a) == expected)

    old_env = os.environ.get("LIGHTHARNESS_EDIT_LOG_DIR")
    with tempfile.TemporaryDirectory(prefix="editlog-selftest-") as tmp:
        os.environ["LIGHTHARNESS_EDIT_LOG_DIR"] = tmp
        try:
            p = log_path()
            fixed_ts = "2026-11-12T17:30:00+08:00"
            for name, (b, a) in base_checks.items():
                rec = build_record(
                    repo="lightharness", file="examples/%s.light" % name,
                    edit_kind="PATCH", before_text="设 甲 为 [1, 2]\n打印(甲[9])\n",
                    after_text="设 甲 为 [1, 2]\n打印(甲[0])\n",
                    check_before=b, check_after=a,
                    ts="2026-11-12T17:30:0%d+08:00" % list(base_checks).index(name)
                    if name != "fixed" else fixed_ts,
                    light_version="0.9.0", backend="cpython")
                chk("schema 校验: %s" % name, validate_record(rec) == [])
                chk("写入: %s" % name, record(rec) is not None)
            chk("4 条 fixture 全部落盘", len(_read_lines(p)) == 4)
            # 去重：完全相同的 (hash_before, hash_after, ts) 不写第二次
            dup = build_record(
                repo="lightharness", file="examples/fixed.light", edit_kind="PATCH",
                before_text="设 甲 为 [1, 2]\n打印(甲[9])\n",
                after_text="设 甲 为 [1, 2]\n打印(甲[0])\n",
                check_before=base_checks["fixed"][0],
                check_after=base_checks["fixed"][1], ts=fixed_ts)
            chk("重复 append 被去重", record(dup) is None)
            chk("去重后仍 4 行", len(_read_lines(p)) == 4)
            good, errs = validate(p)
            chk("validate 全绿", good == 4 and errs == [])
            rows = dump(path=p, outcome="fixed")
            chk("dump 过滤 fixed", len(rows) == 1 and rows[0]["outcome"] == "fixed")
            # 非法行必须报行号
            with open(p, "a", encoding="utf-8", newline="\n") as f:
                f.write('{"schema_version": 1}\n')
            _, errs2 = validate(p)
            chk("非法行报行号", any("第 5 行" in e for e in errs2))
            # schema 拒绝对路径 / edit_kind / 手填 outcome
            bad = build_record(repo="lightharness", file="x.light", edit_kind="PATCH",
                               before_text="a", after_text="b",
                               check_before=base_checks["fixed"][0],
                               check_after=base_checks["fixed"][1])
            bad["file"] = "/tmp/x.light"
            chk("绝对路径被拒绝", any("file" in e for e in validate_record(bad)))
            bad["file"] = "C:/tmp/x.light"
            chk("盘符路径被拒绝", any("file" in e for e in validate_record(bad)))
            bad["file"] = "x.light"
            bad.pop("file_hash_after")
            chk("缺必填字段报错", any("缺少必填字段" in e for e in validate_record(bad)))
            bad = build_record(repo="lightharness", file="x.light", edit_kind="PATCH",
                               before_text="a", after_text="b")
            bad["edit_kind"] = "FIX"
            chk("edit_kind 白名单", any("edit_kind" in e for e in validate_record(bad)))
            bad["edit_kind"] = "PATCH"
            bad["outcome"] = "fixed"  # 手填
            chk("手填 outcome 被拒绝", any("不许手填" in e for e in validate_record(bad)))
            # hash 口径：与 light 归档同口径（换行归一化）
            chk("hash 换行归一化", file_hash("a\r\nb\n") == file_hash("a\nb\n"))
            chk("hash 16 位", len(file_hash("a\nb\n")) == 16)
            # diff 截断标记
            big = build_record(repo="lightharness", file="x.light", edit_kind="RW",
                               before_text="a" * (MAX_DIFF_CHARS + 10), after_text="b")
            chk("超大 diff 标 truncated", big["diff"]["truncated"] is True)
            chk("相对路径工具不泄露目录",
                relative_file("C:/Users/me/secret/x.light") == "x.light")
            chk("绝对路径打码", "<PATH>" in mask_paths("C:/Users/me/secret/x.light"))
        finally:
            if old_env is None:
                os.environ.pop("LIGHTHARNESS_EDIT_LOG_DIR", None)
            else:
                os.environ["LIGHTHARNESS_EDIT_LOG_DIR"] = old_env

    for name, good in checks:
        print("  [%s] %s" % ("通过" if good else "失败", name))
    failed = [n for n, g in checks if not g]
    print("自测结果:", "全部通过（%d 项）" % len(checks) if not failed
          else "存在失败（%d 项）: %s" % (len(failed), ", ".join(failed)))
    return 0 if not failed else 1


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def _cli_record(args) -> int:
    raw = sys.stdin.read() if args.source == "-" else Path(args.source).read_text(encoding="utf-8")
    blocks = []
    try:
        obj = json.loads(raw)
        blocks = obj if isinstance(obj, list) else [obj]
    except ValueError:
        blocks = []
        for no, line in enumerate(raw.splitlines(), 1):
            if not line.strip():
                continue
            try:
                blocks.append(json.loads(line))
            except ValueError as exc:
                print("第 %d 行 JSON 解析失败: %s" % (no, exc), file=sys.stderr)
                return 1
    written = 0
    for rec in blocks:
        if not isinstance(rec, dict):
            print("记录必须是 JSON 对象", file=sys.stderr)
            return 1
        # outcome 不许人填：一律按 check 重算
        rec["outcome"] = derive_outcome(rec.get("check_before"), rec.get("check_after"))
        errs = validate_record(rec)
        if errs:
            print("非法记录: " + "; ".join(errs), file=sys.stderr)
            return 1
        r = record(rec, path=args.path)
        if r is None:
            print("跳过（去重键已存在）: %s" % rec.get("event_id"))
        else:
            written += 1
            print("已写入 %s: %s" % (args.path or log_path(rec.get("ts")), rec["event_id"]))
    print("写入 %d 条" % written)
    return 0


def main(argv=None) -> int:
    _setup_stdout()
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--self-test" in argv:
        return self_test()

    p = argparse.ArgumentParser(description="「编辑前后」日志 schema v1：写入 / 校验 / 回放")
    p.add_argument("--self-test", action="store_true", help="内置自测，不依赖外部文件")
    sub = p.add_subparsers(dest="cmd")

    v = sub.add_parser("validate", help="逐行校验 schema，非法行报行号")
    v.add_argument("path")

    d = sub.add_parser("dump", help="回放（默认 JSONL，一行一条）")
    d.add_argument("--json", action="store_true", help="以 JSON 输出（JSONL，每行一条记录）")
    d.add_argument("--array", action="store_true", help="输出单个 JSON 数组")
    d.add_argument("--path", help="指定日志文件（默认读日志目录下所有 .jsonl）")
    d.add_argument("--outcome", choices=OUTCOMES, help="按 outcome 过滤")
    d.add_argument("--since", help="起始时间（ISO8601，含）")
    d.add_argument("--until", help="结束时间（ISO8601，含）")
    d.add_argument("--limit", type=int, help="最多输出 N 条")

    r = sub.add_parser("record", help="从 JSON / JSONL 追加记录（outcome 仍由 check 推导）")
    r.add_argument("source", help="JSON 文件路径，或 - 表示 stdin")
    r.add_argument("--path", help="指定日志文件（默认按月分文件）")

    args = p.parse_args(argv)
    if args.cmd == "validate":
        good, errs = validate(args.path)
        for e in errs:
            print(e, file=sys.stderr)
        print("校验完成: %d 条合法，%d 条非法" % (good, len(errs)))
        return 1 if errs else 0
    if args.cmd == "dump":
        try:
            rows = dump(path=args.path, outcome=args.outcome, since=args.since,
                        until=args.until, limit=args.limit)
        except ValueError as exc:
            print("回放失败: %s" % exc, file=sys.stderr)
            return 1
        if args.array:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            for rec in rows:
                print(json.dumps(rec, ensure_ascii=False, sort_keys=True))
        return 0
    if args.cmd == "record":
        return _cli_record(args)
    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
