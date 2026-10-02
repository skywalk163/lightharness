# -*- coding: utf-8 -*-
"""Day3 凌晨 T5：缺陷账新增 LP-D-018 / LP-D-019 两行（幂等，带哨兵）。

保真：CRLF + BOM 用 bytes 读写；只在指定锚点后插入一段，不动其它行。
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

LEDGER = Path("G:/dswork/duan-light-merge/lightharness/docs/功能对标/语言缺陷账.md")
GUARD = "Day3 凌晨立账"

ANCHOR = "- 复现入口：`python light-merge/.venv/Scripts/python.exe lightplugin/运行.py 集成/全量挂载.light`"

BLOCK = f"""
**【{GUARD} 2026-10-03】** —— 以下两行源自 Day2 深夜场 T2「全账终审」时挖出的两条**新观察**。
当时按纪律「只挂观察、不改状态」，本批正式立账并配可复跑探针，
避免重演 LP-D-010「真相早就变了、账还停在旧状态」那种漂移。

| 编号 | 现象 | 最小复现 | 期望能力 | 状态 | 复现套件 |
|------|------|----------|----------|------|----------|
| LP-D-018 | **SRC 后端 `返回 <关键字词变量名>` 取不到该变量的值**：函数内 `打印(转字符串(跳过))` 正常输出 `[7]`，但 `返回 跳过` 到调用方变成 `None`；ANTLR 后端同样代码正确返回 `[7]` | `probes/lp018_返回关键字词变量.light`：`段落 乙(值): 设 跳过 为 [] / 跳过.追加(值) / 打印(转字符串(跳过)) / 返回 跳过` → SRC 输出两行 `[7]` 与 `None`；ANTLR 输出 `[7]` 与 `[7]`。反向对照 `lp018_对照_普通名.light`（变量名换成普通名「列表」）两后端均 `[7]`+`[7]` ⇒ 缺口来自「关键字词作变量名 + `返回`」这一组合，不是「返回列表」本身 | 两后端一致：`返回` 应返回该变量的值（与 LP-D-013 同族，但落在 `返回` 语句位而非成员访问位） | 已定性待修（{GUARD}） | 探针 `docs/国庆7天/probes/lp018_返回关键字词变量.light`、`lp018_对照_普通名.light`；命令 `python ../light-merge/cli/light.py run <探针> --backend {{src,antlr}}`；报告 `Day3凌_T5_新账立账.md §二` |
| LP-D-019 | **ANTLR 后端覆盖面缺口（三例同源）**：① 词法关键字 `回调`（`K_CALLBACK`）作段名/循环变量 → `期望 ID，却遇到了 '回调'`；② 判型族内置 `是数字` / `是数字符` 未注册 → `未定义的变量`；③ 索引切片写法 `"abcdef"[1:3]` → 解析失败。**SRC 后端三例均正常** | ① `probes/lp010_重名_严格.light`（ANTLR rc=1）；② `probes/lp019_判型族.light`（SRC 输出 `True`/`False`/`True`，ANTLR rc=1 `未定义的变量: '是数字'`）；③ `probes/lp019_索引切片.light`（SRC 输出 `bc`，ANTLR rc=1 `第4行 第13列 语法错误`） | ANTLR 后端在「内置符号注册」与「词法上下文」上与 SRC 后端对齐；②③ 不涉及语义歧义，属纯覆盖面补齐；① 需按 LP-D-013 的「范式 A 上下文软关键字」同法处理 | 已定性待修（{GUARD}） | 探针 `probes/lp019_判型族.light`、`lp019_索引切片.light`、`lp010_重名_严格.light`；命令同上；报告 `Day3凌_T5_新账立账.md §二` |
"""


def main():
    b = LEDGER.read_bytes()
    bom = b[:3] == b"\xef\xbb\xbf"
    text = b.decode("utf-8-sig")
    nl = "\r\n" if "\r\n" in text else "\n"
    if GUARD in text:
        print("[账] 哨兵已存在，判定已应用，跳过（幂等）")
        return
    if ANCHOR not in text:
        raise SystemExit("[账] 找不到锚点行，中止（避免插错位置）")
    lines = text.split(nl)
    idx = lines.index(ANCHOR)
    block = [l for l in BLOCK.split("\n")]
    # 插入：锚点行之后 + 一个空行
    lines[idx + 1:idx + 1] = [""] + block
    out = nl.join(lines)
    data = out.encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    LEDGER.write_bytes(data)
    print(f"[账] 已在锚点后插入 {len(block)} 行（新账 LP-D-018/019）")


if __name__ == "__main__":
    if "--dry" in sys.argv:
        print(BLOCK)
    else:
        main()
