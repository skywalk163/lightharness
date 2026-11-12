# -*- coding: utf-8 -*-
"""「编辑前后」日志 schema v1 的回归测试（纯标准库 + pytest）。

覆盖任务卡要求的五项：必填字段缺失、outcome 四态推导、重复 append 去重、
file 必须相对路径、edit_kind 白名单；另加校验报错行号、dump 过滤、
真实 checker 输出解析、安全替换钩子的「不猜」行为与原自测不回归。
"""
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
EDIT_LOG_PY = SCRIPTS / "编辑日志.py"
REPLACE_PY = SCRIPTS / "安全替换.py"
BAD_TEXT = "设 甲 为 [1, 2]\n打印(甲[9])\n"
GOOD_TEXT = "设 甲 为 [1, 2]\n打印(甲[0])\n"
FAIL = {"ok": False, "code": "L3001", "severity": "error",
        "stage": "运行", "message": "索引错误 列表索引越界"}
PASS = {"ok": True, "code": None, "severity": None, "stage": None, "message": None}


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader, "加载失败: %s" % path
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def el():
    return _load("lh_edit_log_for_tests", EDIT_LOG_PY)


@pytest.fixture(scope="module")
def sr():
    return _load("lh_safe_replace_for_tests", REPLACE_PY)


def _rec(el, **kw):
    base = dict(repo="lightharness", file="examples/x.light", edit_kind="PATCH",
                before_text=BAD_TEXT, after_text=GOOD_TEXT,
                check_before=None, check_after=None,
                ts="2026-11-12T17:30:00+08:00")
    base.update(kw)
    return el.build_record(**base)


# --------------------------------------------------------------------------
# 1. schema 必填字段
# --------------------------------------------------------------------------
def test_缺任一必填字段都要报错(el):
    rec = _rec(el)
    for key in ("schema_version", "event_id", "ts", "session_id", "task_id",
                "agent", "repo", "file", "file_hash_before", "file_hash_after",
                "edit_kind", "diff", "check_before", "check_after", "outcome",
                "light_version", "backend"):
        broken = dict(rec)
        broken.pop(key)
        errs = el.validate_record(broken)
        assert any("缺少必填字段: %s" % key in e for e in errs), key


def test_合法记录零错误且hash与light归档同口径(el):
    rec = _rec(el)
    assert el.validate_record(rec) == []
    assert rec["file_hash_before"] == "3f8e1a3acc644768"
    assert rec["file_hash_after"] == "1284d1e5c731b464"
    assert el.file_hash("a\r\nb\n") == el.file_hash("a\nb\n")


def test_手填outcome被拒绝(el):
    rec = _rec(el)                       # check 都是 null → unknown
    assert rec["outcome"] == "unknown"
    rec["outcome"] = "fixed"
    assert any("不许手填" in e for e in el.validate_record(rec))


def test_check的ok必须是布尔值(el):
    rec = _rec(el, check_before=FAIL, check_after=PASS)
    rec["check_before"] = {"ok": "false"}
    assert any("ok 必须是布尔值" in e for e in el.validate_record(rec))


def test_diff结构必须合法(el):
    rec = _rec(el)
    rec["diff"] = {}
    assert any("diff" in e for e in el.validate_record(rec))
    rec["diff"] = {"before": "a", "after": "b", "truncated": "yes"}
    assert any("truncated" in e for e in el.validate_record(rec))


def test_ts必须带时区(el):
    rec = _rec(el)
    rec["ts"] = "2026-11-12T17:30:00"
    assert any("ts 必须带时区" in e for e in el.validate_record(rec))


# --------------------------------------------------------------------------
# 2. outcome 四种推导
# --------------------------------------------------------------------------
@pytest.mark.parametrize("before,after,expected", [
    (FAIL, PASS, "fixed"),
    (FAIL, FAIL, "still_failing"),
    (PASS, FAIL, "regressed"),
    (None, None, "unknown"),
    (FAIL, None, "unknown"),
    (PASS, PASS, "unknown"),
])
def test_outcome推导(el, before, after, expected):
    assert el.derive_outcome(before, after) == expected
    rec = _rec(el, check_before=before, check_after=after)
    assert rec["outcome"] == expected
    assert el.validate_record(rec) == []


def test_outcome只接受四态枚举(el):
    rec = _rec(el, check_before=FAIL, check_after=PASS)
    rec["outcome"] = "pass_now"
    assert any("outcome" in e for e in el.validate_record(rec))


