# 第33轮 任务4 交付报告 —— _P0A_NEVER_SPLIT「到」字逐条验证

> 日期：2026-09-15 ｜ 优先级 P0 ｜ 修改区域：`light-merge/src/lexer.py` 的 `_P0A_NEVER_SPLIT`
> 结论：**可删**。撤除后全语料 token 零变化；「到」移除后进入 F/HM，但语料形态为数字范围独立汉字段；**且「到」同时位于 DUAL（`_P0A_HEAD_MERGE_DUAL`，8 字之一），移除 NEVER_SPLIT 后 DUAL 仍生效，范围/词首并入不受影响**。

---

## 1. 目标
对 `_P0A_NEVER_SPLIT` 中的「到」字逐条验证，判定是否可移除（三重判据 G1∧G2∧G3）。

## 2. 场景定位（语料分类）
- **数字范围（独立汉字段）**：`1到10` / `1到10步2` —— 「到」前后为数字/变量，属「整串即关键字」兜底，不依赖 NEVER_SPLIT。
- **复合名成分（词首）**：到达 / 到底 / 到位 —— 词首由 DUAL（含「到」，作「到位」头并入）兜底整词。
- **函数调用 / 变量名**：无高频「到」收尾标识符。

## 3. 三重判据
| 判据 | 口径 | 结果 |
|---|---|---|
| **G1 语料门** | 撤「到」后全语料 tokenize 逐文件 sha 比对 | **通过**：变化文件 = 0 / 857，新增错误 = 0 |
| **G2 编译门** | 含「到」语句可编译 | **通过**：合成探针 `从1到10` tokenize 无异常；全语料 token 流一致 ⇒ 解析一致 |
| **G3 边界门** | 六类边界形态 token 流不变 | **通过**：`遇到`（到 词尾）基线/变体均为单 IDENTIFIER；数字范围 `1到10` 不受影响；DUAL「到位」词首并入不变 |

### 关键发现：到 进入 F/HM，但 DUAL 仍覆盖词首 + 语料不受影响
活性探针确认：撤「到」后 `NEVER_SPLIT True→False`、`F False→True`、`HM False→True`、`_P0A_SUFFIX_SPLIT_SINGLE True→False`。
「到」移除后由「后缀排除集」移入 F 与 HM；但「到」语料唯一形态为**数字后独立汉字段**，词首并入（需后随汉字）不触发；且「到」本就在 DUAL（`_P0A_HEAD_MERGE_DUAL`），词首 `到位` 等由 DUAL 兜底，与 NEVER_SPLIT 正交。故全语料 token 流零变化。
终验（`_antirun_r33_final_zeroregress.py`）真实 lexer（`NEVER_SPLIT=[]`）HM 含「到」共 25 字，与快照比对 0 变化。

## 4. 验证方法
- 引擎 `_antirun_r33_t1234_NEVER_SPLIT逐字验证.py`：快照基线 + 单字变体，全语料比对。
- 单字脚本 `_antirun_r33_t4_到字验证.py` → `_antirun_r33_t4_到字验证.json`（变化=0）。
- 活性探针 `_r33_probe_active.py`：确认 F/HM/SUFFIX 派生集差异与边界形态。

## 5. 执行删除
- 已应用：`_P0A_NEVER_SPLIT` 清零（含「到」）。
- **HM 自校验更新**：「到」合法进入 HM（与 DUAL 正交，二者不互斥），文末断言已扩充为 `(R26∪R27∪R28 移除 ∪ {'步','至','到'})`，import 自检通过。DUAL 字面量（含「到」）未改动。

## 6. 铁律核对
- ✅ 只改「到」所在集合（与模/步/至并集清零）；DUAL 表未动。
- ✅ 逐条隔离验证。
- ✅ G1∧G2∧G3 全通过；特别确认 DUAL 中的「到」不受影响。
- ✅ 删除后全量反跑零回归。

## 7. 交付物
- `light-merge/src/lexer.py`
- `lightharness/_task4_R33_NEVER_SPLIT到字验证.md`
- `lightharness/_antirun_r33_t4_到字验证.py` + `_antirun_r33_t4_到字验证.json`
- 全量反跑证据：`_antirun_r33_final_zeroregress.json`
