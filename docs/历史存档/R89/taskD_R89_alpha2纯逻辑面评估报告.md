# R89-D 交付报告：alpha.2 纯逻辑面评估（session turnWindow + 两项复核）

> 执行时间：2026-09-24 01:0x–01:3x ｜ 仓：`G:/github/deepseek-harness`（上游阅读）+ `lightharness`（移植）
> 结论：turnWindow → **(b) 半移植**（纯算法已落地 + 回归用例进门禁）；两项复核 → **维持不移植**。

---

## 1. 待评估项 1：session history turnWindow 分页（上游 #18 = `50ba2c8bb2`）

### 1.1 上游 diff 实读（`git show 50ba2c8bb2 --stat`）

18 文件 / +219 −58。按面拆开：

| 面 | 文件 | 性质 |
|---|---|---|
| **纯算法** | `packages/api/session-controller/src/history.ts` → `paginate()` | ✅ 纯函数：事件数组 + 计数循环 |
| 协议字段 | `src/types.ts` → `SessionPageRequest.turnWindow{minMessages,minTurns}`、`SessionFollowRequest extends Pick<...>` | ⛔ host/client 双端契约 |
| 校验（抛错） | `src/history.ts` → `validateHistoryWindow()` 抛 `RemoteError('gateway/bad-request', ...)` | ⛔ 宿主传输错误面 |
| 接线 | `src/client/sessions/session.ts`、`src/client/transport.ts`、`src/client/contract/session.ts` | ⛔ host/client 传输 |
| 文档 / e2e / catalog | `docs/*`、`apps/web/tests/seeded-history.e2e.ts`、`extensions/tool-cordis/src/api-catalog.ts` | 附带 |

**核心算法（逐行读过，唯一逻辑改动就是这个循环）**：

```ts
for (let index = end - 1; index >= 0; index--) {
  const event = events[index]
  if (turnWindow !== undefined && event.type === 'turn/start') {
    turns++
    if (count >= turnWindow.minMessages && turns >= turnWindow.minTurns) { cut = index; break }
  }
  if (!MESSAGE_TYPES.has(event.type) || !isAppendSurfaceEvent(event)) continue
  count++
  let groupStart = event.seq
  if (sources !== undefined) for (const s of sources) if (s < groupStart) groupStart = s
  if (count >= maxMessages) { cut = groupStart; break }
}
return { events: events.slice(cut, end), hasMore: cut > 0 }
```

其中 `MESSAGE_TYPES = new Set(['user/message','assistant/message'])`（history.ts:39）、
`isAppendSurfaceEvent = isSurfaceEvent(e) && e.surfaceOp === 'append'`（`packages/core/session/src/surface.ts`）。

**判定**：这个循环是**纯算法**（输入事件数组 + 三个数值参数，输出切片 + 布尔），
不读网络、不碰 host/client 传输、不依赖 RemoteError。而 `turnWindow` 字段声明、
`validateHistoryWindow` 的 RemoteError 抛掷、以及 client 侧传参接线**确属 host/client 双端耦合**。

### 1.2 lightharness 现状核查（⚠️ 与 R88-A 记录有出入，已校准）

- R88-A 记「`会话冷读.light` 有历史分页但未实现 turnWindow 协议参数」。
- 实际通读 `lightharness/src/会话冷读.light`（105 行）：**它没有任何分页**——
  只有 `打开只读句柄 / 句柄读取 / 关闭句柄 / 冷读会话日志` 四段，语义是「只读句柄读全量
  连续日志 + 中断轮闭合器合成平衡转写」，对齐的是上游 `cold-read.ts` 的 `readColdSessionLog`，
  与 `paginate` 是两套东西。
- 全仓 grep：`段落.*分页` 只命中 mcp客户端 / toolcordis / 代理团队 / 团队工具（都是别领域），
  **会话历史分页在 lightharness 里根本不存在**。
- 有利面：lightharness 的事件词汇里**已有 `turn/start`**（`代理循环.light:37 事件类型表`；
  `代理.light:388 己.发出代理事件("turn/start", ...)`），turn 边界计数有现成的事件语义可对齐。

### 1.3 结论：**(b) 半移植**

| | 内容 |
|---|---|
| ✅ 移植 | `paginate` 的完整循环语义：turn 计数 / 消息计数 / `sourceEventSeqs` 组起点回退 / `beforeSeq` 截断 / `hasMore` |
| ✅ 移植 | `validateHistoryWindow` 的数值校验（改为**返回原因串**，不抛 RemoteError） |
| ⛔ 不移植 | `SessionPageRequest.turnWindow` / `SessionFollowRequest` 协议字段、`RemoteError('gateway/bad-request')`、transport/session client 接线 |
| 📌 再评估触发条件 | lightharness 若落地「宿主会话历史分页服务」（host/client 双端 + 传输层），再评估把协议字段与 RemoteError 校验接进本模块（届时纯函数可直接复用） |

**选 (b) 而非 (a)/(c) 的理由**：
- 不是 (a)：协议字段与 RemoteError 校验确实是 host/client 双端耦合，硬搬等于把宿主传输面塞进光明侧，
  违反本轮红线「不搬 host/client 双端网络协议」。
- 不是 (c)：算法本身是纯的、与上游逐行等价、且 lightharness 已有 `turn/start` 事件语义，
  移植成本极低（一个 100 行模块 + 一个用例），放着不移植没有理由。

### 1.4 落地物（均已实测）

