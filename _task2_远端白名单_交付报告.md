# 任务2（remotes 转发白名单）｜交付报告

> 第7轮「宿主逼近」· 任务2 · 2026-09-11
> 仓库：`G:\dswork\duan-light-merge\lightharness`
> 上游：`G:\github\deepseek-harness` @ `a305303422`（0.1.5-rc.2）

## 一、上游对应表

| 上游（0.1.5-rc.2） | 光明实现 | 说明 |
|---|---|---|
| `packages/api/remotes/src/remote-events.ts` L1-29 `API_REMOTE_FORWARDED_EVENTS`（19 条 `{event, mode}`，mode ∈ emit\|waterfall） | `src/远端总线.light` `取转发白名单` 返回的 19 条单层字典（事件名→模式） | 逐条对齐 event/mode；字典键带引号（L-063） |
| 同名常量作为 Host 转发循环与 `ctx.remote.$on` 的唯一定义源（"single home"） | `转发白名单`（模块级常量，= `取转发白名单()` 结果） | 名单即合法键集，命中判定与模式查询同读一份声明 |
| `emit`=广播式转发 / `waterfall`=请求-响应瀑布 | `转发模式` 返回 "emit"/"waterfall"/空；`名单转义模式` 返回是否 waterfall | waterfall 供上层投影选择（顶层 Agent 身份 + JSON 请求字段投影） |

## 二、实现要点

1. **新增 19 条白名单**：`取转发白名单` 返回单层字典 `{事件名: 模式}`，19 条全部按上游 `API_REMOTE_FORWARDED_EVENTS` 逐条对齐（2 条 waterfall：`approval/request`、`user-questions/request`；其余 17 条 emit）。
2. **三个判定段**（均在「转发」区中部，避开文件末尾边界，规避 L-079 生成器错位 else 触发面）：
   - `事件可否转发(事件名)` → 真/假（= `字典包含键(转发白名单, 事件名)`）
   - `转发模式(事件名)` → "emit"/"waterfall"/空（未命中返回 空）
   - `名单转义模式(事件名)` → 是否 waterfall（= `转发模式(事件名) == "waterfall"`）
3. **未触碰既有段落**：旧 `整理直达清单`（11 项）/ `判定可转发` 原样保留（既有 `test_远端总线` 测试 1 断言「11 项」强依赖，零改动保证不回退）。0.1.5 的 19 条白名单作为新增独立体系并存，旧 11 项清单维持历史语义（原版精简白名单）。
4. **语言约束绕法（重要）**：
   - 光明**模块级 `设 X 为 [多行字典]` 字面量解析失败**（编译期报「意外的标记 ]」），故改用 `段落 取转发白名单 接收:` 返回多行字典 + 模块级 `设 转发白名单 为 取转发白名单()`（函数返回上下文的多行字典可正确解析，已验证）。
   - 光明字面量（字典/列表）**不支持尾随逗号**，尾部条目后加 `,` 会触发同一解析错误；末尾条目的逗号必须省略。
   - 该语言约束建议登记为 **L-080**（模块级多行字典字面量解析失败 + 尾逗号不支持）。按本路文件互斥表，缺陷账由**路M 统一回填**，此处先记录绕法。

## 三、测试与 CI

- **新增** `examples/test_远端白名单.light`（rc=0）：
  - 测试 1：白名单长度 == 19
  - 测试 2：19 条全量断言（遍历期望表，每条 事件名→模式，逐条列出）
  - 测试 3：命中/未命中（`approval/request`→真且 waterfall；`llm/adapters-updated`→真且 emit；`user-questions/request`→waterfall；`nonsense/event`→假且 空）
- **回归**：`examples/test_远端总线.light`（既有）仍绿 —— 旧「转发」区（11 项清单）零改动。
- 全量 CI 由路M 统一跑（预期 216 passed / 0 failed）。

## 四、反跑判据（`_antirun_remotes_whitelist.py`，4/4 成立）

| 项 | 操作 | 期望 | 结果 |
|---|---|---|---|
| 基线 | 原始源码 | 测试绿 | ✅ |
| A | 删除白名单 `approval/request` 一条 | 该条断言红 | ✅ |
| B | `approval/request` 模式 waterfall→emit | 该条断言红 | ✅ |
| 恢复 | 还原字节级备份 | 测试绿 | ✅ |

脚本对 `src/远端总线.light` 做字节级备份/恢复，A/B 改反后断言测试必红、恢复后必绿，finally 保证源码无残留（已确认无 `.bak`）。

## 五、未移植项

- 上游 `remote-events.ts` 末尾 `satisfies readonly TypertForwardableEventEntry[]` 是 **TypeScript 类型投影**（type-only，从白名单派生类型），光明无类型系统 → **无需移植**。
- `ctx.remote.$on` 消费端键面读取、Host 转发循环的真实网络 IO → 属 **gateway 总线宿主面**，按本轮背景「OS/协议宿主维持登记」，不在纯逻辑移植范围。
- 既有的旧 11 项清单（`整理直达清单`/`判定可转发`）保留为历史语义，未合并进 19 条体系（避免破坏既有测试断言）。

## 六、移交清单

- 改动文件：`src/远端总线.light`（仅「转发」区新增，未碰 agent-lookup/gateway/客户端 等段落）
- 新增：`examples/test_远端白名单.light`、`_antirun_remotes_whitelist.py`、本报告
- 既有测试 `test_远端总线` 已确认不回退（绿）
- 缺陷账 L-080（模块级多行字典字面量 + 尾逗号约束）移交**路M 统一回填**，本路不在 `语言缺陷账.md` 落笔（文件互斥表规定只读）
- 对标清单 #55 回填语：「api/remotes → 转发白名单 19 条已覆盖（远端总线.light）；gateway 总线宿主面维持登记」（由路M 统一回填）
