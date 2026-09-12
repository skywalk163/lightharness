# 任务4 交付报告 —— SDK 协议域：NDJSON JSON-RPC 2.0 传输层

> 轮次：第 11 轮 · 任务4（SDK 协议域）
> 日期：2026-09-12
> 上游依据：`G:\github\deepseek-harness` @ `a305303422`，`packages/sdk/protocol/src/{transport.ts, types.ts, index.ts}`

---

## 一、上游依据（文件 : 函数/段落）

| 上游位置 | 语义 | 光明落点 |
|---|---|---|
| `transport.ts:62-269` `JsonRpcLineTransport` | 行分隔端点：附监听、收监、挂处理器、pending 请求表 | 抽纯逻辑为 `JSONRPC终端`（同步分派，见「差异」） |
| `transport.ts:121-156` `request()` | 造请求帧 `req_${randomUUID().replaceAll('-','')}` | `造请求ID()` / `造请求帧()` |
| `transport.ts:158-160` `notify()` | 通知帧，无参不带 params | `造通知帧()` |
| `transport.ts:166-173` `flush()` | 写侧屏障 | 未移植（依赖 node:stream 写回调） |
| `transport.ts:175-189` `onData`/`drainLines` | 缓冲拼接 + 按 `\n` 切行 + trim + 空行跳过 | `NDJSON行解码器.推入()` |
| `transport.ts:191-199` `onInputError`/`onInputEnd` | 输入错误/结束失败在途请求 | 未移植（依赖事件流，见「未移植项」） |
| `transport.ts:201-224` `handleLine` | JSON.parse 失败忽略；非对象忽略；id+method→请求 / 仅 id→响应 / 仅 method→通知 | `判别帧()` + `JSONRPC终端.接收行()` |
| `transport.ts:226-238` `handleIncomingRequest` | 无处理器 `-32601`；处理器失败 `-32603`；成功回 `result` | `JSONRPC终端.分派请求()` |
| `transport.ts:240-254` `handleIncomingResponse` | 响应帧 error→JsonRpcResponseError，否则 resolve(result) | `接收行` else 分支记入 `收到响应`（pending 关联未移植） |
| `transport.ts:256-258` `writeError()` | 错误帧 `{code, message}` | `造错误响应帧()` / `造错误()` |
| `transport.ts:260-262` `write()` | `JSON.stringify(message) + '\n'` | `帧编码()` |
| `transport.ts:272-274` `objectParams()` | 非普通对象（数组/标量/空）塌缩为 `{}` | `归一化参数()` |
| `transport.ts:18-28` `JsonRpcResponseError` | wire 错误 `code/message/data` | `造错误()`（wire 形状对齐） |
| `types.ts` / `index.ts` | 业务消息类型（initialize/session.prompt 等） | 协议无关的具体业务词表，本轮不属传输层纯逻辑，未移植（见未移植项） |

---

## 二、实现要点

新建 `src/JSONRPC传输.light`，纯逻辑导出：

- **错误码常量**：`错误码方法未找到() = -32601`、`错误码处理器失败() = -32603`（对齐 transport.ts:229/236）。
- **帧编码（写侧）**：
  - `造请求帧(id, method, params)` → `{jsonrpc:"2.0", id, method, [params]}`；空/数组参数经 `归一化参数` 后不挂 params。
  - `造响应帧(id, result)` → `{jsonrpc, id, result}`。
  - `造通知帧(method, params)` → `{jsonrpc, method, [params]}`，无参不带 params。
  - `造错误(code, message, data?)` → `{code, message, [data]}`，对齐上游 JsonRpcError wire 形状。
  - `造错误响应帧(id, code, message, data?)` → `{jsonrpc, id, error:{...}}`。
  - `帧编码(消息)` → `序列化JSON(消息) + "\n"`（NDJSON 行）。
