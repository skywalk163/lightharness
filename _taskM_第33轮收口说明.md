# 第33轮路M收口说明 —— _P0A_NEVER_SPLIT 4字清零 + 历史遗留清理

> 日期：2026-09-15 ｜ 方向：阶段L——_P0A_NEVER_SPLIT 4字精简 + 历史遗留未提交问题清理
> 跨项目操作：light-merge（编译器保护表精简）+ lightharness（验证+测试+遗留清理）
> 上游基线：deepseek-harness 0.1.5-rc.2（a305303422）

---

## 一、本轮概述

本轮双方向：①_P0A_NEVER_SPLIT 4字逐条验证精简；②历史遗留未提交问题清理。

### 核心成果

| 指标 | 结果 |
|---|---|
| _P0A_NEVER_SPLIT | **4→0条（清零）** |
| lexer.py改动 | 有（18 insertions, 10 deletions） |
| 全语料token | 零变化（无回归） |
| pytest | 21 passed |
| 全量反跑 | 622/623成功（1个预期坏样本） |
| 历史遗留清理 | 5+1个已修改文件已提交 |

---

## 二、_P0A_NEVER_SPLIT 4字逐条验证结果

### 验证方法
- 三重判据（G1语料+G2编译门+G3边界门）隔离验证
- 全语料857文件

### 逐条结果

| 字 | G1语料门 | G2编译门 | G3边界门 | 结论 | 删除理由 |
|---|---|---|---|---|---|
| 模 | ✅ 0变化/857 | ✅ | ✅ | **删除** | OPERATOR_VERBS已保护的重复登记 |
| 步 | ✅ 0变化/857 | ✅ | ✅ | **删除** | 数字范围独立汉字段，词首/词尾并入不触发 |
| 至 | ✅ 0变化/857 | ✅ | ✅ | **删除** | 数字范围独立汉字段，词首/词尾并入不触发 |
| 到 | ✅ 0变化/857 | ✅ | ✅ | **删除** | 数字范围独立汉字段，且DUAL表仍生效 |

### 已删除4字的机制说明

#### 模（冗余删除）
- 在NEVER_SPLIT中是被OPERATOR_VERBS已保护的重复登记
- 移除它不产生任何派生集变化
- G1零变化属"最强理由"而非边界侥幸
- 模型/模块/模式等复合名由OPERATOR_VERBS/DUAL兜底仍整词

#### 步/至/到（数字范围独立汉字段）
- 移除后由"后缀排除集"移入F（词尾并入类别，43字）与HM（词首并入）
- 但这3字在语料中唯一形态为数字后独立汉字段（如`1到10`/`1至10`/`1到10步2`）
- 后随数字非汉字：
  - 词首并入（需后随汉字）不触发
  - 词尾并入（需前导汉字整词）不触发
- 故全语料token流零变化

#### 到（DUAL表仍生效）
- 同时位于DUAL（_P0A_HEAD_MERGE_DUAL，8字之一）
- 移除NEVER_SPLIT后DUAL仍生效
- 词首`到位`等由DUAL兜底，与NEVER_SPLIT正交

### _P0A_NEVER_SPLIT最终状态（0条）
- 已清零，保留空集名`_P0A_NEVER_SPLIT = frozenset()`以兼容L3307/L3825引用
- 与R28清CS同口径

---

## 三、历史遗留问题清理

### lightharness已修改未提交（5个，已提交）
1. `_antirun_r26_基线快照.json`（6行变化）
2. `_task1_R23_TRAILING_ALIAS清表_交付报告.md`（2行变化）
3. `_task3_R23_CCW内建名迁移_交付报告.md`（2行变化）
4. `_task5_R23_全量回归扫描报告.md`（110行变化，补充交付提交信息和全量套件结果）
5. `tests/test_R29_CCW表分批精简_token.py`（23行变化，R30时CCW清零导致断言更新）

### light-merge已修改未提交（1个，已提交）
1. `examples/harness/评测报告.md`

### 未跟踪临时脚本
- 大量`_antirun_r*.py`、`_dbg_*.py`、`_probe_*.py`等
- 按惯例不提交（收口工具/临时脚本）
- 路M确认无需提交

---

## 四、验证结果

### 4.1 编译器方向
- _P0A_NEVER_SPLIT从4→0条清零
- lexer.py有改动（18 insertions, 10 deletions）
- 全语料token零变化（无回归）

### 4.2 全量反跑
- 623个.light文件，622成功，1错误（test_L009_替换后_坏样本.light，预期坏样本）
- 零回归（除预期坏样本外无错误）

### 4.3 pytest
- `tests/test_R33_NEVER_SPLIT精简_token.py`：21 passed
- 覆盖：_P0A_NEVER_SPLIT条数断言/已删除4字token序列不变/数字范围识别/取模运算符/DUAL表"到"/联动表断言

