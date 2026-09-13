# 任务3 交付报告（第 13 轮 · goal 轮驱动域）

- 轮次：第 13 轮 任务3（goal 轮驱动域 / goal-round-driver 纯逻辑面）
- 日期：2026-09-13
- 上游基线：`G:\github\deepseek-harness` @ `a305303422`（0.1.5-rc.2；HEAD `9d9035b7c1` 为 FreeBSD fork +2 平台提交）
- 交付状态：**完成**（测试 PASS + 反跑 3/3，见 §3/§4）

## 一、交付清单

| 文件 | 行数 | 说明 |
| --- | --- | --- |
| `lightharness/src/目标轮驱动.light` | 263 | 上游 `goal-round-driver` 判定族 + 轮次推进状态机 + 提示渲染（纯逻辑面） |
| `lightharness/examples/test_目标轮驱动.light` | 191 | 72 条断言（≥12 达标） |
| `lightharness/_antirun_goalround.py` | 98 | 字节级备份/变异/恢复反跑，3 判据 → `ALL OK` |

## 二、上游对应表（文件 / 行号 / 核心语义）

| 光明实现 | 上游位置（实际行号） | 核心语义 |
| --- | --- | --- |
| `是目标轮来源` | `goal/goal-round-driver/src/index.ts:49-51` | `source.kind === 'goal' && source.round > 0`（round 0 是「非自动续作」标记） |
| `同轮` | `index.ts:54-58` | `goalId`/`revision`/`round` 三者精确相等（RoundIdentity） |
| `同排队记录` | `index.ts:61-63` | 同轮 + `isDeepStrictEqual(content, attempt.content)` → 用 `序列化JSON` 表达深度相等 |
| `取目标引用` | `index.ts:66-68` | `{ id, revision }`（GoalRef，CAS 引用） |
| `可驱动` | `index.ts:102-109` | fiber ACTIVE && !stopping && agent 在册 && status==='idle' && !competingQueued |
| `检查点后就绪` | `index.ts:112-114` | `readyToDrive && !needsCheckpoint`（检查点后所有条件需复验） |
| `推进一轮` §2 | `index.ts:142-154` | needsCheckpoint → 清标记 → `sessions.flush`；失败 → disarm；`!readyAfterCheckpoint` → 返回 |
| `推进一轮` §3 | `index.ts:156-162` | 已有 attempt → 清 attempt + `needsCheckpoint=true` + `requested=true`（让位） |
| `推进一轮` §4 | `index.ts:164-165` | `goal.phase === 'active' && goal.activation === 'armed'` 否则返回 |
| `推进一轮` §5 | `index.ts:166-172` | `roundsStarted >= maxGoalRounds` → `goals.block(code:'round-limit')` |
| `推进一轮` §6 | `index.ts:174-190` | `round = roundsStarted + 1`；`renderGoalRoundPrompt`；构造 RoundAttempt（queued/false/false）；`followup` |
| `推进一轮` §7 + `队列失败封禁判定` | `index.ts:191-204` | 入队抛错 → 清 attempt；最新目标同引用且 active+armed → `block(code:'queue-failed')` |
| `渲染目标轮文本` / `渲染目标轮提示` | `prompt.ts:12-26` | 单块 `{type:'text'}`；`<goal_round>\nObjective: <JSON(客观)>\nRound: 轮/上限\n\n<固定指令>\n</goal_round>` |
| `轮次结束栅栏` | `index.ts:329-339` | `max-tokens` → disarm；`aborted` → claimed/admitted 的 attempt 标 cancelled，否则 disarm |
| `字段别名表` / `视图取` | `goal/goal/src/types.ts:20-25,90-99`（GoalRef/GoalView 字段） | 目标视图字段读取（英文键 + 中文别名回退） |

> 行数说明：任务书标注 `index.ts` 525 行 / `prompt.ts` 80 行，实测为 **457 行 / 26 行**（0.1.5-rc.2 实际体量）；
> 另有 `invariant.ts` 84 行（包内不变量伴随插件），其语义已作为「未移植项」登记（见 §5），未纳入本轮纯逻辑面。

