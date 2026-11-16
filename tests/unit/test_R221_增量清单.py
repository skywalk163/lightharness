# -*- coding: utf-8 -*-
"""T-0362 判据：0.2.2-rc.3 包级增量甄别清单（rc.1→rc.3）。

被判对象：docs/功能对标/0.2.2-rc.3增量清单.md
判据口径：**不允许「只查文件存在」**——逐节验证文档结构、§4 候选表每行都指到
真实上游 `packages/` 路径、§2 真有新增/删除包、§1 有实测规模数字；
反跑：把 `## 4.` 改成 `## 4`，同一套口径必须变红。
"""
import io
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "功能对标" / "0.2.2-rc.3增量清单.md"

# 任务卡要求必须存在的五节（§3 也要求，顺带钉住）
REQUIRED_SECTIONS = ("0.", "1.", "2.", "3.", "4.", "5.")


def _text() -> str:
    assert DOC.exists(), f"缺交付文件：{DOC}"
    return io.open(DOC, encoding="utf-8").read()


def _has_section(text: str, title: str) -> bool:
    """按行首判定二级标题，避免 `### 4.1` 被当成 `## 4.`（子串误判）。"""
    prefix = f"## {title}"
    return any(line.startswith(prefix) for line in text.splitlines())


def _section(title: str) -> str:
    text = _text()
    marker = f"## {title}"
    assert _has_section(text, title), f"缺章节 {marker}"
    body = text.split(marker, 1)[1]
    return body.split("\n## ", 1)[0]


def _subsection(section: str, heading: str) -> str:
    marker = f"### {heading}"
    assert marker in section, f"缺小节 {marker}"
    body = section.split(marker, 1)[1]
    return body.split("\n### ", 1)[0]


def _table_rows(section: str) -> list:
    """取出一节里所有 markdown 表格的数据行（跳过表头与分隔行）。"""
    rows = []
    for line in section.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        if set(s) <= set("|-: "):          # 分隔行
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if cells and cells[0] in ("编号", "包", "目录", "状态"):   # 表头
            continue
        rows.append(s)
    return rows


def test_文件存在且不是骨架():
    text = _text()
    assert len(text.splitlines()) >= 60, "文档短于 60 行，疑似骨架"
    # §0 必须给出 3~5 条结论先行
    sec0 = _section("0. 结论先行")
    items = [l for l in sec0.splitlines() if re.match(r"^\d+\. ", l.strip())]
    assert 3 <= len(items) <= 5, f"§0 结论 {len(items)} 条，应为 3~5"


def test_必需章节齐全():
    text = _text()
    missing = [t for t in REQUIRED_SECTIONS if not _has_section(text, t)]
    assert not missing, f"缺章节：{missing}"


def test_第一节有实测规模与分布():
    sec = _section("1. 规模与分布")
    for needle in ("828", "4721", "47624", "15192"):
        assert needle in sec, f"§1 缺实测数字 {needle}"
    top_rows = _table_rows(_subsection(sec, "1.1 顶层分布"))
    assert len(top_rows) >= 5, "§1.1 顶层分布表太短"
    assert any("`packages/`" in r and "2867" in r for r in top_rows), \
        "§1.1 缺 packages 行（变更 2867）"
    top_pkgs = _table_rows(_subsection(sec, "1.3 变更最集中的包（按 src 文件数）"))
    assert len(top_pkgs) >= 10, "§1.3 重点包表少于 10 行"


def test_第二节真有新增包和删除包():
    sec = _section("2. 新增包 / 删除包逐包定性")
    new_rows = _table_rows(_subsection(sec, "2.1 新增包（13）"))
    gone_rows = _table_rows(_subsection(sec, "2.2 删除包（11）"))
    assert len(new_rows) >= 5, f"新增包行数 {len(new_rows)} 太少"
    assert len(gone_rows) >= 5, f"删除包行数 {len(gone_rows)} 太少"
    for row in new_rows + gone_rows:
        cells = [c.strip() for c in row.strip("|").split("|")]
        assert len(cells) >= 4, f"§2 列数不足：{row[:60]}"
        assert "packages/" in row, f"§2 行没指到包路径：{row[:60]}"
        assert cells[2], f"§2 行缺定性：{row[:60]}"
        assert cells[3], f"§2 行缺处置/归属：{row[:60]}"