- **帧判别（读侧核心）** `判别帧(消息)`：
  - 先判字典类型（非字典→非法）；
  - 用 `.包含("id")` / `.包含("method")` 先判键存在（光明字典缺键抛错，对齐上游 `frame.id` 缺键得 `undefined`）；
  - 按上游顺序：`id 为字符串/整数/浮点 且 method 为字符串 → 请求`；`仅 id → 响应`；`仅 method → 通知`；其余 `非法`。
- **增量行解码器** `NDJSON行解码器`：文本块推入 → 拼进 `待定` 缓冲 → 循环 `查找子串(待定,"\n")` 切行 → `截取` 切出整行、`截取(边界+1,…)` 保留尾部 → `去除空白` → 非空行返回；无 `\n` 则半行留缓冲；`收尾()` 丢弃流末残行。完全复用既有 `e2b配套.light` 解码器范式。
- **内存终端** `JSONRPC终端`：`安装请求处理器`/`安装通知处理器`；`接收行(行)` 完成「trim → JSON.parse 失败忽略 → 判别 → 分派」；请求分派对齐上游（无处理器 `-32601`、处理器抛错 `-32603`、成功回 result）；通知无处理器丢弃；出站帧收进 `待发`，`取待发()` 由宿主写出。
- **ID 生成** `造请求ID()`：对齐上游 `req_${randomUUID().replaceAll('-','')}` 的「`req_` 前缀 + 高熵唯一段」语义。光明无 `node:crypto.randomUUID`，按任务书改用**三段随机整数拼接**（`随机整数(1e8,1e9-1)` + `随机整数(1e4,1e5-1)` + `随机整数(1e3,1e4-1)`，熵约 10^18），前缀仍为 `req_`。未混入时间戳：纯随机三段已满足「100 个全唯一」测试；如需更强单调性，后续可在段首拼 `时间戳()*1000` 毫秒段。

### 与上游的差异（光明无 byte 流一等原语，按任务书用文本行流 + 显式帧分隔模拟）

1. 读侧按**文本块**推入，而非 `Buffer + StringDecoder('utf8')`；多字节 UTF-8 跨块切断由宿主层负责（本项目 `stdlib/UTF8增量解码器.light` 已具备该能力，本模块不重复）。
2. 出站帧收进内存列表 `待发`，由宿主逐行写出；不直接绑定 `node:stream` Writable。
3. 同步语义：处理器段落同步返回结果，抛错即视为失败（对齐上游 `await handler` 的成功/失败两条路径）；无 async/Promise。

---

## 三、测试与 CI

- 新增 `examples/test_JSONRPC传输.light`，断言 **40+ 条**（要求 ≥12），覆盖：
  - 请求/响应/通知帧编码与 params 省略；
  - 错误帧 `code/message/data` 形状与无 data 省略；
  - `帧编码` 以 `\n` 结尾且可往返解析；
  - 三类帧判别（id+method / 仅 id / 仅 method / 非法 / 数字 id / 非字典）；
  - `归一化参数`（数组/空→{}，对象透传）；
  - 增量解码：半行合并（半行不出帧、补齐出帧）、多行一次入、多行同批出多行、`收尾` 丢弃残行；
  - 终端分派：无请求处理器 `-32601`、处理器成功回 result、处理器抛错 `-32603`；
  - 通知：有处理器分派、无处理器丢弃；
  - 非法行忽略（坏 JSON 空行无 id 无 method 全部静默）；
  - 入站响应帧记入 `收到响应`；
  - ID：`req_` 前缀、两次不同、100 个全唯一。
- 运行：`$env:LIGHT_MERGE=...; python 运行.py examples/test_JSONRPC传输.light` → **rc=0（PASS）**。
- 直接相关既有回归：`python -m pytest tests/ -q -k "流 or mcp"` → **2 passed, 238 deselected, rc=0**（未破坏）。
- 未跑全量 CI（铁律，由路M 统一跑）。

---

## 四、反跑判据（`_antirun_jsonrpc.py`，3/3 通过）

对 `src/JSONRPC传输.light` 字节级备份 → 定点篡改 → 跑测试 → 恢复字节 → 重跑：

