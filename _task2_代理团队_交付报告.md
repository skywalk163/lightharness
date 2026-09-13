# 任务2 交付报告：代理团队域（experimental/agent-team 纯逻辑面 → src/代理团队.light）

> 任务来源：`G:\dswork\duan-light-merge\复刻_第14轮_任务prompt分发 (1).md` 任务2
> 日期：2026-09-13 ｜ 上游只读：`G:\github\deepseek-harness` @ `a305303422`（0.1.5-rc.2）
> 目标模块：`lightharness/src/代理团队.light`（对标 #93 agent-team；与 subagent 域互补）

---

## 一、上游对应表（packages/experimental/agent-team/src/，16 文件 2476 行）

> **上游源码与任务书差异的重要声明**：经逐文件精读，任务书预设的若干语义在上游**不存在**——
> 无分页（cursor/limit）、无能力标签与分配推荐、无 idle/busy/offline 枚举、无团队暂停/终止状态机、
> 无活动流聚合文件语义（activity.ts 实为变更等待器）、lifecycle.ts 实为处置所有权。
> 本模块以上游真实语义为主体，任务书点名且测试要求的三项（分页/活动聚合/生命周期状态机）作为
> **补充实现**并在 §五 登记；状态枚举采用上游真实值（任务 pending/in_progress/completed/deleted）。

