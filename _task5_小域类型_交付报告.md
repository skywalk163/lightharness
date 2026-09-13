# 任务5 交付报告：小域类型合并（plan/todo/terminal types → src/小域类型.light）

> 任务来源：`G:\dswork\duan-light-merge\复刻_第16轮_任务prompt分发 (1).md` 任务5
> 日期：2026-09-13 ｜ 上游：`G:\github\deepseek-harness`（本地 HEAD 9d9035b7c1）
> 目标模块：`lightharness/src/小域类型.light`（对标 #108；命名预检查通过——src/ 下无同名模块）

---

## 一、上游对应表（三域 types.ts 合计 271 行）

> **任务书描述与上游源码差异的重要声明**：
> - plan/plan-mode/types.ts **无 PlanMode 枚举**——实际为 `PlanProjection {active, pending}` 与
>   `PlanUnitState {active, wanted, running: {commandId, wanted}|null, activeAtLastHeader}` 两形状；
> - todo/tool-todo/types.ts 的 TodoItem **无 id/优先级/activeForm**（全量快照 last-wins 设计）——
>   任务书「优先级排序」不存在；
> - terminal/terminal/types.ts **无尺寸校验/光标位置**——实际为会话状态/等待原因/信号/读分页形状。
> 以上以源码为准复刻；任务书点名的过滤/缺省校验/枚举变异按语义等价实现（C 判据取待办状态枚举，
> 详见 §四）。

| 上游位置 | 光明段落 | 核心语义 |
|---|---|---|
| plan types.ts PlanProjection | 造计划投影 | {active: 布尔, pending: 布尔} |
| plan types.ts PlanUnitState | 造计划单元状态 | {active, wanted: 布尔\|空, running: {commandId, wanted}\|空, activeAtLastHeader: 布尔\|空} |
| plan types.ts JSDoc 派生语义 | 计划投影计算 | pending = wanted 非 空 且 wanted != active 且 running 非 空（「已记录 /plan 选择目标 != active、未经配对 command/done 结算失败、无更晚 plan/mode 记录」）；active = 单元态 active。上游派生 fold 在宿主面，本层按 JSDoc 语义实现（登记 R16-D5） |
| todo types.ts TodoItem | 待办状态表 / 造待办项 / 是否待办项 | status 三态逐字 `'pending' \| 'in_progress' \| 'completed'`（无 id/优先级）；非法状态/非法 content 抛错（文案自拟对齐字面量清单，登记 R16-D5） |
| todo types.ts `'todo/write'` 事件 | 待办写入事件 / 应用待办写入 | 事件 {todos: 全量快照}；whole-list snapshot、每次写入携带完整替换表 |
| todo types.ts 投影声明 | 待办投影 / 过滤待办 | 投影 fold last-wins（首写前 空）；按状态过滤为补充实现（上游无过滤函数） |
| terminal types.ts TerminalWaitReason | 是等待原因 | `'stdin_read' \| 'inferred_idle' \| 'timeout' \| 'session_exit'` 逐字 |
| terminal types.ts TerminalSignal | 是终端信号 | `'SIGINT' \| 'SIGTERM' \| 'SIGKILL' \| 'SIGTSTP' \| 'SIGHUP'` 逐字 |
| terminal types.ts TerminalSessionStatus | 造运行状态 / 造退出状态 / 是终端会话状态 | `{kind:'running'}` \| `{kind:'exited', exitCode: 数\|空, signal: 文本\|空}` |
| terminal types.ts TerminalSessionSnapshot | 造终端快照 | {sessionId, name?, type, pid?, status}——可选键缺省不落 |
| terminal types.ts TerminalReadRequest/Result | 校验读请求 / 造读结果 | 读请求缺省校验为本层实现（上游缺省 backend-owned）：空/负 → 偏移 0、行数 50，不崩溃（B 判据）；TerminalReadResult {text, totalLines, lineBegin, lineEnd, truncated} |
| terminal types.ts TerminalSendResult | 造发送结果 | {viewport, waitReason, sessionStatus, truncated}，waitReason 非法抛（文案自拟对齐 4 值清单） |
| terminal types.ts 其余（TerminalBackendSession/Backend/SpawnSpec/SendOperation/TerminalBackendCleanupError） | 宿主面剔除 | Agent/AbortSignal/NodeJS.Signals/Promise 依赖（登记 §五） |
| plan/client.ts、todo/client.ts | 并入 types | 上游为 `export type * from './types'` 纯重导出，零内容（任务书注明并入） |

