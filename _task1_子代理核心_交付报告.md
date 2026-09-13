# 任务1 交付报告 —— 子代理核心域（subagent 核心 上：catalog/descriptor/depth/error/assistant-output/inbox）

> 轮次：复刻 第16轮 ｜ 日期：2026-09-13 ｜ 对标卡：**#104（新增）** ｜ 差异编号 **R16-D1** ｜ 缺陷编号预分配 **L-131~L-132**
> 上游只读：`G:\github\deepseek-harness`（本地 HEAD `9d9035b7c1`；任务书标注 `a305303422`，差异见 §六）
> 本路可写文件（4 个，全部新增，零越界）：
> - `lightharness/src/子代理核心.light`（597 行 / 段数见下）
> - `lightharness/examples/test_子代理核心.light`（267 行 / **117 断言**）
> - `lightharness/_antirun_t1_子代理核心.py`
> - `lightharness/_task1_子代理核心_交付报告.md`（本文件）
> 另：最小复现 `lightharness/examples/_repro_L131.light`（铁律 2 要求，缺陷 L-131）
>
> ⚠️ **探针纠偏（重要）**：本路初用 5 个探针（`_probe_r16a~e.light`）探查缺陷，其中两处初步结论被**干净复现推翻**，已据实修正——
> - 探针 r16d 以为「畸形 `段落` 签名被静默丢弃」成立；但用缺冒号签名 `_repro_L131` 原形态复现时，解释器**明确报语法错误**（行 16 列 12「期望冒号」），故该"静默丢弃"**不成立**，不登记为缺陷。
> - 探针 r16b 以为"光明无 isFinite/isNaN 内置、浮点有限性须文本判定"是缺陷；但 `_repro_L132` 原形态复现 `1.0/0.0` 时解释器**直接抛除零错误**（而非产出 `Inf`），即光明根本无法产出 `inf/nan`，"缺 isFinite" 因而**无实际意义**，不登记。
> 真缺陷见 §四：L-131（除法 x/0 抛错而非 ±Inf/NaN）。探针已删除。

---

## 一、上游对应表（文件 / 行号 / 核心语义）

| 上游 | 行 | 核心语义 | 本模块落点 |
|---|---|---|---|
| `subagent/subagent/src/catalog.ts` | 156 | 父侧子代理目录事件载荷、`SUBAGENT_CATALOG_VERSION`、分块投影（`applyCatalogEvent`/`projectSubagentCatalog`/`foldCatalog`）、`validateCatalogState`、`viewCatalog`（行） | §1 `目录载荷版本`/`目录模式表`/`是目录条目`/`造目录条目`/`造目录行`/`是目录行`/`目录状态版本`/`目录投影初值`/`应用目录事件`/`目录条目表`/`校验目录状态`/`造目录确立载荷` |
| `subagent/subagent/src/descriptor.ts` | 323 | 持久描述符 `version=3`、one-shot/continuable 键集、`toolFilter`、`snapshotSubagentDescriptor`（脱敏+JSON 安全校验）、`parseSubagentDescriptor`（旧版本→空、形状不符抛错）、`foldSubagentDescriptor` | §2 `描述符版本`/`描述符基础键表`/`描述符可续键表`/`是工具过滤`/`是单次描述符`/`是可续描述符`/`是描述符`/`造描述符`/`解析描述符`/`折叠描述符`/`解析工具过滤` |
| `subagent/subagent/src/depth.ts` | 51 | `delegationDepth`（头部权威、取较大值）、`maxDepth` 可选非负安全整数 | §3 `读委托深度`/`校验最大深度`/`是合法最大深度` |
| `subagent/subagent/src/error.ts` | 15 | `SubagentError` 名 + 错误码集 | §4 `子代理错误名`/`子代理错误码表`/`是子代理错误码`/`子代理错误消息`/`造子代理错误`/`是子代理错误` |
| `subagent/subagent/src/assistant-output.ts` | 75 | `joinAssistantStreamText` / `collectTextBlocks` / `finalAssistantOutput`（末条非空 assistant 优先，否则回落累计流文本） | §5 `合并助手流文本`/`收集助手文本`/`归一助手输出` |
| `subagent/subagent/src/inbox.ts` | 70 | `ActivationInbox`（投递/积压/`close` 幂等/关闭中拒绝 `ACTIVATION_CLOSING`） | §6 `交付方式表`/`是交付方式`/`造收件箱`/`是收件箱`/`收件箱积压`/`收件箱投递`/`收件箱关闭`/`读收件箱关闭` |

> 任务1 上游仅列上述 6 文件（任务书明确）；`subagent` 包的其余文件（`activation`/`dispatch`/`message-passing`/`sandbox`/`lifecycle`/`index.ts`、宿主 `subagent-local`）均不在本路范围，见 §五剔除。