| 上游位置 | 光明段落 | 核心语义 |
|---|---|---|
| validation.ts（34 行） | 需要文本 / 归一写域 | `${field} must be non-empty` / `${field} exceeds ${N} characters`；写域归一（`\`→`/`、去 `./`、去尾 `/`）+ `invalid workspace-relative write scope ${JSON.stringify(v)}` 逐字 |
| roster.ts（487 行） | 校验成员名 / 造成员事件 / 找活跃成员 | lower-kebab-case ≤64 非 lead（逐字文案）；重名 `was already used in this Team`、上限 `Team member limit N reached`、`only the Team Lead can create teammates`；`active teammate "X" not found` |
| task-graph.ts（69 行） | 断言任务图 / 检测依赖环 | 自引用/重复 blocker/缺失或已删（逐字文案）+ DFS 双色环检测 `task dependency cycle includes "X"`；菱形依赖不误报（访问中回溯重建） |
| task-board.ts（297 行） | 造任务事件 / 改任务事件 / 任务就绪 / 判动作门槛 | 上限 `Team task limit N reached`、id 空间 `Team task id space exhausted`；CAS `stale team task "X" revision E; current revision is C`、deleted、授权 `task mutation requires its owner or Team Lead`；九动作全文案（claim 被占/not ready、release/complete/reopen/reassign 门槛、edit 无字段、set_dependencies 缺参、delete 有依赖者 `still blocks "Y"`）；修订+1、写域归一；ready=blockedBy 全 completed |
| mailbox.ts（331 行） | 发消息事件 / 确认送达事件 / 未读数 | `Agent Teams service is disposing`、自发 `a Team member cannot message itself`、邮箱满 `has N pending messages`、`team message exceeds N bytes`；pending = queued − delivered；目标 active 即 accepted |
| journal.ts（73 行）+ types.ts 持久化事件 | 折叠团队状态 | 4 类事件（team/member、team/task、team/message/queued、team/message/delivered）version 恒 2；纯折叠投影 成员表/任务表/消息表/送达表/下个任务号 |
| invariant.ts（36 行） | 校验事件流 | candidate 回放：`session event N violates the Agent Teams stream: …` |
| error.ts（23 行） | 错误文案承载 | 28 个 TEAM_* 码散布各文件（摘要逐条对齐）；结构化 code 字段未复刻（登记） |
| session-message.ts（31 行） | 消息接受判定 | 投影为 delivered 送达判定（inbox 折叠 splice 形状简化，登记） |
| index.ts（324 行） | 配置键（成员上限 8/任务上限 256/待投递上限 64/消息字节上限 65536） | 校验 `${name} must be a positive safe integer` 并入配置段 |
| client.ts / persisted.ts / projection.ts | 宿主面剔除 | Cordis 客户端/持久化读/投影订阅剔除（投影的纯折叠部分保留为 折叠团队状态） |

**任务书补充实现**（上游无对应，登记 §五）：
- **任务分页** `任务分页(任务表, 游标, 限量)`：cursor=offset、limit>0、返回 {任务表, 下页游标}（第 11 轮 team_task_list 同范式）。
- **活动流聚合** `近期活动(事件表, 条数)`：最近 N 条按时间倒序、连续同类型聚合计数 {种类, 次数, 最近时间}。
- **团队生命周期状态机** `断言团队转移`（活跃/暂停/已终止三态 + 合法转移校验 `invalid team transition: A -> B`）与 **终止清理** `清理终止任务`（in_progress→deleted 墓碑，修订+1；任务书文案 cancelled，上游无该状态，登记）。

## 二、实现要点

1. **事件溯源纯函数化**：状态全部由事件表折叠推导（折叠团队状态），操作段落=校验+构造新事件返回，落库由调用方承担（对齐上游事务内 append + 投影）。
2. **不可变更新**：mutation 构造新任务快照（修订+1，不可变段逐键拷贝），不原地改旧快照。
3. **授权豁免语义**：claim 动作整体豁免 owner-or-lead（否则认领无主/被占错误均不可达，对齐上游可达语义）；reassign 的 lead 检查在授权后（owner 非 lead 才可触发 `only the Team Lead can reassign tasks`）。
4. **DFS 环检测**：访问中/已访双集，回溯时重建移除访问中标记（菱形依赖不误报，测试专条验证）。
5. **绕法**：无 且/或 行内链（L-043）、标识符避关键字（L-084/L-092）、无花括号文案（L-089）、字符串原语内置裸名（L-090）、副本（L-082 修复后原语）。

## 三、测试验证

```
cd G:\dswork\duan-light-merge\lightharness
$env:LIGHT_MERGE="G:\dswork\duan-light-merge\light-merge"; python 运行.py examples/test_代理团队.light
test_代理团队 PASS   （rc=0）
```

`examples/test_代理团队.light` 覆盖 10 组 ≥55 断言：校验族（需要文本/写域 4 形态/成员名 5 形态）、任务图（环/自引用/重复/缺失/菱形不误报/就绪判定 2 态）、看板 create（快照形状/超限/超长主题/依赖缺失）、update（stale/deleted/越权/claim 三形态/release/complete/reopen/edit/set_dependencies/reassign/delete 全动作 + 修订推进）、名册（超限/重名/lead 解析/活跃解析/非活动与未知抛错）、邮箱（已处置/自发/目标非活动/超字节/accepted/邮箱满/确认与未读数推进/接受判定）、投影与 invariant（折叠计数/下个任务号/未知事件/事件流违规）、分页（限量/游标/deleted 过滤/末页无游标/零限抛）、活动聚合（倒序/连续同类型计数/最近时间）、生命周期（三转移合法/非法转移/终止清理 in_progress→deleted）。

## 四、反跑结果（3/3 ALL OK）

`G:\dswork\duan-light-merge\_antirun_t2_代理团队.py`（字节级备份→变异→跑本路测试→断红→恢复→断绿；恢复置于 try/finally）：

```
PASS A 任务图环检测改为不检测 -> 红 (变异后运行 rc=1（期望非 0，真红）)
PASS B 状态流转不再校验(release 门槛失效) -> 红 (变异后运行 rc=1（期望非 0，真红）)
PASS C 邮箱消息确认后不标记已读 -> 红 (变异后运行 rc=1（期望非 0，真红）)
PASS 字节级恢复校验 (sha256 da37a462472b)
PASS 恢复后回归绿 (rc=0)
ALL OK
```

## 五、未移植项（宿主面登记）与任务书/上游差异

- **宿主面剔除**：client.ts（Cordis 客户端/服务总线）、persisted.ts（持久会话读取）、projection.ts 的订阅/缓存机制（纯折叠保留）、roster spawn 的子会话实际拉起与 settle/failed 流程、mailbox 的 dispatchTails 串行投递/steer/flush（accepted 判定简化为「目标 active 即达」）、activity.ts 变更等待器（wait/notify/timeout 10000..3600000）、lifecycle.ts 处置所有权（AbortController/allSettled/超时）。
- **任务书补充实现（上游无对应）**：任务分页、活动流聚合、团队生命周期状态机与终止清理——已实现并测试覆盖；清理终态用上游 deleted 墓碑而非任务书文案 cancelled（上游无该状态）。
- **任务书/上游差异**：状态枚举以上游为准（pending/in_progress/completed/deleted；成员 provisioning/active/failed）；writeScope 重叠警告 `write scopes overlap with X` 已在 摘要 对齐但未入测试断言；邮箱满文案以目标标识替代上游成员名投影。
- 结构化错误码（TEAM_*）以文案承载，未复刻 code 字段。

## 六、语言差异（本轮新缺陷登记）

- 无新缺陷（L-107~L-110 编号空缺，路M 顺延）。
- 行为差异（R14-D2）：localeCompare/JSON.stringify 形态、上游 Map/Set 迭代序语义由显式排序替代。

## 七、移交清单

- `lightharness/src/代理团队.light`（新增，≈660 行）
- `lightharness/examples/test_代理团队.light`（新增，PASS rc=0）
- `G:\dswork\duan-light-merge\_antirun_t2_代理团队.py`（反跑 3/3 ALL OK）
- 本报告。
- 移交路M：对标清单新增 **#93**（agent-team）；行为差异清单 **R14-D2**（任务书补充实现三项 + 状态枚举以源码为准声明）；CI 增 1 个 test_ 文件（273 passed 占 1）。