## 三、实现要点

1. **目标视图形状对齐 `src/目标折叠.light` 的投影字段**（只读参考，不接其内部）：
   `{id, revision, objective, phase, maxGoalRounds, roundsStarted, createdAt, updatedAt, activation}`，
   `phase ∈ active|paused|blocked|complete`、`activation ∈ armed|disarmed`。
   为兼容中文键投影，字段读取统一走 `视图取`（`字段别名表` 英文键优先、中文别名回退：
   `objective↔客观`、`maxGoalRounds↔最大轮数`、`roundsStarted↔已开轮次`、`phase↔阶段`、`activation↔激活`、
   `id↔标识`、`revision↔修订`、`kind↔类别`、`goalId↔目标标识`、`round↔轮次`、`messageId↔消息标识`）。
   测试同时覆盖英文键（§1~§6）与中文键（3j/3k/3l）两种形态。
2. **宿主面全部入参化**：`推进一轮(状态, 目标, 宿主)`，`宿主 = {驱动活跃, 检查点成功, 消息标识, 入队失败, 最新目标}`；
   状态字典承载 `{attempt, competingQueued/竞争排队, needsCheckpoint, requested, stopping, 纤维活跃, 代理在册, 代理空闲}`。
   决策动作集：`wait` / `disarm` / `defer-round` / `reserve` / `block` / `queue-failed`。
3. **文案策略**：阻止块消息按任务书取中文形态（`目标达到配置上限 N 轮`、`无法为目标轮次 N 入队: 原因`），
   码沿用上游 `round-limit` / `queue-failed`；提示正文（Objective/Round/三段固定指令/首尾标记）**逐字对齐** `prompt.ts`。
4. **与既有模块的关系（重要）**：`src/目标折叠.light:365-579` 在更早轮次已内含一份「轮次驱动决策」区块
   （`驱动决策`/`预约有效`/`预步目标决策` 等）。本模块是任务书要求的**专用纯逻辑模块**，语义与之保持一致
   （深比较走 `序列化JSON`、就绪栅栏同口径、轮号 = 已开+1），并补上 `推进一轮` 的检查点阶段与 `queue-failed` 阻止块。
   本轮**未改** `目标折叠.light`（互斥表：只读）；两处并存造成的重复实现已在 §7 提示 路M 决策是否归并。

## 四、测试与反跑结果

- 运行命令：`cd G:\dswork\duan-light-merge\lightharness; $env:LIGHT_MERGE="G:\dswork\duan-light-merge\light-merge"; python 运行.py examples/test_目标轮驱动.light`
- 输出：`test_目标轮驱动 PASS`，**rc=0**（72 条断言，≥12 达标）
- 覆盖：来源判定（正轮/零轮/非 goal/轮次非整数）、同轮比较、同排队记录深比较、目标引用、
  就绪栅栏（stopping/代理空闲/竞争排队/代理不在册/纤维不活跃/需检查点）、目标视图别名读取、
  未激活等待（目标空/非 active/未武装/驱动不活跃）、轮次上限阻止（码/消息/引用）、
  预留下一轮（轮号=已开+1、预约形状 6 字段、落入状态）、已有预约让位（清预约+需检查点+置请求）、
  检查点失败 disarm / 检查点后复验等待、入队失败（阻止码/消息含原因与轮号/清预约/引用变化则不封禁）、
  提示渲染（首尾标记/objective 序列化/Round 轮上限/三段固定指令/单块 text）、轮次结束栅栏（4 分支）。
- 反跑：`python _antirun_goalround.py` → **3/3 ALL OK**
  - A 轮号改 `roundsStarted`（`设 轮 为 已开 + 1` → `已开`）→ 红（rc=1）
  - B 轮次上限不再阻止（`已开 >= 上限` 的 block 分支改为 `已开 > 上限` + 返回 wait）→ 红（rc=1）
  - C 提示缺 `</goal_round>` 收尾（去掉尾标记拼接）→ 红（rc=1）
  - 恢复后 sha256 字节级一致 + 回归绿（rc=0，PASS 已打印）
