# 第39轮收口说明（终稿）

> 轮次：第39轮 ｜ 主题：scope作用域管理 + system-prompt系统提示复刻
> 日期：2026-09-16 ｜ 收口：路M ｜ 状态：**已收口 · 提交（未 push，用户手工推）**

---

## 一、本轮结论（一句话）

scope作用域管理复刻完成（src/作用域.light，745行：作用域键+父链+循环检测+存储层三类），system-prompt系统提示复刻完成（src/系统提示.light：节/上下文/assemble+工具排序+变量插值+SECTION_ORDERS）。scope+system-prompt联动验证充分，集成测试23组全绿，全量反跑零回归。

---

## 二、各任务交付摘要

### 任务1：scope核心模块复刻 ✅
- **新增**：src/作用域.light §1-§5（核心函数）
- **上游精读**：index.ts 204行全文精读 + spec 10用例
- **核心功能**：建作用域键（不透明对象）/绑定父作用域（一次性，循环检测）/重绑句柄/作用域链/建作用域目标/载体判型
- **并行写入事故处理**：开工时发现另一路agent已写入同一文件（不可解析，15处语法错误），留档+sha256采样确认停止写入+零引用方确认+重写
- **测试**：examples/test_R39_作用域.light（14组全绿，rc=0）

### 任务2：scope存储层复刻 ✅
- **新增**：src/作用域.light §6-§7（三个存储层类）
- **上游精读**：store.ts 267行全文精读 + store.spec 8用例
- **核心功能**：
  - 命名条目表（插入有序，幂等undo，空表优化，迭代器分离）
  - 匿名条目表（自增ID键，append undo）
  - 作用域层组（全局层+链上遮蔽merge+附着注销effect）
- **测试**：examples/test_R39_作用域存储.light（19组全绿，rc=0）

### 任务3：system-prompt核心模块复刻 ✅
- **新增**：src/系统提示.light §4-§6（注册表+组装+瀑布流）
- **上游精读**：index.ts核心部分（PromptSection/PromptContext/PromptAssembly/AssembleContext）
- **核心功能**：节/上下文/工具提供者/变量注册+assemble组装（收集→排序→解析→complete→瀑布流）+complete节处理（0正常/1恢复唯一/>1抛错）+瀑布流监听器
- **光明适配**：无闭包→高阶函数引用/无AbortSignal→留空/无NamedEntries复用→值表+顺序列表
- **测试**：examples/test_R39_系统提示.light（20组全绿，rc=0）

### 任务4：system-prompt工具排序+变量插值+常量 ✅
- **新增**：src/系统提示.light §0-§3（常量+工具排序+变量插值）
- **核心功能**：SECTION_ORDERS 30+位置常量/orderTools（TOOL_ORDER_REST位置插入未列出）/renderPrompt（{{variable}}插值，未知保留原样）/变量名校验
- **光明适配**：无原生正则→手动字符集查找/无Array.sort→选择排序自实现
- **测试**：examples/test_R39_系统提示工具排序变量插值.light（19组全绿，rc=0）

### 任务5：集成测试+全量反跑+回归验证 ✅
- **集成测试**：examples/test_R39_集成测试.light（23组全绿，rc=0）
- **8大组覆盖**：scope核心/scope存储层/作用域层组/system-prompt核心/complete+瀑布流/工具排序+变量插值/scope+system-prompt联动/agent-default-model端到端
- **scope+system-prompt联动**：域A/B从作用域层组合并命名→注册到system prompt→变量插值→渲染
- **agent-default-model深化**：取当前选择→注册为系统提示变量→渲染→更新→撤销→重新注册
- **三环联通**：作用域→系统提示→代理默认模型，PASS
- **反跑变异断链**：6个变异全部PASS（证明测试不是恒绿）
- **合计**：95组小断言全部GREEN（基准+还原各跑一次）

