# 任务3 交付报告 —— api 网关协议域（stream-protocol / remote-error-codes / remote-events / types）

> 轮次：复刻 第16轮 ｜ 日期：2026-09-13 ｜ 对标卡：**#106（新增）** ｜ 差异编号 **R16-D3** ｜ 缺陷编号预分配 **L-135~L-136**
> 上游只读：`G:\github\deepseek-harness`（本地工作副本 HEAD `9d9035b7c1`；任务书标注 `a305303422`，差异见 §六）
> 本路可写文件（4 个，全部新增，零越界）：
> - `lightharness/src/网关协议.light`（427 行 / 59 段）
> - `lightharness/examples/test_网关协议.light`（176 行 / **73 断言**）
> - `lightharness/_antirun_t3_网关协议.py`
> - `lightharness/_task3_网关协议_交付报告.md`（本文件）
> 另：最小复现 `lightharness/examples/_repro_L135.light`（铁律 2 要求，缺陷 L-135）
>
> ⚠️ **分发文档偏差（重要，非语言缺陷，已据实处理）**：任务书测试要求与反跑判据 B 提到「流控制（序列号/确认/窗口）」「心跳帧」，但**上游 `stream-protocol.ts` 实际不存在**这些概念——全文件仅定义 `ready/emit/waterfall/cancel`（RemoteEvent 下行帧）与 `open/cancel/item/error/end`（RemoteStream 服务端消息），无任何 heartbeat/ping/pong/sequence/window/backpressure。已据实忠实复刻现有内容，并将反跑 B 判据落地为「**错误帧空 details 不丢字段**」。

---

## 一、上游对应表（文件 / 行号 / 核心语义）

| 上游 | 行 | 核心语义 | 本模块落点 |
|---|---|---|---|
| `api/gateway/src/stream-protocol.ts` | 6-18 | 协议常量：多路路径/事件流端点/结果端点/流负载/就绪帧 | §0 `远程流多路路径`/`远程事件流端点`/`远程事件结果端点`/`远程事件流负载`/`远程事件流就绪` |
| `api/gateway/src/stream-protocol.ts` | 211-238 | `isRemoteEventId`/`isRemoteEventClientId`/`isRemoteEventAgentId`（品牌串校验） | §1 `网是远程事件标识`/`网是远程JSON值`（含标识校验辅助 `网有效标识`/`网字符串属性`/`网精确键`/`网仅含键`/`网含于`/`网是布尔`/`网是数字`/`网是记录`） |
| `api/gateway/src/stream-protocol.ts` | 270-313 | `parseRemoteStreamClientMessage`/`parseRemoteStreamServerMessage`/`parseMessage`（含 `exactKeys` 验证器） | §1 `网解析远程流客户端消息`/`网解析远程流服务器消息`/`网解析消息`（验证器 `网校验客户端消息`/`网校验服务器消息`） |
| `api/gateway/src/stream-protocol.ts` | 243-268 | `RemoteStreamClientMessage`（open/cancel）/ `RemoteStreamServerMessage`（item/error/end）/ `RemoteStreamFailure` | §1 `是客户端开启消息`/`是客户端取消消息`/`是服务器项目帧`/`是服务器错误帧`/`是服务器结束帧` + 对称构造器 `造开启消息`/`造取消消息`/`造项目帧`/`造错误帧`/`造结束帧`/`序列化流消息` |
| `api/gateway/src/stream-protocol.ts` | 33-65 | `RemoteEventDownlinkFrame`（ready/emit/waterfall/cancel） | §1 `造就绪帧`/`造发射帧`/`造瀑布帧`/`造取消事件帧` + `是就绪帧`/`是发射帧`/`是瀑布帧`/`是取消事件帧` |
| `api/gateway/src/stream-protocol.ts` | 87-99,101-143,145-209 | `RemoteEventResult`/`parseRemoteEventResult`、`projectRemoteEventRequest`、`projectRemoteEventRejection`/`restoreRemoteEventRejection`、`isRemoteJsonValue` | §1 `网解析远程事件结果`/`网投影远程事件请求`/`网解析远程事件拒绝`/`网投影远程事件拒绝`/`网还原远程事件拒绝` |
| `api/gateway/src/remote-error-codes.ts` | 8-35 | `TypertGatewayFaultDetails { endpoint, field? }` + `RemoteErrorDetailsMap`（17 码） | §2 `网关错误码表`(17)/`是网关错误码`/`造网关错误详情`(field 可选)/`是网关错误详情` |
| `api/remotes/src/remote-events.ts` | 16-36 | `API_REMOTE_FORWARDED_EVENTS`（19 条 `{event, mode: emit|waterfall}`） | §3 `转发事件表`(19)/`是转发事件`/`查转发事件模式`/`是事件模式`/`是转发事件条目` |
| `api/remotes/src/types.ts` | 17-27 | `ApiRemoteForwardedEvent`（事件名投影）/ `TypertRemoteEventSelection`（选择位） | §4 `转发事件名表`/`是转发事件名`/`是事件选择` |

