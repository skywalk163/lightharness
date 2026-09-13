# 任务4 交付报告 —— 调度深化与任务守卫域（schedule 深化 + jobs 品牌/类型 + guard 交叉核对）

> 轮次：复刻 第15轮 ｜ 日期：2026-09-13 ｜ 对标卡：**#101（新增）** ｜ 差异编号 **R15-D4** ｜ 缺陷编号预分配 **L-127~L-128**
> 上游只读：`G:\github\deepseek-harness`（本地 HEAD `9d9035b7c1`；任务书标注 `a305303422`，差异见 §六）
> 本路可写文件（4 个，全部新增，零越界）：
> - `lightharness/src/调度深化.light`（574 行 / 58 段）
> - `lightharness/examples/test_调度深化.light`（227 行 / **128 断言**）
> - `lightharness/_antirun_t4_调度深化.py`
> - `lightharness/_task4_调度深化_交付报告.md`（本文件）
> 另：最小复现 `lightharness/examples/_repro_L127.light`（铁律 2 要求，缺陷 L-127）

---

## 一、上游对应表（文件 / 行号 / 核心语义）

| 上游 | 行 | 核心语义 | 本模块落点 |
|---|---|---|---|
| `schedule/schedule/src/projection.ts` | 14–17 `ScheduleProjectionState` | 继承切点 `inheritedEventCount` + 完整折叠 `FoldedSchedules` | §2 `投影初值` / `投影应用`（状态形状） |
| `schedule/schedule/src/projection.ts` | 19–30 `scheduleId` 变换 | 通过 delete 解码反推合法 id | §1 `是调度变更`（delete 分支：`id` 必为字符串） |
| `schedule/schedule/src/projection.ts` | 32–43 `scheduleRecord` 变换 | 通过 create 解码反推合法记录 | §1 `是调度记录` / `是调度变更`（create 分支） |
| `schedule/schedule/src/projection.ts` | 47–66 `stateSchema`（strict + superRefine） | 三条不变量：seenIds 唯一 / active.id 必出现过 / active.id 唯一 | §2 `校验投影状态` / `是合法投影状态` |
| `schedule/schedule/src/projection.ts` | 69–85 `scheduleProjectionDefinition` | `init` / `apply`（seq 切点）/ `wire.view=active` / `stateVersion=2` | §2 `投影状态版本` / `投影初值` / `投影应用` / `投影视图` |
| `schedule/schedule/src/projection.ts` | 74 | `event.seq < inheritedEventCount \|\| event.type !== 'schedule/change'` → 状态原样 | §2 `投影应用` 前置守卫 |
| `schedule/schedule/src/transaction.ts` | 5 | `const tails = new WeakMap<Agent, Promise<void>>()` | §3 **L-127 命中点**：改为「字符串归属令牌 → 标记」字典 |
| `schedule/schedule/src/transaction.ts` | 13–23 `runScheduleTransaction` | `prior`/`tail`、`finally` 中「仅当尾仍是我自己的才删除」 | §3 `造事务尾表` / `事务入队` / `事务收尾` / `事务占用` |
| `schedule/schedule/src/types.ts` | 全 228 行 | `ScheduleStatus`/`AfterSchedule`/`AtSchedule`/`EverySchedule`/`ScheduleChange`/`PersistenceUncertainError`/`ScheduleView`/`ScheduleDeleteResult`/`ScheduleToolError` 码集 | §1 全部形状判据与错误族 |
| `schedule/schedule/src/types.ts` | 「固定间隔绝不小于五分钟」注释 | `everySeconds ≥ 300` | §1 `是每调度记录` |
| `jobs/jobs/src/brand.ts` | 19 `JobId` / 26–28 `JobId(id)` | 品牌同一性函数（不校验） | §4 `造任务标识`（+ 项目级 `是任务标识形状`） |
| `jobs/jobs/src/brand.ts` | 15–18 注释 | 「registry generates `<kind>-N`；可预测，靠 owner 授权而非保密」 | §4 `是任务标识形状` 的判据依据 |
| `jobs/jobs/src/types.ts` | 17 `JobStatus` | `running → (stopping) →` 恰好一个终态 | §4 `任务状态表` / `是合法任务状态` / `是任务终态` / `是任务活动态` |
| `jobs/jobs/src/types.ts` | 23–29 `JobKindMap`/`JobKind` | 可声明合并的生产者种类 | §4 `任务种类表` / `是合法任务种类` |
| `jobs/jobs/src/types.ts` | 32–39 `JobOutcome` | `status ∈ 终态子集` + 可选 `detail`/`output` | §4 `是任务结局` |
| `jobs/jobs/src/types.ts` | 46–69 `JobStart` | `kind`/`label` 必填，`outputLimitBytes` 可选，`run()` 宿主能力 | §4 `是任务启动声明`（`run` 按宿主面剔除） |
| `jobs/jobs/src/types.ts` | 72–91 `JobHooks` | `cancel`/`done`/`readOutput` 运行时控制面 | **剔除**（宿主能力，纯类型） |
| `jobs/jobs/src/types.ts` | 97–128 `JobSnapshot` | 六必填 + 四可选字段 | §4 `是任务快照` |
| `jobs/jobs/src/types.ts` | 131–140 `JobRead` | `text` + `snapshot` | §4 `是任务读取` |
| `jobs/jobs/src/types.ts` | 146–149 `JobDoneListener` | `(snapshot, owner?) => void` | §4 `是完成监听载荷` / `监听器种类表` |
| `jobs/jobs/src/types.ts` | 160 `JobsChangedListener` | `(owner: Agent \| undefined) => void`；`undefined` 表示无主任务变化 | §4 `是变更监听载荷` |
| `guard/repeat-tool-reminder/src/index.ts`（233 行） | — | 连续重复工具调用提醒 / 通配 / 阈值 | **已覆盖** `src/重复提醒.light` → §5 只读集成回归 |
| `guard/timeout-policy/src/index.ts`（81 行） | — | 超时限定解析 / 截止推导 / 策略结局 | **已覆盖 #52** `src/超时策略.light` → §5 只读集成回归 |