# --------------------------------------------------------------------------
# 3. append-only 去重
# --------------------------------------------------------------------------
def test_重复append被去重且不同ts不去重(el, tmp_path, monkeypatch):
    monkeypatch.setenv("LIGHTHARNESS_EDIT_LOG_DIR", str(tmp_path))
    p = tmp_path / "2026-11.jsonl"
    rec = _rec(el)
    assert el.record(rec) is not None
    assert el.record(rec) is None                 # 同一 (hash_before, hash_after, ts)
    assert len(p.read_text(encoding="utf-8").splitlines()) == 1
    rec2 = _rec(el, ts="2026-11-12T17:30:01+08:00")
    assert el.record(rec2) is not None
    assert len(p.read_text(encoding="utf-8").splitlines()) == 2
    assert el.validate(p)[1] == []


def test_历史含非法行时拒绝追加(el, tmp_path, monkeypatch):
    monkeypatch.setenv("LIGHTHARNESS_EDIT_LOG_DIR", str(tmp_path))
    p = tmp_path / "2026-11.jsonl"
    p.write_text("{oops\n", encoding="utf-8")
    with pytest.raises(ValueError) as exc:
        el.record(_rec(el))
    assert "第 1 行" in str(exc.value)


def test_拒绝写入非法记录(el, tmp_path, monkeypatch):
    monkeypatch.setenv("LIGHTHARNESS_EDIT_LOG_DIR", str(tmp_path))
    bad = _rec(el)
    bad["file"] = "/tmp/x.light"
    with pytest.raises(ValueError):
        el.record(bad)


# --------------------------------------------------------------------------
# 4. file 必须是相对路径
# --------------------------------------------------------------------------
@pytest.mark.parametrize("bad", [
    "/tmp/x.light", "\\tmp\\x.light", "C:/tmp/x.light", "D:\\repo\\x.light",
    "../x.light", "a/../../x.light", "",
])
def test_file拒绝绝对路径与穿越(el, bad):
    rec = _rec(el)
    rec["file"] = bad
    assert any("file 必须是 repo 相对路径" in e for e in el.validate_record(rec))


@pytest.mark.parametrize("good", ["x.light", "src/a/b.light", "docs\\x.light"])
def test_file接受相对路径(el, good):
    rec = _rec(el)
    rec["file"] = good
    assert el.validate_record(rec) == []


def test_relative_file不泄露本机目录(el):
    assert el.relative_file("C:/Users/me/secret/x.light") == "x.light"
    assert el.relative_file("/home/skywalk/dswork/light/a.light") == "a.light"
    assert "<PATH>" in el.mask_paths("C:/Users/me/secret/x.light")


# --------------------------------------------------------------------------
# 5. edit_kind 白名单
# --------------------------------------------------------------------------
@pytest.mark.parametrize("kind", ["FR", "RW", "PATCH"])
def test_edit_kind合法值(el, kind):
    rec = _rec(el, edit_kind=kind)
    assert el.validate_record(rec) == []


@pytest.mark.parametrize("bad", ["FIX", "fix", "REFACTOR", "", None, 1])
def test_edit_kind拒绝其它值(el, bad):
    rec = _rec(el)
    rec["edit_kind"] = bad
    assert any("edit_kind" in e for e in el.validate_record(rec))


def test_安全替换按实际行为判edit_kind(sr):
    assert sr._choose_edit_kind("甲[9]", "甲[0]", BAD_TEXT) == "PATCH"   # 整串替换
    assert sr._choose_edit_kind("甲", "乙", "设 甲 为 1\n") == "FR"       # 逐个标识符
    assert sr._choose_edit_kind("全文", "新全文", "全文") == "RW"          # 全文件重写
    assert sr._choose_edit_kind("甲[9]", "甲[0]", BAD_TEXT, "RW") == "RW"  # 显式声明


# --------------------------------------------------------------------------
# 6. validate / dump / checker 解析
# --------------------------------------------------------------------------
def test_validate非法行必须报行号(el, tmp_path):
    p = tmp_path / "x.jsonl"
    lines = [json.dumps(_rec(el), ensure_ascii=False),
             "{oops",
             '{"schema_version": 1}',
             json.dumps(_rec(el, ts="2026-11-12T17:30:02+08:00"), ensure_ascii=False)]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    good, errs = el.validate(p)
    assert good == 2
    assert any("第 2 行" in e for e in errs)
    assert any("第 3 行" in e for e in errs)


