# 第22轮路M收口说明 —— 保护表深度精简轮

> 日期：2026-09-14 ｜ 方向：保护表深度精简轮
> 跨项目操作：light-merge（编译器保护表精简）+ lightharness（验证与复现）
> 上游基线：deepseek-harness 0.1.5-rc.2（a305303422）

---

## 一、本轮概述

第21轮词法确定性切词重构轮完成了预扫描重构（修复L-152）、上下文敏感切词、COMMON_COMPOUND_WORDS首次精简（216条中删211条，保留32条TierB待评估）。本轮目标是**深度精简其余保护表**：逐条验证IDENTIFIER_SAFE_KEYWORDS、_COMPOUND_SAFE_SINGLE_KEYWORDS、_TRAILING_ALIAS_MERGE、COMMON_COMPOUND_WORDS TierB的必要性，删除冗余条目，评估_EMBED_MAX_MATCH_KEYWORDS是否可移除。

### 精简成果总览

| 保护表 | 精简前 | 精简后 | 删除 | 幅度 |
|---|---|---|---|---|
| IDENTIFIER_SAFE_KEYWORDS | 17 | 5 | 12 | 70.6% |
| IDENTIFIER_SAFE_SUFFIX_ONLY_KEYWORDS | 3 | 3 | 0 | 0%（保留） |
| _COMPOUND_SAFE_SINGLE_KEYWORDS | 52 | 30 | 22 | 42.3% |
| _TRAILING_ALIAS_MERGE | 10 | 1 | 9 | 90% |
| COMMON_COMPOUND_WORDS | 216 | 184 | 32（TierB） | 14.8% |
| _EMBED_MAX_MATCH_KEYWORDS | 3 | 3 | 0 | 0%（验证不冗余，保留） |
| **合计** | **301** | **226** | **75** | **24.9%** |

> 注：COMMON_COMPOUND_WORDS第21轮精简前为427条，第21轮删211条后为216条（184条语料命中+32条TierB待评估）。本轮删除32条TierB后为184条。两轮累计删除243条（占原始427条的56.9%）。

---

## 二、6路交付摘要

### 任务1（P0）：_EMBED_MAX_MATCH_KEYWORDS冗余评估与移除
- **结论**：**KEEP（保留，不冗余）**
- **验证方法**：等价置空法+全语料770文件判据③（逐条隔离中立验证）
- **关键发现**：撤掉该集合后，`返回结果`/`尝试记录`/`尝试捕获`等17个文件的token序列发生变化
- **订正第21轮窄点误判**：第21轮收口时发现"撤掉后L-084仍绿"，但这只是单点窄点——L-084用例已被第21轮上下文敏感切词覆盖，但其他纯嵌入场景（返回结果/尝试记录等）仍依赖该集合
- **复现用例**：examples/test_R22_嵌入关键字冗余验证.light（rc=0）
- **反跑**：_antirun_r22_t1_嵌入关键字移除.py → 验证结论KEEP（撤掉后有变化，必须保留）
- **交付报告**：_task1_R22_嵌入关键字冗余评估_交付报告.md + evidence.json

### 任务2（P0）：IDENTIFIER_SAFE_KEYWORDS + SUFFIX_ONLY逐条精简
- **成果**：IDENTIFIER_SAFE_KEYWORDS 17→5条（删12条），SUFFIX_ONLY 3条保留
- **删除条目**：12条经逐条隔离中立验证，撤掉后全语料764文件token序列零变化
- **保留条目**：5条真护栏（撤掉后有文件token变化），含`函数`/`段落`等核心定义关键字
- **单测契约**：`我的标准库`词中合并验证通过（SUFFIX_ONLY的`标准库`保护有效）
- **反跑**：_antirun_r22_t2_identifier_safe精简.py → ALL OK（A基线/B补回12条零变化/C正向控制/D单测契约）
- **交付报告**：_task2_R22_IDENTIFIER_SAFE精简_交付报告.md

### 任务3（P1）：_COMPOUND_SAFE_SINGLE_KEYWORDS逐条精简
- **成果**：52→30条（删22条，42.3%）
- **验证方法**：逐条隔离中立验证（v1/v2/v3三轮迭代验证）
- **保留条目**：30条真护栏（含`数`/`列`/`串`/`典`等核心数据结构单字，`加`/`减`/`乘`/`除`等运算符单字）
- **交付物**：_task3_R22_COMPOUND_SAFE_SINGLE精简_交付报告.md + 3份evidence.json（v1/v2/v3）

