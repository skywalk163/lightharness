# 任务3 交付报告：工具域修复（T1-S18 concludesTurn 传播 + T4-D2 执行策略默认值）

- 轮次：第 9 轮（行为差异修复）任务3
- 分支：`task-9-tools`（worktree `wt-R9T3`，基 `e2088c5`=第8轮收口点）
- 说明：本路由路M 接手完成（原 agent 被停时已完成 src 改动+测试+反跑，路M 验证后提交并补本报告）
- 互斥表内 src：`src/工具.light` ✅；`src/代理.light` 核实已消费 concludesTurn，无需改动；其余 src 零改动

---

## 1. 上游依据与核实结论

### T1-S18 concludesTurn 传播
- 上游：`packages/core/agent-loop/tests/tool-calls.spec.ts`、`packages/core/tools/tests/tools.spec.ts`
- 上游语义：工具执行函数可返回 `ToolExecutionResult`（含 `concludesTurn` 字段），执行结果应传播该值；`concludesTurn=true` 时代理循环结束当前轮次，不再继续请求模型。
- 光明现状（修复前）：`造工具结果`（工具.light:33）硬编码 `"concludesTurn": 假`；执行主路径（:404）也硬编码假。
- **代理.light 核实**：L600/L636 已有 `如果 结果.包含("concludesTurn") 且 结果["concludesTurn"] == 真` 消费逻辑——代理循环已支持 concludesTurn，只需工具侧传播。

### T4-D2 执行策略默认值
- 上游：`packages/core/tools/tests/execution-mode.spec.ts`
- **核实结论**（路M 实读上游 spec）：
  - L28: `returns parallel only for an explicit true classifier`——只有显式 `isConcurrencySafe: () => true` 才 parallel
  - L40: `defaults to exclusive for a tool with no isConcurrencySafe declaration`——未声明默认 exclusive
  - L51: unknown tool → exclusive
  - L56-66: classifier 返回 false → exclusive；throwing classifier → exclusive；truthy non-boolean → exclusive
- **决策**：改默认 `parallel` → `exclusive`（对齐上游），同步更新既有测试断言。

---

## 2. 修复点（文件:行）

| ID | 文件:行 | 修复内容 |
|---|---|---|
| T1-S18 | `src/工具.light:28-30`（造工具结果） | 新增 `结论=假` 参数，返回 `"concludesTurn": 结论`（向后兼容，缺省假） |
| T1-S18 | `src/工具.light:406-414`（执行主路径） | 工具返回值若为 dict 且含 `concludesTurn` → 传播结论标志；若含 `content` → 用 content 作内容块；否则原值作内容块。错误路径维持 concludesTurn=假 |
| T4-D2 | `src/工具.light:28`（造工具定义） | 默认 `策略="parallel"` → `"exclusive"` |
| T4-D2 | `src/工具.light:353`（执行策略） | 未注册默认 `"parallel"` → `"exclusive"` |

---

## 3. 测试与 CI

- 新增 `examples/test_修复_工具.light`（13 场景 S1-S13，全绿 rc=0）：
  - S1-S8：concludesTurn 传播（dict 含真/假、列表返回缺省假、dict 含 content+concludesTurn、错误路径假、未知工具假、造工具结果辅助函数、**S8 代理循环集成——concludesTurn=true 工具结束轮次，模型仅调用一次**）
  - S9-S13：执行策略默认值（未显式传→exclusive、未知工具→exclusive、显式 parallel、显式 exclusive、造工具定义默认 mode=exclusive）
- 既有断言更新（行为对齐，非测试迁就）：
  - `examples/test_工具.light`：默认并行断言 parallel→exclusive（2 处）
  - `examples/test_工具深.light`：默认并行断言 parallel→exclusive（1 处）
- 回归抽查全绿：`test_工具` / `test_工具深` / `test_修复_工具`
- 全量 CI 由路M 统一跑。

---

## 4. 反跑判据（_antirun_tools_fix.py，4 项 ALL RED）

| 项 | 变异（测试文件自身断言） | 结果 |
|---|---|---|
| A1 | S1 concludesTurn 传播断言 真→假 | ✅ 红→恢复绿 |
| A2 | S5 错误路径 concludesTurn 断言 假→真 | ✅ 红→恢复绿 |
| B1 | S9 默认策略断言 exclusive→parallel | ✅ 红→恢复绿 |
| B2 | S10 未知工具策略断言 exclusive→parallel | ✅ 红→恢复绿 |

字节级备份/恢复测试文件自身，4/4 ALL RED。

---

## 5. 差异清单回填状态

| ID | 状态 |
|---|---|
| T1-S18 | ✅ 第9轮已修复（concludesTurn 传播 + 代理循环集成验证） |
| T4-D2 | ✅ 第9轮已修复（默认 exclusive，上游 execution-mode.spec 核实确认） |

---

## 6. 语言缺陷新登记

无。本轮修复未依赖光明缺失能力。

---

## 7. 移交清单

- 改 `src/工具.light`（4 处：造工具结果签名、执行主路径传播、造工具定义默认、执行策略默认）
- 新增 `examples/test_修复_工具.light`（13 场景）
- 更新 `examples/test_工具.light` / `examples/test_工具深.light`（默认值断言 3 处）
- 新增 `_antirun_tools_fix.py`（4 判据）
- 未动：`src/代理.light`（已消费 concludesTurn，核实无需改）、`docs/`（路M 统一回填）
