# 第37轮收口说明（终稿）

> 轮次：第37轮 ｜ 主题：R34-D3代理循环统一 + agent-default-model小模块复刻
> 日期：2026-09-16 ｜ 收口：路M ｜ 状态：**已收口 · 提交（未 push，用户手工推）**

---

## 一、本轮结论（一句话）

R34-D3代理循环统一完成（stdlib旧版重命名为代理运行时，零回归），agent-default-model复刻完成（src/代理默认模型.light，导出11项，14组测试全绿）。全量反跑870文件零回归，pytest 1209 passed。

---

## 二、各任务交付摘要

### 任务1：R34-D3代理循环统一 ✅
- **方案**：方案B（重命名）——stdlib/代理循环.light → stdlib/代理运行时.light
- **关键发现**：
  1. 实为三处同名，不是两处：①stdlib旧版（应用层）②src新版（核心层）③src/代理.light内的`类 代理循环`（驱动层，17处引用，不受影响）
  2. R34-D3登记前提（stdlib优先于src）**被实证证伪**：`运行.py`实际顺序为**SRC > ROOT > STDLIB**
  3. stdlib旧版是**孤儿**（全语料0个导入方）
- **实现**：git mv保留历史 + 头部注释更新 + 4个stdlib文件comment引用更新（事件总线/代理工具集/并发/重试）
- **零回归**：5个文件token流与HEAD完全一致
- **踩坑修正**：Python open批量改写导致CRLF→LF，已还原后用Edit工具重做

### 任务2：agent-default-model复刻 ✅
- **新增**：src/代理默认模型.light（导出11项）
- **上游精读**：index.ts 109行逐元素映射 + spec 5用例作为行为契约
- **光明适配**：
  - 无cordis/Service → 字典+函数（entry/source/写回三态）
  - 无schemastery → 手动谓词（required=键存在且为字符串）
  - settings集成 → 内存化投影（挂载/写用户层/卸载可逆）
- **上游对齐**：selection()缺省推理力度省略键；ReasoningEffortId无验证（未知力度原样保留）；saveSelection未挂载时no-op；settings卸载回退组合入口
- **测试**：examples/test_R37_代理默认模型.light（14组全绿，rc=0）
- **实现期修正**：写用户层校验合并后生效设置（对齐上游部分节行为）；更新默认模型推理力度二态语义（传空=清除）

### 任务3：集成测试 ✅（§5路由M补做）
- examples/test_R37_集成测试.light（rc=0）
- §1-4：代理循环统一后导入路径/核心状态机/事件格式/中止路径（任务3交付）
- §5：agent-default-model集成覆盖（路M补做，6组全PASS）
  - 建配置/取选择/更新/校验/投影/端到端联动

### 任务4：全量反跑+回归验证+导入路径检查 ✅
- 全量反跑：870文件，无新增解析错误，零回归
- 回归验证：345文件，342绿，3红逐一取证（2个EXPECT_RED钉子+1个运行残留污染已复跑转绿）
- 导入路径检查：6处`从 代理循环 导入`全部正确；1处`从 代理运行时 导入`正确
- 边界发现：light-merge/stdlib/代理循环.light是语言仓库自带同名旧版，不在本轮统一范围

### 任务5：性能对比+联动评估+pytest ✅
- 性能：无显著变化（构造性不变Δ=0，本机噪声±35%）
- 联动评估：零影响（旧版是孤儿）
- 同类风险登记：加密.light/重试.light同时存在于src与stdlib（建议后续评估）
- pytest：test_R37_代理循环统一_token.py（7用例全绿）
- 全量回归：382 passed / 0 failed

### 任务6：全量验证+质量审查+docs回填 ✅（路M执行）
- 补做§5集成测试（6组全PASS）
- pytest全量：1209 passed / 1 skipped（路M复测）
- 质量审查：5路交付物全部合格
- docs回填：对标清单#158、行为差异R34-D3更新+R37-D1/D2

---

## 三、验收标准核对

| 项 | 状态 | 证据 |
|---|---|---|
| R34-D3代理循环统一完成 | ✅ | stdlib/代理运行时.light，同名冲突消除 |
| agent-default-model复刻完成 | ✅ | src/代理默认模型.light，导出11项 |
| 集成测试全部通过 | ✅ | test_R37_集成测试.light rc=0（11组） |
| 全量反跑零回归 | ✅ | 870文件0新增ERR |
| 回归验证无有效回归 | ✅ | 345文件342绿+3红逐一取证 |
| 导入路径检查无遗漏 | ✅ | 6处全部正确 |
| 性能对比数据 | ✅ | 构造性不变Δ=0 |
| 联动评估结论 | ✅ | 零影响 |
| pytest全量通过 | ✅ | 1209 passed / 1 skipped |
| docs三件回填 | ✅ | #158 / R34-D3更新+R37-D1/D2 |
| 收口说明完成 | ✅ | 本文档 |
| git提交 | ✅ | 见§五 |

---

## 四、保护表总账（第37轮后，无变化）

| 表 | 数量 | 状态 |
|---|---|---|
| CS | 0 | R28清零 |
| CCW | 0 | R30清零 |
| _P0A_NEVER_SPLIT | 0 | R33清零 |
| _EMBED_MAX_MATCH_KEYWORDS | 3 | 真护栏 |
| OPERATOR_VERBS | 19 | 真护栏 |
| _P0A_MERGE_WHOLE | 2 | 真护栏（整理模型消息/记录类型） |

---

## 五、提交清单

### lightharness
```
git add stdlib/代理运行时.light stdlib/事件总线.light stdlib/代理工具集.light stdlib/并发.light stdlib/重试.light
git add src/代理默认模型.light
git add examples/test_R37_代理默认模型.light examples/test_R37_集成测试.light
git add tests/test_R37_代理循环统一_token.py
git add docs/功能对标/对标清单.json docs/功能对标/行为差异清单.md
git add _task1_R37_代理循环统一.md _task2_R37_agent-default-model复刻.md
git add _task3_R37_集成测试.md _task4_R37_全量反跑+回归验证+导入路径检查.md
git add _task5_R37_性能对比+联动评估+pytest.md _task6_R37_全量验证+质量审查.md
git add _taskM_第37轮收口说明.md
git commit -m "第37轮：R34-D3代理循环统一 + agent-default-model复刻"
```

> 注意：stdlib/代理循环.light → stdlib/代理运行时.light 是rename（git mv），git会自动识别。

---

## 六、后续轮次建议

1. **继续上游复刻**：上游core包还有agent-tool-presentation、scope、system-prompt等模块可复刻
2. **同类风险评估**：加密.light/重试.light同时存在于src与stdlib，建议后续按同法评估是否统一
3. **light-merge/stdlib/代理循环.light**：语言仓库自带同名旧版，是否同步重命名属上游仓库决策
4. **test_会话存储.light健壮性**：建议改为随机子目录根，避免残留污染（本轮不改既有测试）
5. **_P0A_MERGE_WHOLE剩2条**：真护栏，不再尝试精简，每5轮复验
