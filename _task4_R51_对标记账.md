# 任务4（R51·P1）交付报告 —— 对标记账（#20/#84 改名 + #21/#57 上游已移除）

> 日期：2026-09-17 ｜ 状态：**完成**
> 交付物：`docs/功能对标/对标清单.json`（4 条记账）、本报告
> 铁律遵守：只改状态/描述（原版包+状态），功能字段零改动。
> 上游核实基线：`ea53423b60`（0.1.6-alpha.1 release），对比基线 `a305303422`（0.1.5-rc.2）。

---

## 一、上游事实核实（防误标，先查证后记账）

| 事实 | 核实方式 | 结果 |
|---|---|---|
| `packages/code-runtime` → `packages/ptc-runtime` | `git ls-tree ea53423b60 packages/` | 0.1.6 中无 `code-runtime`，有 `packages/ptc-runtime`（含 `ptc-runtime/`纯类型+词表 与 `ptc-runtime-node/`宿主执行）✅ 改名 |
| `experimental/code-runtime-python` → `experimental/ptc-runtime-python` | `git ls-tree -r ea53423b60` | 0.1.6 中仅存在 `packages/experimental/ptc-runtime-python/`（py/bootstrap.py、py/protocol.py、src/protocol.ts）✅ 改名 |
| `packages/e2b` 上游移除 | `git ls-tree -r ea53423b60 | grep packages/e2b | wc -l` | **0 个文件**（0.1.5-rc.2 时存在）✅ 已移除 |

## 二、四条记账内容（对标记账.json）

| 编号 | 更新字段 | 内容摘要 |
|---|---|---|
| #20 | 原版包 + 状态 | 原版包改记 `packages/ptc-runtime（0.1.6-alpha.1 起改名）`；状态追加「0.1.6记账：包改名；R51任务3 已对齐保留字表+PtcRun 契约纯逻辑面（判据 examples/test_R51_ptc契约.light，新条目归任务6登记）；宿主执行面维持登记不移植」。状态值保持 v2（宿主执行面仍存在） |
| #84 | 原版包 + 状态 | 原版包改记 `experimental/ptc-runtime-python/src/protocol.ts（0.1.6-alpha.1 起改名）`；状态追加「包改名，协议层语义不变（fd3 帧面已覆盖）；0.1.6 新增保留字表+契约见 R51任务3」。状态保持 done |
| #21 | 状态 | 追加「0.1.6记账：上游 0.1.6-alpha.1 已移除 packages/e2b（全树 0 文件），『维持不移植』记账作废，改记『上游已移除』；光明 src/e2b客户端.light 为既有本地实现，上游无对应」。状态保持 v2（作为上游无对应的登记态） |
| #57 | 状态 | 追加「0.1.6记账：上游已移除 packages/e2b，e2b 配套宿主变更的『维持登记不移植』记账作废，改记『上游已移除』」。状态保持 done（复刻面本身已完成，作废的只是宿主跟随记账） |

## 三、核验

- `git diff --stat docs/功能对标/对标清单.json`：6 处改动（4 条状态 + 2 条原版包），逐行复核无其他字段触碰；
- 更新后 JSON 可正常解析（184 条完整）；
- #20 状态中对新条目的引用采用「R51任务3」表述而非前向条目号（#185-#187 归任务6登记，避免悬空引用）。

## 四、口径说明

- 「上游已移除」与「维持不移植」是两种不同记账态：前者表示上游自身删包、光明侧实现转为
  无上游对应的本地能力（e2b 相关 src 保留不动）；后者表示上游存在但宿主面决定不跟随。
  本次 #21/#57 从后者改记前者。
