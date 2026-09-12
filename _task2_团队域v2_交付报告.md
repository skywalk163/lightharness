# 任务2（团队域）#65/#66 事件 v2 收口 + tool-agent-team 工具 交付报告

> 日期：2026-09-12 ｜ 路：任务2 ｜ 上游只读：`G:\github\deepseek-harness` @ `a305303422`（0.1.5-rc.2）

## 一、上游依据（文件:函数）

| 上游文件 | 依据函数/形状 | 本路对应 |
|---|---|---|
| `packages/experimental/agent-team/src/types.ts` | `SessionEventMap` 四条事件 `team/member`/`team/task`/`team/message/queued`/`team/message/delivered` 均 `version:2`；delivered 仅 `{version,teamId,messageId,targetId}`（无 delivery） | `src/团队依赖图.light` 构造*通知 + 包装*记录 |
| `packages/experimental/agent-team/src/task-graph.ts` | `assertTaskGraphCandidate` 四类违规（missing/duplicate/cycle/self） | `src/团队依赖图.light` 校验任务接线（前轮已在，本轮未改逻辑） |
| `packages/experimental/agent-team/src/task-board.ts` | `appendAndFlush(root,'team/task',{version:2,teamId,task})`；`dependencies`/`taskView` 派生 | `src/团队看板.light` 投影v2任务/投影v2记录/投影全部v2记录 |
| `packages/experimental/tool-agent-team/src/index.ts` | 9 个工具 `defineTool` 定义；`wait_agent` no-progress 短路（ACTIVE_WAIT_STATUSES/NO_ACTIVE_PEER_MESSAGE/timeout 10000..3600000 默认 30000）；`team_task_list` 过滤+分页（cursor>=0, limit 1..100 默认 50, nextCursor）；`jsonOutput` render | `src/团队工具.light` |
| `packages/experimental/agent-team/src/fold.ts`（#67 既有） | `applyTeamEvent` 读 `record.type`/`record.data`；data.version!=2 且非本团队静默忽略、本团队抛 unsupported | `examples/test_团队事件v2.light` 互操作用例 |

## 二、实现要点

### 1. #65 `src/团队依赖图.light`（事件词汇补齐 v2）
- 现状：构造*通知（成员/任务/排队/送达）前轮已是 `version:2`，送达通知本就无 `delivery` 字段。
- 本轮新增「第五节 v2 事件信封包装」四个导出：`包装成员记录/包装任务记录/包装排队记录/包装送达记录`，把内层载荷包成 #67 折叠期望的外层信封 `{"type","data":{"version":2,"teamId",...},"seq"}`。补齐后 #65 产出记录可直接喂 `折叠团队` 跑通互操作（此前 #65 只造内层 data，缺外层信封）。
- 注释明确记录 v1→v2 差异：delivery 调度字段已移除（队列即 durable inbox）。

### 2. #66 `src/团队看板.light`（事件词汇补齐 v2，保留中文事件汇）
- 既有中文状态机（待办/进行中/完成 + 前置项 + 优先级）与中文事件汇（task-created/task-updated/task-completed/task-deleted）**原样保留**，`test_团队看板` 既有回归不破。
- 本轮新增「v2 事件投影桥接」四段：
  - `映射看板状态(中文态)`：待办→pending / 进行中→in_progress / 完成→completed（对齐上游 TeamTaskSnapshot.status 枚举）。
  - `投影v2任务(标识,记录,版本号=1)`：中文记录→上游 v2 TeamTaskSnapshot（id/revision/subject/description/status/blockedBy/writeScopes）。
  - `投影v2记录(团队标识,标识,记录,版本号=1,序号=0)`：包成 #67 折叠信封。
  - `投影全部v2记录(团队标识,任务表,序号起=0)`：整表投影。
- 与 #67-70（折叠/花名册/信箱/日志 v2）对齐：投影出的 task 快照满足 #67 `校验任务载荷`（status 英文枚举、blockedBy/writeScopes 列表、revision=1）。

### 3. 新建 `src/团队工具.light`（tool-agent-team 纯逻辑）
- 工具定义面：9 个工具的 `parameters` JSON Schema（`spawn_teammate模式`/`send_message模式`/`list_agents模式`/`wait_agent模式`/`interrupt_agent模式`/`team_task_create模式`/`team_task_list模式`/`team_task_update模式`）+ `团队工具声明表()`（name/description/parameters）。参数键名对齐上游英文 snake_case（target/timeout_ms/task_id/expected_revision/action/blocked_by/write_scopes 等）。
- 纯逻辑派生：
  - wait_agent：`解析等待超时`（默认 30000）/`判等待超时合法`（safe integer 且 [10000,3600000]）/`是否活跃等待状态`（running/provisioning）/`有无活跃等待伙伴`/`无进展等待结果`（`{timedOut:false,noProgress:{reason:"no-active-peer",message}}`）。
  - team_task_list：`过滤团队任务`（status 精确 / owner==unowned 表无 ownerName / ready 精确）/`判分页`（cursor 非负 safe integer、limit 1..100）/`分页切片`（[cursor,cursor+limit)，未取尽附 nextCursor）。
  - `渲染JSON文本`（jsonOutput → `[{"type":"text","text":JSON.stringify(value)}]`）。