---

## 二、实现要点

### §1 父侧子代理目录（catalog.ts）
- `SUBAGENT_CATALOG_VERSION=0`；`mode ∈ {one-shot, continuable}` 二值校验。
- 目录事件载荷形状：`{version, childId, childCreatedAt, mode}` + continuable 必带 `label`；`childId` 非空串、`childCreatedAt` 非负整数。
- **分块投影**：`应用目录事件` 对非 `subagent/catalog` 事件或 `seq < inheritedEventCount`（继承切点）一律原样回退；否则 `head` 追加 `data`。`目录条目表` 把 `head` 投影为 `view` 行（`{id, createdAt, mode, label?}`），键序对齐上游对象字面量（规避 L-116 键序对拍假红）。
- `validateCatalogState` 三不变量：状态须字典、`inheritedEventCount` 非负整数、`head` 为列表且每项 `是目录条目`。

### §2 持久描述符（descriptor.ts）
- `version=3`；one-shot 键集 `{version,mode,provider,label}`，continuable 另含 `agentProvider/agentModel/agentReasoningEffort/persona/toolFilter`。
- `toolFilter`：`{allow?, deny?}` 至少其一为字符串数组；用 `核只含键` 拒绝未知键。
- `造描述符`（快照）：剔除非当前键、可选键空值不落、`核是JSON安全值` 兜底（见 §五 偏差）。
- `解析描述符`：`version != 3` → 返回 `空`（旧版本不解析）；当前版本形状不符 → 抛错，文案逐条对齐上游（`must be an object` / `must be a number` / `one-shot or continuable` / `unknown field` / `provider must be a string` / `label must be a string` / `allow and/or deny` / `array of strings` / `JSON-serializable`）。
- `折叠描述符`：首条 `subagent/descriptor` 事件为准（`fold` 语义）。

### §3 委托深度（depth.ts）
- `读委托深度`：头部权威且单调（取 `headerDepth` 与 `runtimeDepth` 较大值）；运行时深度须非负安全整数。
- `校验最大深度`：可缺省（`空`→真）、非负安全整数；`是合法最大深度` 同语义但返回布尔而非抛错。

### §4 子代理错误（error.ts）
- 本模块复刻面唯一具体码为 `ACTIVATION_CLOSING`（来自 inbox 关闭拒绝）。
- 光明抛错无属性位，按本项目既定约定把码并进消息（`"消息 [码]"`），`是子代理错误` 按 `name == "SubagentError" && code ∈ 码集` 判定（消费方只依据 `code` 路由，见 §五）。

### §5 最终助手输出（assistant-output.ts）
- `归一助手输出`：遍历事件流，**末条非空 `assistant/message` 的 `content` 优先**；否则把 `assistant/message`/`assistant/attempt` 的 `stream` 片段累计拼接为单一 text 块；全空 → `空`。

### §6 激活期收件箱（inbox.ts）
- `造收件箱`：`{代理标识, 关闭中, 下轮, 下一步}`（均为列表字段）。
- `收件箱投递`：关闭中（`关闭中==真`）→ 抛 `ACTIVATION_CLOSING`；`steer` 进 `下一步`、`queue` 进 `下轮`。
- `收件箱关闭`：幂等（已关闭返回 `假`），同步置 `关闭中=真`。

> 本地辅助段一律「核」前缀（`核字段齐备`/`核只含键`/`核是整数标量`/`核是安全整数`/`核是JSON安全值`…），避免 src 后端内联同测模块时的 codegen 段重定义（与第14轮 T5C 纪律一致）。

---

## 三、验证结果

### 测试（117 断言，远高于铁律 7 的「≥10」）
```
cd lightharness && python 运行.py examples/test_子代理核心.light
===== 第 16 轮任务 1：subagent 子代理核心（上）=====
test_子代理核心 PASS
RC=0
```

### 反跑 3/3（`python _antirun_t1_子代理核心.py`）
```
✓ A 目录列举丢结果 (判红运行 rc=1)
✓ B 空收件箱误判积压 (判红运行 rc=1)
✓ C 深度最大值选择反向 (判红运行 rc=1)
✓ 字节级恢复校验 (sha256 37a9bfcc81bf)
✓ 恢复后回归绿 (rc=0，PASS 已打印)
ALL OK
```
- **A**：`目录条目表` 去掉遍历产出（直接 `返回 结果`）→ `1y`「条目表 与行一致」红。
- **B**：`收件箱积压` 末句恒 `返回 真`（覆盖 `长度(下一步)>0` 判定）→ `6f`「空箱无积压」红。
- **C**：`读委托深度` 的 `头 > 运` 改 `头 < 运`（最大值选择反向）→ `3b`/`3e` 红。
- 三判据均**真变异立红**；恢复走 `finally` 并做逐字节 sha256 校验（第13轮教训）。

