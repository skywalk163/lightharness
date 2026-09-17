# 任务2（R52·P1）交付报告 —— test-support/remote-mock 纯逻辑复刻

> 日期：2026-09-17 ｜ 状态：**完成**
> 交付物：`src/远程mock.light`（新建）、`examples/test_R52_远程mock.light`、本报告
> 上游基线：deepseek-harness 0.1.6-alpha.1（ea53423b60）
> `packages/test-support/remote-mock/src/{remote-mock.ts, streams.ts, log.ts}`
> 铁律遵守：`src/mock大模型服务器.light` 零改动；纯逻辑 mock，不接真实网络。

---

## 一、上游对照（只读）

remote-mock 是 Typert Remote 流量的端点命名拟真：`<namespace>/<method>` 键的一元应答表 +
流脚本表 + 活流控制 + 载具日志 + Connection 载具面。本轮对齐的纯逻辑面：

| 上游 | 内容 |
|---|---|
| `remote-mock.ts` | `RemoteTable`（unary/stream/streams 三段装载）、`ok()` 信封、`dispatch`（无规则 → miss+MissingUnaryRule，不记调用；函数规则同步抛 → failed 记录）、`open`（无脚本 → miss）、`modeOf`/`load`/`endpoints`/`assertNoUnmatched`/`noRuleMessage`、`OpenStreams`（push/end/fail 只作用 open 态并返回命中数）、`argsOf` 载荷解包（`{args: 数组}` / `{args: 对象}` / TypeError）、`RemoteMock.create`（`$events` ready 帧代数递增） |
| `streams.ts` | `StreamScript`/`frames`/`openStream` 构造器、`MockStream` 状态机（push 计数/等待者直达、end/fail 仅 open、pull 四分支含「stream has one consumer」、cancel 清队、drained 判定）、`toError` |
| `log.ts` | `MockLogStore`：calls/streams/requests/unmatched，全局 seq 从 0 起，requests 剔除 `$` 前缀端点并取首参 |

## 二、修改（src/远程mock.light 新建，约 430 行 46 段）

- **信封/脚本**：`造成功信封`、`造帧脚本`（推完即结束）、`造开放脚本`（推完保持开放）、
  `造规范错误`（toError）；
- **拟流（MockStream）**：`造拟流`/`拟流推入`/`拟流结束`/`拟流失败`/`拟流读取`/`拟流排空否`/
  `拟流取消`/`拟流跑脚本`/`拟流排队数`——同步步进状态机：读取返回
  `{态: 值/完/败/挂起}`，挂起时交付**信箱**（首格引用），后续推送/定局/取消直接填信箱；
- **日志**：`造拟真日志`/`日志记调用`/`日志记流`/`日志记未匹配`/`日志调用`/`日志流`/
  `日志请求`/`日志未匹配`（全局序号跨表递增，从 0 起）；
- **拟真（RemoteMock）**：`造远程拟真`/`拟真一元`/`拟真流声明`/`拟真装载`/`拟真模式`/
  `拟真派发`/`拟真开放`/`拟真端点表`（字典序插入）/`无规则消息`/`拟真参数解包`/
  `拟真断言无未匹配`/`活流筛选`/`活流逐个推入/结束/失败`/`造事件拟真`（$events ready 帧，
  `mock-client-<代>` 代数递增）；
- 函数规则经 `type(规则) == type(造规范错误)` 判别后直调（光明函数为一等值，
  先例：`工具.light` 的 `执行函数(参数)`）。

## 三、验证结果

| 项 | 结果 |
|---|---|
| `python 运行.py examples/test_R52_远程mock.light` | **rc=0，全断言通过** |
| 判据规模 | 7 大组约 80 组断言 |
| 既有回归 | test_mock大模型服务器 rc=0（铁律零改动侧证）；pytest 子集 846 passed / 3 failed = 基线存量，零新增红 |

判据覆盖要点：ok 信封；两脚本构造与执行语义；拟流推入计数/等待者信箱直达/四态读取/
单消费者抛错/取消清队/脚本抛错转失败；日志过滤与 `$events` 剔除与全局序号；
值规则 verbatim（含信封）/函数规则调用/无规则 miss 不记调用/规则抛错记 failed；
流声明保留语义与装载顺序；模式判定；活流控制命中计数与状态迁移；载荷解包三支；
断言无未匹配双态；$events ready 帧与代数递增。

## 四、已登记偏差

- **D-1**：`Promise`/`AsyncIterable`/`AbortSignal` → 同步步进状态机 + 信箱引用（挂起的
  读取由后续推送/定局填信箱）；上游「派发后异步结算」压缩为「同步派发即结算」，
  `pending` 中间态保留在日志条目形状中；
- **D-2**：vitest spy（unaryMocks/streamMocks 调用计数与 mockReset）→ 剔除，日志即观测面；
- **D-3**：`remote-proxy`（按生成命名空间自动代理）→ 剔除（纯语法糖），端点显式注册；
- **D-4**：`endpoints()` 上游为字典序 sorted；光明用稳定插入 + 字典序插入等价实现；
- **D-5**：上游规则函数同步抛经 `answerOf` 转 rejected promise 再结算为 failed；
  光明同步版在派发方捕获并记 failed 后上抛，单路径结算语义一致。
