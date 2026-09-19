# R74 JSON-RPC 传输四项深化 —— 路5B 交付报告

- 仓库：`G:\dswork\duan-light-merge\lightharness`
- 改动文件（严格受限面）：
  - `lightharness\src\JSONRPC传输.light`（在既有 `JSONRPC终端` 之后**追加**新类/段落，未触碰任何既有符号）
  - `lightharness\examples\test_R74_路5_JSONRPC深化.light`（新增）
- 未触碰：`light-merge\`、`docs\功能对标\对标清单.json`、`src\` 其它模块、`CLI判定逻辑.light`

---

## 一、既有契约（先读懂再动手）

原始 `JSONRPC传输.light`（标 `done(纯逻辑层)`）已实现**纯逻辑同步**部分，对齐上游 `packages/sdk/protocol/src/transport.ts`：
- 三类线帧判别 `判别帧`：id+method→请求 / 仅 id→响应 / 仅 method→通知 / 其余→非法（静默忽略）。
- 帧编解码 `造请求帧/造响应帧/造通知帧/造错误响应帧/帧编码`（NDJSON 行尾带 `\n`）。
- 增量行解码器 `NDJSON行解码器`（半行合并、收尾残行）。
- 内存终端 `JSONRPC终端`：安装请求/通知处理器、`接收行` 判别分派、出站帧收进 `己.待发`、`取待发` 消费。
- 错误码 `-32601`(method not found) / `-32603`(handler failed)。

**登记缺口（原话「依赖 node:stream + Promise，留后续轮宿主包」）已不成立**：光明现已有一等 async/await（R70-B：`异步 段落` / `等待` / `并发等待` / `首个完成`；`捕获` 可接 `异常`）与 `src/中止.light`（`中止令牌` = AbortSignal 等价 + `轮询中止` 异步竞速）。故用光明现有异步能力做等价实现，不再挂「宿主包」标签。

---

## 二、四项实现说明（全部落在本模块，纯逻辑可测）

新增 `JSONRPC异步终端` 类 + 模块级异步桥 + `内存字节流`（可读写字节流的内存回环实现）。

### 1) pending 请求表（并发撮合、按 id 寻址）
- `发请求(方法, 参数, 令牌)` 内部：`造请求ID()` 生成 id → `终端.写出(帧)` 写缓冲 → `创建Future()` → `终端.挂起表[标识] 为 未来`（**dict 按 id 挂号**）。
- 响应到达走 `收行 → 结算响应`：`设 未来 为 己.挂起表[标识]; 字典删除(己.挂起表, 标识); 未来拒绝/ set_result`。
- 并发多请求各自独立条目，响应按 id 撮合，**互不串味**；结算后条目从 `挂起表` 移除。
- 错误响应帧 → `未来拒绝(未来, "JSONRPC错误 code=… msg=…")` 以异常明确拒绝（不挂死）。

### 2) 取消信号（中止令牌 = AbortSignal 等价）
- `协发请求` 有令牌时走竞速：`任务甲 = 创建任务(等待挂起(未来))` vs `任务乙 = 创建任务(轮询中止(令牌))` → `等待 首个完成([任务甲, 任务乙])`。
- **中止先到**：`字典删除(终端.挂起表, 标识)` 清理 pending → `任务甲.cancel()` + `任务乙.cancel()` → `抛出 "请求已取消: <id> 原因=<来源>"`。
- 等待方收到**明确取消异常**（可 `捕获` 接住），既不挂死也不静默；pending 表条目被清理。

### 3) flush（缓冲帧强制写出）
- `挂接流(流对象)` 把传输层接到可读写字节流。
- `flush()`：把 `己.待发` 中每帧 `流.写文本(帧)` 推到对端可读缓冲，清空待发，返回写出帧数；无流挂接返回 0。

### 4) 流挂接（接到可读写字节流，而非只吃/吐字符串）
- 原 `JSONRPC终端` 只能 `接收行(字符串)` / 往 `待发` 吐字符串。新 `JSONRPC异步终端` 可 `挂接流(内存字节流)`：
  - 写侧：`flush()` 把缓冲帧写到流（`写文本`）。
  - 读侧：`收流()` 从流 `读一行()` 逐行喂给 `收行`，经判别后分派/结算。
- 提供 `内存字节流`（实现 `写文本()` / `读一行()` 接口、`连接对端` 构成双向回环），真实场景换成 socket 流（同样实现这两个方法）即可，无需 node:stream。

---

## 三、匿名闭包作实参 这个坑，我是怎么绕的

**坑（上轮路5 死因，已回退）**：`终端.安装请求处理器(段落 好处理 接收 方法, 参数: …)` 直接编译失败 → `意外的标记: 「:」`，并连带打红 `test_JSONRPC传输.light`。L-022 的匿名闭包只覆盖「赋值给变量」与「返回闭包」，**不覆盖函数调用实参位置**。

**绕法（严格遵守任务书规定）**：一律先定义**具名 `段落`**，再把变量名传进去——
```light
段落 好处理 接收 方法, 参数:
  返回 ["echo": 参数["n"]]