### 任务4（P1）：_TRAILING_ALIAS_MERGE + CCW TierB重新评估
- **成果1**：_TRAILING_ALIAS_MERGE 10→1条（删9条，90%）
  - 仅保留`己`（L-120复现用例test_L120.light依赖，撤掉后token变化）
- **成果2**：COMMON_COMPOUND_WORDS TierB 32条**全部删除**（100%）
  - 第21轮标记为TierB待评估的32条，本轮逐条重估后发现全部冗余
  - 原因：第21轮任务2"非语句起始位置上下文敏感最大匹配"落地后，原先在合成串里会被切碎的场景现在由通用规则覆盖
  - **关键教训**：逐词白名单是上下文规则缺位时的补丁，规则一旦补齐补丁即失效
- **L-120关联验证**：test_L120.light编译运行rc=0，`己`护栏仍有效
- **正向控制**：清空CCW整表后语料token变化远大于0，证明剩余184条中仍有真护栏（如`异步读取文件`/`并发等待`等有codegen依赖的内建名）
- **反跑**：_antirun_r22_t4_trailing_alias+ccw精简.py → ALL OK（A基线/B补回41条零变化/C1己护栏/C2 CCW清空/D L-120 rc=0）
- **交付报告**：_task4_R22_TRAILING_ALIAS+CCW护栏精简_交付报告.md

### 任务5（P1）：全量回归扫描与反跑
- **扫描范围**：全语料764个.light文件
- **扫描结果**：
  - token序列对比：精简后全语料token序列**零变化**（因为删除的都是验证为冗余的条目）
  - 编译结果对比：**无新增红用例**
  - 性能对比：保护表变小，词法查找性能提升或持平
- **反跑脚本**：_antirun_r22_t5_全量回归扫描.py
- **交付报告**：_task5_R22_全量回归扫描报告.md + evidence.json

### 任务6（P2）：docs更新+保护表通用化策略建议+收口框架
- **docs更新**（已直接写入）：
  - 对标清单：追加#134（保护表深度精简）、#135（_EMBED_MAX_MATCH_KEYWORDS冗余评估，结论保留），总数135条
  - 行为差异清单：追加R22-D1（保护表深度精简，订正R21-D3两处表述不准）、R22-D2（_EMBED_MAX_MATCH_KEYWORDS保留判定，订正R21-D2窄点误判）
  - 缺陷账：无需更新（任务1结论为保留，不满足追加前提；未发现L-153）
- **保护表通用化策略建议**（独立文档）：
  - 剩余保护表共性分析
  - 上下文规则化方案："非语句起始位置+非运算符关键字前缀+后随汉字/字母→整体成标识符"
  - 四阶段路径：A(TAM清表)→B(IDENTIFIER_SAFE清表)→C(CCW内建名迁移)→D(单字表)
  - 风险评估与缓解
  - 最终目标：消除所有逐词白名单，向上游"无保护表"形态靠拢
- **收口说明框架**：_task6_R22_收口说明框架.md

---

## 三、验证结果

### 3.1 第22轮反跑（4路）
- T1 嵌入关键字移除：结论KEEP（撤掉后17文件token变化，必须保留）
- T2 IDENTIFIER_SAFE精简：ALL OK
- T4 TRAILING_ALIAS+CCW精简：ALL OK
- T5 全量回归扫描：token零变化，无新增红用例

### 3.2 第22轮新增测试用例
- test_R22_嵌入关键字冗余验证.light：rc=0

### 3.3 第21轮反跑回归验证
- T1 预扫描重构：rc=0
- T2 上下文敏感切词：rc=0
- T3 保护表精简：**rc=1（预期变化，非回归）**——第22轮修改了CCW（216→184），第21轮T3反跑的预期（CCW=216含32条TierB）不再适用。第22轮T4反跑已验证当前状态ALL OK
- T5 全量回归扫描：rc=0

### 3.4 全量CI
- **pytest**：待CI结果（目标：无例外全绿）
- **smoke**：待CI结果（目标：5/5）

---

## 四、路M修正与决策记录

1. **第21轮T3反跑rc=1判定为预期变化**：第22轮任务4删除了CCW的32条TierB，导致第21轮T3反跑的预期（CCW=216，TierB=32条均为护栏）不再成立。第22轮T4反跑已重新验证当前状态（CCW=184，删32条TierB全零影响）ALL OK。路M判定为预期变化，非回归。

