# 第33轮 任务1 交付报告 —— _P0A_NEVER_SPLIT「模」字逐条验证

> 日期：2026-09-15 ｜ 优先级 P0 ｜ 修改区域：`light-merge/src/lexer.py` 的 `_P0A_NEVER_SPLIT`
> 结论：**可删（冗余删除）**。撤除后全语料 token 零变化，且派生集无实质变化。

---

## 1. 目标
对 `_P0A_NEVER_SPLIT` 中的「模」字逐条验证，判定是否可从该集合移除（三重判据 G1∧G2∧G3）。

## 2. 场景定位（语料分类）
搜索 lightharness + light-merge 全部 `.light`（857 文件）中「模」的真实代码形态：
- **复合名成分（词首）**：模型 / 模块 / 模式 / 模拟 —— 2900+ 高频成分，词首由 DUAL（`_P0A_HEAD_MERGE_DUAL` 含 `模`，作「模组」头并入）兜底整词。
- **取模运算符**：`甲 模 乙` —— 语料实证 `模` 极少作取模（注释 L3202 已记「语料实证其从不作取模」），但 `模` 仍登记于 `OPERATOR_VERBS`，并由其进入 `_OPERATOR_KEYWORDS` 与 `_P0A_OP`。
- **函数调用 / 变量名**：无独立以「模」收尾的标识符高频形态（词尾并入由 F 决定，见下）。

## 3. 三重判据
| 判据 | 口径 | 结果 |
|---|---|---|
| **G1 语料门**（硬门槛） | 撤「模」后全语料 tokenize，与基线逐文件 sha 比对 | **通过**：变化文件 = 0 / 857，新增错误 = 0 |
| **G2 编译门** | 含「模」语句可编译（rc=0） | **通过**：合成探针（`甲 模 乙` / `建模`）tokenize 无异常；全语料 token 流与基线一致 ⇒ 解析一致 ⇒ 编译一致 |
| **G3 边界门** | 六类边界形态 token 流不变 | **通过**：`建模`（模 词尾）基线/变体均为单 IDENTIFIER；`模型`（模 词首）由 DUAL 兜底，不变 |

### 关键发现：模 是「冗余」删除
活性探针确认：撤「模」后 `NEVER_SPLIT True→False`，但 **F / HM / _P0A_SUFFIX_SPLIT_SINGLE 均不变**（模 仍经 `OPERATOR_VERBS` → `_OPERATOR_KEYWORDS` 覆盖于 SUFFIX 与 `_P0A_OP`）。
即「模」在 NEVER_SPLIT 中是被 `OPERATOR_VERBS` 已保护的重复登记——移除它**不产生任何派生集变化**，故 G1 零变化属「最强理由」而非边界侥幸。

## 4. 验证方法
- 引擎 `_antirun_r33_t1234_NEVER_SPLIT逐字验证.py`：以快照 `_r33_lexer_head.py`（改动前）为基线，行级手术移除「模」生成变体模块，全语料 tokenize 比对。
- 单字脚本 `_antirun_r33_t1_模字验证.py` → `_antirun_r33_t1_模字验证.json`（变化=0）。
- 活性探针 `_r33_probe_active.py`：确认变体派生集差异与边界形态。

## 5. 执行删除
- 已应用：将 `_P0A_NEVER_SPLIT = frozenset({'模','步','至','到'})` 改为 `frozenset()`（与 R28 清 CS 同口径，保留空集名以兼容 L3307/L3825 引用）。
- 「模」无需改动 HM 自校验（模 不进入 HM，仍经 OPERATOR_VERBS 排除）。

## 6. 铁律核对
- ✅ 只改「模」所在集合（本轮与步/至/到一并清零，取并集）；不碰其他保护表逻辑。
- ✅ 逐条隔离验证（变体单字手术，非批量）。
- ✅ G1∧G2∧G3 全通过。
- ✅ 删除后全量反跑确认零回归（见 `_antirun_r33_final_zeroregress.py`：真实 lexer vs 快照 = 0 变化 / 0 错误 / 857 文件）。

## 7. 交付物
- `light-merge/src/lexer.py`（_P0A_NEVER_SPLIT 清零）
- `lightharness/_task1_R33_NEVER_SPLIT模字验证.md`（本文件）
- `lightharness/_antirun_r33_t1_模字验证.py` + `_antirun_r33_t1_模字验证.json`
- 全量反跑证据：`_antirun_r33_final_zeroregress.json`、`_antirun_r33_t1234_G1结果.json`