> 注：`remote-error-codes.ts`/`types.ts` 在上游仅为 `interface`/`type` 声明（纯类型层）；`makeGatewayErrorDetails`/`ApiRemoteForwardedEvent` 由 `@deepseek-ai/dsh-typert-protocol` 包代码生成，本 checkout 不含该包。本路按 interface 形状自建同语义构造/判别段（见 §五偏差）。

---

## 二、实现要点

### §0 协议常量
- 5 个常量：`/api/remote.mux`、`$events`、`$events/result`、`{args:{}}`、`{type:"ready"}`，与上游 `REMOTE_*` 常量逐一对齐。

### §1 流协议（stream-protocol.ts）
- **验证器对齐 JS 语义（关键，见 §四 L-135）**：上游 `exactKeys` + `value.type === 'x'` 依赖「undefined 短路」——缺失键返回 `undefined` 不抛。光明字典缺失键访问抛 `KeyError`，故 `网校验客户端消息`/`网校验服务器消息`/`是服务器项目帧`/`是服务器错误帧`/`是服务器结束帧` 全部改用 `字典获取(值, 键, 空)` 安全取值，空对象 `{}` 走到底抛 `"api gateway: invalid Remote stream server message"`。
- **深度守卫**：`网访JSON值`（递归 JSON 值判定）深度 > 128 拒循环，对齐既有 L-131（`-0`/`Inf` 不可产）。
- **对称构造器**（复刻增补）：上游用 TS 对象字面量构造帧，本路补 `造开启消息`/`造项目帧`/`造错误帧`/`造结束帧`/`造就绪帧`/`造发射帧`/`造瀑布帧`/`造取消事件帧` 供 round-trip 测试。
- **事件拒绝投影/还原**：`网投影远程事件拒绝` 缺 `name` 补 `"Error"`；`网还原远程事件拒绝` 因 Error 无属性位返回错误状字典（对齐第14轮 error 偏差）。
- **请求投影省略 signal**：`网投影远程事件请求` 按上游投影省略 `signal` 字段（小幅偏差，见 §五）。

### §2 远程错误码（remote-error-codes.ts）
- `网关错误码表` 17 项（gateway/ambiguous-endpoint … gateway/signature-invalid），与 `RemoteErrorDetailsMap` 一致。
- `造网关错误详情`：`field` 为可选参数（上游 `field?: string`），默认 `空`；仅当 `字段 != 空` 才写 `field` 键。

### §3 远程事件（remote-events.ts）
- `转发事件表` 19 条，每条 `{event, mode}`；`查转发事件模式` 查 `mode`（emit/waterfall）；`是转发事件条目` 校验 `mode ∈ {emit, waterfall}`。

### §4 远程类型（types.ts）
- `转发事件名表` = 事件名投影；`是转发事件名` 校验事件名在白名单；`是事件选择` 校验选择位字典。

> 本地辅助段一律带「网」前缀（上游 `parse*`/`is*`/`exactKeys` 概念），避免 src 后端内联同测模块时的 codegen 段重定义。

---

## 三、验证结果

### 测试（**73 断言**：64 `断言相等` + 9 `应抛错`，远超铁律 7 的「≥12」）
```
cd lightharness && python 运行.py examples/test_网关协议.light
===== 第 16 轮任务 3：api 网关协议 =====
test_网关协议 PASS
RC=0
```

### 反跑 3/3（`python _antirun_t3_网关协议.py`）
```
=== 第 16 轮任务 3 反跑判据（api 网关协议）===
✓ A 数据帧 value 字段改名 data (判红运行 rc=1)
✓ B 错误帧丢弃 details 字段 (判红运行 rc=1)
✓ C 网关错误码表首码改错 (判红运行 rc=1)
✓ 字节级恢复校验 (sha256 7f03413e9b31)
✓ 恢复后回归绿 (rc=0，PASS 已打印)
ALL OK
```
- **A**：`造项目帧` 的 `"value"` 字段改名为 `"data"` → `1a`「项目帧 round-trip 判别」红（`是服务器项目帧` 因精确键不匹配返回假）。
- **B**：`造错误帧` 构造时丢弃 `"details"` 键 → `1e`「错误帧 round-trip 判别」红（`是服务器错误帧` 因缺 `details` 精确键返回假）。
- **C**：`网关错误码表` 首码 `gateway/ambiguous-endpoint` 改错 → `2b`「命中错误码」红。
- 三判据均**真变异立红**；恢复走 `finally` 并做逐字节 sha256 校验。
- 注：分发文档 B 原文为「空负载心跳帧」，上游无心跳帧，已据实以「错误帧空 details 不丢字段」落地。

### 缺陷复现
```
cd lightharness && python 运行.py examples/_repro_L135.light   → rc=0（L-135 复现通过）
```
复现三方面：① 光明 `消息["type"]` 缺失键直接抛 `KeyError`（JS 返回 undefined）；② `字典获取(消息,"type",空)` 安全返回 空（对齐 undefined 短路）；③ 链式 `错帧["error"]["code"]` 缺子对象亦抛 `KeyError`，须嵌套 `字典获取` 绕。

