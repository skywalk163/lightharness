# -*- coding: utf-8 -*-
"""T-0365 判据：0.2.2-rc.2/rc.3 宿主面增量登记（§11 append）。

被判对象：docs/宿主面登记清单.md
判据口径：不接受「只断言文件存在」——逐行验证 §11 的表格结构（5 列、末列含「登记」、
每行都指到上游 `packages/` 或 `apps/` 路径、每行写清为什么不移植）、子节数与
统计行按 §10 的 126 基数累加一致，并确认 §9/§10 原文与 126 基数未被破坏。
反跑：删掉 §11、或破坏任意一行的状态列，同一套断言必须变红。
"""
import io
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "宿主面登记清单.md"

HEADINGS = ("宿主能力", "上游实现面", "lightharness 现状", "三平台可行性", "状态")
BASE_TOTAL = 126                 # §10 收口值：登记 113 → **126**
MIN_ROWS = 8                     # 任务书下限：§11 表格数据行 ≥ 8
REASON_TAGS = ("缺宿主层", "平台专属", "依赖 Node 生态", "纯 UI", "文档")

# 任务书要求「判不准归属」单列、不硬塞进表；这 7 项必须在 §11 里留痕
UNRESOLVED = (
    "代码块",
    "Star",
    "多语言",
    "Gemini",
    "更新渠道",
    "Cordis Core",
    "Worktree 评审",
)


def _text() -> str:
    assert DOC.exists(), f"缺交付文件：{DOC}"
    return io.open(DOC, encoding="utf-8").read()


def _count_heading(text: str, num: str) -> int:
    """按行首锚定数二级标题（`## 11.` 不能误数进 `### 11.1`）。"""
    return len(re.findall(r"(?m)^## %s" % num, text))


def _section11() -> str:
    text = _text()
    assert _count_heading(text, "11.") == 1, "§11 应出现且仅出现一次"
    return text.split("\n## 11.", 1)[1].split("\n## ", 1)[0]


def _rows(section: str) -> list:
    """取出章节内的表格数据行（跳过表头与分隔行）。"""
    rows = []
    for line in section.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        if set(s) <= set("|-: "):                      # 分隔行
            continue
        if all(h in s for h in HEADINGS):               # 表头（5 个字段名同时出现）
            continue
        rows.append(s)
    return rows


def _check(text: str) -> None:
    """对给定全文跑 §11 全套断言；反跑时用损坏文本调用，必须抛 AssertionError。"""
    assert _count_heading(text, "11.") == 1, "§11 应出现且仅出现一次"
    body = text.split("\n## 11.", 1)[1].split("\n## ", 1)[0]

    subs = [l for l in body.splitlines() if l.startswith("### 11.")]
    assert 3 <= len(subs) <= 4, f"§11 子节 {len(subs)} 个，应为 3~4 个（不许写成一整张大表）"

    rows = _rows(body)
    assert len(rows) >= MIN_ROWS, f"§11 表格数据行 {len(rows)}，至少 {MIN_ROWS} 行"

    for r in rows:
        cells = [c.strip() for c in r.strip("|").split("|")]
        assert len(cells) == 5, f"不是 5 列：{r[:90]}"
        assert "登记" in cells[-1], f"末列缺「登记」：{r[:90]}"
        assert any(t in r for t in REASON_TAGS), f"没写清「为什么登记不移植」：{r[:90]}"
        assert ("packages/" in r) or ("apps/" in r), f"指不到上游包/文件：{r[:90]}"

    assert "**统计更新**" in body, "§11 缺统计更新行"
    total = BASE_TOTAL + len(rows)
    assert f"登记 {BASE_TOTAL} → **{total}**" in body, (
        f"统计行未按 §10 的 {BASE_TOTAL} 基数累加：应为 {BASE_TOTAL} → **{total}**"
    )
    assert "**跟进**" in body, "§11 缺跟进行"


def test_文件不是骨架():
    text = _text()
    assert len(text.splitlines()) >= 400, "文档过短，疑似骨架"


def test_s11_结构合规():
    _check(_text())


def test_s11_分主题子节():
    body = _section11()
    subs = [l for l in body.splitlines() if l.startswith("### 11.")]
    titles = [s for s in subs]
    assert len(titles) == len(set(titles)), "子节标题重复"
    assert "client" in body and "宿主侧" in body, "子节主题缺失"


def test_每行五个字段顺序不乱():
    rows = _rows(_section11())
    for r in rows:
        cells = [c.strip() for c in r.strip("|").split("|")]
        assert cells[0] and cells[1] and cells[2] and cells[3] and cells[4], f"有空列：{r[:90]}"
        assert cells[4].startswith("登记"), f"状态列必须以「登记」开头：{r[:90]}"


def test_判不准归属单列且未进表():
    body = _section11()
    assert "判不准归属" in body, "缺「判不准归属」单列小节"
    bullets = [l for l in body.splitlines() if l.strip().startswith("- ")]
    assert len(bullets) >= 7, f"判不准归属只列了 {len(bullets)} 条，应 ≥ 7"
    for kw in UNRESOLVED:
        assert kw in body, f"判不准归属缺条目：{kw}"
    for r in _rows(body):
        assert "判不准" not in r, "判不准归属的条目被硬塞进了表格"


def test_旧章节与126基数未被破坏():
    text = _text()
    assert "## 9. 0.2.1-rc.3 增量宿主面登记" in text, "§9 被破坏"
    assert "## 10. 0.2.2-rc.1 增量宿主面登记" in text, "§10 被破坏"
    assert "登记 113 → **126**" in text, "§10 的 126 基数被改写"
    order = [text.index("## 9."), text.index("## 10."), text.index("## 11.")]
    assert order == sorted(order), "章节顺序错乱（§11 必须在 §10 之后）"
    assert text.rstrip().endswith("*R221-C 追加 §11（2026-11-16，T-0365）：仅 append 本节，未改既有章节、未移植代码。*")


def test_反跑_删掉整节必须红():
    head = _text().split("\n## 11.", 1)[0]
    assert _count_heading(head, "11.") == 0
    with pytest.raises(AssertionError):
        _check(head)


def test_反跑_破坏一行状态列必须红():
    text = _text()
    row = _rows(_section11())[0]
    assert "登记" in row
    with pytest.raises(AssertionError):
        _check(text.replace(row, row.replace("登记", ""), 1))


def test_反跑_删掉一行统计必须红():
    text = _text()
    body = _section11()
    stats = [l for l in body.splitlines() if "**统计更新**" in l][0]
    with pytest.raises(AssertionError):
        _check(text.replace(stats, "*（统计行被删）*", 1))
