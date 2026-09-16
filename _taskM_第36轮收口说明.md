# 第36轮收口说明（终稿）

> 轮次：第36轮 ｜ 主题：技术债清理轮
> 日期：2026-09-16 ｜ 收口：路M ｜ 状态：**已收口 · 分路提交（未 push，用户手工推）**

---

## 一、本轮结论（一句话）

技术债清零：R29/R30两个死文件移入docs/历史存档（门禁零噪音）、test_lexer 3条基线红重写（10/10）、性能预计算常量（零风险整洁度改进）、L-154/R35-D2两项评估均结论"不立项，维持现状"。全量反跑676文件0差异，pytest 1200 passed。

---

## 二、各任务交付摘要

### 任务1：R29/R30死文件终态处理 ✅
- **方案**：方案B（移入docs/历史存档/），两文件统一处理
- **操作**：`git mv` examples/test_R29_CCW精简边界.light → docs/历史存档/；examples/test_R30_CCW通用化边界.light → docs/历史存档/
- **test_回归.py**：移除2条EXPECT_RED登记，改为说明性注释
- **理由**：两文件自入库起从未rc=0（解析期即失败），设计前提被R30 CCW清零自推翻；token层钉桩已由pytest接管
- **验证**：test_回归.py 381 passed / 0 failed

### 任务2：light-merge test_lexer 3条基线红修正 ✅
- **3条红测试全部选方案B（重写）**：
  - `test_basic_keywords`：`设甲为三。`→`设 甲 为 三。`（规范写法），新增钉现状断言`设甲为三。`整体成词
  - `test_multiple_keywords`：`遍历列表映射筛选`→拆为三段（`遍历映射。`/`映射 筛选。`/`遍历 列表。`）
  - `test_complex_expression`：`设甲为三加五。`→`设 甲 为 三 加 五。`，新增`三加五`粘连钉现状断言
- **根因**：`为`属_EMBED_MAX_MATCH_KEYWORDS（恒带空格），无空格游程被整体并成IDENTIFIER
- **验证**：test_lexer.py 10/10通过，净增12条断言
- **铁律**：未改lexer.py，只改测试

### 任务3：性能优化——预计算常量 ✅
- **改动**：`_OPERATOR_KEYWORDS - _P0A_UNARY_PREFIX_KW`预计算为模块常量`_OPERATOR_KEYWORDS_NO_UNARY_PREFIX`（26元）
- **附加**：import自校验④（防止未来_P0A_UNARY_PREFIX_KW增删时遗漏同步）
- **热路径探查**：仅R21闸门3一处是per-token重复集合差构造，其余均已预计算
- **性能结果**：ABAB交替+严格配对，Δ=+1.15%（σ=8.98%，噪声带内）——**未观测到~1.9%回收**，属零风险代码整洁度改进
- **验证**：全量反跑676文件0差异，pytest 5用例全绿

### 任务4：L-154深度评估 ✅（只评估，不改代码）
- **结论**：**不立项修复，维持现状**
- **4方案对比**：①重引白名单（违背精简方向）②扩展一元前缀通用规则（与`非甲=not甲`冲突）③改进报错信息（可单独登记低优先待办）④维持现状（全语料零命中，收益≈0）
- **决定性事实**：受影响的3个合成名（异步读取文件/并发等待/常量时间比较）在全语料中零命中
- **后续**：`test_ccw_names_split_after_ccw_cleared`钉住现状

### 任务5：R35-D2词首/词尾不对称评估 ✅（只评估，不改代码）
- **结论**：**不立项对称化，维持现状**
- **理由**：不对称符合中文构词语法（`非空`是复合名，`甲非`是"甲不是"表达式）；对称化会破坏`甲非0`等词尾切分形态，风险>收益
- **已钉住**：pytest覆盖三态（词首/词中/词尾）

### 任务6：全量验证+质量审查+docs回填 ✅
- **全量反跑**：676文件，0差异
- **pytest全量**：1200 passed / 1 skipped（比R35的1197多3个）
- **test_lexer**：10/10通过
- **质量审查**：5路交付物质量合格，铁律全部遵守
- **docs回填**：对标清单#157、行为差异R36-D1/D2/D3、缺陷账L-154状态更新

---

## 三、验收标准核对

| 项 | 状态 | 证据 |
|---|---|---|
| R29/R30死文件终态处理 | ✅ | git mv到docs/历史存档/，test_回归.py移除EXPECT_RED |
| test_lexer.py 10/10 | ✅ | 3条重写，净增12断言 |
| 性能优化完成 | ✅ | 预计算常量+自校验，ABAB噪声带内 |
| L-154评估给出明确建议 | ✅ | 不立项，维持现状 |
| R35-D2评估给出明确建议 | ✅ | 不立项对称化，维持现状 |
| 全量反跑零回归 | ✅ | 676文件0差异 |
| pytest全量通过 | ✅ | 1200 passed / 1 skipped |
| docs三件回填 | ✅ | #157 / R36-D1D2D3 / L-154更新 |
| 收口说明完成 | ✅ | 本文档 |
| git分路提交 | ✅ | 见§五 |

---

## 四、保护表总账（第36轮后，无变化）

| 表 | 数量 | 状态 |
|---|---|---|
| CS（_COMPOUND_SAFE_SINGLE） | 0 | R28清零 |
| CCW（COMMON_COMPOUND_WORDS） | 0 | R30清零 |
| _P0A_NEVER_SPLIT | 0 | R33清零 |
| _EMBED_MAX_MATCH_KEYWORDS | 3 | 真护栏（R22/R31双重验证） |
| OPERATOR_VERBS | 19 | 真护栏（R32验证） |
| _P0A_MERGE_WHOLE | 2 | 真护栏（R35验证，整理模型消息/记录类型） |
| HM（_P0A_HEAD_MERGE_SINGLE） | 25 | 扩展 |
| DUAL（_P0A_HEAD_MERGE_DUAL） | 8 | — |
| F（_TRAILING_ALIAS_CLASS） | 46 | — |

---

## 五、提交清单（分路提交，未 push）

### light-merge
```
git add src/lexer.py tests/test_lexer.py
git commit -m "第36轮：技术债清理——test_lexer 3条基线红重写 + 性能预计算常量"
```

### lightharness
```
git add docs/功能对标/对标清单.json docs/功能对标/行为差异清单.md docs/功能对标/语言缺陷账.md
git add docs/历史存档/test_R29_CCW精简边界.light docs/历史存档/test_R30_CCW通用化边界.light
git add tests/test_回归.py tests/test_R36_性能优化_token.py
git add _task1_R36_R29R30死文件处理.md _task2_R36_test_lexer基线红修正.md
git add _task3_R36_性能优化.md _task4_R36_L-154深度评估.md _task5_R36_R35-D2不对称评估.md
git add _task6_R36_全量验证+质量审查.md _taskM_第36轮收口说明.md
git commit -m "第36轮收口M：技术债清理——R29/R30死文件移档 + docs回填 + 收口"
```

---

## 六、后续轮次建议

1. **继续上游复刻**：技术债已清零，可回到上游复刻主线。上游core包还有agent-default-model、agent-tool-presentation、scope、system-prompt等模块可复刻。
2. **_P0A_MERGE_WHOLE剩2条**：真护栏，不再尝试精简，每5轮复验一次即可。
3. **L-154报错可诊断性增强**：低优先待办，可在后续轮次顺手做。
4. **门禁机CI（192.168.0.88）**：push后由门禁机跑全量核验。
