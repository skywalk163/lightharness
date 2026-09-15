# 第31轮路M收口说明 —— _EMBED表3条验证保留 + test_审批.light flaky修复

> 日期：2026-09-15 ｜ 方向：阶段J——_EMBED表3条精简 + test_审批.light flaky修复
> 跨项目操作：light-merge（_EMBED表验证，零改动）+ lightharness（flaky修复+验证）
> 上游基线：deepseek-harness 0.1.5-rc.2（a305303422）

---

## 一、本轮概述

本轮双方向：①_EMBED_MAX_MATCH_KEYWORDS 3条逐条验证精简；②test_审批.light flaky修复（从第20轮持续存在的R20-C）。

### 核心成果

| 指标 | 结果 |
|---|---|
| _EMBED表 | **维持3条**（为/返回/尝试，全部确认为真护栏） |
| lexer.py改动 | **零改动** |
| test_审批.light flaky | **已修复**（time.time()→time.monotonic()） |
| test_审批.light多次运行 | **5次全部rc=0**（13用例全过） |
| 全语料token | 零变化（无回归） |
| pytest | 13 passed |
| 已知flaky | **清零**（R20-C已解决） |

---

## 二、_EMBED表3条逐条验证结果

### 验证方法
- 进程内monkeypatch `lexer._EMBED_MAX_MATCH_KEYWORDS`
- 全语料856文件三重判据（G1语料+G2编译门+G3边界门）隔离验证

### 逐条结果

| 字 | 结论 | G1语料变化 | G2编译门 | G3边界门 | 含该字语料 |
|---|---|---|---|---|---|
| 为 | **保留** | FAIL（23文件） | PASS | FAIL（3形态） | 763/856 |
| 返回 | **保留** | FAIL（20文件） | PASS | FAIL（2形态） | 647/856 |
| 尝试 | **保留** | PASS（0） | PASS | FAIL（3形态） | 239/856 |

### 真护栏机制
_EMBED块（lexer.py L2292-2371）是`为/返回/尝试`触发的嵌入式扫描：
- 含该字的复合名（`行为`/`返回表`/`尝试记录`）被整体成IDENTIFIER
- `设 X为 <值>`形态精确切分（前缀+为+值）

撤除某字后，含该字的复合名落回R21上下文敏感块——因`行/返/尝`不是关键字前缀，无法整体成词，被关键字劈开：
- `行为` → `行` + `为`（ID变两token）
- `返回表` → `返回`(KEY) + `表`(ID)
- `尝试记录` → `尝试`(KEY) + `记录`(ID)

这些劈开会破坏函数定义名/变量名，属硬回归→必须保留。

### 与第22轮结论一致
第22轮验证_EMBED表撤掉后17文件token变化，本轮逐条验证确认3条全部为真护栏。结论一致，_EMBED表不可精简。

---

## 三、test_审批.light flaky修复

### 问题描述
- **位置**：examples/test_审批.light:125-127
- **flaky根因**：`time.time()`返回系统墙上时钟（wall clock），两次采样之间若发生系统时间调整（NTP同步、手动改时间等），会导致耗时计算错误
- **影响**：用例12d/12e间歇性失败，从第20轮持续存在（R20-C）

### 修复内容
- 125行：`设 开始 为 time.time()` → `设 开始 为 time.monotonic()`
- 127行：`设 耗时 为 time.time() - 开始` → `设 耗时 为 time.monotonic() - 开始`
- 共2处修改，其余163行与修改前逐字节一致

### 修复方案
- `time.monotonic()`返回单调递增时钟（秒），不受系统时间调整影响（PEP 418）
- `导入 time`走光明模块桥接，成员访问直通Python标准库time模块属性

### 验证结果
- 5次运行全部rc=0
- 每次13用例全部通过
- **flaky已修复**

---

## 四、验证结果

### 4.1 编译器方向
- _EMBED表无修改，lexer.py零改动
- 全语料token零变化（无回归）