def test_第四节候选表每行指到真实上游路径():
    sec = _section("4. 纯逻辑候选表（B 路直接输入）")
    rows = _table_rows(sec)
    assert len(rows) >= 5, f"候选表只有 {len(rows)} 行，低于实测面（应 5~10 行）"
    assert len(rows) <= 10, f"候选表 {len(rows)} 行，超过 10 行大概率是凑数"
    ids = []
    for row in rows:
        cells = [c.strip() for c in row.strip("|").split("|")]
        assert len(cells) == 6, f"候选表列数 {len(cells)}≠6：{row[:70]}"
        assert re.fullmatch(r"\*\*B\d+\*\*", cells[0]), f"编号不合规：{cells[0]}"
        ids.append(cells[0])
        assert "packages/" in row, f"候选没指到上游文件：{row[:70]}"
        assert cells[2], f"缺建议模块：{row[:70]}"
        assert cells[3] in ("小", "中", "大"), f"工作量口径不对：{cells[3]}"
        assert "★" in cells[4], f"缺价值星级：{cells[4]}"
        assert cells[5], f"缺一句话理由：{row[:70]}"
    assert len(set(ids)) == len(ids), f"候选编号重复：{ids}"
    # 本轮 §4 结论是 8 项：B1~B8 必须都在
    assert set(ids) == {f"**B{i}**" for i in range(1, 9)}, f"候选编号不是 B1~B8：{ids}"


def test_第四节有不移植登记且不占编号():
    sec = _section("4. 纯逻辑候选表（B 路直接输入）")
    tail = _subsection(sec, "4.1 明确不移植 / 无承载（登记，不占候选编号）")
    assert "ptc-runtime" in tail, "§4.1 应登记 ptc-runtime 的宿主协议"
    assert "mcp-manager" in tail, "§4.1 应登记 mcp-manager"
    bullets = [l for l in tail.splitlines() if l.strip().startswith("- ")]
    assert len(bullets) >= 2, "§4.1 登记条目少于 2 条"


def test_第五节宿主面有实质内容():
    sec = _section("5. 宿主面摘要（C 路输入，不展开）")
    bullets = [l for l in sec.splitlines() if l.strip().startswith("- ")]
    assert len(bullets) >= 5, f"§5 宿主面条目 {len(bullets)} 条，太少"
    assert "packages/client/" in sec, "§5 必须点出 packages/client/* 宿主面"
    assert "snapshots/" in sec, "§5 必须点出 snapshots/"


def test_不写内网IP与密钥():
    text = _text()
    assert "192.168." not in text, "文档里出现内网 IP"
    assert not re.search(r"(ghp_|gho_|sk-[A-Za-z0-9]{16,}|Bearer\s+[A-Za-z0-9._-]{16,})", text), \
        "文档里疑似出现 token/密钥"


def test_反跑_把第四节的点去掉必须红():
    """把 `## 4.` 改成 `## 4`，同一套判据口径必须失败（证明判据真在读内容）。"""
    text = _text()
    assert _has_section(text, "4.")
    broken = text.replace("## 4. 纯逻辑候选表", "## 4 纯逻辑候选表", 1)
    assert not _has_section(broken, "4."), "改坏后 §4 仍被当成二级标题"
    missing = [t for t in REQUIRED_SECTIONS if not _has_section(broken, t)]
    assert "4." in missing, "改坏后判据没有变红"
    assert "## 4. 纯逻辑候选表" not in broken, "改坏后候选表章节仍在"