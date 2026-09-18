# -*- coding: utf-8 -*-
"""R62 任务4：对标清单追加 R62 条目（无损往返自证）。

约束（memory 已固化）：ensure_ascii=False + 保持原缩进 + CRLF + 无尾换行；
append 前先做「去掉新条目后与原文件逐字节一致」的无损往返自证。
"""
from __future__ import annotations

import io
import json
from pathlib import Path

P = Path(r"G:\dswork\duan-light-merge\lightharness\docs\功能对标\对标清单.json")

NEW = {
    "编号": 203,
    "功能": "R62：sync 打包瘦身 + unified(ANTLR)腿 builtin 缺口补齐 + tests/ 旧式「接收」语法现代化（阶段一）",
    "原版包": "——（本条为工程基建轮，非功能对标；对应 deepseek-harness 的 CI/打包与代码生成两侧能力）",
    "光明模块": "lightharness/scripts/同步0.82.py, light-merge/src/code_generator_unified.py, light-merge/tests/**",
    "状态": "done；① 同步包 120.43MB/5338文件 → 30.3MB/4344文件（−74.8%），新增目录名前缀排除(_taskR11B_test_)与相对路径排除(docs/历史存档、demo_video、2026-09-11-d613c31d、light_verify.tar.gz、data/finetune)，build_tarball 改 os.walk+剪枝（打包耗时 −54%）；② unified 腿 builtin_map 补 25 条「字符串处理同族」映射（含核心缺口 去除空格→_light_builtin.去除空白，R61 只在 hook 腿修过），键数 124→149，两腿差集 174→149；③ tests/ 旧式「段落 名 接收 参数」→「段落 名(参数)」：287 行 / 46 文件，仅替换两分支等价的 SAFE 形态，FFI/默认值/*args/空格式类型/匿名闭包/断言文本一律不碰",
    "证据": [
        "lightharness/scripts/同步0.82.py（EXCLUDE_DIR_PREFIXES / EXCLUDE_REL_PREFIXES / os.walk 剪枝）",
        "lightharness/_task1_R62_sync瘦身.md（排除规则 diff + 打包前后实测表）",
        "light-merge/src/code_generator_unified.py（L167 起新增 25 条字符串同族 builtin 映射）",
        "light-merge/_task2_R62_unified去除空格缺口.md（差集清单 + 行为差异登记）",
        "light-merge/tests/**（46 文件 287 行旧式接收→括号式）",
        "light-merge/_task3_R62_接收语法现代化.md（等价性确认表 + 禁改项核对）",
        "lightharness/reports/082_lightmerge基线_2026-09-19-051950.json（R62 门：7884 用例 0 红）"
    ],
    "本轮目标": "让 R61 拆仓的文件数红利兑现为体积红利；补齐 unified 腿与 hook 腿的 builtin 缺口（对齐两腿）；把 tests/ 源串的废弃语法清零以压降 DeprecationWarning",
    "反跑判据": "① 把 EXCLUDE_REL_PREFIXES 清空重打包，tar.gz 必回到 120MB 量级；② 删掉 unified 的 '去除空格' 映射，_probe_R62_unified_builtin.py 必报 FAIL 且产物回退为裸名 去除空格(' x ')；③ 把任一 SAFE 形态改回旧式，全量 DeprecationWarning 计数必回升",
    "语言缺陷": []
}


def dump(d) -> str:
    return json.dumps(d, ensure_ascii=False, indent=2)


def main() -> None:
    orig = io.open(P, encoding="utf-8", newline="").read()
    d = json.loads(orig)
    items = d["条目"]

    # ── 无损往返自证：不追加时，重序列化必须与原文件逐字节一致 ──
    rt = dump(d).replace("\n", "\r\n")
    if rt != orig:
        print("⛔ 无损往返自证失败：重序列化与原文件不一致")
        print(f"   原长度 {len(orig)} / 重排长度 {len(rt)}")
        for i, (a, b) in enumerate(zip(orig, rt)):
            if a != b:
                print(f"   首个差异 @{i}: 原 {orig[max(0,i-40):i+40]!r}")
                print(f"                重排 {rt[max(0,i-40):i+40]!r}")
                break
        raise SystemExit(1)
    print(f"✅ 无损往返自证通过（{len(items)} 条目，逐字节一致）")

    last = items[-1].get("编号")
    NEW["编号"] = int(last) + 1
    print(f"   现有最大编号 {last} → 新条目编号 {NEW['编号']}")

    items.append(NEW)
    out = dump(d).replace("\n", "\r\n")
    io.open(P, "w", encoding="utf-8", newline="").write(out)

    # 回读校验
    back = json.loads(io.open(P, encoding="utf-8", newline="").read())
    assert len(back["条目"]) == len(items), "回读条目数不符"
    assert back["条目"][-1]["编号"] == NEW["编号"], "回读编号不符"
    raw = io.open(P, encoding="utf-8", newline="").read()
    assert not raw.endswith("\n"), "出现了尾换行"
    assert "\r\n" in raw, "CRLF 丢失"
    print(f"✅ 已追加 # {NEW['编号']}，回读校验通过（{len(back['条目'])} 条目）")


if __name__ == "__main__":
    main()
