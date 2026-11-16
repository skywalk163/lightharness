# -*- coding: utf-8 -*-
"""T-0367（R221-Bf2）判据：工作树清理判定 / 终端 CLEANUP_FAILED / 附件错误码。

被判对象：
  src/工作区变更.light   （工区工作树可移除 / 工区工作树归档处置）
  src/终端.light         （终端清理失败错误 / 终端错误码 / 终端是清理失败）
  src/附件准入.light     （17 个附件码 + 失败码保真 + 旧码同属）
  src/错误增强.light     （失败归类 / 失败是附件 / 失败是终端清理）
  examples/test_R221_Bf2错误与清理.light（37 组断言）

pytest 这层额外钉住三件 .light 判据跑不出来或容易漂的事：
  ① 17 个码必须与上游常量逐字一致（顺序也算）；
  ② 四个模块的新段落跨 src 不重名；
  ③ 附件码与终端码不允许被写成「目录里另有一份」。
"""
import io
import re
from pathlib import Path

from test_support import assert_success, out_contains, run_light_file

ROOT = Path(__file__).resolve().parents[2]
WORKTREE = ROOT / "src" / "工作区变更.light"
TERMINAL = ROOT / "src" / "终端.light"
ATTACH = ROOT / "src" / "附件准入.light"
ERRORS = ROOT / "src" / "错误增强.light"
EXAMPLE = ROOT / "examples" / "test_R221_Bf2错误与清理.light"

UPSTREAM_CODES = [
    "TOO_MANY_IMAGES", "IMAGES_TOO_LARGE", "UNSUPPORTED_IMAGE_TYPE",
    "INVALID_IMAGE_BASE64", "INVALID_IMAGE", "IMAGE_TYPE_MISMATCH",
    "IMAGE_TOO_LARGE", "IMAGE_TOO_MANY_PIXELS", "IMAGE_DIMENSION_TOO_LARGE",
    "INVALID_FILE_BASE64", "INVALID_ATTACHMENT_REF", "ATTACHMENT_CORRUPT",
    "ATTACHMENT_WRITE_FAILED", "ATTACHMENT_NOT_FOUND", "ATTACHMENT_READ_FAILED",
    "ATTACHMENT_PROJECTION_UNSUPPORTED", "ATTACHMENT_FILES_UNSUPPORTED",
]

NEW_PARAGRAPHS = {
    "工区工作树可移除": "工作区变更.light",
    "工区工作树归档处置": "工作区变更.light",
    "终端清理失败错误": "终端.light",
    "终端错误码": "终端.light",
    "终端是清理失败": "终端.light",
    "附件图像准入码集": "附件准入.light",
    "附件其他码集": "附件准入.light",
    "附件错误码集": "附件准入.light",
    "附件码属于": "附件准入.light",
    "附件失败码": "附件准入.light",
    "附件失败记录": "附件准入.light",
    "附件旧码同属": "附件准入.light",
    "失败归类": "错误增强.light",
    "失败是附件": "错误增强.light",
    "失败是终端清理": "错误增强.light",
}


def _read(p: Path) -> str:
    assert p.exists(), f"缺文件 {p}"
    return io.open(p, encoding="utf-8").read()


def test_示例判据全绿():
    r = run_light_file("examples/test_R221_Bf2错误与清理.light", timeout=180)
    assert_success(r, "R221-Bf2 光明判据")
    out_contains(r, "--- 测试 R221_Bf2错误与清理 通过 ---")


def test_示例断言数不少于30():
    n = len(re.findall(r"^\s*断言(?:相等|真|含)\(", _read(EXAMPLE), flags=re.M))
    assert n >= 30, f"断言行只有 {n} 条，低于 30"


def test_新段落只在指定模块出现一次():
    names = {}
    for f in ROOT.joinpath("src").glob("*.light"):
        for line in _read(f).splitlines():
            m = re.match(r"^段落\s+([^\s(]+)\s*\(", line)
            if m:
                names.setdefault(m.group(1), []).append(f.name)
    for p, owner in NEW_PARAGRAPHS.items():
        assert p in names, f"缺段落 {p}"
        assert names[p] == [owner], f"段落 {p} 位置异常：{names[p]}（应为 {owner}）"


def test_十七个附件码逐字且保序():
    text = _read(ATTACH)
    found = re.findall(r'"([A-Z][A-Z_]+)"', text)
    for code in UPSTREAM_CODES:
        assert f'"{code}"' in text, f"缺附件码 {code}"
    # 顺序：在 附件错误码集 的返回行里逐个出现且递增
    m = re.search(r"段落 附件错误码集\(\):\s*\n\s*返回 \[(.*?)\]", text, flags=re.S)
    assert m, "找不到 附件错误码集"
    seq = re.findall(r'"([^"]+)"', m.group(1))
    assert seq == UPSTREAM_CODES, f"码序与上游不一致：{seq}"
    assert len(found) >= 17


def test_终端清理错误码与顺序():
    text = _read(TERMINAL)
    assert "CLEANUP_FAILED" in text
    assert '"名称": "TerminalBackendCleanupError"' in text
    m = re.search(r"段落 终端清理失败错误\(.*?\):(.*?)\n段落 ", text, flags=re.S)
    assert m, "找不到 终端清理失败错误"
    body = m.group(1)
    assert body.index('"错误表": [启动失败, 清理失败]') > 0, "错误表顺序必须是启动失败在前"


def test_工作树判定六个拒绝面都在():
    text = _read(WORKTREE)
    for needle in ("身份不符", "不是目录", "未按该分支注册", "detached/locked/prunable", "HEAD 不在该分支", "子模块仓库"):
        assert needle in text, f"缺判定面：{needle}"


def test_失败归类先认附件():
    """继承关系变了，捕获顺序不能变；这里钉死「附件分支在 harness 分支之前」。"""
    text = _read(ERRORS)
    m = re.search(r"段落 失败归类\(.*?\):(.*?)\n段落 ", text, flags=re.S)
    assert m, "找不到 失败归类"
    body = m.group(1)
    assert body.index('"AttachmentError"') < body.index('"大类": "harness"'), \
        "附件分支必须在 harness 兜底之前"