def test_dump按outcome过滤(el, tmp_path):
    p = tmp_path / "x.jsonl"
    recs = [_rec(el, check_before=FAIL, check_after=PASS,
                 ts="2026-11-12T17:30:0%d+08:00" % i) for i in range(2)]
    recs.append(_rec(el, check_before=FAIL, check_after=FAIL,
                     ts="2026-11-12T17:30:09+08:00"))
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs),
                 encoding="utf-8")
    assert len(el.dump(path=p)) == 3
    fixed = el.dump(path=p, outcome="fixed")
    assert len(fixed) == 2 and all(r["outcome"] == "fixed" for r in fixed)
    assert len(el.dump(path=p, limit=1)) == 1
    assert len(el.dump(path=p, since="2026-11-12T17:30:09+08:00")) == 1


def test_dump遇非法行拒绝回放(el, tmp_path):
    p = tmp_path / "x.jsonl"
    p.write_text(json.dumps(_rec(el), ensure_ascii=False) + "\n{oops\n", encoding="utf-8")
    with pytest.raises(ValueError):
        el.dump(path=p)


def test_parse_check_json取首条error级诊断(el):
    stdout = ('进度日志\n{"schema_version": 1, "ok": false, "diagnostics": ['
              '{"code": "W1", "severity": "warning"}, '
              '{"code": "L3001", "severity": "error", "stage": "运行", '
              '"message": "索引错误 列表索引越界"}]}')
    chk = el.parse_check_json(stdout, 1)
    assert chk["ok"] is False
    assert chk["code"] == "L3001" and chk["stage"] == "运行"
    assert el.parse_check_json(stdout, 2) is None          # 用法错误不猜
    assert el.parse_check_json("没有 JSON", 0) is None      # 解析失败不猜


def test_parse_check_json的PASS结果(el):
    stdout = '{"schema_version": 1, "ok": true, "diagnostics": []}'
    assert el.parse_check_json(stdout, 0)["ok"] is True


# --------------------------------------------------------------------------
# 7. CLI 与真实编辑路径的钩子
# --------------------------------------------------------------------------
def _run(script, *args, env=None, timeout=90):
    return subprocess.run([sys.executable, str(script), *args],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env, timeout=timeout)


def test_编辑日志self_test全绿(tmp_path):
    env = dict(os.environ, LIGHTHARNESS_EDIT_LOG_DIR=str(tmp_path))
    r = _run(EDIT_LOG_PY, "--self-test", env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "全部通过" in r.stdout
    assert "存在失败" not in r.stdout


def test_安全替换原self_test不回归且不产生日志(tmp_path):
    env = dict(os.environ, LIGHTHARNESS_EDIT_LOG_DIR=str(tmp_path))
    r = _run(REPLACE_PY, "--self-test", env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "自测结果: 全部通过" in r.stdout
    assert list(tmp_path.glob("*.jsonl")) == []


def test_不传check时落null与unknown(tmp_path):
    env = dict(os.environ, LIGHTHARNESS_EDIT_LOG_DIR=str(tmp_path))
    bad, out = tmp_path / "bad.light", tmp_path / "fixed.light"
    bad.write_text(BAD_TEXT, encoding="utf-8")
    r = _run(REPLACE_PY, str(bad), "甲[9]", "甲[0]", "--out", str(out), env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert out.read_text(encoding="utf-8") == GOOD_TEXT
    logs = list(tmp_path.glob("*.jsonl"))
    assert len(logs) == 1
    rec = json.loads(logs[0].read_text(encoding="utf-8").splitlines()[0])
    assert rec["check_before"] is None and rec["check_after"] is None
    assert rec["outcome"] == "unknown"
    assert rec["edit_kind"] == "PATCH"
    assert rec["file"] == "fixed.light"           # 不落绝对路径


def test_no_edit_log与dry_run都不写日志(tmp_path):
    env = dict(os.environ, LIGHTHARNESS_EDIT_LOG_DIR=str(tmp_path))
    bad, out = tmp_path / "bad.light", tmp_path / "fixed.light"
    bad.write_text(BAD_TEXT, encoding="utf-8")
    r = _run(REPLACE_PY, str(bad), "甲[9]", "甲[0]", "--out", str(out),
             "--no-edit-log", env=env)
    assert r.returncode == 0
    assert list(tmp_path.glob("*.jsonl")) == []
    r = _run(REPLACE_PY, str(bad), "甲[9]", "甲[0]", "--dry-run", env=env)
    assert r.returncode == 0
    assert list(tmp_path.glob("*.jsonl")) == []
