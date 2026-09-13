# 任务2 交付报告 —— 子代理续传域（subagent 续传 下：continuation-messages/control-types/run-settlement/model-selection/model-selection-state）

> 轮次：复刻 第16轮 ｜ 日期：2026-09-13 ｜ 对标卡：**#105（新增）** ｜ 差异编号 **R16-D2** ｜ 缺陷编号预分配 **L-133~L-134**
> 上游只读：`G:\github\deepseek-harness`（本地 HEAD `9d9035b7c1`；任务书标注 `a305303422`，差异见 §六）
> 本路可写文件（4 个，全部新增，零越界）：
> - `lightharness/src/子代理续传.light`（370 行 / 39 段）
> - `lightharness/examples/test_子代理续传.light`（176 行 / **83 断言**）
> - `lightharness/_antirun_t2_子代理续传.py`
> - `lightharness/_task2_子代理续传_交付报告.md`（本文件）
> 另：最小复现 `lightharness/examples/_repro_L133.light`（铁律 2 要求，缺陷 L-133）
>
> ⚠️ **翻译纠偏（重要，非语言缺陷）**：本路在 `请求代理选项` 初版把「基线」初始化为 `设 基数 为 空`（None），当 `已配置==空` 且请求携带 `provider/model` 时调用 `字典设置(基数=None,…)` 触发 `TypeError: 'NoneType' object does not support item assignment`。上游语义为 `base = configured ?? {}`，正确初始值应为**空字典** `{}`。已改为 `设 基数 为 {}` 并复测通过。这是**本路翻译笔误**，已在运行前修复，**不登记为新语言缺陷**；仅作诚实留痕。

---

## 一、上游对应表（文件 / 行号 / 核心语义）

| 上游 | 行 | 核心语义 | 本模块落点 |
|---|---|---|---|
| `subagent/subagent/src/continuation-messages.ts` | 155 | 相邻 Agent 消息来源/构造、可续回父指引（`send_message` steered）、结算单行摘要、结算通知组装 | §1 `代理消息来源`/`造代理消息`/`带可续回执指引`/`结算摘要`/`造结算消息` |
| `subagent/subagent/src/control-types.ts` | 149 | `diagnostic`/`child`/`directory`/`address`/`promptRequest` 形状校验、`CHILD_DIAGNOSTIC_REASONS`（3）、`SubagentErrorCode` 码集（7） | §2 `子代理诊断原因表`/`是子代理诊断项`/`是子代理子项`/`是子代理列表项`/`是子代理目录`/`是子代理地址`/`是子代理提示请求`/`子代理错误码表`/`是子代理错误码` |
| `subagent/subagent/src/run-settlement.ts` | 76 | `finalText`/`failureDetail`/`runOutcome`（completed→{status,output}；aborted 无 diagnostic→killed；其余→failed） | §3 `末段文本`/`失败详情`/`运行结局` |
| `subagent/tool-subagent/src/model-selection.ts` | 197 | `allowModelRoute`/`modelRouteKey`/`assertAllowedModelRoutes`/`hasDelegatedModelRequest`/`assertNonEmpty`/`requestAgentOptions`/`assertAllowedModelSelection`/`hasConfiguredModelSelection` | §4 `允许模型路线`/`模型路由键`/`断言允许模型路线`/`有委托模型请求`/`续断言非空`/`请求代理选项`/`断言允许模型选择`/`有配置模型选择` |
| `subagent/tool-subagent/src/model-selection-state.ts` | 82 | `MODEL_SELECTION_POLICY_KEY`/`VERSION=1`/`applyModelSelectionPolicy`/`readModelSelectionPolicy`/`recordModelSelectionPolicy`（幂等首条落库） | §5 `模型选择策略键`/`模型选择策略版本`/`投影模型选择策略`/`读模型选择策略`/`记录模型选择策略` |
| `subagent/subagent/src/internal.ts` | 111 | 全量宿主面（Symbol/Object.defineProperty/Promise） | §五 **整体剔除**（见 §五） |

