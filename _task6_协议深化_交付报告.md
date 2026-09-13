# 任务6 交付报告 —— 协议深化域（ACP MCP/模型控制/更新 + Hooks 分离/事件/运行器/类型）

> 轮次：复刻 第15轮 ｜ 日期：2026-09-13 ｜ 对标卡：**#103（新增）** ｜ 差异编号 **R15-D6** ｜ 缺陷编号预分配 **L-130**
> 上游只读：`G:\github\deepseek-harness`（本地 HEAD `9d9035b7c1`；任务书标注 `a305303422`，差异见 §六）
> 本路可写文件（4 个，全部新增，零越界）：
> - `lightharness/src/协议深化.light`（593 行 / 52 段）
> - `lightharness/examples/test_协议深化.light`（408 行 / 12 段 / **159 断言** = 138 `断言相等` + 21 `检查抛含`）
> - `lightharness/_antirun_t6_协议深化.py`
> - `lightharness/_task6_协议深化_交付报告.md`（本文件）
> 本路无新语言缺陷（L-130 编号空缺，顺延给后续路）。

---

## 一、上游对应表（文件 / 行 / 核心语义）

上游合计 **900 行**，纯逻辑面全部移植；宿主面（I/O、异步尾链、取消令牌）按铁律剔除并登记 §五。

