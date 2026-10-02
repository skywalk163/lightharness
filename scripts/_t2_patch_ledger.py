# -*- coding: utf-8 -*-
"""Day2深夜 T2：缺陷账终态刷新（幂等，带哨兵 guard；只改「状态」列与「复现套件」列）。

改两本账：
  1) lightharness/docs/功能对标/语言缺陷账.md   （CRLF + BOM，bytes 读写）
  2) lightplugin/_archive/reports/语言缺陷反馈.md （LF，无 BOM）

幂等：所有改动都带哨兵串；已应用则跳过（不会二次插入）。
保真：主账按「| 分隔的表格单元」定点替换，第 0~3 列（编号/现象/最小复现/期望能力）原样保留。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path("G:/dswork/duan-light-merge")
LEDGER_MAIN = ROOT / "lightharness/docs/功能对标/语言缺陷账.md"
LEDGER_SRC = ROOT / "lightplugin/_archive/reports/语言缺陷反馈.md"

GUARD = "Day2深夜 T2 刷新"
SEP = " | "

# ── 主账：{行号(1-based): {列索引: 新值}}  4=状态列, 5=复现套件列 ──────────
MAIN_CELLS = {
    1712: {
        4: (
            "✅ **销账（SRC 后端）** ｜ ⚠️ **ANTLR 后端原始形态仍红 → 并入 LP-D-013 族**（%s）："
            "真因 Day1 已由 `src/lexer.py:_lpd013_010_reclassify_declared_keywords`（:1227-1388）"
            "按「声明过的名字在标识符位重分类为 IDENTIFIER」修掉，账行滞后才显示「已定性待修」，非本批新修；"
            "本批实测：三探针 SRC 后端全 rc=0（均输出 `a`），ANTLR 后端仅 `lp010_重名` rc=0，"
            "`lp010_重名_严格`/`lp010_账内原文`（段名与循环变量同为词法关键字 `回调`）仍 rc=1 ——"
            "根因是 `LightLangLexer.g4` 的 `K_CALLBACK` 词法缺口，属 LP-D-013 同族，非 LP-D-010 本体"
        ) % GUARD,
        5: (
            "探针 `docs/国庆7天/probes/lp010_{重名,重名_严格,账内原文}.light`；"
            "命令 `python ../light-merge/cli/light.py run <探针> [--backend antlr]`；"
            "日志 `logs/day2-night/T1_*.log`；报告 `Day2夜_T1_LPD010真修.md` + `Day2深_T2_缺陷账终态刷新.md §二`"
        ),
    },
    1713: {
        4: (
            "**已改靶 + ANTLR 收口（Day2，2026-10-02）**：默认 SRC 后端本已可用；真实缺口为 ANTLR 后端解析失败"
            "（`多余的 '结束'`）。已修 g4 `tryStmt`（单 `结束` + 多捕获 + 可选 `最终`）、"
            "两层缩进预处理识别 `捕获`/`最终` 为延续子句、AST/interpreter 支持多捕获+finally。"
            "4 探针两后端全通过，门三元零回归（failed 61→61）。"
            "**本批复跑（%s）**：4 探针 × 2 后端 = 8 次 CLI 调用 **rc 全 0**，输出逐项一致"
            "（probe→`TRY_OK`；probe2→`CATCH_OK: boom`+`AFTER`；finally→`TRY_OK`+`FINALLY_OK`+`AFTER`；"
            "multi_catch→`CATCH1: boom`+`FINALLY`+`AFTER`）→ **双后端收口确认**，无新增残余"
        ) % GUARD,
    },
    1714: {
        4: (
            "**部分收口（Day2 夜场 2026-10-02，6c1c31e 三模块 B 入口 + A/B 等价证明 + 探针固化）**："
            "任务拉取泵 / 工具执行 / 代理循环 三模块与代理.驱动调度层已落地原生并发 B 入口"
            "（`异步 段落`/`等待`/`创建任务`/`并发等待`、`轮询抽`、`并发轮询`、`具并发执行`、`具异步执行`、"
            "`具登记异步处理`、`循异步派发`、`注册协监听`、`驱动异步`），9 用例 A/B 等价证明全绿。"
            "**本批复跑（%s，本机 Windows + light-merge/.venv，reps=1，耗时 67.5s）**："
            "`用例总数=9 通过=9 失败=0`（含反向哨兵「同步段落内写 `等待` 必须报错」），rc=0。"
            "仍靠注入式的场景：同步段落内写 `等待` 必须报错（反向哨兵用例为证）、"
            "串行桥接与调用方手写 while 仍保留（A 路径不退场）→ 维持「部分收口」"
        ) % GUARD,
    },
    1722: {
        4: (
            "✅ **已修复（双后端）** ｜ ANTLR 侧由 Day2N T2 交付（light-merge `221db4fc6`，%s）："
            "改法为 `LightLangParser.g4` 的 `primary`/`identifier_like` 新增 `K_EXPORT`/`K_CONTINUE` 分支"
            "（范式 A 上下文软关键字，不带 ID 跟随、不带 `.`/`(` 后缀，故不误吞 `导出`/`跳过` 语句），"
            "visitor 还原中文名，`interpreter_core` 补 `LightBoundListMethod`（追加/移除/弹出/反转/清空）。"
            "**本批实测**：`lp013_probe` SRC/ANTLR **均 rc=0 且输出 `[1]`**；`lp013_probe2` 两后端均 rc=0、"
            "无「无法识别的语法元素」（`tests/unit/test_Day4_LP013_探针回归.py` 断言口径）。"
            "⚠️ **新观察（未并入本行状态，建议单独立项）**：`lp013_probe2` SRC 输出 `None` 而 ANTLR 输出 `[7]`，"
            "二分后定位到 **`返回 跳过`** 这一步（函数内 `打印(转字符串(跳过))` 两后端都得 `[7]`，"
            "SRC 的 `返回 跳过` 却取不到该变量）→ 属「关键字词作变量名时的 `返回` 取值」残留，"
            "**不影响成员访问解析本体**"
        ) % GUARD,
        5: (
            "探针 `probes/lp013_probe{,2}.light`；回归 `lightharness/tests/unit/test_Day4_LP013_探针回归.py`（4 用例）；"
            "报告 `Day2夜_T2_LPD013_ANTLR补缺口.md` + `Day2深_T2_缺陷账终态刷新.md §二`"
        ),
    },
    1732: {
        5: (
            "stdlib/内置核心判型.light:81-84 / :63-64；探针 `probes/lp016_probe.light`、`lp016_followup.light`。"
            "**本批复跑（%s，新观察，不改状态）**：`lp016_probe` SRC rc=0（输出 `True`/`False`/`True`，名实已对齐）；"
            "**ANTLR 后端 rc=1（未定义的变量：'是数字'）**，`lp016_followup` ANTLR 亦 rc=1"
            "（未定义的变量：'是数字符'）→ ANTLR 后端未注册判型族内置，SRC 侧才成立。"
            "属新观察项，建议下一批单独立账"
        ) % GUARD,
    },
    1742: {
        4: (
            "✅ **已修复（双后端，%s）** —— Day2N T2 用「范式 A 上下文软关键字」补齐 ANTLR："
            "`primary`/`identifier_like` 允许 `K_EXPORT`/`K_CONTINUE` 出现在表达式基名位与标识符位"
            "（不带 ID 跟随、不带 `.`/`(` 后缀，故不误吞 `导出`/`跳过` 语句）。"
            "本批实测两探针 × 两后端 = 4 次运行 **rc 全 0**。"
            "残留见 LP-D-013 行（`返回 跳过` 在 SRC 后端返回 `None`，建议单独立项）"
        ) % GUARD,
    },
}

# ── 源账：整句替换「- **状态**：…」───────────────────────────────────────
# 源账按**行号**整行替换（原 - **状态** 行无缩进，逐位置唯一）
SRC_LINES_TARGET = {
    275: "LP-D-010",
    296: "LP-D-011",
    313: "LP-D-012",
    351: "LP-D-013",
    403: "LP-D-016",
}
SRC_STATUS_NEW = {
    "LP-D-010": (
        "    - **状态**：✅ **销账（SRC 后端；%s）** —— 真因 Day1 已修"
        "（`src/lexer.py:_lpd013_010_reclassify_declared_keywords`），账行滞后才显示「待修」。"
        "本批复跑：`lp010_{重名,重名_严格,账内原文}` 三探针 SRC 全 rc=0；"
        "⚠️ ANTLR 后端仅 `lp010_重名` rc=0，另两例（`回调` 作段名/循环变量）仍 rc=1 —— "
        "属 K_CALLBACK 词法缺口，**并入 LP-D-013 族**。"
    ) % GUARD,
    "LP-D-011": (
        "    - **状态**：✅ **已改靶 + ANTLR 收口（Day2 2026-10-02）** —— SRC 后端本已可用；"
        "ANTLR 侧补齐 g4 `tryStmt` + 缩进预处理 + visitor/interpreter 多捕获与 finally。"
        "本批复跑（%s）：4 探针 × 2 后端 = 8 次运行 **rc 全 0**，双后端收口确认。"
    ) % GUARD,
    "LP-D-012": (
        "    - **状态**：⚠️ **部分收口（Day2 夜场 2026-10-02）** —— 三模块原生并发 B 入口已落地，"
        "9 用例 A/B 等价证明全绿。本批复跑（%s，本机 reps=1，67.5s）：`9 通过 / 0 失败`。"
        "仍靠注入式的场景：同步段落内写 `等待` 必须报错、串行桥接与手写 while 的 A 路径不退场。"
    ) % GUARD,
    "LP-D-013": (
        "    - **状态**：✅ **已修复（双后端；Day2N T2 2026-10-02，light-merge `221db4fc6`）** ——"
        "ANTLR 侧用「范式 A 上下文软关键字」补 `K_EXPORT`/`K_CONTINUE`。"
        "本批复跑（%s）：`lp013_probe` 两后端 rc=0 且输出 `[1]`，`lp013_probe2` 两后端 rc=0 无语法元素报错。"
        "⚠️ 残留（建议单独立项）：SRC 的 `返回 跳过` 取值缺口导致 `lp013_probe2` 输出 `None`（ANTLR 输出 `[7]`）。"
    ) % GUARD,
    "LP-D-016": (
        "    - **状态**：✅ **SRC 侧名实已对齐（Day2 2026-10-02）**，`lp016_probe` SRC rc=0"
        "（`True`/`False`/`True`）。⚠️ **本批新观察（%s）**：ANTLR 后端 rc=1（未定义的变量：'是数字'），"
        "即 ANTLR 未注册判型族内置 —— 建议下一批单独立账。"
    ) % GUARD,
}


def patch_main():
    b = LEDGER_MAIN.read_bytes()
    bom = b[:3] == b"\xef\xbb\xbf"
    text = b.decode("utf-8-sig")
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)

    already = [ln for ln in MAIN_CELLS if GUARD in lines[ln - 1]]
    if len(already) == len(MAIN_CELLS):
        print("[主账] 哨兵已存在于全部目标行，判定已应用，跳过（幂等）")
        return already

    changed = []
    for ln, cells in MAIN_CELLS.items():
        idx = ln - 1
        if GUARD in lines[idx]:
            print(f"[主账] 行 {ln} 已含哨兵，跳过")
            continue
        parts = lines[idx].split(SEP)
        last = len(parts) - 1
        for ci, val in cells.items():
            if ci > last:
                raise SystemExit(f"行 {ln} 只有 {last + 1} 个数据列，无法写第 {ci} 列，中止")
            parts[ci] = val + " |" if ci == last else val
        lines[idx] = SEP.join(parts)
        changed.append(ln)

    out = nl.join(lines)
    data = out.encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    LEDGER_MAIN.write_bytes(data)
    print(f"[主账] 已写回：{LEDGER_MAIN.name} 改动行 {changed}")
    return changed


def patch_src():
    text = LEDGER_SRC.read_text(encoding="utf-8", newline="")
    if GUARD in text:
        print("[源账] 哨兵已存在，判定为已应用，跳过（幂等）")
        return None
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)
    changed = []
    for ln, key in SRC_LINES_TARGET.items():
        idx = ln - 1
        old = lines[idx]
        if not old.startswith("- **状态**"):
            print(f"[源账] ⚠️ 行 {ln} 不是状态行（跳过）：{old[:60]}…")
            continue
        if GUARD in old:
            print(f"[源账] 行 {ln} 已含哨兵，跳过")
            continue
        new = SRC_STATUS_NEW[key].lstrip()   # 新串按未缩进写就位数不定，统一去左空白
        lines[idx] = new
        print(f"[源账] {key}（行 {ln}）\\n  旧: {old[:110]}…\\n  新: {new[:110]}…")
        changed.append(key)
    if changed:
        LEDGER_SRC.write_text(nl.join(lines), encoding="utf-8", newline="")
    print(f"[源账] 已写回：{LEDGER_SRC.name} 改动 {changed}")
    return changed


if __name__ == "__main__":
    if "--dry" in sys.argv:
        print("dry-run：仅预览")
        for ln, cells in MAIN_CELLS.items():
            for ci, v in cells.items():
                print(f"  main:{ln}:col{ci} -> {v[:160]}…")
        for k, v in SRC_STATUS_NEW.items():
            print(f"  src:{k} -> {v[:160]}…")
    else:
        patch_main()
        patch_src()