---

## 四、语言缺陷登记

### L-135（新增）光明字典缺失键访问抛 KeyError，而 TS/JS 返回 undefined（可安全短路）
- **证据**：`_repro_L135.light` 中 `消息["type"]`（消息缺 `type` 键）抛 `KeyError: 'type'`；`错帧["error"]["code"]`（错帧缺 `error`）抛 `KeyError: 'error'`。上游 `stream-protocol.ts` 验证器大量依赖 `value.type === 'x' && exactKeys(...)` 的「undefined 短路」语义——缺失键不抛、后续 `&&` 自然短路。
- **触发面**：任何把 TS/JS「对象属性缺失返回 undefined」逻辑直译为「光明字典下标访问」的移植；帧/消息/事件校验器（exactKeys 模式）首当其冲。
- **绕法**：所有帧/消息/事件校验器改用 `字典获取(值, 键, 空)` 安全取值（缺失 → 空，等价 undefined 短路）；链式访问用 `字典获取(字典获取(值, "error", 空), "code", 空)`。本模块 §1 全部校验器已落地此绕法。
- **复现**：`examples/_repro_L135.light`（rc=0）。

> 预分配 **L-136 未占用**：本路在 §0–§4 仅发现 L-135 一处独立语言缺陷（其余：chr 缺失已归 L-133、JSON 排序语义归 L-116、循环深度归 L-131；`field` 可选属翻译对齐非缺陷），按第15轮先例空缺顺延。

---

## 五、上游面剔除与偏差登记

| 上游面 | 处置 | 理由 |
|---|---|---|
| `gateway/index.ts`(1204) / `stream-server.ts`(224) / `gateway/types.ts`(159) | **整体剔除** | cordis+node 宿主面，无纯逻辑可复刻 |
| `remotes/index.ts`(167) | **整体剔除** | cordis+node 宿主面 |
| `stream-protocol.ts` 的「心跳帧/流控制/序列号/窗口」 | **不存在（据实剔除）** | 上游全文件无此概念，任务书描述与实际不符 |
| `remote-error-codes.ts` 的 `makeGatewayErrorDetails`（由 protocol 包代码生成） | **偏差（自建同语义）** | 本 checkout 无 `@deepseek-ai/dsh-typert-protocol` 包；按 `TypertGatewayFaultDetails{endpoint,field?}` 自建构造器，`field` 可选默认 空 |
| `types.ts` 的 `ApiRemoteForwardedEvent`（类型投影） | **偏差（自建同语义）** | 类型层由包生成；本路按事件名列表自建 `转发事件名表`/`是转发事件名`/`是事件选择` |
| `projectRemoteEventRequest` 省略 `signal` 字段 | **偏差（小幅）** | 上游投影省略 signal；本路 `网投影远程事件请求` 同样省略，保留非 agent 字段 |
| `restoreRemoteEventRejection` 的 Error 无属性位 | **偏差（对齐既有）** | 第14轮 error 偏差：返回错误状字典而非实例 |
| 帧构造器（`造*` 系列） | **复刻增补** | 上游用 TS 对象字面量，本路补对称构造器供 round-trip |

---

## 六、待路M裁定 / 移交清单

1. **对标卡 #106**：本路新增，建议登记为「api 网关协议（stream-protocol/remote-error-codes/remote-events/types）纯逻辑面」，注明任务3 覆盖任务书列出的 4 文件；宿主面（index/stream-server/gateway-types/remotes-index）及不存在的心跳/流控概念整剔。
2. **行为差异 R16-D3**：建议记录两条 ——（a）L-135 字典缺失键 KeyError vs undefined 短路，§1 校验器全量改用 `字典获取(...,空)` 安全取值；（b）上游 `makeGatewayErrorDetails`/`ApiRemoteForwardedEvent` 由 protocol 包代码生成、本 checkout 不含量，按 interface 形状自建同语义段。
3. **缺陷账**：L-135 已登记并附 `_repro_L135.light`；L-136 空缺（本路无第二独立缺陷）。缺陷账（语言缺陷账.md）更新归路M。
4. **文档/上游版本差异**：任务书头部标注上游 `a305303422`，本地工作副本 HEAD 为 `9d9035b7c1`。本路以目录布局与文件内容为对齐依据（任务3 的 4 文件全部存在且语义吻合），未发现内容漂移；如路M有权威 pin，请以 pin 复核。
5. **未移植项**（供 #106 备注）：cordis+node 宿主面（gateway index/stream-server/gateway-types/remotes index）、protocol 包生成的类型/构造器。
6. **任务书偏差提醒**：任务书测试要求「流控制（序列号/确认/窗口/流控状态/乱序处理）」与反跑 B「空负载心跳帧」均指向不存在的上游概念；本路已据实复刻现有内容并调整 B 判据，建议路M在任务书层面订正该描述以免误导后续轮次。
