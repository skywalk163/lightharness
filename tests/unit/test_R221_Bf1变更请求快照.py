# -*- coding: utf-8 -*-
"""T-0366（R221-Bf1）判据：forge 快照概览 / diff 定 head / 评审读取码。

被判对象：
  src/变更请求.light                        （新增「六、快照概览与失败码」一组段落）
  examples/test_R221_Bf1变更请求快照.light  （29 组断言的光明判据）

本文件把 .light 判据接进 pytest，并额外守住两件 .light 测不到的事：
  ① 九个新导出必须真的出现在 `导出` 行（否则示例是假绿）；
  ② 既有导出一个都不能丢（防止「删旧逻辑充数」）。
"""
import io
import re
from pathlib import Path

import pytest

from test_support import assert_success, out_contains, run_light_file

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "src" / "变更请求.light"
EXAMPLE = ROOT / "examples" / "test_R221_Bf1变更请求快照.light"

NEW_EXPORTS = [
    "变更请求快照缺省",
    "变更请求快照补全",
    "变更请求快照校验",
    "变更请求检查构造",
    "变更请求失败码集",
    "变更请求失败语义",
    "变更请求失败可重试",
    "变更请求差异过期",
    "变更请求评审读取码",
]

OLD_EXPORTS = [
    "变更请求键", "下次轮询延迟", "URL身份", "同变更请求URL",
    "找变更请求URL", "找自身URL", "绑定追加", "记录推送", "评审归一",
]


def _source() -> str:
    assert MODULE.exists(), f"缺模块 {MODULE}"
    return io.open(MODULE, encoding="utf-8").read()


def _export_line(text: str) -> str:
    line = [l for l in text.splitlines() if l.startswith("导出 ")]
    assert len(line) == 1, f"导出 行应恰有一行，实际 {len(line)}"
    return line[0]


def test_示例判据全绿():
    r = run_light_file("examples/test_R221_Bf1变更请求快照.light", timeout=180)
    assert_success(r, "R221-Bf1 光明判据")
    out_contains(r, "--- 测试 R221_Bf1变更请求快照 通过 ---")


def test_示例覆盖断言数不少于25():
    text = io.open(EXAMPLE, encoding="utf-8").read()
    n = len(re.findall(r"^\s*断言(?:相等|真|列表含|抛含)\(", text, flags=re.M))
    assert n >= 25, f"断言行只有 {n} 条，低于 25"


def test_九个新导出都在导出行():
    line = _export_line(_source())
    missing = [name for name in NEW_EXPORTS if name not in line]
    assert not missing, f"导出行缺：{missing}"


def test_既有导出一个都没丢():
    line = _export_line(_source())
    missing = [name for name in OLD_EXPORTS if name not in line]
    assert not missing, f"既有导出被删：{missing}"


def test_段落名不重复():
    names = re.findall(r"^段落\s+([^\s(]+)\s*\(", _source(), flags=re.M)
    dup = sorted({n for n in names if names.count(n) > 1})
    assert not dup, f"段落名重复：{dup}"


def test_快照字段规格是13个且与缺省键一致():
    """规格表与缺省字典的键必须一一对上，否则校验/补全会漂移。"""
    text = _source()
    spec = re.search(r"段落 变更请求快照字段规格\(\):\s*\n\s*返回 \[(.*?)\]\s*\n", text, flags=re.S)
    assert spec, "找不到 变更请求快照字段规格 的返回表"
    pairs = re.findall(r'\["([^"]+)",\s*"([^"]+)"\]', spec.group(1))
    assert len(pairs) == 13, f"规格表只有 {len(pairs)} 个字段"

    default = re.search(r"段落 变更请求快照缺省\(引用\):\s*\n\s*返回 \{(.*?)\}\s*\n", text, flags=re.S)
    assert default, "找不到 变更请求快照缺省 的返回字典"
    keys = re.findall(r'"([^"]+)":', default.group(1))
    assert sorted(keys) == sorted(k for k, _ in pairs), "缺省键与规格表不一致"
    assert "引用" in keys, "缺省快照必须带引用"


def test_失败码集含三个新增码():
    text = _source()
    m = re.search(r"段落 变更请求失败码集\(\):\s*\n\s*返回 \[(.*?)\]", text, flags=re.S)
    assert m, "找不到 变更请求失败码集"
    codes = re.findall(r'"([^"]+)"', m.group(1))
    assert len(codes) == 6, f"失败码集应为 6 个，实际 {len(codes)}"
    for c in ("stale", "unsupported", "unavailable"):
        assert c in codes, f"失败码集缺 {c}"