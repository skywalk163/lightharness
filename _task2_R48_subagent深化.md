# 任务2（R48）：subagent 父属目录 + human inbox + chunked-list —— 交付报告

> 日期：2026-09-17 ｜ 轮次：第48轮 ｜ 优先级：P0 ｜ 对标号：#18
> 交付物：`src/子代理核心.light`（追加 §7-§9）、`src/子代理深化.light`（追加 §5-§6）、
> `examples/test_R48_subagent深化.light`、本报告
> 上游基线：deepseek-harness 0.1.5-rc.2（a305303422），上游源 `G:\github\deepseek-harness\packages\subagent\`

---

## 1. 做了什么

R34 的 §1-§4 是**原型设计**（directory.ts/inbox.ts/chunked-list.ts 三个文件在 0.1.5-rc.2 并不存在，
当时按设计灵感实现，v2 缺口因此保留）。本轮按上游**真实源码**逐段对齐三个纯逻辑面：

| 上游文件 | 上游锚点 | 复刻位置 | 内容 |
|---|---|---|---|
| `subagent/src/control-types.ts` | SubagentListEntry/SubagentCatalog/SubagentAddress/回执 | 子代理核心 §7 | child/diagnostic 行形状谓词、目录视图、回执、地址 |
| `subagent/src/control.ts` | validateControlRequest / catalogView / rejectPrompt / rejectCatalogRead / isCancellation | 子代理核心 §7+§9 | 载荷校验、live 活动替换、Remote 拒绝码映射 |
| `subagent/src/list-children.ts` | compareCorpusRecords / descendantCandidates / childRow / sameLifecycle / subagentParents | 子代理核心 §8 | created,id 稳定序、无递归前序遍历、同生命周期见证键、父代集合 |
| `subagent/src/index.ts` (prompt L415-448) | 人工提示准入序列 | 子代理核心 §9 | 校验→时区规范化→父可用→组装持久源 |
| `subagent/src/catalog.ts` | appendChunkedList/iterateChunkedList 承载投影 head | 子代理深化 §5 | 分块目录投影（分块列表接进 subagent） |
| `core/agent-loop/src/inbox.ts` | splice 规范化/claim/clear/locate/replace/remove | 子代理深化 §6 | 人工介入收件箱入队/出队 |

### 2.1 分块目录投影（子代理深化 §5，chunked-list 接进 subagent）

- #78 的 `src/分块列表.light`（不可变追加分块链表，块容量 64）以**只读导入**接入：
  `应用分块目录事件` 用 `追加分块` 承载 head（追加只复制最新块、旧块共享），
  `分块目录条目表` 用 `遍历分块` 保事件序展平；
- 对齐 catalog.ts 投影四件：init（只继承切点）/ apply（非 `subagent/catalog` 或
  `seq < inheritedEventCount` → 状态原样）/ wire.view（行构造）/ state 校验
  （继承数非负安全整数 + 分块校验 + 条目谓词）；
- 新增 `分块目录查找`（父属目录的「查找」面）与 `目录块计数`（跨块观测面）。
- #104 的 §1 平表承载 head **原样保留**（改掉会破坏既有 test_子代理核心 1w 断言；两套投影并存，
  分块版才是上游原样）。

### 2.2 人工介入收件箱（子代理深化 §6，human inbox 入队/出队）

对齐 agent-loop inbox.ts 的纯逻辑（剔除会话持久化/事件总线/分发器宿主面）：

- **两列待办箱**：下轮（queue：人工提示排队为独立新轮次）/ 下一步（steer：贴近当前步）；
- **规范化拼接（splice）**：负偏移自尾计（越界压 0）、正偏移截到列长、删除数截断到
  `[0, 列长-实起]`；实删为 0 且无插入 → 状态原样（载荷 空）；
- **跨列标识唯一不变式**：候选+另列存量合看，重复标识抛
  `message "X" is already pending [DUPLICATE_PENDING_MESSAGE]`（对齐上游 invalid inbox splice）；
- **持久拼接载荷**：`{target: next-turn|next-step, start, inserted}`，removedCount 为 0 省略，
  记取消且有移除时带 `outcome: "canceled"`（对齐 agent/inbox/spliced 事件数据）；
- **入队/出队**：`箱投递`（queue→下轮尾、steer→下一步尾、未知方式拒绝）、`箱前置`、
  `箱认领`（claim：取走全部下一步；目标=下轮时再取下轮队首一条）、`箱清空`（先下一步后下轮，
  顺序对齐上游 durable cancel）、`箱替换`/`箱移除`（在位才成功）、`箱定位`、`箱积压`。

### 2.3 控制面词汇与准入（子代理核心 §7+§9）

- **行形状**（control-types.ts）：child 行 `{kind, id, mode, label?, activity, hasChildren}`
  （continuable 必须有持久标签，缺失抛 `[INVALID_CHILD_ROW]`）；diagnostic 行
  `{kind, id, reason ∈ corrupt|unsupported|unavailable}`（未知缘由抛错）；`是控制行` 谓词；
- **目录视图**（catalogView 纯化）：durable 行活动状态由注入的 live 活动表替换（无记录默认
  inactive），诊断行透传，`parentAvailable` 只是投递期提示；
- **载荷校验**（validateControlRequest 纯化）：list 仅需非空父标识；prompt/interrupt 需父/子
  非空 + mode 必须 `continuable`；prompt 额外要求 delivery ∈ {queue, steer}；诊断串风格返回
  （空 = 合法）；
- **提示准入**（index.ts prompt 纯化）：校验（坏 → `gateway/bad-request`）→ clientTimeZone
  规范化（复用 #78 `时间工具.规范客户端时区`，坏 → `subagent/invalid-time-zone`）→
  父不在线（→ `subagent/parent-unavailable`）→ 组装持久源
  `{kind:"user", rpcId: requestId, clientTimeZone?}`（时区仅提供时携带）；
- **拒绝映射**（rejectPrompt/rejectCatalogRead/isCancellation 纯化）：
  CANCELLED→gateway/cancelled；MODEL_DOES_NOT_SUPPORT_IMAGES→subagent/attachment-invalid；
  NOT_RESUMABLE→not-resumable；UNAUTHORIZED→unauthorized；
  DRAINING/ACTIVATION_CLOSING/CONTINUATION_UNAVAILABLE/PERSISTENCE_UNAVAILABLE→
  delivery-unavailable；SUBAGENT_CONTROL_PROJECTIONS_UNAVAILABLE→projections-unavailable；
  其余→gateway/internal；
- `子代理全错误码表`（11 码）；§4 的 `子代理错误码表` 维持第16轮原状不动。

---

## 2. 验证结果

| 项 | 结果 |
|---|---|
| `python 运行.py examples/test_R48_subagent深化.light` | **rc=0，全断言通过** |
| 测试规模 | 约 90 组断言，5 大组（分块投影/收件箱/控制词汇/目录查找/准入映射） |
| 既有回归 | test_子代理核心 / test_子代理深化 / test_子代理续传 / test_子智能体×3 全 rc=0 |

关键断言组：
1. **分块投影**：65 条事件跨两块（块容量 64）、跨块展平保序、切点内忽略、超容块/坏条目/
   负继承数拒绝、按子标识查找；
2. **收件箱**：queue/steer 入队、负偏移自尾计、跨列重复标识抛错、认领（step 目标只取下一步 /
   next-turn 目标附加下轮队首一条）、清空顺序、outcome=canceled 载荷；
3. **目录查找**：6 节点嵌套语料（普通会话作途经节点）前序候选顺序 甲→丁→丙→戊、
   深度 1/1/2/3、同刻兄弟按标识决胜、见证键缺省位不同判异、父代集合去重；
4. **准入映射**：三方法好/坏载荷全分支、时区坏例拒绝、11 码全错误码表、
   提示准入四段序列全分支。

---

## 3. 铁律核对

- ✅ 只补纯逻辑，不接真实子会话拉起（无子进程/无会话落日志/无墙钟）；
- ✅ 既有 subagent 测试不破（子代理核心/深化/续传/子智能体 全 rc=0）；
- ✅ 只改 `src/子代理核心.light` + `src/子代理深化.light`，既有段零修改（只追加）；
- ✅ 全量 pytest 回归见路M收口记录（基线外零新增红）。

## 4. 已登记偏差

- **D-1**：上游 zod union 类型判别 → 光明显式谓词（是控制行），语义等价；
- **D-2**：catalogView 的 live Agent 注册表采样 → 活动表注入（宿主面剔除）；
- **D-3**：splice 的 `Number.isSafeInteger`/NaN 防御 → 光明入参为整数域，保留负偏移/截断两支；
- **D-4**：#104 §1 平表 head 与 §5 分块 head 并存（§5 为上游原样；§1 平表版不删避免破既有测试）。
