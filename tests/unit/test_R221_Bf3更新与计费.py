# -*- coding: utf-8 -*-
"""T-0368（R221-Bf3）判据：插件更新方式 + 搜索按计费选凭据。

被判对象：
  src/插件注册表.light                     （新增「更新方式判定」「安装结果核对」）
  src/网页搜索.light                       （新增「计费方式与有序凭据来源」）
  examples/test_R221_Bf3更新与计费.light   （35 组断言的光明判据）

pytest 这层额外守住 .light 测不到的三件事：
  ① 示例必须真的绿（rc=0 且打印通过行）；
  ② 新增段落跨 src 不得重名（光明语言里重名会静默串味）；
  ③ 既有导出一个都不能丢（防止删旧逻辑充数）。
"""
import io
import re
from pathlib import Path

from test_support import assert_success, out_contains, run_light_file

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "src" / "插件注册表.light"
SEARCH = ROOT / "src" / "网页搜索.light"
EXAMPLE = ROOT / "examples" / "test_R221_Bf3更新与计费.light"

NEW_PARAGRAPHS = [
    "插件更新_拒绝", "插件更新方式", "插件更新_是语义版本", "安装结果核对",
    "Web计费方式合法", "Web计费来源表", "Web选首来源", "Web取消码",
]

OLD_REGISTRY_EXPORTS = ["选首个响应注册表", "造安装规格", "归类安装失败", "推导启停后清单"]


def _read(p: Path) -> str:
    assert p.exists(), f"缺文件 {p}"
    return io.open(p, encoding="utf-8").read()


def test_示例判据全绿():
    r = run_light_file("examples/test_R221_Bf3更新与计费.light", timeout=180)
    assert_success(r, "R221-Bf3 光明判据")
    out_contains(r, "--- 测试 R221_Bf3更新与计费 通过 ---")


def test_示例断言数不少于30():
    text = _read(EXAMPLE)
    n = len(re.findall(r"^\s*断言(?:相等|真|含|抛含)\(", text, flags=re.M))
    assert n >= 30, f"断言行只有 {n} 条，低于 30"


def test_新段落全部存在且跨src不重名():
    names = {}
    for f in ROOT.joinpath("src").glob("*.light"):
        for line in _read(f).splitlines():
            m = re.match(r"^段落\s+([^\s(]+)\s*\(", line)
            if m:
                names.setdefault(m.group(1), []).append(f.name)
    for p in NEW_PARAGRAPHS:
        assert p in names, f"缺段落 {p}"
        assert names[p] == ["插件注册表.light"] or names[p] == ["网页搜索.light"], \
            f"段落 {p} 出现在多处：{names[p]}"


def test_注册表既有导出未丢():
    text = _read(REGISTRY)
    line = [l for l in text.splitlines() if l.startswith("导出 ")]
    assert len(line) == 1, "插件注册表应有唯一导出行"
    missing = [n for n in OLD_REGISTRY_EXPORTS if n not in line[0]]
    assert not missing, f"既有导出被删：{missing}"


def test_更新拒绝文案与上游逐字一致():
    """文案是模型面文本，改动即语义漂移，这里钉死三句。"""
    text = _read(REGISTRY)
    for s in (
        "is not a third-party package installed in this profile",
        "carries plugin management and cannot be removed",
        "declares no semver version",
        "is installed neither from a registry under its own name nor from a Git commit",
    ):
        assert s in text, f"缺上游文案：{s}"


def test_计费来源顺序被钉死():
    """auto 的两种顺序是本卡的语义核心，改顺序必须红。"""
    text = _read(SEARCH)
    m = re.search(r"段落 Web计费来源表\(.*?\):(.*?)\n段落 ", text, flags=re.S)
    assert m, "找不到 Web计费来源表"
    body = m.group(1)
    assert body.index('返回 [账号来源, 密钥来源]') < body.index('返回 [密钥来源, 账号来源]'), \
        "auto 的两条顺序被调换"