> 任务2 上游列上述 5 个纯逻辑文件（任务书明确）；`internal.ts` 为宿主面（Symbol/Promise/defineProperty），无纯逻辑可复刻，整文件剔除。

---

## 二、实现要点

### §1 相邻代理消息 / 可续回执指引 / 结算（continuation-messages.ts）
- `造代理消息`：内容前加 `"Agent <id> sent a message: "`，保留原块并附 `source`。
- `带可续回执指引`：父标识经 `序列化JSON` 嵌入回执文案（绕 L-133，见 §四）；指引块 = 原提示块追加回父 text。
- `结算摘要`：5 个已知 `stopReason` 分支 + 默认分支（`ended abnormally (<reason>)`）。
- `造结算消息`：`summary` 去重；`output` 缺省给占位文案 `"It left no closing message."`。

### §2 控制类型校验（control-types.ts）
- `子代理诊断原因表` 3 值：`corrupt`/`unsupported`/`unavailable`；`是子代理诊断项` 严格白名单校验 `reason`（反跑 B 立红点）。
- `是子代理子项`：`activity ∈ {running, inactive}`；`mode=one-shot` 直通，`mode=continuable` 须 `label` 非空串。
- `子代理错误码表` 7 值（unauthorized/attachment-invalid/delivery-unavailable/projections-unavailable/parent-unavailable/not-resumable/invalid-time-zone）。

### §3 单次运行结局（run-settlement.ts）
- `运行结局`：`completed`→`{status, output: 末段文本(output)}`；`aborted` 无 `diagnostic`→`{status: killed}`、有 `diagnostic`→`{status: failed, detail}`；`error/max-tokens/refusal` 及默认→`{status: failed, detail}`。

### §4 模型路由选择（model-selection.ts）
- `模型路由键`：上游用 `provider\0model`，明亮缺 chr（L-133）无法生成 NUL，改用 `序列化JSON([provider, model])` 作无碰撞唯一键。
- `断言允许模型路线`：数组校验 + 每项 provider/model 非空串 + 重复键检测。
- `请求代理选项`：**关键修正**——基线 `基数` 初始化为 `{}`（非 `空`）；`已配置` 非空时按 `路由变` 决定「去 `reasoning_effort`」或「整本拷贝」；再叠加请求的 provider/model/reasoning_effort。

### §5 模型选择策略投影（model-selection-state.ts）
- `投影模型选择策略`：仅首条 `subagent/model-selection-policy` 事件落库；路线表经 `断言允许模型路线` 校验且非空，否则抛错。
- `读模型选择策略`/`记录模型选择策略`：投影态直回传 / 幂等首条落库。

> 本地辅助段一律带「续」前缀（`续新列表`/`续拷贝列表`/`续字段齐备`/`续只含键`/`续含于`/`续拷贝字典`/`续去字段`/`续是布尔`/`续取可选`），避免 src 后端内联同测模块时的 codegen 段重定义。

---

## 三、验证结果

### 测试（**83 断言**：74 `断言相等` + 9 `应抛错`，远高于铁律 7 的「≥10」）
```
cd lightharness && python 运行.py examples/test_子代理续传.light
===== 第 16 轮任务 2：subagent 子代理续传（下）=====
test_子代理续传 PASS
RC=0
```

### 反跑 3/3（`python _antirun_t2_子代理续传.py`）
```
✓ A 结算摘要 completed 分支错 (判红运行 rc=1)
✓ B 诊断项原因白名单放宽 (判红运行 rc=1)
✓ C 模型路由键改分隔符拼接 (判红运行 rc=1)
✓ 字节级恢复校验 (sha256 a5300b7f093a)
✓ 恢复后回归绿 (rc=0，PASS 已打印)
ALL OK
```
- **A**：`结算摘要` 的 `completed` 文案改错 → `1h`「摘要 completed」红。
- **B**：`是子代理诊断项` 改 `返回 真`（接受任意 reason）→ `2c`「非法原因拒绝」红。
- **C**：`模型路由键` 改 `provider + "|" + model` 拼接（绕回 L-133 之前的分隔符思路）→ `4a`「模型路由键 唯一编码」红。
- 三判据均**真变异立红**；恢复走 `finally` 并做逐字节 sha256 校验。