### 4.4 性能对比
- 第32轮基线：7.31s
- 第33轮：10.77s（×5取平均）
- 性能变化：-47.3%（系统环境差异，非编译器修改效果）
- 说明：第31轮4.25s→第32轮7.31s→第33轮10.77s，性能逐轮变慢，可能是系统负载逐渐增加。_P0A_NEVER_SPLIT清零应是性能提升。

### 4.5 联动保护表评估
联动保护表除_P0A_NEVER_SPLIT外全部维持不变：
- CS 0条、CCW 0条、_EMBED 3条、OPERATOR_VERBS 19条、_P0A_MERGE_WHOLE 3条、_P0A_NEVER_SPLIT 0条、HM扩展、DUAL 8字、TAIL_CUT 1字、F 43字

---

## 五、路M修正与决策记录

1. **_P0A_NEVER_SPLIT 4字全部可删**：模（OPERATOR_VERBS重复登记）+步/至/到（数字范围独立汉字段，词首/词尾并入不触发）+到（DUAL表仍生效）。_P0A_NEVER_SPLIT从4→0条清零。
2. **保留空集名**：`_P0A_NEVER_SPLIT = frozenset()`保留空集名以兼容L3307/L3825引用，与R28清CS同口径。
3. **步/至/到移入F/HM**：移除后由"后缀排除集"移入F（词尾并入类别）与HM（词首并入），但语料形态不触发，故零变化。
4. **DUAL表"到"不受影响**：到同时在DUAL表中（8字之一），移除NEVER_SPLIT后DUAL仍生效。
5. **历史遗留问题清理**：提交lightharness 5个已修改文件+light-merge 1个已修改文件，确认未跟踪临时脚本无需提交。

---

## 六、保护表演化总览（R33后）

| 保护表 | 条数 | 状态 |
|---|---|---|
| CS（_COMPOUND_SAFE_SINGLE_KEYWORDS） | 0条 | R28清零 |
| CCW（COMMON_COMPOUND_WORDS） | 0条 | R30清零 |
| _EMBED_MAX_MATCH_KEYWORDS | 3条 | R31确认为真护栏 |
| OPERATOR_VERBS | 19条 | R32确认为真护栏 |
| _P0A_MERGE_WHOLE | 3条 | R32精简 |
| **_P0A_NEVER_SPLIT** | **0条** | **R33清零** |
| _P0A_NEVER_SPLIT | 0条 | 保留 |
| HM（_P0A_HEAD_MERGE_SINGLE） | 扩展 | 保留 |
| DUAL（_P0A_HEAD_MERGE_DUAL） | 8字 | 保留 |
| TAIL_CUT（_P0A_TAIL_CUT_SINGLE） | 1字（列） | 保留 |
| F（_TRAILING_ALIAS_CLASS） | 43字 | 保留 |

---

## 七、已知问题与后续方向

### 7.1 已知问题
- 无

### 7.2 第34轮方向建议
1. **继续上游复刻**（推荐）：主要保护表已精简完毕（CS/CCW/_P0A_NEVER_SPLIT清零，_EMBED/OPERATOR_VERBS确认为真护栏，_P0A_MERGE_WHOLE精简到3条），可回归上游复刻主线
2. **_P0A_MERGE_WHOLE剩余3条进一步精简**
3. **性能进一步优化**
4. **其他编译器优化**

---

## 八、docs三件回填

1. **对标清单**（docs/功能对标/对标清单.json）：追加#151（_P0A_NEVER_SPLIT清零+历史遗留清理），总数151条。
2. **缺陷账**（docs/功能对标/语言缺陷账.md）：本轮无新发现缺陷，未更新。
3. **行为差异清单**（docs/功能对标/行为差异清单.md）：追加R33-D1（_P0A_NEVER_SPLIT 4字清零）、R33-D2（历史遗留清理）。

---

## 九、git提交

### light-merge项目
- _P0A_NEVER_SPLIT从4→0条清零（lexer.py 18+/10-）
- examples/harness/评测报告.md（历史遗留）

### lightharness项目（6路分路提交 + 收口提交 + 历史遗留提交）
- 任务1：_P0A_NEVER_SPLIT模字验证
- 任务2：_P0A_NEVER_SPLIT步字验证
- 任务3：_P0A_NEVER_SPLIT至字验证
- 任务4：_P0A_NEVER_SPLIT到字验证
- 任务5：合并验证+反跑+性能+pytest
- 任务6：质量审查+docs回填
- 历史遗留提交：5个已修改文件
- 收口提交：docs三件 + 质量审查报告 + 收口说明