...
服务端.安装请求处理器(好处理)   # 传变量名，不内联匿名闭包
```
`发请求` 内部返回模块级 `协发请求(己, …)` 协程（也是先定义命名段落再引用），全程无「匿名闭包作实参」。每改一次即重跑 `examples/test_JSONRPC传输.light` 确认未被打红（见第五节输出）。

> 附：本轮还顺手踩/验证的其它光明语法点（避免再翻车）：
> - 空字典字面量是 `{}`（`挂起表 等于 []` 是 list，按字符串 id 索引会 `TypeError: list indices must be integers`，已改为 `{}`）。
> - Python 方法名直传：`未来.set_result(v)`、`未来.done()`、`未来.result()` 可用；`完成` 等中文翻译名**不存在**（Future 无 `.完成` 属性）。
> - `新建 异常` / `新建 错误` 仅作 `抛出` 的**直接实参**（特殊 raise 形式）可用；作为普通表达式（如 `未来.set_exception(新建 错误(...))`）会 `name '错误' is not defined`。模块内改走 `未来拒绝(未来, 字符串)`（stdlib，字符串自动包 Exception）。
> - `等待 任务.result()` 在同步段调用会因任务尚未被事件循环唤醒而 `InvalidStateError`；须 `等待 任务` 驱动。
> - 类体不支持 `异步 段落`：异步逻辑放在模块级 `异步 段落`，类方法为同步桥 `返回 协发请求(己, …)`。

---

## 四、验收判据逐条实测（贴真实输出）

**既有用例必须仍 rc=0（上轮翻车点，反复确认）：**
```
$ python 运行.py examples/test_JSONRPC传输.light
=== JSONRPC传输 开始 ===
--- test_JSONRPC传输 PASS ---
__RC__=0
```

**新增用例四组断言全过：**
```
$ python 运行.py examples/test_R74_路5_JSONRPC深化.light
=== R74 JSONRPC深化 开始 ===
--- test_R74_路5_JSONRPC深化 PASS ---
__RC__=0
```
覆盖：甲=pending 并发按 id 撮合（乱序响应 丙→甲→乙 不串味）、乙=取消后 pending 清理+明确取消异常、丙=flush 落流、丁=流挂接端到端回声、戊=错误响应以异常明确拒绝。

**定向 pytest 门禁（仅 JSONRPC/传输，带 --basetemp，不跑全量以免与路2F 改编译器交叉污染）：**
```
$ python -m pytest tests/test_回归.py -q -p no:cacheprovider \
    --basetemp=G:/dswork/duan-light-merge/lightharness/_tmp_basetemp_r74_5B \
    -k "JSONRPC or 传输"
2 passed in 15.71s
__RC__=0
```
收集确认两项均被纳入：`test_example_exit_code[test_JSONRPC传输.light]` 与 `test_example_exit_code[test_R74_路5_JSONRPC深化.light]`（470 项中 2 项匹配）。

---

## 五、#74 条目更新文本（供主 agent 落盘 `对标清单.json`）

**状态（建议改为）：** `done(纯逻辑层+一等异步等价实现)`
**说明（建议追加）：** 缺口四项已用光明现有一等 async/await（R70-B）+ `src/中止.light` 的中止令牌在纯逻辑层等价实现，不再依赖 node:stream 宿主包：pending 请求表按 id 挂号 asyncio.Future 并撮合、取消信号经 `首个完成` 竞速清理 pending 并抛明确取消异常、flush 强制落已挂接可读写字节流、流挂接经 `内存字节流`（实现 `写文本/读一行`）使传输层脱离「只吃/吐字符串」。

**证据路径（追加到 `证据` 数组）：**
- `lightharness/examples/test_R74_路5_JSONRPC深化.light`（新增，四组断言全过，rc=0）
- `lightharness/src/JSONRPC传输.light`（#228 起追加 `JSONRPC异步终端` / `内存字节流` / 模块级 `协发请求` `等待挂起`）
- `lightharness/_task5B_R74_JSONRPC.md`（本报告）

> 注：全量门禁由主 agent 在最后统一跑，本路仅定向确认 JSONRPC 相关全绿。
