# -*- coding: utf-8 -*-
"""R65 任务4：对标清单追加 R65 条目（无损往返自证）。

约束：ensure_ascii=False + indent=2 + CRLF + 无尾换行；append 前先无损往返自证。
"""
from __future__ import annotations

import io
import json
from pathlib import Path

P = Path(r"G:\dswork\duan-light-merge\lightharness\docs\功能对标\对标清单.json")

NEW = {
    "功能": "R65：stdlib 旧式「接收」语法现代化·第一批（41 模块 / 562 行）+ unified 腿 builtin 差集清零（149→35）+ 同步包再压",
    "原版包": "——（工程基建轮，非功能对标；对应 deepseek-harness 的打包链路与代码生成两腿一致性）",
    "光明模块": "light-merge/stdlib/**（41 文件）, light-merge/src/code_generator_unified.py, lightharness/scripts/同步0.82.py",
    "状态": "done；① stdlib 接收现代化首批：只取「整模块全部 SAFE」的 41 个模块、改 562 行；stdlib 单次解析 DeprecationWarning 1321→969（−26.6%），0.82 全量 warnings 53455→45067（−8388）——证实 R62「warning 大头在 stdlib」的判断。② unified 腿 builtin_map 149→263 键、差集 149→35（剩余全为 FFI 族）；产物头部补 import math/random/functools/json（顺带修掉 json.loads 的既有隐患）；114 键逐键经 stdlib/builtins.py hasattr 核查零缺实现。③ 同步包 30.32MB→27.49MB（4281 文件/4281），新增排除 light.egg-info、sessions、.ci、_082_lm_results_*.xml。④ 关键发现并修复：参数名含关键字子串（如 消息列表/词列表）时括号式会被切成两个参数 → 建立「产物函数签名逐模块对拍」护栏",
    "证据": [
        "light-merge/stdlib/**（41 文件 562 行旧式接收→括号式）",
        "light-merge/_task1_R65_stdlib接收现代化首批.md（等价性反例 + 签名对拍护栏 + warning 量化）",
        "light-merge/src/code_generator_unified.py（114 键 + 头部 import）",
        "light-merge/_task2_R65_unified差集清零.md（分族清单 + 可解析性核查）",
        "lightharness/scripts/同步0.82.py（R65 排除项）",
        "lightharness/_task3_R65_包体再压与flaky登记.md（F-01/F-02 登记 + 误判纠正）",
        "lightharness/reports/082_lightmerge基线_2026-09-19-074303.json（R65 门：7884 用例 0 红）"
    ],
    "本轮目标": "把 R62 判定的「warning 大头在 stdlib」落成第一批实改并量化收益；把 unified 腿除 FFI 外的 builtin 差集清零；建立「语法现代化前必须做产物签名对拍」的工程护栏",
    "反跑判据": "① 把任一 stdlib 模块的括号式改回旧式，_probe_R65_stdlib_warn.py 计数必回升；② 删掉 unified 的任一补入键，_probe_R62_builtin_diff.py 差集必重新变大；③ 把某参数名改成含「列表」的复合名并保留括号式，产物签名对拍必报出 def 名(甲, 列表) 分裂",
    "语言缺陷": []
}


def dump(d) -> str:
    return json.dumps(d, ensure_ascii=False, indent=2)


def main() -> None:
    orig = io.open(P, encoding="utf-8", newline="").read()
    d = json.loads(orig)
    items = d["条目"]
    if dump(d).replace("\n", "\r\n") != orig:
        print("⛔ 无损往返自证失败")
        raise SystemExit(1)
    print(f"✅ 无损往返自证通过（{len(items)} 条目）")
    NEW["编号"] = int(items[-1].get("编号")) + 1
    print(f"   编号 {items[-1].get('编号')} → {NEW['编号']}")
    items.append(NEW)
    io.open(P, "w", encoding="utf-8", newline="").write(dump(d).replace("\n", "\r\n"))
    back = json.loads(io.open(P, encoding="utf-8", newline="").read())
    raw = io.open(P, encoding="utf-8", newline="").read()
    assert len(back["条目"]) == len(items) and back["条目"][-1]["编号"] == NEW["编号"]
    assert "\r\n" in raw and not raw.endswith("\n")
    print(f"✅ 已追加 #{NEW['编号']}，回读校验通过（{len(back['条目'])} 条目）")


if __name__ == "__main__":
    main()