- 执行面 `团队工具面`：构造时注入「团队能力」字典（spawnTeammate/sendMessage/listMembers/waitForChange/interrupt/createTask/listTasks/getTask/updateTask/callerId），9 个 execute 方法只做参数缺省与纯逻辑分流，真实 IO 一律委托注入能力，不实例化宿主 Agent/Cordis ctx。

### 4. 工具注册表挂载
- **未改** `src/工具.light` / `src/核心工具.light`。团队工具 execute 依赖宿主 agentTeams 服务（Cordis ctx），纯逻辑层无法真实注入；本路内聚导出 `团队工具面` + `团队工具声明表`，宿主在具备 agentTeams 能力时按注册表契约（`注册表.注册(造工具定义(...))`）挂载，零破坏既有注册项。此项在报告「移交清单」标注。

## 三、测试与 CI

| 测试 | 断言数 | 结果 |
|---|---|---|
| `examples/test_团队事件v2.light`（新建） | ≥18（v2 内层载荷×4、信封×2、折叠互操作×3、v1 宽容×2、看板投影×8） | rc=0 |
| `examples/test_团队工具.light`（新建） | ≥30（9 工具定义、参数校验×6、wait 纯逻辑×9、wait 执行面×3、列任务过滤分页×7、判分页×3、呈现×2） | rc=0 |
| `examples/test_团队依赖图.light`（既有） | — | rc=0 |
| `examples/test_团队看板.light`（既有） | — | rc=0 |
| `examples/test_团队折叠.light`（既有） | — | rc=0 |
| `examples/test_团队日志.light` / `test_团队花名册.light` / `test_团队服务.light`（既有） | — | rc=0 |

- `python -m pytest tests/ -q -k 团队` → 250 deselected（tests/ 仅 `test_回归.py`，团队域测试均为 `examples/*.light` 经 `运行.py` 跑，已逐个全绿）。
- 未跑全量 CI（按铁律交由路M）。

## 四、反跑判据（`_antirun_team_v2.py`，字节级备份/恢复）

| 项 | 改动 | 期望红 | 恢复绿 | 结果 |
|---|---|---|---|---|
| A | `#65 构造送达通知` version 2→1 | test_团队事件v2 rc=1 | rc=0 | PASS |
| B | `#66 投影v2记录` data.version 2→1（task-board v2 标记改错） | test_团队事件v2 rc=1 | rc=0 | PASS |
| C | `#66/团队工具 判等待超时合法` 下限 10000→1000（参数校验放宽） | test_团队工具 rc=1 | rc=0 | PASS |

脚本输出：`全部符合判据`，script_rc=0。

## 五、未移植项 / 已知差异

1. **团队工具 execute 宿主侧未接入**：9 个工具的真实 `ctx.agentTeams.*` 调用（spawnTeammate/sendMessage/listMembers/waitForChange/interrupt/createTask/listTasks/getTask/updateTask）需 Cordis ctx + Agent 宿主，纯逻辑层只复刻工具定义/参数校验/结果呈现/分流逻辑；`团队工具面` 通过注入能力字典桥接，宿主真实挂载点留待后续轮。
2. **#66 看板为简化模型**：subject/description 简化（subject 用任务标识占位、description 空串）、writeScopes 恒空、revision 恒 1（简化版无 CAS revision 概念）；只投影当前快照，不逐次 append team/task 事件。这与上游 task-board.ts 的全量 revision/CAS 不同，但满足 #67 `校验任务载荷` 的 v2 形状要求，互操作验证通过。
3. **语言陷阱登记**（建议路M 入 `语言缺陷账.md`）：光明里「等待」是 await 语句关键字（`等待 异步睡眠(...)`），**不能作局部变量名**（`设 等待 为 X` → `'await' outside async function`）；函数名含「等待」子串合法（如 `校验等待时限`）。本路在 `团队工具.light` 把局部变量改名为「等候调用」规避。另：项目源文件为 CRLF 无 BOM，Edit 工具按 LF 匹配会失配，本路统一用字节级 PowerShell 追加（CRLF 保持一致）。
4. **task-board 版本 2 标记**：#66 看板原中文事件汇（task-created 等）保留作内部事件；v2 标记只出现在新增的「投影桥接」输出上，二者并存。

## 六、移交清单（绝对路径）

1. `G:\dswork\duan-light-merge\lightharness\src\团队依赖图.light`（改：+v2 信封包装四函数）
2. `G:\dswork\duan-light-merge\lightharness\src\团队看板.light`（改：+v2 投影桥接四段）
3. `G:\dswork\duan-light-merge\lightharness\src\团队工具.light`（新建：tool-agent-team 纯逻辑）
4. `G:\dswork\duan-light-merge\lightharness\examples\test_团队事件v2.light`（新建，≥10 断言）
5. `G:\dswork\duan-light-merge\lightharness\examples\test_团队工具.light`（新建，≥6 断言）
6. `G:\dswork\duan-light-merge\lightharness\_antirun_team_v2.py`（新建，3 项反跑）
7. `G:\dswork\duan-light-merge\lightharness\_task2_团队域v2_交付报告.md`（本报告）

**未越界**：未改 `src/工具.light`/`src/核心工具.light`/其他域 src；未跑全量 CI；docs/功能对标/ 未动（留路M 回填 #65/#66/#77 状态与缺陷账）。