**三域命名空间隔离**：同模块段落名以域词区分（计划投影计算/待办投影/是终端会话状态…），测试专条验证判别互不干扰。

## 二、实现要点

1. **形状优先**：三域均为纯类型文件，复刻=形状构造 + 逐字枚举判别 + 少量派生计算（计划投影/待办投影折叠/读请求缺省）。
2. **投影语义**：todo 投影 last-wins（首写前 空 null 语义）；plan 投影派生按 JSDoc 三条件（登记：上游派生 fold 在宿主投影器）。
3. **可选键缺省不落**：快照 name/pid、待办 capturedFormatVersion 同族语义（省略非 null）。
4. **绕法**：无 且/或 行内链（L-043）、标识符避关键字与单字别名切分（L-119/L-120/L-084）、无花括号文案（L-089）、可选键先 字典包含键（L-103）。

## 三、测试验证

```
cd G:\dswork\duan-light-merge\lightharness
$env:LIGHT_MERGE="G:\dswork\duan-light-merge\light-merge"; python 运行.py examples/test_小域类型.light
test_小域类型 PASS   （rc=0）
```

`examples/test_小域类型.light` 覆盖 4 组 ≥45 断言：计划域（待定四条件/形状/隔离）、待办域（构造/形状校验三形态/非法状态与内容/last-wins 全量替换/三状态过滤+空表/事件形状逐字/投影 last-wins 与首写前空/投影项校验）、终端域（等待原因 4+1/信号 5+1/状态两形态+非法/快照可选键/读结果形状/空与负与合法读请求三态/发送结果与非法原因）、三域命名空间隔离。

## 四、反跑结果（3/3 ALL OK）

`lightharness/_antirun_t5_小域类型.py`（BASE 自定位；字节级备份→变异→跑本路测试→断红→恢复→断绿；恢复置于 try/finally）：

```
PASS C=变异 待办状态枚举 in_progress 改错 -> 红 (变异后运行 rc=1（期望非 0，真红）)
PASS 字节级恢复校验 (sha256 920c38b5caf7)
PASS A/B 判据（待办构造过滤 + 空终端读请求）回归绿 (rc=0)
ALL OK
```

A=正常（待办构造→写入→过滤输出一致）与 B=边界（空终端读请求校验回默认不崩溃）为测试内场景，随回归绿验证；C=变异（待办状态枚举 `in_progress`→`in-progress`，非法状态断言立红）恢复后绿。

## 五、未移植项（宿主面登记）与任务书/上游差异

- **宿主面剔除**：plan/index.ts+invariant.ts（cordis+defineTool）、todo/index.ts+invariant.ts、terminal/index.ts（cordis）、terminal-bash/（node 宿主面）；terminal types 中依赖 Agent/AbortSignal/NodeJS.Signals/Promise 的 TerminalBackendSession/Backend/BackendSpawnSpec/SendOperation/TerminalBackendCleanupError。
- **任务书/上游差异**：plan 域无 PlanMode 枚举（C 判据取待办状态枚举等价变异）；todo 无 id/优先级（过滤按状态实现）；terminal 无尺寸/光标（读请求缺省校验为本层实现）；plan 投影派生与 todo 过滤为 JSDoc/任务书语义的本层实现。
- CommandId/Branded 品牌类型以字符串承载。

## 六、语言差异（本轮新缺陷登记）

- 无新缺陷（L-139 编号空缺，路M 顺延）。开发中曾疑 import 语句 `从` 后紧跟中文模块名（无空格）触发词法合并（`从小域类型` 被切分/合并报「类型别名」或 NameError）——属 **L-120 已知同族**，标准空格形态 `从 小域类型 导入` 正常，不重复登记。

## 七、移交清单

- `lightharness/src/小域类型.light`（新增，≈230 行）
- `lightharness/examples/test_小域类型.light`（新增，PASS rc=0）
- `lightharness/_antirun_t5_小域类型.py`（反跑 3/3 ALL OK，BASE 自定位）
- 本报告。
- 移交路M：对标清单新增 **#108**（plan/todo/terminal types 合并）；行为差异清单 **R16-D5**（三域任务书差异声明+补充实现两项）；CI 增 1 个 test_ 文件（292+ 占 1）。
