# 第43轮 任务1 交付报告 —— 真实LLM往返（客户端.light 真POST + SSE解析 → 本机 mock服务端）

> 日期：2026-09-16 ｜ 优先级 P0 ｜ 修改区域：examples（零修改 客户端.light / mock大模型服务器.light）

## 1. 根因 / 背景

第43轮把「大脑」接真：此前 agent 循环用大模型**回放**（纯逻辑测试支撑），本轮换成
`客户端.light`（真实 HTTP POST /chat/completions + SSE 解析 + wire 映射）真打本机
`mock大模型服务器.light`（真实 HTTP 服务端，内核分配端口）。任务1 即验证这条
**真实 LLM 往返**：客户端真 POST → SSE 流解析成 chunk 列表 → wire 完成原因/用量映射正确。

### 1.1 复刻中暴露的两个真实链路坑（均已解决/登记）

**坑A（隐蔽死锁，已绕行）**：`客户端.light.对话响应` 走 `HTTPPost`（urllib，**阻塞**），
而 mock 服务端跑在光明异步事件循环（处理循环）。同进程内若主协程直接调阻塞客户端会
**冻死事件循环 → 服务端收不到 accept → 连接无响应 → 死锁**。
**处置**：把阻塞客户端丢进 OS 线程（光明 `线程` 模块），主协程轮询 `异步睡眠` 让出事件循环
喂服务端——正是 `客户端.light` 自身 `对话响应协程` 的既定模式（阻塞 HTTP 丢线程 + 轮询让步）。
`mock大模型服务器.light` 的 `处理循环` 作为主循环任务常驻，非阻塞客户端线程请求到来时被驱动。

**坑B（mock 服务端 HTTP 集成既有缺陷，登记 L-162）**：`mock大模型服务器.light` 的
`mock处理器` 把 `分派` 的**列表响应** `[状态, 头, 体]` 直接返回，而
`HTTP服务端.处理连接` 用 `响应["状态"]`（**字典**）访问 → `KeyError` → 连接无响应即关、
服务端 `错误数 +1`、客户端收到「Remote end closed / timed out」。
这是 mock 服务端 HTTP 集成的预存 bug（行为逻辑 `分派` 是对的，仅响应形状与
`HTTP服务端` 契约不匹配）。**零修改铁律禁止改源码**，故本测试**自写 handler**：
- 完整复用 `分派` 的全部行为逻辑（FIFO 消费 / 脚本化响应 / SSE 帧 / 路由鉴权守卫 /
  请求记录）—— 零修改 `mock大模型服务器.light`；
- 仅把 `分派` 的 `[状态, 头, 体]` 列表转成 `HTTP服务端` 期望的 `{"状态","头","体"}`
  字典响应形状（边界转换放在测试装配层，不进源码）。

> 效果：任务1 仍是对 `mock大模型服务器.light` 行为逻辑（含真实 HTTP 服务端传输）的
> 端到端真验，只是绕开了其 handler 响应形状缺陷；缺陷本身登记 L-162 待源码修复。

## 2. 交付物

| 文件 | 说明 |
|---|---|
| `examples/test_R43_真实LLM往返.light` | 真实LLM往返验收，rc=0 |
| `lightharness/_task1_R43_真实LLM往返.md` | 本报告 |

## 3. 设计要点

- **真实传输**：`启动Mock服务` 不复用（其硬编码坏 handler），改为
  `新建Mock服务(选项)`（持有行为逻辑）+ `新建 HTTP服务端(我的处理器, 5.0)` +
  `创建任务(处理循环(服务端))`，端口内核分配（`服务端.端口()`）。
- **客户端**：`客户端(端点, "test-key", "deepseek-flash")` 真 POST
  `http://127.0.0.1:<port>/v1/chat/completions`，`对话响应(消息, 选项, 工具)` 经 urllib
  真实往返（线程内）+ SSE 解析 + wire 映射。
- **SSE / wire 断言**：用 `流.块组装器` 把 chunk 列表重装，校验文本/推理/工具调用增量、
  完成原因（stop / tool-calls / max-tokens / 空响应 EMPTY_RESPONSE）、usage 桶
  （输入=3，输出=23）。
- **确定性**：mock 脚本 `["success","tool_call_success","reasoning_success","max_tokens","empty"]`
  每轮消费一项；断言 `请求记录` 长=5 证明逐次真实打到服务端。
- **超时兜底**：HTTP 超时 5.0s，线程轮询有界，不会无限挂起。

## 4. 验证结果（本机 Windows 实跑）

```
python 运行.py examples/test_R43_真实LLM往返.light   →   EXIT_CODE=0
```
逐轮断言全绿：
- 轮1 success → 文本块 "mock response recovered" + finish stop + usage(输入3/输出23)
- 轮2 tool_call_success → tool-call 块 name=mock_tool arguments={"value":"mock"} + finish tool-calls
- 轮3 reasoning_success → reasoning 块 "mock reasoning" + text 块 + finish stop
- 轮4 max_tokens → finish max-tokens（wire length → max-tokens）
- 轮5 empty → finish error / EMPTY_RESPONSE
- 请求记录消费满 5 次（真实往返逐次命中）

## 5. 待办/风险提示

- **L-162（本轮新缺陷）**：`mock大模型服务器.light` 的 `mock处理器` 返回列表响应而
  `HTTP服务端` 期望字典响应，导致经真实 HTTP 起 mock 服务端时连接无响应。建议源码侧把
  `mock处理器` 的返回从 `[状态,头,体]` 改为 `{"状态","头","体"}`（或 `分派` 直接返回字典）。
  本轮因零修改铁律在测试层绕行，未动源码。
- 任务2（真实 agent 循环）复用本任务的「服务端任务 + 客户端线程」并发模型与 L-162 绕行 handler。
- 0.82 FreeBSD 复测归任务3。
