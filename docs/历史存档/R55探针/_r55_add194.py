# -*- coding: utf-8 -*-
"""R55 任务6：给 docs/功能对标/对标清单.json 追加 #194（全量测试基线固化）。

保格式要点（实测）：
  * 文件用 CRLF 行尾、无 BOM、无结尾换行 → 写回时 LF→CRLF 且不加末尾 \n
  * json.dumps(ensure_ascii=False, indent=2) 能原样往返整份文件，不会打乱其余 193 条
"""
from __future__ import annotations
import json
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
P = ROOT / "lightharness" / "docs" / "功能对标" / "对标清单.json"

ITEM = {
    "编号": 194,
    "功能": "全量测试基线固化 + 跨平台回归门（0.82 跑 light-merge 全量 / 本机跑 lightharness 全量）",
    "原模块": "回归验证基建（此前无全量基线，靠口述「零新增红」判定）",
    "光明模块": "lightharness/scripts/082全量回归.py + scripts/回归基线.py + scripts/多平台矩阵.py",
    "状态": "已完成",
    "完成轮次": "第55轮",
    "备注": (
        "任务1/2/3/4/5 合并交付。解决 R53~R54「light-merge 全量 pytest 在小浣熊/workbuddy 上卡住」："
        "根因是 8106 条用例 + 本机 xdist 不稳定的组合，处置是**把全量固化到 0.82（FreeBSD 15.1）**。"
        "实测基线：0.82 light-merge（py3.11、pytest 9.1.1、无 xdist/pytest-timeout）"
        "串行跑 -m 'not slow' → 7806 用例 / 7596 通过 / 117 失败 / 80 跳过 / 13 xfail / 1516.8s，无 hang；"
        "本机 Windows lightharness（py3.13）→ 1272 用例 / 1262 通过 / 7 失败 / 3 跳过 / 1494s。"
        "新增三件套：一键化脚本 082全量回归.py（sync/test/diff/all/show）、"
        "共用基线库 回归基线.py（junitxml→基线JSON→新增红diff）、"
        "多平台矩阵.py 新增 --mode gate（本机快门 + 0.82 基准，两侧各自与自己上一份基线比新增红，均为 0 才 rc=0）。"
        "判据沿用 CI 口径：新增红 = 本轮失败集合 − 基线失败集合；首次跑把失败记为基线，不判红。"
        "跨平台核对结果：3 条词法红两平台逐字一致（非平台差异）；4 条 example 红为 Windows 独占（0.82 绿），"
        "已排除 CRLF 行尾，剩余候选为 py3.13 vs py3.11 / OS 路径差异，未隔离、已登记待办。"
        "slow 用例 303 条本轮未纳入（脚本已支持 --mode full）。"
    ),
    "证据": [
        "lightharness/scripts/082全量回归.py",
        "lightharness/scripts/回归基线.py",
        "lightharness/scripts/多平台矩阵.py",
        "lightharness/reports/082_lightmerge基线_2026-09-18-002428.json",
        "lightharness/reports/本机lh基线_2026-09-18-003014.json",
        "lightharness/_task1_R55_082_lightmerge基线.md",
        "lightharness/_task2_R55_一键化脚本.md",
        "lightharness/_task3_R55_本机基线固化.md",
        "lightharness/_task4_R55_回归门升级.md",
        "lightharness/_task5_R55_回归流程验证.md",
        "lightharness/_task6_R55_docs+移档.md",
    ],
}

def dump(d) -> str:
    """按原文件风格序列化：实測定为该仓库用 ensure_ascii=False + indent=1 + CRLF + 无文件尾换行。"""
    return json.dumps(d, ensure_ascii=False, indent=1).replace("\n", "\r\n")


raw = io.open(P, encoding="utf-8", newline="").read()
d = json.loads(raw)
before = dump(d)
items = d["条目"]
if before != raw:
    raise SystemExit("❌ 序列化风格与原文件不一致（会波及全文），已中止，请先校准 dump() 的格式化参数")
print("[自检] 往返格式一致 ✅")

if any(i.get("编号") == 194 for i in items):
    print("[skip] #194 已存在，不重复追加")
else:
    items.append(ITEM)
    d["版本"] = "覆盖记录至第55轮（全量测试基线固化：0.82 light-merge + 本机 lightharness 双平台门）"
    out = dump(d)
    io.open(P, "w", encoding="utf-8", newline="").write(out)
    print("已追加 #194 ｜ 条目数", len(items))

# 校验：除新增块外不得有其他改动
if True:
    after = json.loads(io.open(P, encoding="utf-8", newline="").read())
    print("[校验] 条目数", len(after["条目"]), "｜ #194 存在:",
          any(i.get("编号") == 194 for i in after["条目"]))