---

## 二、实现要点

### §1 调度类型与错误族
- 封闭词表一律「`是字符串` 前置 + 逐项比较」，非法/非串输入安全返回假（L-103 同族纪律）。
- `调度工具错误码表` 10 条与上游 `ScheduleToolError` 码集逐条一致；`造持久不确定错误` 额外携带必填 `operation` 与可选 `id`，`id` 缺省时不落键（保键序）。
- 三种记录形状（`after` / `at` / `every`）共享 `是记录骨架`（`id`/`kind`/`prompt`/`scheduledAt`，且 `prompt` 修剪后非空），再各自判 `kind` 与专属字段域；`是每调度记录` 额外强制 `everySeconds ≥ 300`。
- `是调度变更` 严格 `version === 1` 且 `operation ∈ {create, delete, dispatch}`，并按 operation 分派必填字段（create→`schedule`；delete/dispatch→`id`）。
- `构造调度视图` 按记录原键序写入后再补 `state`/`deliveryMode`（**规避 L-116**：`序列化JSON` 保插入序，键序须与上游对象展开一致）；`是调度视图` 反向剔除这两个键后复用 `是调度记录`。
- `造删除结果` 复刻上游判别结果：`deleted:true` 时不带 `code`；`deleted:false` 时带 `code:'schedule_not_found'`。

### §2 调度投影（`projection.ts`）
- `投影状态版本() == 2`；`投影初值(继承事件数)` 返回空 `active`/`seenIds`。
- `投影应用` 逐句对照：`seq < inheritedEventCount` 或 `type != 'schedule/change'` → **状态原样返回**（不新建对象，测试以 `==` 判同一内容）。
- 活动集以「`id → 记录`」字典承载维护（create 覆盖 / delete 移除 / dispatch 推进），返回时**还原为列表**并保插入序，以对齐上游 `active: ScheduleRecord[]` 的形态；`seenIds` 用 `拷贝列表` 快照（**规避 T5C-07 悬空句柄**）。
- `应用单条变更` 复用 `定时.派发记录`（#29）判定 every 派发的下一次目标；一次性 dispatch（无 acceptedAt）→ 退出活动集，every dispatch（带 acceptedAt）→ 保留并推进 `scheduledAt`。三处越界（id 复用 / delete 目标不在活动 / dispatch 目标不在活动）一律 `抛出 新建 错误(...)`，与上游 `decodeScheduleChange` 的抛错语义对齐。
- `投影折叠` 直接委托 `定时.折叠调度事件`，**证明投影层与域层同源**（测试 2l/2m 对拍）。
- `校验投影状态` 逐条复刻 superRefine 三条不变量，返回中文诊断串（`""` 表合法）；`是合法投影状态` 即 `校验 == ""`。

