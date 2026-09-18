# R57 任务5 交付 —— docs + MEMORY + 移档

> 日期：2026-09-18 ｜ 内容：对标清单 #196 追加（含无损往返自证）、MEMORY.md 回填（任务3/4 + 收口 + 全量纪律 + dispatch 工具）、R57 探针移档、#195 归因更正收口
> 本报告由主 agent（豆包）在收口阶段补写，WorkBuddy 侧交付物为 _task1~4_R57_*.md。

---

## 一、对标清单 #196 追加（成功，无损）

- 文件：`docs/功能对标/对标清单.json`
- **无损往返自证通过**（`json.dumps(ensure_ascii=False, indent=1).replace("\n","\r\n")` == 原始全文），随后插入，写回保持 **indent=1 + CRLF + 无文件尾换行**。
- 回读验证：条目数 195 → **196**，编号连续 1..196，历史条目（抽查 #195）未变。
- #196 覆盖：L-173 词法器修复 / L-174 登记 / flaky+性能断言处置 / G7 复现用例入 tests / G8 gate_remote --py / 101 存量红画像 / **#195「16 条红」归因更正** / 全量纪律。

## 二、#195 归因更正（保留原文，不篡改历史）

R56 写入 #195 的「R54 引入 16 条新红（NameError: name '错误' is not defined）」经 R57 复核**不成立**：

| 证据 | 结果 |
|---|---|
| 6 份 0.82 junitxml 交叉（任务4） | 16 条只在 5/6 轮红，**最终真基线 072454 该文件 0 红**（反常） |
| 0.82 当前副本定向跑（任务1 ×3 轮 + 主 agent 独立复核） | `tests/test_stdlib_phase9.py` **57 passed**（含 测试断言工具 16 条） |
| 结构核对 | `错误 ∉ VERB_ARITY / STDLIB_VERB_ARITY / ALL_VERB_ARITY`，而 R54 两处改动全以 `VERB_ARITY` 为键 → **结构上碰不到 `错误`** |

**处置**：不改 `src/parser_stmt.py`（无失败用例支撑的改动 = 纯风险）；#195 原文保留、在 #196 备注中更正并给证据；MEMORY.md 对应条目已标注「R57 已证不成立/不可复现」。

## 三、MEMORY.md 回填

- 已在既有 R57 任务1+2 段落后补：任务3（G7/G8 闭环 + 判别力实证）、任务4（100 红 12 类画像 + cross_platform 预警）、**R57 全量纪律**（不并行全量 / 一轮 1 次 / 只走 0.82 py3.12 / 本机不跑全量）、**dispatch.ps1 新工具**（CodeBuddy CLI 指挥 + deepseek-v4-flash 1M 上下文 + UTF-8 BOM 坑）。
- 全量纪律与 dispatch 工具为跨轮长期有效项，已写入「当前轮次状态」之外的长期区（含于 R57 段，后续轮次可上提）。

## 四、探针移档（11 个文件 → `docs/历史存档/R57探针/`）

| 来源 | 文件 |
|---|---|
| 任务1 | `_r57_probe_tokens.py`（切分探针）、`_r57_dump_tokens.py`（全语料 A/B token 转储）、`_r57_cmp_one.py`（单文件 diff）、`_r57_082.py`（0.82 执行助手）、`_r57_lexer_base.py`（HEAD 版 lexer 快照，256KB）、`_r57_tok_base.tsv` / `_r57_tok_patched.tsv` / `_r57_tok_patched2.tsv`（38084 语料 token 流，各 2.9MB） |
| 任务2 | `_r57_diag_flaky.py`（flaky 根因打点诊断） |
| 任务3 | `_r57_task3_副本核对.py`、`_r57_task3_082定向验证.py`（已在 R57探针/） |
| 收口复核（主 agent） | `_r57_verify_phase9.py`（0.82 phase9 独立复核） |

一次性扫描工具（`_r57_scan_models.py` / `_r57_scan_ds.py`，分析 CodeBuddy CLI 内部用）已删除，不留档。

## 五、遗留 / 说明

1. `2026-09-18.md` 逐日日志的 R57 收口段随路M 结果一并补写（见路M 交付）。
2. 对标清单 #196 证据已含 `_task5_R57_docs+移档.md` 本身与 `R57探针/` 目录。
3. L-174（设甲为三）按任务书登记未修，留给专门词法轮。
