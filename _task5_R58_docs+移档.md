# 任务5 R58：docs + MEMORY + 移档

> 日期：2026-09-18 ｜ 轮次：R58 ｜ 性质：docs 定稿前的准备工作

---

## 一、对标清单 #197 追加

**文件**：`lightharness/docs/功能对标/对标清单.json`

- 追加前：196 条（#196 为 R57 词法+codegen 修复轮）
- 追加后：197 条
- **格式纪律自证通过**：
  - 无 BOM ✅
  - indent=1 ✅
  - CRLF 行尾 ✅
  - 无文件尾换行 ✅
  - 无损往返：json.loads(json.dumps(indent=1, ensure_ascii=False)) 后条目数=197、#196 内容未变、#197 在位 ✅
  - 读盘二次校验通过 ✅
- 脚本：`docs/历史存档/R58探针/_r58_append_benchmark.py`

**#197 内容摘要**：R58 词法收尾与环境红清账轮——L-174 修复 + 16 条词法红 + 18 条环境红 + 65 条语义债归因画像。

---

## 二、MEMORY.md 更新

**文件**：`.workbuddy/memory/MEMORY.md`

追加「R58 任务4+5」条目，记录：
- 任务4 三十条归因结论摘要（R59 行动清单）
- 任务5 docs/MEMORY/移档完成
- 纪律补充：环境红先试装依赖、词法保护表改动必做 token A/B

> 注：MEMORY.md 在任务4执行期间已被任务1 agent 更新（L-174 已修、lexer 保护表/R58 分支改动已记录），本次在其基础上追加，未覆盖已有内容。

---

## 三、探针移档

**目标目录**：`lightharness/docs/历史存档/R58探针/`

移入 30 个文件：
- 任务1 探针：_r58_dump_tokens.py、_r58_extract_lexer_reds.py、_r58_i196.txt、_r58_lexer_reds.txt、_r58_peek_reds*.py/txt、_r58_probe1~6.py/txt、_r58_tok_*.tsv/txt
- 任务2 探针：_r58_task2_0.82.py、_r58_task2_check.log、_r58_task2_install.log、_r58_task2_test.log
- 任务3 探针：_r58_task3_A.json、_r58_task3_工作底表.json
- 任务5 探针：_r58_append_benchmark.py
- 任务4 中间文件：_task4_R58_30条原始message.txt

与 R56/R57 同规（`docs/历史存档/R5N探针/`）。

---

## 四、交付物清单

| 文件 | 说明 |
|---|---|
| `lightharness/docs/功能对标/对标清单.json` | #197 已追加（196→197） |
| `.workbuddy/memory/MEMORY.md` | R58 任务4+5 条目已追加 |
| `lightharness/docs/历史存档/R58探针/` | 30 个探针文件已移档 |
| `lightharness/_task4_R58_其余存量归因.md` | 任务4 Markdown 报告 |
| `lightharness/_task4_R58_其余存量归因明细.json` | 任务4 结构化明细 |
| `lightharness/_task5_R58_docs+移档.md` | 本文件 |

---

## 五、铁律遵守

- #196 内容未改（历史记录），只追加 #197 ✅
- 对标清单无损往返自证通过后才写盘 ✅
- 未 commit（外发 agent 不 commit，主 agent 统一合流）✅
- 未跑全量测试 ✅