| 上游 | 行 | 核心语义 | 本模块落点 |
|---|---|---|---|
| `acp/acp/src/mcp.ts` | 143 | `normalizeServerName`：NFKD（`String.normalize("NFKD")`）→ 前缀化 → k 截断 + `sha256` 8-hex 后缀；`entriesToRecord(Header[])→Record`；`assertHttpUrl`（http/https 判据）；`isValidAbsolutePath`（`node:path.isAbsolute`：`/`、`\` 前缀，**Windows 盘符 `C:\` 为真**，行 6 直引 `node:path`）；`mountAcpMcpServers`（宿主装载面） | §1 `归一服务器名`/`折叠服务器名`/`条目成记录`/`解析服务器申报`/`断言HTTP网址`/`校验HTTP网址`/`绝对路径判定`/`解析MCP配置` |
| `acp/acp/src/model-control.ts` | 237 | `AcpModelControl` 类状态机：`selection`/`turn`/`snapshot`（暂停）/`select(server,?)`/`model`（`selectModel`）/`reasoning_effort`；快照 = `{selection, turn, choice}`；`setModel` 复位快照 | §2 `造控制状态`/`快照选择`/`钉住轮次`/`放开轮次`/`当前选择`/`模型选择值`/`组装选项`/`设定配置值` |
| `acp/acp/src/updates.ts` | 111 | `committedUpdate`/`updateBatch`/`updateConfirmation` 形状；`update({sessionUpdate, toolCallId, assistantBlock})`；`assistantBlockToAcp`（block→acp，未知类型→空）；空块批次仍产出换行 join | §3 `解析工具入参`/`调用更新`/`结果更新`/`占用更新`/`助手更新批次`（复用 `src/acp内容.light` 的 `assistantBlockToAcp`） |
| `hooks/hook-protocol/src/detached.ts` | 62 | `createDetachedRunner`：`{run, settle, inFlight, settleAll}`；`run` 在飞计数 +1，`settle` -1；`settleAll` 并行为空 | §4 `造分离跟踪器`/`登记运行`/`结算运行`/`在飞数量`/`结算全部`/`排空运行` |
| `hooks/hook-protocol/src/events.ts` | 104 | 钩子事件形状：`HookEvent1`（引用）/`HookEvent2`（结果）{nonce, pid, source, stdin, stdout, stderr, exitCode, dial, runTTLMs, emitTTLMs, seq}；`stderrSummary` 截断（默认 2000） | §5 `默认标准错误摘要上限`/`摘要标准错误`/`构造引用事件`/`构造结果事件` |
| `hooks/hook-protocol/src/runner.ts` | 106 | `DEFAULT_HOOK_TIMEOUT_MS = 600_000`；`runHook`：spawn → stdin 写入 → 汇聚 stdout/stderr → exitCode（`code ?? 0` → **空→空语义**）；`tail` Promise 尾链（异步串行化） | §6 `默认钩子超时毫秒`/`构输入流`/`运行钩子` |
| `hooks/hook-protocol/src/types.ts` | 137 | `CommandHook`/`HookDialect`/`HookRunResult`/`HookEventSource`/`matcher`/`group` 等形状判据与默认值构造 | §7 `判方言`/`构造指令钩`/`判指令钩`/`构造匹配组`/`判匹配组`/`判产出形`/`判选择形` |
| `acp/acp/src/index.ts`、`types.ts` | — | 注册表/挂载/类型汇出 | **宿主面**，`src/协议深化.light` 不承接（见 §五） |

### 键映射约定（贯穿 §1–§7）

- **外层协议载荷用英文键**（忠实上游 JSON 形状）：MCP `transport/serverName/command/args/env/cwd/failOnStartupError/url/headers`；事件 `turn/point/dialect/handlerId/matcher/decision/exitCode/stderrSummary/durationMs`；更新 `sessionUpdate/messageId/toolCallId/title/kind/status/rawInput/content/used/size`；助手块 `type/text` 或 `type/image/data/mimeType`。
- **仅对接宿主既有 `解析钩子产出`（`src/钩子协议.light`）时用中文键**（`退出码/标准输出/标准错误` + 可选 `裁定/缘由/续行标志/停止缘由/系统消息/钩子时机名`），隔离边界只此一处。
- **块表内键用英文**（`block["type"]`/`block["text"]`，忠实上游 `assistantBlockToAcp` 入参形状）。

---

## 二、实现要点

### §1 MCP 面（`mcp.ts`，差异 R15-D6-a）
- `折叠服务器名`：先 NFKD 归一（内置近似：删除组合变音符），超长（>20）则 `20 字符串 + "_" + SHA256 hex 前 8 位`，否则原样返回；**折叠后长度恒 29**（20+1+8）而非 32——测试断言即此值。
- `绝对路径判定`：新版显式支持 **Windows 盘符**语义（长度≥3、首字符为字母、次位为 `:` 即真），对齐 `node:path.isAbsolute` 在 Windows 的行为；`C:\x` → 真、`x:/y` → 真、空串 → 假。
- `解析MCP配置`：`传输` 键驱动分支——`"stdio"` → 命令/参数/环境/工作目录/失败启动容错；`"http"` → 网址 + 可选头表；两分支都产出**同一稳定键集合**，便于判据 A 变异注入。头部解析统一交给 `校验HTTP网址` + `断言HTTP网址`（http/https 前缀，异常走 `抛出`）。
- `mountAcpMcpServers`（真实 spawn/连接生命周期）**不移植**，登录 §五-a；模块保留其纯构造部分为 `解析MCP配置` 供测试驱动。

### §2 模型控制面（`model-control.ts`）
- 无类实例 → **字典状态 + 段落函数**：`造控制状态` 产 `{选择: 空, 轮次: 0, 快照: 空}`；`快照选择` 在**暂停时刻**固化 `{快照: {选择, 轮次, 选择形}}` 并把 `轮次` 清零的语义复刻为：快照记录当前选择与轮次，`放开轮次` 后恢复快照选择并沿用其轮次。
- `组装选项`：`{value, label?}` 形状；`设定配置值`：`选择`/`模型`/`推理开销` 三键白名单赋值，未知键抛错；`模型选择值` 规范化 `{serverName: 空 或 文本}`。
- `造控制状态` 暴露原始 `选择`（可为空），供 `当前选择` 惰性求值（空选择 → `模型选择值` 的空服务器名形态，不抛错，对应上游 `select` 的宽容语义）。

### §3 更新面（`updates.ts`，判据 B 命中点）
- `助手更新批次`：**空块表必须返回 `[]`**（判据 B 变异点：提前 `返回 空` 即红）；非空时逐块 `assistantBlockToAcp`（未知类型块 → 跳过），`用量` 若存在则按 `列表追加` 尾插 `{标题, 状态, 用量}` 项，最终 `序列化JSON` 输出。
- `调用更新`/`结果更新`/`占用更新`：三类更新的键形状（`sessionUpdate/messageId/toolCallId/title/kind/status/...`）经 `更新批次` 序列化 round-trip 后逐键不丢（判据 B 的往返断言）。
- `解析工具入参`：`rawInput` 支持 `JSON 文本`（`解析JSON`）与 `已解析值` 双入口，解析失败 → 抛错。

### §4 分离面（`detached.ts`）
- `造分离跟踪器` 产 `{在飞: 0, 运行: 登记运行, 结算: 结算运行, 结算全部: 结算全部, 排空: 排空运行}`；`登记运行` 在飞 +1 并返回入参原样；`结算运行` 在飞 ≥1 时 -1（越界减抛错），且在飞归零时若挂起排空等待则放行；`结算全部` 无条件清零并放行；`排空运行` 在飞为 0 时立即返回真。

### §5 事件面（`events.ts`）
- `默认标准错误摘要上限` = 2000；`摘要标准错误`：空 → 空串（判据 D 副产物），否则逐段拼接 + `…（省略 N 字符）` 后缀，超限截断；**空摘要不落键**（`构造结果事件` 只在非空时写 `stderrSummary`，测试用 `字典包含键==假` 断言而非读到空串）。
- `构造引用事件`/`构造结果事件`：按上游 `HookEvent` 形状组键，未提供时可选键**不写**；`decision` 传透；`durationMs` 由 `滴答时钟` 取样差计算（测试用递增 2 的假时钟 → 断言 `时长毫秒==2`）。

### §6 运行器面（`runner.ts`，判据 C 命中点）
- `默认钩子超时毫秒` = 600000；`构输入流`：输入文本按行切分（空输入 → 空列表）。
- `运行钩子`：**成功分支 `设 退出码 为 执行结果["退出码"]`（空 → 空，而不是 `?? 0`）**——这是判据 C 的变异点，改成 `设 退出码 为 0` 测试立即立红；`执行结果` 无 `退出码` 键时保持空；`标准输出/标准错误` 透传；超时不支（宿主面）。
- `tail` Promise 尾链（`runHook` 内异步串行化队列）**不移植**，登录 §五-b。

### §7 类型面（`types.ts`）
- `判方言`/`判指令钩`/`判匹配组`/`判产出形`/`判选择形`：逐字段形状判据（必填键集合 + 可选键放行 + 类型抽查），全部返回严格布尔；`构造指令钩`/`构造匹配组` 提供默认值构造后走同一判据（构造即通过）。`判产出形` 要求 `退出码/标准输出/标准错误` 三键**存在**（`判产出形({})==假` 已用测试锁定）。

---

## 三、测试验证

- 文件：`lightharness/examples/test_协议深化.light`（408 行 / 12 段）
- 运行：`cd lightharness && python 运行.py examples/test_协议深化.light`
- 结果：**`test_协议深化 PASS`，rc=0**
- 断言统计：**159 个**（`断言相等` ×138 + `检查抛含` ×21），远超任务书 ≥14 要求；覆盖三态：
  - **正常**：MCP stdio/http 双配置 round-trip、折叠服务器名（40 个 a → 长 29）、模型全生命周期（选择→暂停→恢复→改选）、更新批次往返、分离跟踪器增减、事件构造、运行钩子退出码 5、指令钩/匹配组/产出形/选择形判真；
  - **边界**：空服务器申报表、空助手块批次 → `[]`、空标准错误 → 不落键、空退出码 → 空、绝对路径盘符分支、`x:/y`、`C:\x`；
  - **异常**：`检查抛含` 覆盖 带空列表的命令 抛、未知类型块 抛、越界结算 抛、坏 JSON 工具入参 抛、`判产出形({})`、数学域名外取值 抛、`断言HTTP网址` 非 http(s) 抛 等 21 处。
- 模块导入链：`从 钩子协议 导入 解析钩子产出`、`从 acp内容 导入 assistantBlockToAcp` + 10 条内置/标准库导入；导出末尾 `导出 判方言 构造指令钩 判指令钩 构造匹配组 判匹配组 判产出形 判选择形`（空格分隔、无句号）。

---

## 四、反跑结果（判据 A/B/C，ALL OK）

文件：`lightharness/_antirun_t6_协议深化.py`（参照 `_antirun_t5_预设深化.py` 结构与 `BASE = dirname(abspath(__file__))`）

| 判据 | 变异点（红） | 恢复判据 | 结果 |
|---|---|---|---|
| A：正常输出 | `解析MCP配置` 现 `"传输": "stdio"` → 变异为 `"STDIO"`（键值不匹配 → 配置判据红） | 字节级恢复（sha256 一致）+ 回归 `test_协议深化 PASS` rc=0 | ✅ |
| B：边界 | `助手更新批次` 空块表分支改为提前 `返回 空`（丢 `[]` 形状 → 空批次序列化断言红） | 同上 | ✅ |
| C：变异立红（真实语义） | `运行钩子` 成功分支 `设 退出码 为 执行结果["退出码"]` → `设 退出码 为 0`（破坏空→空语义 → 成功退出码 5 与空退出码两处用例同时红） | 同上 | ✅ |

- 全量输出：`A 判红运行 rc=1` / `B 判红运行 rc=1` / `C 判红运行 rc=1`，恢复后 `sha256 a3b96954f210... 一致`，回归 `test_协议深化 PASS`（rc=0）。
- **反跑结论：3/3 ALL OK**。

---

## 五、未移植项（宿主面剔除，登记 R15-D6）

| 编号 | 上游 | 内容 | 处置 |
|---|---|---|---|
| R15-D6-a | `mcp.ts mountAcpMcpServers` / `assertHttpUrl` 的运行时连接 | 真实 spawn ACP 子进程 / HTTP 探测、进程生命周期 | 宿主面接线，本模块保留 `解析MCP配置`/`校验HTTP网址`/`断言HTTP网址` 纯函数；待模型服务域接线时复用 |
| R15-D6-b | `runner.ts runHook` 的 `tail` Promise 尾链 | spawn 后 async 尾任务的**异步串行化队列**（防并发尾竞态） | 宿主面（需 `运行.js`/Node 进程面），本模块以 `构输入流`+同步 `运行钩子` 承载纯逻辑；行为差异登记 |
| R15-D6-c | `runner.ts` AbortController 取消令牌 | 超时/手动取消通道 | 宿主面，本模块 `默认钩子超时毫秒` 常量保留，取消语义待接线 |
| R15-D6-d | 工具注册表接入点 / `approval:*` 词汇注册 | ACP 服务器注册进宿主工具域 | 非本模块职责，登记待办 |
| R15-D6-e | 凭据事件 `/ credential` 事件流 | 会话面事件流 | 宿主面，登记待办 |

> 对照任务书 §五（行为差异登记义务）：本路差异集中为「宿主面 I/O 与异步面不落 `src/协议深化.light`」，与任务书剔除铁律一致，标 **R15-D6**；不属语言层差异，故不占用缺陷编号。

---

## 六、语言差异（光明 ↔ TS）

本路**无新语言缺陷**（预分配编号 **L-130 空缺，顺延给后续路**）；复刻全程命中并沿用既有避坑表：

| 缺陷 | 现象 | 本路绕法 |
|---|---|---|
| L-037 | `断言` 降级 no-op | 一律 `断言相等`/`检查抛含` |
| L-051 | 字符串字面量仅单行 | 长文本拆多段拼接/`\u000a` |
| L-084 | 段落名禁含「为」 | 段落名全部取「….化/….判/….造…」形态，无「为」字 |
| L-086 | 禁花括号量词 | 无正则量词依赖 |
| L-088 | `捕获 as` 不可用 | `尝试/捕获 错误:` + 布尔标志 |
| L-089 | 手写 JSON 不可靠 | 一律 `序列化JSON`/`解析JSON` |
| L-090 | 字符串裸名与 import 共存错乱 | 原语常量名避开 import 符号集 |
| L-119 / L-120 | 标识符别名/关键字序列切分 | 段落名走「非别名 + 不可切分」白名单（`判产出形`、`排空运行` 等） |
| L-125 | 内建 `四舍五入` 银行家舍入 | 本路无舍入路径（折叠长度整数推导），规避 |
| L-129 | `0 == 假` / 类型混淆 | 判型一律 `是布尔值`/`是字符串` 类型判别，不用 `==` 兜真值 |

另沿 R15（前轮）已登记：L-091（`HMAC_SHA256` 非标准）、L-127（字典键须标量）——本路未触碰，不重复登记。

---

## 七、移交清单

| 文件 | 行数 | 说明 |
|---|---|---|
| `src/协议深化.light` | 593 / 52 段 | ACP MCP + 模型控制 + 更新 + Hooks 分离/事件/运行器/类型 纯逻辑域（CRLF 无 BOM） |
| `examples/test_协议深化.light` | 408 / 12 段 / 159 断言 | 三态全覆盖，`python 运行.py` 直跑 rc=0 |
| `_antirun_t6_协议深化.py` | — | 判据 A/B/C 变异注入→判红→字节级恢复→回归绿，ALL OK |
| `_task6_协议深化_交付报告.md` | 本文件 | 溯源/键映射/差异/反跑 |

- 铁律核对：4 个可写文件全部新增，`src/` 既有模块（`网络钩子GitHub.light`/`钩子协议.light`/`acp内容.light` 等）、`stdlib/`、`scripts/`、`运行.py`、`tests/`、`docs/功能对标/`、README、第三方 `examples/*` 均零触碰。
- 溯源：上游 7 文件（900 行）→ 本模块 §1–§7 一一对应，见 §一。