| 文件 | 说明 |
|---|---|
| `lightharness/src/会话历史分页.light`（新增） | `历史分页()` / `校验历史窗口()` / `是消息类型()` / `是追加界面事件()` / `计入消息()` / `历史消息类型表`；文件头逐条写明「移植了什么 / 不移植什么」 |
| `lightharness/examples/test_R89_D_turnWindow分页.light`（新增） | 8 组断言，每组带反跑点 |

回归用例覆盖（改反即红）：
1. 无 turnWindow → 退化为按 `maxMessages` 数消息（切点 = 第 N 条消息自身序号）；
2. **有 turnWindow → 页面起点必须落在 `turn/start` 序号上**（三轮布局 minMessages=4/minTurns=2 → 切=6，
   绝不从一轮中间切开）；
3. 「且」关系：minTurns=3 → 继续往上翻到最早一轮（切=0）；
4. 历史耗尽（两个最小值都凑不够）→ 切=0、还有更多=假、返回全量；
5. `maxMessages` 触发时按 `sourceEventSeqs` 最小来源序号回退（groupStart）；
6. `beforeSeq` 截断；
7. `校验历史窗口`：minMessages>maxMessages / ≤0 / minTurns≤0 / 缺字段 → 各返回不合法原因；
8. 消息类型表 = `user/message` + `assistant/message`。

实测结果：
```
$ python 运行.py examples/test_R89_D_turnWindow分页.light
test_R89_D_turnWindow分页: 全部断言通过        RC=0

$ python -m pytest tests/test_回归.py -q -k R89_D -o addopts=
1 passed, 523 deselected in 7.95s               RC=0
```
（用例进 `tests/test_回归.py`，即自动纳入 LH 三平台门禁；纯逻辑无平台依赖。）

---

## 2. 待复核项 2：tool-jobs wake（#49 / #59 / #78）—— **维持不移植**

| commit | 实际标题（实读） | 结论 |
|---|---|---|
| `#78 b6775f6d4f` | `fix(tool-jobs): wake an idle owner for every completion by default` | ✅ 与记录一致 |
| `#49 d257fa4af7` | `fix(agent-team): limit the reminder to the lead identity` | ⚠️ **与 wake 无关**（是 agent-team 提醒收敛到 lead 身份） |
| `#59 2d651b8359` | —— | ⚠️ **在本 fork 仓不可解析**（`fatal: ambiguous argument`） |

#78 的核心改动（实读 `index.ts` diff）：
```diff
-  maxConsecutiveWakes: z.number().min(1).default(3),
+  maxConsecutiveWakes: z.number().min(1),
-  const wakeBudget = config.maxConsecutiveWakes ?? 3
+  const wakeBudget = config.maxConsecutiveWakes
```
即「wake 预算默认 3 → 无界，上限改为 opt-in」。该预算服务于 `ctx.jobs` 插件在
**idle owner 上开 turn** 的宿主编排（wakeup delivery / next-step inbox）。
lightharness 未实现 tool-jobs 链路（无后台作业 + 唤醒编排）→ **维持不移植**，结论与 R88-A 一致。
#49（agent-team 身份提醒）同样属宿主编排面 → 维持不移植。

---

## 3. 待复核项 3：subprocess spill containment（#110 `cfa84ed4e3`）—— **维持不移植**

实读：`packages/subprocess/subprocess-local/src/output.ts` +126 行，新增
`SpillOptions.onFailure: SpillFailureReporter`；spill 文件 `open`/`write` 失败时
`catch → spill.onFailure(error, this.label)` 降级为内存 tail，**上报一次且不 kill host**
（注释：*"reports once through SpillOptions.onFailure, and never interrupts"*）。

这是 **Node `fs` 层的错误处理宿主面**（文件描述符 / 临时目录 / 进程存亡），
lightharness 侧的 `src/溢出.light` + `src/溢出保留.light`（R88 新增）是**纯逻辑的溢出保留**，
不涉及真实文件打开失败与宿主进程存亡 → **维持不移植**，结论与 R88-A 一致。

---

## 4. 判据自查

| 判据 | 结果 |
|---|---|
| turnWindow 三选一明确结论 | ✅ **(b) 半移植**，理由见 §1.3 |
| 移植项本机 pytest 门禁全绿 | ✅ `test_回归.py -k R89_D` 1 passed；`运行.py` RC=0 |
| 不移植项理由成立 | ✅ 两项均为宿主编排 / Node fs 错误面，已实读 diff 取证 |
| 红线：不搬 host/client 协议、不硬搬 HTTP | ✅ 未引入任何网络/传输面，校验改为返回原因串 |
| 未 commit/push | ✅ 只写文件 |

---

## 5. 遗留 / 登记

- **协议面登记**：`SessionPageRequest.turnWindow` 字段 + `RemoteError('gateway/bad-request')` 校验
  + client 接线 —— 记为「不移植」，触发条件见 §1.3。
- **R88-A 记录校准**（两点，建议同步修正 `_taskA_R88_alpha2差量清单.md`）：
  1. `会话冷读.light` 没有历史分页（对齐的是 `cold-read.ts` 的全量冷读，不是 `paginate`）；
  2. #49 不是 tool-jobs wake（是 agent-team lead 提醒），#59 在本 fork 仓无法解析。
- **未做**：把 turnWindow 接进任何宿主分页服务（无宿主面可接）；上游 e2e
  （`session-history-journal.host.spec.ts` 8 组 `it.each`）未逐条对拍——光明侧用等价的
  8 组断言覆盖，但语义对拍是「逐行读 diff 后重写」，非自动翻译。