### §3 调度事务（`transaction.ts`，L-127 命中点）
- 上游以 `WeakMap<Agent, Promise>` **按 Agent 对象身份**串行化；光明字典键须为可哈希标量，对象身份键不可表达（L-127）→ 绕法把「归属」降为**字符串令牌**、把「尾是否仍属本事务」记为**标记值**而非对象身份。
- `事务入队` 返回前序标记并登记本标记为当前尾；`事务收尾` 仅在「当前尾仍等于本标记」时才清除（等价上游 `if (tails.get(agent) === tail) tails.delete(agent)`）——防止后到事务被前者的收尾误删（测试 3f/3g 钉死）。

### §4 任务品牌与类型（`jobs`）
- `造任务标识` 保留 `JobId(id)` 的同一性语义（不校验）；另加项目级 `是任务标识形状`：按上游注释 `<kind>-N` 判据——最后一个连字符位置 ∈ (0, len-1) 且其后全为数字。上游不校验，属本研究加强项（已登记 §五）。
- `是任务终态`/`是任务活动态` 显式枚举，避免把 `stopping` 误判为终态；`是任务结局` 只接受终态子集 + 可选 `detail`/`output` 串。
- `是任务快照` 六必填 + 四可选，`reported` 严格布尔（用 `!= 真 且 != 假` 判，**规避 L-129 的 `0 == 假` 陷阱**）；`finishedAt` 可选但须非负整数。
- 监听器：完成载荷须含 `snapshot`；变更载荷**只要求 `owner` 键存在**（`undefined` 即「无主任务发生变化」，是刻意语义）。

### 本地工具
`字段齐备` / `是非负整数` / `是正整数` / `是空白码` / `修剪空白` / `拷贝表` / `拷贝列表` / `列表包含值` —— 全部本地实现，**规避跨模块同名段**（codegen 按段名映射，同名会函数重定义）。

---

## 三、验证结果

### 测试（128 断言，高于铁律 7 的「≥10」）
```
cd lightharness && python 运行.py examples/test_调度深化.light
===== 第 15 轮任务 4：schedule 深化 + jobs 品牌/类型域（纯逻辑面）=====
test_调度深化 PASS
RC=0
```

### 反跑 3/3（`python _antirun_t4_调度深化.py`）
```
✓ A 投影忽略继承切点 (判红运行 rc=1)
✓ B 事务收尾不校验身份 (判红运行 rc=1)
✓ C 任务终态漏 failed (判红运行 rc=1)
✓ 字节级恢复校验 (sha256 d04dd4ad08a4)
✓ 恢复后回归绿 (rc=0，PASS 已打印)
ALL OK
```
- **A**：`投影应用` 的 `事件["seq"] < 继承数` → `< 0 - 1`（永不成立），继承内事件被误折叠 → 2f「继承切点 忽略继承内事件」红。
- **B**：删掉 `事务收尾` 的 `如果 尾表[归属标识] != 本标记: 返回 假` → 旧标记会误删后到事务的尾 → 3f/3g 红。
- **C**：`是任务终态` 末句 `返回 值 == "failed"` → `返回 假` → 4l/4q 红。
- 三判据均**真变异立红**，恢复走 `finally` 并做逐字节 sha256 校验（第13轮教训：C 判据曾残留变异）。

### 复现
```
python 运行.py examples/_repro_L127.light   → RC=0
```

---

## 四、语言缺陷登记