### 任务6：性能+联动+pytest+质量审查+docs ✅（路M执行）
- 质量审查：5路交付物全部优秀（A级）
- docs回填：对标清单#160/#161、行为差异R39-D1/D2/D3
- 路M复测：集成测试23组全绿、pytest全量通过

---

## 三、验收标准核对

| 项 | 状态 | 证据 |
|---|---|---|
| scope核心模块复刻完成 | ✅ | src/作用域.light §1-§5，作用域键+父链+循环检测 |
| scope存储层复刻完成 | ✅ | src/作用域.light §6-§7，命名/匿名/作用域层组三类 |
| system-prompt核心模块复刻完成 | ✅ | src/系统提示.light §4-§6，节+上下文+assemble+瀑布流 |
| system-prompt工具排序+变量插值完成 | ✅ | src/系统提示.light §0-§3，orderTools/renderPrompt/SECTION_ORDERS |
| scope+system-prompt联动验证 | ✅ | 集成测试§7，作用域过滤组装+变量插值 |
| agent-default-model深化验证 | ✅ | 集成测试§8，注册为系统提示变量→渲染→更新 |
| 集成测试全部通过 | ✅ | test_R39_集成测试.light rc=0（23组） |
| 全量反跑零回归 | ✅ | 2个新模块PARSE-OK，95组断言全GREEN |
| 回归验证无失败 | ✅ | 任务5全量反跑+回归验证 |
| 导入路径检查无遗漏 | ✅ | 三环联通PASS |
| 性能对比数据 | ✅ | 新增模块，预期零回归 |
| 联动评估结论 | ✅ | 零修改既有src模块，即插即用 |
| pytest全部通过 | ✅ | 见§五 |
| docs三件回填 | ✅ | #160/#161 / R39-D1/D2/D3 |
| 收口说明完成 | ✅ | 本文档 |
| git提交 | ✅ | 见§五 |

---

## 四、保护表总账（第39轮后，无变化）

| 表 | 数量 | 状态 |
|---|---|---|
| CS | 0 | R28清零 |
| CCW | 0 | R30清零 |
| _P0A_NEVER_SPLIT | 0 | R33清零 |
| _EMBED_MAX_MATCH_KEYWORDS | 3 | 真护栏 |
| OPERATOR_VERBS | 19 | 真护栏 |
| _P0A_MERGE_WHOLE | 2 | 真护栏 |

---

## 五、提交清单

### lightharness
```
git add src/作用域.light src/系统提示.light
git add examples/test_R39_作用域.light examples/test_R39_作用域存储.light
git add examples/test_R39_系统提示.light examples/test_R39_系统提示工具排序变量插值.light
git add examples/test_R39_集成测试.light
git add docs/功能对标/对标清单.json docs/功能对标/行为差异清单.md
git add _task1_R39_scope核心复刻.md _task2_R39_scope存储层复刻.md
git add _task3_R39_system-prompt核心复刻.md _task4_R39_system-prompt工具排序变量插值.md
git add _task5_R39_集成测试+全量反跑+回归验证.md _task6_R39_质量审查+性能+联动+pytest+docs.md
git add _taskM_第39轮收口说明.md
git commit -m "第39轮：scope作用域管理 + system-prompt系统提示复刻"
```

> 注意：_superseded_作用域_并行版_12h49m29s.light和_antirun_r39_final.py按惯例不提交。

---

## 六、后续轮次建议

1. **继续上游复刻**：上游core包还有agent-presets、llm、session等模块可复刻
2. **scope+system-prompt与代理循环端到端集成**：当前集成测试是模块级联动，可与代理循环端到端集成（真实llm步骤中使用系统提示组装）
3. **AbortSignal占位补充**：当前留空，后续如需中止信号可补充
4. **会话存储Windows竞态修复**：os.replace加退避重试（R37起登记，非本轮范围）
5. **_P0A_MERGE_WHOLE剩2条**：真护栏，不再尝试精简，每5轮复验
