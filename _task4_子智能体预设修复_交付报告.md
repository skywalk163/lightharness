# 任务4 交付报告：子智能体+预设域修复（T4-D1 / T4-D4）

- 轮次：第9轮（行为差异修复）任务4
- 分支：`task-9-subpreset`（worktree `wt-R9T4`，基 `e2088c5`=第8轮收口点）
- 互斥表内 src：`src/子智能体.light` ✅、`src/预设.light` ✅；其余 src 零改动
- 上游依据（只读）：`G:\github\deepseek-harness\packages\subagent\subagent\tests\assistant-output.spec.ts`、
  `packages\preset\agent-presets\tests\display.spec.ts`、`src\display.ts`（字典键定义）

## 1. 修复点（文件:行，先核实后改）

### T4-D1 取最后回答 形态（src/子智能体.light，类 子智能体 内 :91 起）

**核实结论**：旧 `取最后回答` 只收集 text 块、reasoning-only 消息因文本为空被跳过、无输出返回 `""`；
上游 `finalAssistantOutput` 返回**内容块表**、reasoning-only 消息视为非空、无输出返回 `undefined`。

**修复**（保持向后兼容，按任务书 a/b/c）：
1. 新增 `取最后回答块表`：遍历 `assistant/message`，收集 content 中 type ∈ {text, reasoning} 的块；
   块表非空即视为非空消息（reasoning-only 因此纳入）；无输出返回 `空`（光明无 undefined 哨兵）。
2. `取最后回答`（拼接文本）改为内部调用 `取最后回答块表`，仅拼接 text 块文本，空表返回 `""`——
   行为与旧实现等价（reasoning 无 text 不产文本），既有调用方零影响。

### T4-D4 shipped 预设字典翻译（src/预设.light，metadata 区 :121 后新增）

**核实结论**：光明无 shipped 预设显示文案字典；上游 `display.ts` 内置集合
`standard/ptc/minimal/cordis`，`trust==="system"` 且命中内置集 → 字典键（名称+描述），
其余（含 system 非内置与全部 user）→ `name ?? id` + 可选 description 原样。

**修复**：
1. 新增 `内置预设文案(标识)`：模块级字典，覆盖 standard/ptc/minimal/cordis 四枚中文文案
   （standard→标准模式/完整的编码 agent。，ptc→编码模式，minimal→极简模式，cordis→组装模式）。
2. 新增 `造显示文本(预设)`：system+命中内置 → 返回字典文案；否则 name 优先（去除空白）、
   无 name 回退 id、description 非空原样保留；非字典输入 → `空`（防御）。

## 2. 测试与 CI

- 新增 `examples/test_修复_子智能体预设.light`（两部分，PASS rc=0）：
  - 部分1 T4-D1：无输出→`空`/`""`；越过末尾空消息取最后非空（块表形状+文本拼接）；
    reasoning-only 视为非空（返回 reasoning 块、文本拼接为空串）；混合 text+reasoning 块表完整、拼接只取 text。
  - 部分2 T4-D4：shipped standard/minimal → 字典文案；system 非内置 → 回退 id；
    user name 优先/description 原样；user 无 name → 回退 id；无 description 不产出键；非字典 → `空`。
- 既有回归（src 改动后复跑，全绿 rc=0）：`test_子智能体` / `test_子智能体1.5` / `test_子智能体深化` / `test_预设`。
- 全量 CI 由路M 统一跑（既有用例数不变，新增 1 个测试文件 → 以路M 实际计数为准）。

## 3. 反跑判据（_antirun_subpreset_fix.py，2 项全过，字节级备份/恢复 src）

| # | 改反操作 | 预期 | 实测 |
|---|---|---|---|
| A | `取最后回答块表` 条件改回只收 text（丢 reasoning 分支） | reasoning-only 非空断言红 | rc=1 红 ✅，恢复 rc=0 绿 ✅ |
| B | `造显示文本` 内置命中条件 `!=` 改 `==`（删字典查找） | shipped 字典文案断言红 | rc=1 红 ✅，恢复 rc=0 绿 ✅ |

## 4. 既有断言更新

无。`取最后回答` 文本行为与旧实现语义等价（reasoning 无 text 不产文本），
`test_子智能体` 系列全部原样通过；`test_预设` 未触及既有段落。

## 5. 差异清单回填状态（供路M）

- **T4-D1**：✅ 第9轮已修复——新增 `取最后回答块表`（块表形态/reasoning 非空/无输出→空哨兵），
  `取最后回答` 复用块表拼接。残余说明：上游 `finalAssistantOutput` 的 assistant/attempt 流式文本
  回退（场景「falls back to text deltas」）不在本轮修复范围（第8轮清单未列该差异），维持现状。
- **T4-D4**：✅ 第9轮已修复——新增 `内置预设文案`/`造显示文本`，shipped 四内置走字典文案，
  user 元数据原样保留，无元数据回退 id（对齐 display.spec 三场景）。
- 未涉及：T4-D2（任务3）、T2/T3 域（任务1/2）。

## 6. 语言缺陷新登记

无。本轮两处修复未依赖光明缺失能力（无深拷贝/浅拷贝需求：
块表组装为新列表；字典查找为纯逻辑）。

## 7. 移交清单

- 提交范围：仅 `wt-R9T4`；`git add -A` + commit。
- 临时脚本 `_patch_sub.py` / `_patch_preset.py` 提交前已删除。
- 差异清单回填、全量 CI、收口说明：路M统一执行。