### L-127（新增）字典键须为可哈希标量，对象/列表身份键不可表达
- **证据**：`字典设置(表, [1,2], 真)` 抛 Python 运行时原生 `TypeError: unhashable type: 'list'`（**未走光明错误体系**，无中文诊断，也不能被 `是字典/是...错误` 一类判据识别）。
- **触发面**：任何以对象身份作字典键/Set 键的移植。本路上游 `transaction.ts:5` 的 `WeakMap<Agent, Promise>` 直接命中。
- **绕法**：以字符串令牌作键承载归属身份（`造事务尾表` 形态），把「是否仍属本事务」记为标记值。
- **复现**：`examples/_repro_L127.light`（含前提断言：若对象键已被支持或异常文本改变则主动报错复核）。

> 预分配 **L-128 未占用**（本路未再发现独立缺陷），按第14轮先例空缺顺延。

---

## 五、上游面剔除与偏差登记

| 上游面 | 处置 | 理由 |
|---|---|---|
| `schedule/domain.ts` | **剔除** | **已覆盖 #29** `src/定时.light`；本模块投影**只读复用**其状态机，保证不产生第二份语义 |
| `schedule/tools.ts` / `index.ts` / `invariant.ts` / `persistence.ts` / `runtime.ts` / `client.ts` | **剔除** | 宿主装配面 / Cordis 不变量 / 存储后端 / 调度器运行时 / 纯类型重导出（并入 types） |
| `jobs/index.ts` / `invariant.ts` | **剔除** | Cordis Service 定义与不变量安装器（宿主面） |
| `jobs-local/` / `tool-jobs/` | **剔除** | **已覆盖 #53** `src/任务系统.light` |
| `guard/repeat-tool-reminder` / `guard/timeout-policy` | **剔除（只读回归）** | 分别由 `src/重复提醒.light` 与 **#52** `src/超时策略.light` 覆盖；本路测试 §5 对其做只读集成回归，证明无需重复实现 |
| `jobs/types.ts` 的 `JobHooks`（cancel/done/readOutput） | **剔除** | 运行时控制面（Promise/回调），纯类型无逻辑 |
| `ProjectionDefinition` / `SessionLogOffset` / `z.ZodType` 类型装配 | **简化** | 光明无类型品牌与 zod 运行时；保留同一性语义与不变量判据 |
| 任务标识形状（`<kind>-N`） | **加强（本研究新增）** | 上游 `JobId` 不校验；按上游注释不变量补可测判据 |

---

## 六、待路M裁定 / 移交清单

1. **对标卡 #101**：本路新增，建议登记为「schedule(projection/transaction/types) + jobs(brand/types) 纯逻辑面」，并注明 `domain.ts` 已由 #29、`jobs-local`/`tool-jobs` 已由 #53、guard 两包已由 `重复提醒.light`/#52 分别覆盖，避免与 #29/#52/#53 的边界被误读为重复。
2. **行为差异 R15-D4**：建议记录两条 ——（a）事务串行化由「Agent 对象身份」降为「字符串归属令牌」（L-127 绕法，语义等价但键类型不同）；（b）任务标识形状判据为本研究加强项（上游不校验）。
3. **任务书反跑判据映射**：任务书 §反跑判据3项 写的是「A every 投影下次运行时间 / B 空调度事务 / C timeout-policy 默认超时改错」，但 `timeout-policy` 已在 #52 覆盖（本路不可写其源文件）。故 A/B 落在投影与事务本体（2f 继承切点、3f/3g 事务身份），C 等价落在「终态判定漏 failed」——同为**可变异且测试立红**的判据，覆盖任务书意图。
4. **文档/上游版本差异**：任务书头部标注上游 `a305303422`，本地工作副本 HEAD 为 `9d9035b7c1`。本路以**目录布局与文件内容**为对齐依据（任务书列出的全部 schedule / jobs / guard 文件均存在且语义吻合），未发现内容漂移；如路M有权威 pin，请以 pin 复核。
5. **未移植项**（供 #101 备注）：`runScheduleTransaction` 的 Promise 尾链异步执行体、投影 `apply` 的事件流驱动、JobHooks 运行时控制面、`randomUUID` 类身份生成。
