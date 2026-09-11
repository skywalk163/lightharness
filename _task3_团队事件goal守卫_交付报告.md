# 任务3 交付报告｜团队事件版本2 + goal 恢复守卫

- 轮次：第 5 轮（0.1.5-rc.2 遗留收尾）
- 任务：任务3（团队事件+goal守卫）
- 分支：`task-5-team-goal`（worktree `wt-T3`，基于 main `4e06d53`）
- 对应遗留：#65 事件版本2 / #66 看板复核 / tool-goal resume-paused 守卫

---

## 1. 上游对应表

| 上游文件 | 上游变更 | 光明对应文件 | 光明变更 | 对齐状态 |
|---|---|---|---|---|
| `agent-team/src/types.ts:221` | `team/member` version 1→2 | `src/团队依赖图.light:69` | `构造成员通知` version 1→2 | ✅ 逐行对齐 |
| `agent-team/src/types.ts:223` | `team/task` version 1→2 | `src/团队依赖图.light:73` | `构造任务通知` version 1→2 | ✅ 逐行对齐 |
| `agent-team/src/types.ts:225` | `team/message/queued` version 1→2 | `src/团队依赖图.light:77` | `构造排队通知` version 1→2 | ✅ 逐行对齐 |
| `agent-team/src/types.ts:228` | `team/message/delivered` version 1→2 | `src/团队依赖图.light:81` | `构造送达通知` version 1→2 | ✅ 逐行对齐 |
| `agent-team/src/types.ts` | `TeamMessageSnapshot`/`SendTeamMessageRequest` 移除 `delivery` 字段 | — | 光明侧从未实现 `delivery` 字段 | ✅ 无对应点（从未存在） |
| `agent-team/src/task-board.ts:70,212` | 两处 `team/task` 事件 version 1→2 | `src/团队看板.light` | **无对应移植点**（见 §3） | ✅ 已核对 |
| `goal/tool-goal/src/index.ts:280-286` | `resume` + `current.phase === 'paused'` + id/rev 命中 → `GOAL_TOOL_RESUME_PAUSED` | `src/目标折叠.light` 新增 `判定模型可恢复` | 纯决策段：paused + id/rev 命中 → 抛错 | ✅ 语义对齐 |

---

## 2. 实现要点

### 2.1 团队依赖图事件 version 1→2

`src/团队依赖图.light` 四个事件构造段的 `"version": 1` 统一改为 `"version": 2`，注释同步标注对齐上游 `types.ts` `SessionEventMap`。这四个段是事件形状词汇的所有者，全仓 src 无调用方（仅测试消费），升级不影响运行时行为。

`examples/test_团队依赖图.light` 四处 version 断言 `1` → `2`，每处标注反跑注释。

### 2.2 团队看板复核结论

**已核对（无对应移植点）。**

上游 `task-board.ts` 两处 `team/task` 事件 version bump（行 70、212）发生在 `TaskBoard` 类的 `journal.appendAndFlush(root, 'team/task', { version: 2, ... })` 调用中——这是通过 Cordis session journal 发射的版本化持久事件。

光明侧 `src/团队看板.light` 的任务变更走本地 `造记录("task-created"/"task-updated"/"task-completed", ...)` 记录形状 + 注入的 `追加事件` 能力函数，**不发射上游 `team/task` 版本化事件**。grep 确认 `团队看板.light` 不引用 `团队依赖图` 的任何构造函数，也不引用 `构造任务通知` 等。

因此 version 1→2 的 bump 在光明看板无对应代码点。看板的本地记录形状（`种类`/`任务标识`/`数据`/`序号`）不含 version 字段，不受上游 version 变更影响。

### 2.3 goal 模型恢复守卫

`src/目标折叠.light` 新增纯决策段 `判定模型可恢复`（接收 `目标`, `引用`）：

```
段落 判定模型可恢复 接收 目标, 引用:
  设 阶段 为 字典获取(目标, "phase")
  如果 阶段 == "paused" 且 字典获取(目标, "id") == 字典获取(引用, "id") 且 字典获取(目标, "revision") == 字典获取(引用, "revision"):
    抛出 新建 错误("the model cannot resume a paused goal; the user must resume it")
  返回 真
```

对齐上游 `tool-goal/src/index.ts:280-286`：
- 上游判据：`args.action === 'resume' && current?.id === ref.id && current.revision === ref.revision && current.phase === 'paused'`
- 光明判据：`阶段 == "paused" 且 id 命中 且 revision 命中`（action 由调用方决定，纯决策段只做守卫判定）
- 错误文案逐字对齐：`"the model cannot resume a paused goal; the user must resume it"`
- active/blocked → 放行（返回真）；complete → 放行（由 `恢复激活判定` 另行拒绝）；引用不匹配 → 放行（交下游 `GoalService.resume` 处理）

`工具.light` 无 goal 工具注册（宿主层），守卫作为纯决策段落放进 `目标折叠.light`，与既有 `恢复激活判定`（用户侧恢复）并列。

### 2.4 新增测试

`examples/test_目标恢复守卫.light`（7 组用例）：
- A: paused + 引用命中 → 拒绝（错误文案含 "the model cannot resume a paused goal"）
- B: active + 引用命中 → 放行
- C: blocked + 引用命中 → 放行
- D: complete + 引用命中 → 放行（守卫不拦，由下游拒绝）
- E: paused + id 不匹配 → 放行；paused + revision 不匹配 → 放行
- F: paused rev=2 + 引用命中 rev=2 → 拒绝（多轮修订场景）
- G: paused rev=2 + 旧引用 rev=1 → 放行（引用已过期）

---

## 3. 测试与 CI

### 定向用例

| 测试 | rc | 说明 |
|---|---|---|
| `test_团队依赖图` | 0 | version 2 断言通过 |
| `test_目标恢复守卫` | 0 | 新增，7 组全绿 |
| `test_目标恢复激活` | 0 | 既有回归 |
| `test_目标折叠` | 0 | 既有回归 |
| `test_团队看板` | 0 | 既有回归 |
| `test_团队折叠` | 0 | 既有回归 |
| `test_团队花名册` | 0 | 既有回归 |
| `test_团队服务1.5` | 0 | 既有回归 |

### 反跑判据

`_antirun_team_goal.py`（6 项全 PASS）：
1. 成员通知 version 改回 1 → 红 (rc=1)
2. 任务通知 version 改回 1 → 红 (rc=1)
3. 排队通知 version 改回 1 → 红 (rc=1)
4. 送达通知 version 改回 1 → 红 (rc=1)
5. 守卫 paused 拒绝改放行 → 红 (rc=1)
6. 引用不匹配放行改拒绝 → 红 (rc=1)

### 全量 CI

由路M 统一跑。本路自验：8 个定向用例全绿 + 6 项反跑全红。

---

## 4. 未移植项

| 上游 | 原因 |
|---|---|
| `task-board.ts` version bump | 光明看板不发射上游版本化事件，无对应移植点（§2.2） |
| `types.ts` `delivery` 字段移除 | 光明侧从未实现该字段 |
| `tool-goal` 工具注册（defineTool/ctx.tools.register） | 宿主层，不移植；纯决策段已提取至 `目标折叠.light` |
| `authority.ts`（requireDirectHuman/completionAuthority） | 宿主层权限判定，不移植 |

---

## 5. 移交清单

无。本路触碰的文件（`团队依赖图.light`/`目标折叠.light`/对应测试）与其它任务文件互斥，无跨路移交。
