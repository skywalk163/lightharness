# 第38轮收口说明（终稿）

> 轮次：第38轮 ｜ 主题：agent-tool-presentation 工具展示模式复刻
> 日期：2026-09-16 ｜ 收口：路M ｜ 状态：**已收口 · 提交（未 push，用户手工推）**

---

## 一、本轮结论（一句话）

agent-tool-presentation复刻完成——新增src/工具展示.light（导出18项），实现native/ptc/both三模式工具展示+作用域隔离+codeRuntime条件等待+卸载恢复，零修改既有src模块（通过代理注册表适配器实现零侵入联动）。上游8契约全映射，全量反跑873文件零回归，pytest全量通过。

---

## 二、各任务交付摘要

### 任务1：agent-tool-presentation核心模块复刻 ✅
- **新增**：src/工具展示.light（281行，导出18项：6常量+8函数+1类+1工厂）
- **上游精读**：index.ts 72行逐元素映射 + spec 8契约（7用例+隐含disposer）
- **光明适配**：
  - 配置字典范式（对齐第37轮代理默认模型）
  - 模块级作用域展示表（单进程解释器，作用域隔离）
  - codeRuntime条件等待（待代码运行时标记+等待函数，对齐上游ctx.inject语义）
  - 零修改适配层（工具展示注册表代理类）
- **上游对齐**：inject=['tools']（codeRuntime是条件等待不是静态依赖）、mode必填不设默认值、ptc无codeRuntime时pending不静默降级、presentAs返回disposer随row卸载解除
- **测试**：examples/test_R38_工具展示.light（14组全绿，rc=0）

### 任务2：与现有模块联动适配 ✅
- **核心决策**：零修改适配（依赖注入+代理注册表适配器）
- **现有模块分析**：工具.light（描述表()是过滤源数据）、代码运行时.light（存在性判定）、代理循环.light（L459注册表.描述表()）、代理.light（构造透传注册表）、代理默认模型.light（配置范式参考）
- **实现**：
  - 工具展示注册表代理类：包装(作用域ID, 注册表)，覆写描述表()为按作用域过滤，其余10+方法透传
  - 造代理工具展示工厂：代理携带配置的薄包装
- **零修改**：不改动任何既有src模块，代理循环传入代理即自动获得过滤后的工具列表

### 任务3：集成测试 ✅
- examples/test_R38_集成测试.light（rc=0，11组全绿）
- **上游8契约全映射**：
  1. inject=['tools']，不持有codeRuntime
  2. 作用域隔离（一个ptc，其余native）
  3. both模式展示两者
  4. 卸载恢复（HMR安全）
  5. ptc无codeRuntime时pending（不应用，不静默降级）
  6. codeRuntime到达后应用
  7. mode必填，不设默认值（空/非法/大小写敏感）
  8. presentAs返回disposer（注销函数，幂等）
- **端到端三模式对比**：native=[echo,search,write_file]、ptc=[run_code]+SDK、both=[echo,search,write_file,run_code]+SDK
- **代理循环联动**：真实状态机，同一循环同一注册表，不同作用域看到不同工具列表

### 任务4：全量反跑+回归验证+导入路径检查 ✅
- **全量反跑**：873文件（R37终态870+本轮新增3），新增解析错误0，2个既有红与R30起登记一致
- **回归验证**：347个test_*.light，344绿，3红逐一取证：
  - test_L101.light：EXPECT_RED钉子（回调是保留关键字）
  - test_L143.light：EXPECT_RED钉子（作用域是保留关键字）
  - test_会话存储.light：Windows竞态+残留放大，复跑rc=0（与本轮改动无关）
- **导入路径检查**：从工具展示导入仅2处（测试文件），无其他引用方；同名冲突检查通过；模块搜索路径SRC>ROOT>STDLIB

### 任务5：性能对比+联动评估+pytest ✅
- **性能**：新增3文件对全量lexer性能完全中性（+1.45%在Windows抖动区间±5%）
- **三模式微基准**：apply/unapply亚微秒级，visible(ptc)最快（0.4µs），visible(both)最慢但仍1.1µs，生成SDK O(n)（20工具~12µs）
- **联动评估**：对既有模块零影响（零侵入设计，旧消费者行为完全不变）；工具展示只import builtins层，即插即用
- **pytest**：tests/test_R38_工具展示_token.py（13用例，7维度覆盖），13/13全绿；R37(7)+R38(13)=20 passed无跨轮回归

### 任务6：质量审查+docs回填 ✅（路M执行）
- 质量审查：5路交付物全部优秀（A级）
- docs回填：对标清单#159、行为差异R38-D1/D2
- 路M复测：集成测试11组全绿、pytest全量通过

---

## 三、验收标准核对

| 项 | 状态 | 证据 |
|---|---|---|
| agent-tool-presentation核心模块复刻完成 | ✅ | src/工具展示.light，导出18项 |
| 与现有模块联动适配完成 | ✅ | 零修改既有src模块，代理注册表适配器 |
| 上游8用例映射全部覆盖 | ✅ | 集成测试11组全绿 |
| 三模式端到端对比验证 | ✅ | native/ptc/both工具列表差异明确 |
| 集成测试全部通过 | ✅ | test_R38_集成测试.light rc=0 |
| 全量反跑零回归 | ✅ | 873文件0新增ERR |
| 回归验证无有效回归 | ✅ | 347文件344绿+3红逐一取证 |
| 导入路径检查无遗漏 | ✅ | 从工具展示导入仅2处（测试文件） |
| 性能对比数据 | ✅ | +1.45%在Windows抖动区间，零回归 |
| 联动评估结论 | ✅ | 零侵入，即插即用 |
| pytest全部通过 | ✅ | 13/13全绿+全量通过 |
| docs三件回填 | ✅ | #159 / R38-D1/D2 |
| 收口说明完成 | ✅ | 本文档 |
| git提交 | ✅ | 见§五 |

---

## 四、保护表总账（第38轮后，无变化）

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
git add src/工具展示.light
git add examples/test_R38_工具展示.light examples/test_R38_集成测试.light
git add tests/test_R38_工具展示_token.py
git add docs/功能对标/对标清单.json docs/功能对标/行为差异清单.md
git add _task1_R38_agent-tool-presentation复刻.md _task2_R38_联动适配.md
git add _task3_R38_集成测试.md _task4_R38_全量反跑+回归验证+导入路径检查.md
git add _task5_R38_性能对比+联动评估+pytest.md _task6_R38_质量审查报告.md
git add _taskM_第38轮收口说明.md
git commit -m "第38轮：agent-tool-presentation工具展示模式复刻"
```

---

## 六、后续轮次建议

1. **继续上游复刻**：上游core包还有scope、system-prompt、agent-presets等模块可复刻
2. **工具展示真实端到端smoke测**：需真实LLM+真实codeRuntime，当前等价Python模拟已证微秒级
3. **会话存储Windows竞态修复**：os.replace加退避重试（R37起两次验证，非本轮范围）
4. **test_会话存储随机子目录根改造**：消除残留放大（R37起登记）
5. **代理类透传方法扩口风险**：代理模式固有tradeoff，未来工具注册表新增方法时需同步
6. **_P0A_MERGE_WHOLE剩2条**：真护栏，不再尝试精简，每5轮复验
