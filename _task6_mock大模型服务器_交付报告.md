# 任务6 交付报告：可脚本化 OpenAI 兼容 mock LLM 服务器（测试支撑域）

- 日期：2026-09-12
- 轮次：第 11 轮
- 本路范围：测试支撑域，复刻 `llm-mock-server` 的纯逻辑（行为队列 / SSE / 随机权重 / 请求消费 / 生命周期）

---

## 一、上游依据（文件 : 函数）

上游只读仓库：`G:\github\deepseek-harness\packages\test-support\llm-mock-server\src\`

| 上游符号 | 文件 : 函数/常量 | 本模块对应 |
|---|---|---|
| 预置行为表 | `index.ts` 内 `MOCK_LLM_BEHAVIORS`（24 项） | `设 全部项 为 [...]`（24 项，含 `random` 占位） |
| 默认随机权重 | `index.ts` `DEFAULT_MOCK_LLM_RANDOM_WEIGHTS` | `设 默认随机权重 为 [...]`（13 键，数值对齐） |
| 最大定时延迟 | `index.ts` `MAX_MOCK_LLM_TIMER_DELAY_MS=2147483647` | `设 最大定时延迟毫秒 为 2147483647` |
| 带种子随机 | `index.ts` `seededRandom`（mulberry32） | `类 播种随机`（确定性整数 LCG，见「刻意差异」） |
| 加权随机 | `index.ts` `chooseRandomBehavior` | `段落 选随机项` |
| 文本切块 | `index.ts` `splitText` | `段落 切分文本` |
| SSE 帧 | `index.ts` `openSse`/`writeSse`/`writeDone` | `段落 对象帧`/`原文帧`/`完成帧体` |
| 终止块 | `index.ts` `terminalChunk` | `段落 终端块` |
| 错误 JSON | `index.ts` `httpError` | `段落 错误JSON` |
| 行为→响应 | `index.ts` `runBehavior` | `段落 Mock大模型服务器.造脚本响应` |
| 脚本队列消费 | `index.ts` `selectBehavior` | `段落 Mock大模型服务器.消费脚本` |
| 请求处理次序 | `index.ts` `handle` | `段落 Mock大模型服务器.分派`（方法→路径→鉴权→体 JSON→消费→执行） |
| 服务器入口 | `index.ts` `startMockLlmServer` | `段落 新建Mock服务`（纯逻辑）+ `段落 启动Mock服务`（复用 HTTP服务端 bind） |
| CLI 参数 | `cli.ts` `parseMockLlmCliArgs` | 未移植（见「未移植项」） |
| 进程包装 | `bin.ts` | 未移植（见「未移植项」） |

## 二、实现要点

1. **纯逻辑核心 + HTTP 层复用**：`Mock大模型服务器.分派(请求)` 走与 `stdlib/HTTP服务端.light` 完全一致的请求/响应字典契约——入参 `["方法","路径","头","体"]`，出参 `[状态, 头字典, 体]`。测试直接 `新建Mock服务(选项).分派(请求)`，零 socket、零时序抖动；`启动Mock服务(选项, 超时值)` 才 `新建 HTTP服务端(mock处理器, 超时值)` 真 bind 内核端口。**未复制任何 HTTP/socket/分帧实现。**
2. **行为队列 FIFO**：构造时记录 `序列` 与 `末支`（序列末项）；`消费脚本` 用 `光标` 自增取 `序列[光标]`，**越界判定** `索引 < 长(序列)`：越界且 `重复末位=真`→复用 `末支`；越界且 `重复末位=假`→`脚本耗尽`（分派回 500 `MOCK_SCRIPT_EXHAUSTED`）。
3. **24 种行为覆盖**：固定回复 `success`；流式分片（按码点切块→终止块→[DONE]）；错误族 `rate_limit`(429+`Retry-After: ceil(毫秒/1000)`) / `server_error`(500) / `service_unavailable`(503) / `auth_error`(401) / `invalid_request`(400) / `context_overflow`(400 invalid_request_error) / `quota_exceeded`(429)；语义空回复族 `empty`(终止块+DONE) / `empty_body`(200 空体) / `stream_eof`(单条 role 帧无 DONE)；畸形流 `malformed_json`(原文帧 `{not-json`) / `malformed_event`(`choices:[null]`) / `wrong_content_type`(JSON 头但流体)；传输退化族 `connection_reset`/`stream_disconnect`/`stall`/`partial_eof`/`partial_disconnect`；`reasoning_success`(先 reasoning_content 分片再 success 流)；`tool_call_success`(两半工具参数分片 + finish_reason:tool_calls)；`max_tokens`(finish_reason:length)；`slow_success`(同 success 线形状)。
4. **SSE 帧**：`对象帧` 输出 `data: {json}\n\n`，`完成帧体` 输出 `data: [DONE]\n\n`；`空` 序列化→`null`、布尔→`true/false`（stdlib/JSON 契约）。
5. **确定性随机**：上游 mulberry32 用 `>>>`/异或/`Math.imul`，光明无位运算原语；改用整数 LCG（`状态=(状态*1664525+1013904223)%4294967296`，返回 `状态/4294967296`）。契约只要求「种子可注入、同种子同序列、异种子异序列、按权重比例」，不复刻上游浮点流。
6. **守卫次序**：非 POST→405（`Allow: POST`）；路径不以 `/chat/completions` 结尾→404；配置了 `API密钥` 才校验 `Authorization: Bearer <key>`（错/缺→401）；体非 JSON→400。**以上前置拒绝都不消费脚本**（`请求记录` 不增长）。

## 三、测试与 CI

- 新增 `examples/test_mock大模型服务器.light`：**49 条断言**（≥12），覆盖：
  1. 行为队列 FIFO 消费顺序（状态 + `请求记录[行为]`）
  2. 流式 SSE 帧形状（`data:` 开头 / 含 DONE / 以 DONE 结尾 / 首片文本 / 帧数=3 片+终止+DONE / 数帧一致）
  3. 7 种错误状态码 + `rate_limit` 的 `Retry-After` 向上取整
  4. 语义空回复族 `empty`/`empty_body`/`stream_eof`（终止块 / 空体 / 无 DONE / 块数）
  5. 随机权重种子确定性（同种子同序列 / 异种子异序列 / 四次都消费 / 只在权重行为内）
  6. 耗尽 500 与循环末位复用
  7. 守卫 401(无/错令牌)/405(非POST)/404(路径错)/坏 JSON 400 且不消耗脚本
  8. `reasoning_success` 含 reasoning_content、`tool_call_success` 含 tool_calls 与 mock-call-1
  9. `启动Mock服务` 真实内核端口 > 0
- 运行：`$env:LIGHT_MERGE=...; python 运行.py examples/test_mock大模型服务器.light` → **rc=0**。
- 既有回归（直接跑 .light 等效验证）：`examples/test_客户端.light` **rc=0**、`examples/test_总入口.light` **rc=0**。
- 未跑全量 CI（按铁律，全量由路M 统一跑）。

## 四、反跑判据（`_antirun_mockllm.py`，字节级备份/恢复 src）

| 判据 | 注入（锚点） | 期望 | 实测 |
|---|---|---|---|
| A | FIFO→LIFO：`设 选中 为 己.序列[索引]` 改为 `己.序列[长(己.序列)-1-索引]` | 注入→红；恢复→绿 | 注入 rc=1，恢复 rc=0 ✅ |
| B | 去 `[DONE]`：`完成帧体` 返回 `"data: [DONE]\n\n"` 改为 `""` | 注入→红；恢复→绿 | 注入 rc=1，恢复 rc=0 ✅ |
| C | 忽略种子：`己.状态 为 种子 % 4294967296` 改为 `己.状态 为 0` | 注入→红（同/异种子序列趋同）；恢复→绿 | 注入 rc=1，恢复 rc=0 ✅ |

脚本用 `open(SRC,"rb").read()` 字节级备份，注入后跑测试断言 `rc!=0`，再 `open(SRC,"wb")` 写回原字节并断言 `rc==0`，`finally` 兜底恢复并清理 `.antirun.bak`。运行 `python _antirun_mockllm.py` → **rc=0**。

## 五、未移植项 / 刻意差异

1. **连接级字节拆链行为退化**：`HTTP服务端` 契约是「一次请求→一条完整响应字典」，不支持响应中途 RST/半关/挂起。故 `connection_reset`/`stream_disconnect`/`partial_disconnect`/`stall` 退化为线上可观察形状（SSE content-type + 空体或部分体、无 [DONE]），不断言真实拆链时序。
2. **mulberry32→整数 LCG**：光明无 `>>>`/异或/`Math.imul` 位运算，改用确定性 LCG（见实现要点 5）。
3. **`slow_success`/`chunkDelayMs` 块间延时不模拟**：计时维度，本层不实现，线形状同 `success`。
4. **`cli.ts`/`bin.ts` 未移植**：`connection_refused`、`--listen-delay`、进程级包装属 CLI 生命周期，非 `index.ts` 的行为逻辑；本层以 `启动Mock服务(选项, 超时值)` 直接复用 `HTTP服务端` 完成 bind。
5. **`malformed_event` 退化为 `choices:[null]`**：对齐上游线上形状。

## 六、语言坑登记（已落账）

- **L-084**（`docs/功能对标/语言缺陷账.md`）：赋值关键字 `为` 恒为独立 KEYWORD，切碎尾部中文标识符（`行为`→`行`+`为`）。最小复现 `examples/_repro_L084.light`（按预期报「意外的标记」）。本模块绕法：裸标识符一律避 `为` 字（`全部项`/`末支`/`消费脚本`/`造脚本响应`/`选随机项`/`命中`），字符串键 `"行为"` 保留。
- 复用既有绕法/原语：多行集合字面量（L-002）、`字符串(bytes,"utf-8")`、`dict.获取(k,缺省)`、`%` 取模、`//` 整除。

## 七、移交清单（绝对路径）

| 交付物 | 绝对路径 |
|---|---|
| 源模块 | `G:\dswork\duan-light-merge\lightharness\src\mock大模型服务器.light` |
| 测试（49 断言） | `G:\dswork\duan-light-merge\lightharness\examples\test_mock大模型服务器.light` |
| 反跑脚本 | `G:\dswork\duan-light-merge\lightharness\_antirun_mockllm.py` |
| 本报告 | `G:\dswork\duan-light-merge\lightharness\_task6_mock大模型服务器_交付报告.md` |
| L-084 复现 | `G:\dswork\duan-light-merge\lightharness\examples\_repro_L084.light` |

**对外契约**（供下游测试/传输层使用）：
- `从 mock大模型服务器 导入 新建Mock服务, 启动Mock服务`
- `新建Mock服务(选项)` → 纯逻辑实例；`实例.分派(["方法","路径","头","体"])` → `[状态, 头字典, 体]`；`实例.请求记录`（每次消耗一条）；`实例.端口()`/`实例.停止()`。
- 选项键：`序列`(必填)/`重复末位`/`随机种子`/`随机权重`/`成功文本`/`部分文本`/`推理文本`/`块大小`/`重试毫秒`/`请求ID`/`工具名`/`工具参数`/`API密钥`。