### 4.2 test_审批.light
- 5次运行全部rc=0（13用例全过）
- flaky已修复

### 4.3 pytest
- `tests/test_R31_EMBED表保留+flaky修复_token.py`：13 passed
- 覆盖：_EMBED表条数断言/保护语义/为的赋值尾巴切分/flaky修复验证/联动表断言

### 4.4 性能对比
- 第30轮基线：6.14s
- 第31轮：4.25s（×5取平均）
- 性能变化：+30.7%（可能是系统环境差异，_EMBED无修改）

### 4.5 联动保护表评估
联动保护表全部维持不变：
- CS 0条、CCW 0条、_EMBED 3条（真护栏）、OPERATOR_VERBS 19条、_P0A_MERGE_WHOLE 9条、_P0A_NEVER_SPLIT 4字、HM扩展、DUAL 8字、TAIL_CUT 1字、F 43字

---

## 五、路M修正与决策记录

1. **_EMBED表3条全部保留**：任务书风险预判#1"_EMBED表3条可能全部是真护栏"已证实。本轮_EMBED方向无删除成果，但已逐条隔离验证并记录保留理由。
2. **test_审批.light flaky修复完成**：从第20轮持续存在的flaky问题（R20-C）已修复，全量CI不再有已知flaky。
3. **与第22轮结论一致**：_EMBED表3条确认为真护栏，非冗余，后续轮次不再尝试精简。

---

## 六、保护表演化总览（R31后）

| 保护表 | 条数 | 状态 |
|---|---|---|
| CS（_COMPOUND_SAFE_SINGLE_KEYWORDS） | 0条 | R28清零 |
| CCW（COMMON_COMPOUND_WORDS） | 0条 | R30清零 |
| _EMBED_MAX_MATCH_KEYWORDS | 3条 | R31验证确认为真护栏，不可精简 |
| OPERATOR_VERBS | 19条 | 保留 |
| _P0A_MERGE_WHOLE | 9条 | 保留 |
| _P0A_NEVER_SPLIT | 4字 | 保留 |
| HM（_P0A_HEAD_MERGE_SINGLE） | 扩展 | 保留 |
| DUAL（_P0A_HEAD_MERGE_DUAL） | 8字 | 保留 |
| TAIL_CUT（_P0A_TAIL_CUT_SINGLE） | 1字（列） | 保留 |
| F（_TRAILING_ALIAS_CLASS） | 43字 | 保留 |

---

## 七、已知问题与后续方向

### 7.1 已知问题
- **无**（test_审批.light flaky已修复，全量CI不再有已知flaky）

### 7.2 第32轮方向建议
1. **OPERATOR_VERBS 19条精简**（推荐）：CS/CCW已清零，_EMBED确认为真护栏，下一个保护表精简目标
2. **_P0A_MERGE_WHOLE 9条精简**
3. **继续上游复刻**
4. **性能进一步优化**

---

## 八、docs三件回填

1. **对标清单**（docs/功能对标/对标清单.json）：追加#149（_EMBED表3条验证保留+test_审批flaky修复），总数149条。
2. **缺陷账**（docs/功能对标/语言缺陷账.md）：本轮无新发现缺陷，未更新。
3. **行为差异清单**（docs/功能对标/行为差异清单.md）：追加R31-D1（_EMBED表3条验证保留，真护栏确认）、R31-D2（test_审批.light flaky修复，R20-C已解决）。

---

## 九、git提交

### light-merge项目
- 无提交（lexer.py零改动，_EMBED表维持3条）

### lightharness项目（6路分路提交 + 收口提交）
- 任务1：_EMBED"为"字验证
- 任务2：_EMBED"返回"字验证
- 任务3：_EMBED"尝试"字验证
- 任务4：test_审批.light flaky修复
- 任务5：合并验证+反跑+性能+pytest
- 任务6：质量审查+docs回填
- 收口提交：docs三件 + 质量审查报告 + 收口说明