- 回归门禁抽样：`python -m pytest tests/ -q -k "u76ee or u4f1a or L092"` → **23 passed, 242 deselected**（含本用例）

## 五、未移植项（宿主面登记）

| 上游位置 | 内容 | 处置 |
| --- | --- | --- |
| `index.ts:76-100` | `apply(ctx)` / `stateFor`（Map<Agent, DriverState>）/ `currentGoal`（`ctx.agents.get`/`ctx.goals.get`） | 宿主：agent 生命周期与 goal 服务接线 |
| `index.ts:117-135` | `disarm`（`ctx.goals.disarm`）/ `restoreOtherClaimed`（`agent.inbox.prepend`） | 宿主：goal 服务 + inbox 回插 |
| `index.ts:205-241` | `requestDrive`（`ctx.agents.withoutInitiator` 串行驱动循环 + `run.then(retire)`） | 宿主：并发/事件循环 |
| `index.ts:245-317` | `ctx.effect` 事件接线：`agent/error|created|disposed|session-start|status`、`goal/changed`、`agent/inbox/inserted|claimed|discarded`、`session/event` | 宿主：cordis 事件层；其中 `session/event turn/end` 的**纯决策面**已移植（`轮次结束栅栏`） |
| `index.ts:346-359` | `validReservation`（fail-closed 合取，读 live fiber/agent/goal） | 宿主：与 `目标折叠.预约有效` 重复，本轮不重复移植 |
| `index.ts:361-426` | `agent/pre-step` 钩子（reject / restoreOtherClaimed / `startsRequestSeries`） | 宿主：pre-step 钩子接线 |
| `index.ts:428-456` | 既存 agent 强制 disarm + 关闭时 `stopping`/`cancel`/`await allSettled` | 宿主：生命周期收尾 |
| `invariant.ts:1-84` | 包内不变量伴随插件（重放 `foldGoal` 校验目标轮提示内容与持久前缀一致） | 宿主：invariants 服务接线；需 `foldGoal` 全量折叠（`目标折叠` 已有） |

## 六、语言差异（新缺陷 + 建议编号）

见 §任务4 报告 §6 同一条（编号 **L-093**，由任务4 报告统一登记；本轮实测该缺陷正是任务3/4 跨模块调试的共性坑）。

本轮任务3 自身未发现新的编译器缺陷：
- 布尔链（`且`）在 `如果` 条件内联可用（第12轮 L-043 已缓解），本模块未使用行内布尔链以防回归；
- `段落` 级函数名 `取目标引用`（`取` 为关键字词根）**模块级可用**（类成员名仍需避开）；
- `字典获取(字典, 缺失键)` 返回 Python `None`（与 `空` 比较成立），已据此写 `视图取` 的缺省回退。

## 七、移交清单

1. 交付物 3 件（§一 表格）+ 本报告；建议 路M 提交形如
   `任务3(goal轮驱动域): goal-round-driver纯逻辑面复刻(判定族+轮次状态机+提示渲染; 反跑3/3)`。
2. 对标回填建议：**#88 = goal-round-driver**（对应 `src/目标轮驱动.light` + `examples/test_目标轮驱动.light`）。
   注意 `#35 目标折叠` 状态串已含「0.1.5路3：goal 激活边界/轮次驱动(目标折叠.light)」—— 是否把驱动面归并到 #35 或单列 #88，请 路M 决策并保持两处状态一致。
3. 缺陷账：**新增 L-093**（跨模块未捕获异常位置块错配；repro `examples/_repro_L093.light`）。
4. 未移植项（§五 表格）建议在 #88 状态串登记「宿主面：agent 接线/inbox/pre-step/驱动循环/生命周期未移植」。