### 缺陷复现
```
cd lightharness && python 运行.py examples/_repro_L131.light   → rc=0（L-131 复现通过）
```

---

## 四、语言缺陷登记

### L-131（新增）明亮除法 `x / 0` 抛 除零错误，而非产生 ±Infinity / NaN
- **证据**：`_repro_L131.light` 中 `1/0` 与 `1.0/0.0` 均抛 `除零错误`（float division by zero）。上游 deepseek-harness 为 TS/JS：`1/0 === Infinity`、`0/0 === NaN`，且可被 `Number.isFinite`/`Number.isNaN` 值语义判定。
- **触发面**：任何由 JS 数值逻辑移植、且除式可能以 0 为除数的代码——复刻时不能依赖 `Infinity`/`NaN` 作"无穷/非数"哨兵，必须在调用点 `尝试/捕获` 兜底；亦无法用值语义表达"非数"。
- **绕法**：复刻面涉及除法的逻辑须显式 `尝试/捕获 除零错误`；本模块无除法，未触发，但 `核是有限数` 保留为防御性兜底（因光明无法产出 `inf/nan`，该段实质为死代码，见 §五）。
- **复现**：`examples/_repro_L131.light`（rc=0）。

> 预分配 **L-132 未占用**：初探针误判"畸形段静默丢弃""缺 isFinite"两项，均经干净复现证伪（见页首纠偏），本路未再发现独立缺陷，按第15轮先例空缺顺延。

---

## 五、上游面剔除与偏差登记

| 上游面 | 处置 | 理由 |
|---|---|---|
| `subagent/subagent/src/index.ts`（Cordis Service 装配） | **剔除** | 宿主服务装配面；纯逻辑面已复刻 |
| `subagent/subagent/src/activation.ts` / `dispatch.ts` / `message-passing.ts` / `sandbox.ts` / `lifecycle.ts` | **剔除** | 运行时/宿主/沙箱/并发语义，不在任务1 6 文件清单 |
| `subagent-local/`（宿主 fs / 进程 / 注册） | **剔除** | 宿主面 |
| `descriptor.ts` 的 `isRemoteJsonValue` 环路检测 | **简化** | 光明无对象身份/环路检测；以递归深度上限（>128 返回假）近似，且因 L-131 无法产出 `inf/nan`，`核是有限数` 实为死代码（防御性保留） |
| `depth.ts` 的 `-0`（`-0` 与 `0` 在 JS 严格不等） | **偏差** | 光明整型 `-0` 与 `0` 不可区分（`type(-0.0)==float` 但值等 0），`核是安全整数` 与 `核是非负整数` 对 `-0` 按 `0` 处理，不单独区分 |
| `error.ts` 的 `SubagentError` 属性位 | **偏差** | 光明抛错无属性位，码并入消息（`"消息 [码]"`），判定退化为 `code ∈ 码集`（上游注释已许可消费方只依 `code` 路由） |
| `assistant-output.ts` 的 `MessageContent` 类型 | **简化** | 光明无联合类型；以字典 `type` 字段分支 |
| `inbox.ts` 的 `ActivationInbox` 并发安全 | **剔除** | 宿主并发语义；本模块只做单线程纯逻辑 |

---

## 六、待路M裁定 / 移交清单

1. **对标卡 #104**：本路新增，建议登记为「subagent 核心（catalog/descriptor/depth/error/assistant-output/inbox）纯逻辑面」，并注明任务1 仅覆盖任务书列出的 6 文件，其余 subagent 文件（activation/dispatch/message-passing/sandbox/lifecycle）归后续任务（任务书任务2 续传面另立卡 #105）。
2. **行为差异 R16-D1**：建议记录两条 ——（a）L-131 除法语义（x/0 抛错 vs JS Infinity/NaN）；（b）descriptor 环路检测以深度上限近似、`-0` 不可区分、错误码并入消息，三项为本研究简化/偏差，非上游行为。
3. **探针纠偏留存**：本路在 §页首与 §四明确登记了两处"初判缺陷→复现证伪"的结论，供缺陷账（语言缺陷账.md）参考，避免后续轮次重复误判。
4. **文档/上游版本差异**：任务书头部标注上游 `a305303422`，本地工作副本 HEAD 为 `9d9035b7c1`。本路以**目录布局与文件内容**为对齐依据（任务1 的 6 文件全部存在且语义吻合），未发现内容漂移；如路M有权威 pin，请以 pin 复核。
5. **未移植项**（供 #104 备注）：Cordis Service 装配、宿主 subagent-local、activation/dispatch/message-passing/sandbox/lifecycle、并发安全的 inbox、descriptor 真环路检测。