### 缺陷复现
```
cd lightharness && python 运行.py examples/_repro_L133.light   → rc=0（L-133 复现通过）
```

---

## 四、语言缺陷登记

### L-133（新增）明亮缺「码→字符(chr)」内置，仅有「字符→码(ord)」方向的 `字符转ASCII`
- **证据**：`_repro_L133.light` 中 `字符转ASCII("A") == 65`（ord 可用）；`码转字符(65)` / `ASCII转字符(65)` 均抛 `NameError: name '...' is not defined`（chr 不可用）。上游 `modelRouteKey` 用 `provider + "\0" + model`（NUL 分隔符）作稳定身份键，明亮既无 chr 内置、也无 `\0` 字符串转义，无法生成 NUL。
- **触发面**：任何需要按"字符码"反查字符、或生成含控制字符分隔符的拼接逻辑；移植 TS/JS 含 `\0`/`\x00` 分隔符的键编码时须改用 JSON 数组编码等无碰撞替代。
- **绕法**：`模型路由键` 改用 `序列化JSON([provider, model])` 作唯一键（保留插入序、无碰撞）；本模块已落地。
- **复现**：`examples/_repro_L133.light`（rc=0）。

> 预分配 **L-134 未占用**：本路在 §1–§5 仅发现一处翻译笔误（见页首纠偏，已修，非语言缺陷），未再发现第二个独立语言缺陷（多行 `+` 续写、chr 缺失均已在 L-119/L-120/L-133 既有红线内处理），按第15轮先例空缺顺延。

---

## 五、上游面剔除与偏差登记

| 上游面 | 处置 | 理由 |
|---|---|---|
| `subagent/subagent/src/internal.ts` 全量（Symbol/defineProperty/Promise） | **整体剔除** | 宿主运行时面，无纯逻辑可复刻 |
| `model-selection.ts` 的 `provider\0model` 分隔符 | **偏差（绕法）** | 明亮缺 chr（L-133）且 `\0` 无法字面生成；改 `序列化JSON([provider,model])` 编码 |
| `requestAgentOptions` 的 `base = configured ?? {}` | **偏差（已修正）** | 初译误用 `空`(None) 作基线触发崩溃；改正为 `{}` 对齐上游 `?? {}` |
| `control-types.ts` 的 `MessageContent`/`ChildActivity` 联合类型 | **简化** | 明亮无联合类型；以字典 `type`/`kind`/`activity` 字段分支 |
| `run-settlement.ts` 的 `stopReason` 穷举 | **对齐** | 5 已知 + 默认分支，与上游一致 |
| `model-selection-state.ts` 的 `recordModelSelectionPolicy` 幂等 | **对齐** | 已设置则不重复（上游语义） |

---

## 六、待路M裁定 / 移交清单

1. **对标卡 #105**：本路新增，建议登记为「subagent 续传（continuation-messages/control-types/run-settlement/model-selection/model-selection-state）纯逻辑面」，注明任务2 覆盖任务书列出的 5 文件，`internal.ts` 整文件剔除。
2. **行为差异 R16-D2**：建议记录两条 ——（a）L-133 缺 chr 内置、`模型RouteKey` 绕用 JSON 编码；（b）`requestAgentOptions` 基线 `?? {}` 对齐（已修正为 `{}`）。
3. **缺陷账**：L-133 已登记并附 `_repro_L133.light`；L-134 空缺（本路无第二独立缺陷）；翻译笔误已修不单列。缺陷账（语言缺陷账.md）更新归路M。
4. **文档/上游版本差异**：任务书头部标注上游 `a305303422`，本地工作副本 HEAD 为 `9d9035b7c1`。本路以目录布局与文件内容为对齐依据（任务2 的 5 文件全部存在且语义吻合），未发现内容漂移；如路M有权威 pin，请以 pin 复核。
5. **未移植项**（供 #105 备注）：`internal.ts` 宿主运行时面（Symbol/Promise/defineProperty）。