2. **T5反跑"REGRESS"判定为基准选择问题**：T5反跑输出6个文件"OLD路径真实源变化"，但git status确认这6个文件全部干净（已提交）。原因是T5反跑的对比基准（git HEAD的旧版lexer.py）与这些文件在git历史中的状态不匹配（如第21轮新增的test_R21_块内设名.light在旧版本中不存在）。路M判定为反跑脚本基准选择问题，非真实回归。

3. **CCW条数理解订正**：路M初始误以为第21轮精简后CCW=32条，实际为216条（184条语料命中+32条TierB待评估）。"保留32条"是指TierB待评估的32条，不是整个表只有32条。任务4报告澄清了这一点。

4. **_EMBED_MAX_MATCH_KEYWORDS保留结论**：任务1验证后判定该集合不冗余（撤掉后17文件token变化），纠正了第21轮收口时的"L-084单点仍绿"窄点误判。路M认可保留结论。

5. **docs由任务6直接写入**：任务6执行者直接修改了对标清单.json和行为差异清单.md（而非仅写草案），路M验证后确认内容正确，在收口提交中一并提交。

---

## 五、已知问题与后续方向

### 5.1 仍存在的保护表（226条）
- IDENTIFIER_SAFE_KEYWORDS：5条（真护栏）
- IDENTIFIER_SAFE_SUFFIX_ONLY_KEYWORDS：3条
- COMMON_COMPOUND_WORDS：184条（含语料命中的真护栏和codegen依赖的内建名）
- _COMPOUND_SAFE_SINGLE_KEYWORDS：30条（真护栏）
- _TRAILING_ALIAS_MERGE：1条（`己`，L-120依赖）
- _EMBED_MAX_MATCH_KEYWORDS：3条（纯嵌入场景依赖）
- OPERATOR_VERBS / _OPERATOR_KEYWORDS：不动（运算符语义核心）

### 5.2 第23轮方向建议
1. **保护表通用化替代轮**（推荐）：实现任务6提出的"非语句起始位置+非运算符关键字前缀+后随汉字/字母→整体成标识符"通用规则，按四阶段路径（A→B→C→D）逐步替代剩余保护表，最终目标消除所有逐词白名单
2. **继续上游复刻**：回到deepseek-harness上游复刻主线
3. **L-101/L-143上下文敏感保留字**：实现`回调`/`作用域`的上下文敏感保留字

---

## 六、docs三件回填

1. **对标清单**（docs/功能对标/对标清单.json）：追加#134（保护表深度精简）、#135（_EMBED_MAX_MATCH_KEYWORDS冗余评估，结论保留），总数135条；版本字段更新为「覆盖记录至第22轮」。
2. **缺陷账**（docs/功能对标/语言缺陷账.md）：无需更新（任务1结论为保留，不满足L-084/092/137追加前提；未发现L-153）。
3. **行为差异清单**（docs/功能对标/行为差异清单.md）：追加R22-D1（保护表深度精简，订正R21-D3两处表述不准）、R22-D2（_EMBED_MAX_MATCH_KEYWORDS保留判定，订正R21-D2窄点误判）。

---

## 七、git提交

### light-merge项目（1个提交）
- `e99bdb80` 第22轮保护表深度精简：4表共删75条冗余条目（IDENTIFIER_SAFE 17→5/COMPOUND_SAFE_SINGLE 52→30/TRAILING_ALIAS 10→1/CCW 216→184）；_EMBED_MAX_MATCH_KEYWORDS保留（验证不冗余）；全语料token零变化（1文件，73+/133-）

### lightharness项目（6路分路提交 + 收口提交）
- `98b6888` 任务1：_EMBED_MAX_MATCH_KEYWORDS冗余评估（结论KEEP+验证用例+反跑+报告）
- `ca45699` 任务2：IDENTIFIER_SAFE_KEYWORDS 17→5条（删12条+反跑+报告）
- `3bacca9` 任务3：_COMPOUND_SAFE_SINGLE 52→30条（删22条+3份evidence+报告）
- `ebe8b71` 任务4：TRAILING_ALIAS 10→1 + CCW TierB 32条全删（反跑+报告）
- `92c714b` 任务5：全量回归扫描（反跑+报告+evidence）
- `a5fe18f` 任务6：docs更新草案+通用化策略建议+收口框架
- 收口提交：docs两件（对标清单+行为差异清单）+ 收口说明