| 判据 | 篡改 | 篡改后 | 恢复后 |
|---|---|---|---|
| A 响应帧判别改错 | 把「仅 id→响应」提前到「id+method→请求」之前（id+method 误判为响应） | rc=1（红）✅ | rc=0（绿）✅ |
| B 非法行忽略改抛错 | `捕获 错误: 返回` 改为 `捕获 错误: 抛出 错误`（坏 JSON 行外抛） | rc=1（红）✅ | rc=0（绿）✅ |
| C 增量半行合并改错 | 无 `\n` 残块被当作完整行吐出（破坏半行保留） | rc=1（红）✅ | rc=0（绿）✅ |

脚本输出：`全部反跑判据通过（篡改→红，恢复→绿）`，rc=0。

---

## 五、未移植项（依赖 node:stream / async / 宿主绑定，留待后续轮）

1. **pending 请求表 + Promise 关联**（`pending: Map<id,{resolve,reject}>`，transport.ts:68, 124-155, 240-254）：光明无 Promise/Future，客户端「发请求等响应」的异步关联未移植；本模块只做服务端分派纯逻辑 + 响应帧记录。
2. **AbortSignal 中止**（transport.ts:116-137）：无对应原语。
3. **流挂接/摘除**（`start()`/`close()`，transport.ts:76-92）与输入 `error`/`end` 事件失败在途请求（`failPending`，transport.ts:264-268）：依赖事件流。
4. **`flush()` 写侧屏障**（transport.ts:166-173）：依赖 Writable 写回调。
5. **`JsonRpcResponseError` 异常类**（transport.ts:18-28）：本模块以字典 wire 形状 `{code,message,data}` 表达错误帧；服务端向上抛错的异常类型化未做（光明同步语义下用「错误响应帧 + 消息文本」表达）。
6. **`types.ts` 业务消息词表**（initialize/session.prompt/shutdown/四类通知载荷）：属具体业务形状，非传输层纯逻辑；待 SDK client/server 包落地时再补，本模块与方法名/载荷形状解耦。
7. **UTF-8 多字节跨块解码**：光明侧由 `stdlib/UTF8增量解码器.light` 承担，本模块按文本行流模拟，不重复实现字节级 StringDecoder。

---

## 六、语言特性使用与缺陷

- 复用既有原语：`查找子串`/`截取`/`字符串长度`/`去除空白`/`是字符串`/`是整数`/`是浮点`/`是字典`/`是空`/`时间戳`/`随机整数`/`从 JSON 导入 解析JSON,序列化JSON`。
- 两个绕法（非缺陷，按既有规范写）：字典键缺失会抛错，读 `id`/`method`/`params` 一律先 `.包含(键)`（对齐上游 `frame.id` 缺键为 undefined 的宽容语义）。
- 未触发新语言缺陷，无需登记 `L-084+` / 新增 `_repro_Lxxx.light`。
- 本轮未使用「副本/深拷贝/浅拷贝/尾随逗号」新原语（本模块无需可变复合值深拷贝）。

---

## 七、移交清单

| 交付物 | 绝对路径 |
|---|---|
| 传输层模块 | `G:\dswork\duan-light-merge\lightharness\src\JSONRPC传输.light` |
| 单元测试（40+ 断言） | `G:\dswork\duan-light-merge\lightharness\examples\test_JSONRPC传输.light` |
| 反跑脚本（3 判据） | `G:\dswork\duan-light-merge\lightharness\_antirun_jsonrpc.py` |
| 本报告 | `G:\dswork\duan-light-merge\lightharness\_task4_JSONRPC传输_交付报告.md` |

**路M 收口建议**：
- 对标卡 **#74 sdk/protocol NDJSON JSON-RPC 传输** → `src/JSONRPC传输.light`，状态「已跟随」。
- 本路仅新建互斥表内文件（`src/JSONRPC传输.light`、`examples/test_JSONRPC传输.light`、反跑脚本、本报告），未改任何他域文件。
- 后续若做 SDK client/server 宿主包，在本传输层之上补 pending 关联 + AbortSignal + flush 即可，线帧形状已对齐上游。
