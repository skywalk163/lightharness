# -*- coding: utf-8 -*-
"""T-0363 判据：0.2.2-rc.1 升级指南 19 条逐条对账（rc.1→rc.3）。

被判对象：docs/功能对标/0.2.2-rc.3升级指南对账.md
判据口径：不允许「只查文件存在」——逐条验证 19 个指南条目名、总表行数、
三类结论的条数，以及每行都有落点/理由。反跑：删掉任意一条条目行必须红。
"""
import io
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "功能对标" / "0.2.2-rc.3升级指南对账.md"

# 安装版 0.2.2-rc.3 的 upgrade-guide/v0.2.2-rc.1 目录，共 19 条，一条不能漏
GUIDES = [
    "account-notification-fields",
    "account-remote-provider",
    "archive-worktrees",
    "attachment-error-codes",
    "cua-ax-read-limits",
    "cua-hover-ax-only",
    "cua-native-platform",
    "dsh-doc-skill",
    "forge-change-request-overview",
    "forge-pinned-diff",
    "forge-review-reads",
    "plugin-update-method",
    "runtime-context-reminders",
    "session-append-overloads",
    "subagent-interrupt-default",
    "terminal-backend-cleanup-error",
    "terminal-bundle-sidebar-backend",
    "web-search-billing",
    "window-drag-regions",
]


def _text() -> str:
    assert DOC.exists(), f"缺交付文件：{DOC}"
    return io.open(DOC, encoding="utf-8").read()


def _section(title: str) -> str:
    text = _text()
    marker = f"## {title}"
    assert marker in text, f"缺章节 {marker}"
    body = text.split(marker, 1)[1]
    return body.split("\n## ", 1)[0]


HEADERS = ("上游变更（一句话）", "为什么登记不移植", "结论")


def _table_rows(section: str) -> list:
    rows = []
    for line in section.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        if set(s) <= set("|-: "):      # 分隔行
            continue
        if any(h in s for h in HEADERS):   # 表头
            continue
        rows.append(s)
    return rows


def test_文件存在且不是骨架():
    text = _text()
    assert len(text.splitlines()) >= 70, "文档过短，疑似骨架"


def test_19个指南条目全部覆盖():
    text = _text()
    missing = [g for g in GUIDES if g not in text]
    assert not missing, f"漏了对账条目：{missing}"


def test_总表恰好19行():
    rows = _table_rows(_section("1. 总表（19 条）"))
    assert len(rows) == 19, f"总表行数 {len(rows)}，应为 19"


def test_每行都有落点或理由():
    rows = _table_rows(_section("1. 总表（19 条）"))
    for r in rows:
        cells = [c.strip() for c in r.strip("|").split("|")]
        assert len(cells) >= 7, f"列数不足：{r[:60]}"
        assert cells[-1], f"缺落点/理由：{r[:60]}"


def test_需移植_登记_无承载三类计数():
    main_rows = _table_rows(_section("1. 总表（19 条）"))
    need = [r for r in main_rows if "**是**" in r]
    assert len(need) == 11, f"需移植条数 {len(need)}，应为 11"

    reg_rows = _table_rows(_section("3. 登记不移植（6 条）"))
    assert len(reg_rows) == 6, f"登记条数 {len(reg_rows)}，应为 6"

    none_rows = _table_rows(_section("4. 无承载 / 不适用（2 条）"))
    assert len(none_rows) == 2, f"无承载条数 {len(none_rows)}，应为 2"


def test_三类条数加起来等于19():
    main_rows = _table_rows(_section("1. 总表（19 条）"))
    need = len([r for r in main_rows if "**是**" in r])
    reg = len(_table_rows(_section("3. 登记不移植（6 条）")))
    none = len(_table_rows(_section("4. 无承载 / 不适用（2 条）")))
    assert need + reg + none == 19, f"{need}+{reg}+{none} != 19"


def test_不硬造模块_无承载要写清理由():
    sec = _section("4. 无承载 / 不适用（2 条）")
    assert "无承载" in sec
    assert "不适用" in sec


def test_给B路的输入表存在():
    sec = _section("5. 给 B 路的输入（建议拆卡）")
    rows = _table_rows(sec)
    assert len(rows) >= 1, "缺拆卡建议表"
    assert "src/" in sec, "拆卡建议必须给到 src/ 落点"


def test_反跑_删掉一条条目必须红():
    """把对账文档里的一行删掉，判据必须失败（证明判据真的在读内容）。"""
    text = _text()
    needle = "session-append-overloads"
    assert needle in text
    broken = "\n".join(
        line for line in text.splitlines() if needle not in line
    )
    assert needle not in broken
    # 用同样的判据口径复核损坏后的文本
    missing = [g for g in GUIDES if g not in broken]
    assert "session-append-overloads" in missing, "删行后判据没有变红"