# _task4_大模型回放_交付报告

> 第12轮 · 任务4（测试支撑域）｜llm-replay 纯逻辑面（会话 → 模型调用脚本）
> 日期：2026-09-12 ｜ 仓库：`G:\dswork\duan-light-merge\lightharness` ｜ 编译器：`light-merge`（LIGHT_MERGE）
> 上游（只读）：`G:\github\deepseek-harness` @ `a305303422`（0.1.5-rc.2）

---

## 1. 上游依据（文件:函数）

| 上游 | 函数 / 常量 | 光明侧投影 |
|---|---|---|
| `packages/test-support/llm-replay/src/index.ts` | `parseSessionLog(text)` | `解析会话日志`（JSONL → 事件表；投影行 seq0/time0、打包行基数、dense seq、complete/projected 混合拒绝、非对象行拒绝） |
| 同上 | `parseSessionHeader(text)` | `解析会话头`（标识 / 创建时间 / 继承事件数；v0 seedLength 缺省 0） |
| 同上 | `deriveReplayScript(events)` | `推导回放脚本`（compaction/summary `llmStreamCall=true` → rawOutput 块展开 block-start→block-end→usage→finish；assistant/message、assistant/attempt 内嵌流展开且末块须 finish，否则抛「thrown stream 需 replay.override.json 侧车」） |
| `packages/llm/llm/src/assistant-stream.ts` | `expandAssistantStream` | `展开助手流`（text-chunks/reasoning-chunks/tool-call-chunks 压缩记录 → text-delta/reasoning-delta/tool-call-delta 增量；普通 chunk 直通） |
| `packages/test-support/llm-replay/src/index.ts` | `resolveScriptedEntry` / `collectStrings` / `resolveFromRequest` / `substituteString` / `substituteValue` | `解析脚本条目` + `收集字符串` + `取最后匹配` + `替换字符串模板` + `替换值`（`{{fromRequest:<pattern>}}` 用当前请求消息语料全部字符串叶子 join("\n") 的「最后匹配」替换） |
| 同上 | `materializeSessionTokens` | `物化会话令牌` + `物化字符串` + `物化值`（`{{session:N}}` 按首次调用序绑定实体会话 id；非数字 / `{{session:0}}` 保留；未绑定抛错） |
| 同上 | `ReplayEntry` / `ReplayOverrideDoc` | `解析覆盖文档`（chunks / throw / hang 三形 + `ReplayEntry[]` 或 `{patches}` 校验）、`应用覆盖补丁`（at>len 抛、重复 at 抛、at==len 追加）、`整理会话脚本`（主脚本 + 子脚本 createdAt 升序、平局 recordedId 字典序） |

**跳过宿主接线**：`installLlmReplay`（Cordis 监听）/ `loadReplayScript` / `loadSessionScripts` 的文件 IO 与覆盖合并装配、`LlmAdapter` 类与宿主注册。

## 2. 实现要点

- **头部版本迁移**：复用 `会话格式.目录读头`（v3 头直读；v0/v1/v2 头按标准链 v0→v1→v2→v3 迁移）。**目录对象在本模块内自建**：不能 import 并使用 `会话格式.当前目录`——「当前目录」是编译器内置映射名（builtins 的 `os.getcwd()`），编译器强制发射为带括号调用 → `'dict' object is not callable`；本模块用 `造目录("current", V3编解码, 创建链(迁移表), [主:3, 次:0])` 构造等价 `会话目录`，两处 `目录读头(会话目录, ...)`。
- **投影行语义**（对齐上游 session-format v3 投影快照）：打包行类型（text-chunks / reasoning-chunks / tool-call-chunks）用 `seq0`/`time0` 键，其余用 `seq`/`time`；有序/有时须成对；complete 与 projected 行混合拒绝；projected 行补 dense seq（按 `行基数` 累加：data.texts / data.args 长度，普通行 1）与 time=0。
- **脚本推导顺序**：compaction/summary 显式 `llmStreamCall: true` → 逐 rawOutput 块发射 `block-start(index, blockType)` → `block-end(index, block)` →（有 usage 时）`usage` → `finish(reason: stop)`；`llmStreamCall` 缺省/假 或 无 rawOutput 的 compaction 忽略。assistant/message 与 assistant/attempt：取 `data.stream`（英文）或 `data.流`（光明中文）双键 → `展开助手流` → 末块非 finish 抛错；空流跳过；轮次键 `turn/step` 为键（缺省 `undefined/undefined`）。
- **请求插值**：`收集字符串` 递归取全部字符串叶子 → `连接行` 为语料 → `取最后匹配`：无捕获组 → 全匹配；单捕获组 → 组1；多捕获组 → 组1（对齐 `last[1] ?? last[0]`）；占位符模式取到首个 `}}`，连续 `}` 归入模式。
- **会话令牌**：`{{session:N}}`（N ≥ 1）按首次调用序（`编号 - 1` 下标）绑定实体会话 id；`{{session:0}}` 与非数字保留原样；未绑定的序数抛错。
- **覆盖文档**：chunks（校验块 type ∈ 回放块类型表）、throw（消息/码非空、accepted 布尔校验）、hang（readyFile 非空字符串）；文档形态 `ReplayEntry[]` 或 `{patches:[{at,entry}]}`，at 为非负整数；补丁 at>len / 重复 at 拒绝，at==len 追加，否则原位替换。
- **事件类型兼容**：`assistant/message` / `compaction/summary` 等类型名英文原样；数据键 stream/流 双键兼容（光明 v3 落盘中文键）。

## 3. 测试与 CI

| 测试 | 断言数 | 覆盖 |
|---|---|---|
| `examples/test_大模型回放.light` | 65（要求 ≥10） | 日志解析（投影行、dense seq、混合拒绝、非对象行拒绝）/ 会话头（标识/创建时间/seedLength 继承）/ 脚本推导（compaction 展开顺序、显式 llmStreamCall、纯摘要忽略、抛流判错）/ 展开助手流（直通 + 双文本 + 双工具增量）/ fromRequest 插值（最后匹配语义、无捕获/单捕获组）/ 会话令牌（首呼序绑定、未绑定抛错、`{{session:0}}` 保留）/ 覆盖文档（chunks/throw/hang、ReplayEntry[]、patches 校验）/ 补丁应用（越界/重复拒绝、追加）/ 脚本排序（createdAt/recordedId） |

测试构造要点：日志/覆盖文档文本一律用 `序列化JSON` 构造（光明字符串内 `{标识符}` 触发插值破坏，手写 JSON 字面量不可靠）；抛错判据用具名零参段落 + `尝试/捕获 错误:` + 布尔标志（`捕获 错误 as 变量` 不支持）。

运行：`python 运行.py examples/test_大模型回放.light`（输出通过标记）。

**相关既有回归**（铁律 6，任务书点名）：`test_会话格式` ✅（`目录读头`/`造目录`/迁移链复用）；`test_客户端` / `test_压缩` 未直接引用（回放逻辑不依赖 HTTP 客户端与压缩器，任务书「若引用」条件不成立，未跑；如需全量由路M 统一）。

## 4. 反跑判据（`_antirun_replay.py`，字节级备份/恢复 src，3/3 通过）

| 项 | 改错内容 | 红 | 绿 |
|---|---|---|---|
| A 脚本推导顺序改错 | compaction 块先 finish 后 usage | rc=1 ✅ | rc=0 ✅ |
| B fromRequest 插值去掉 | 占位符不替换（保留模式原文） | rc=1 ✅ | rc=0 ✅ |
| C 父子首呼绑定改错 | `{{session:N}}` 一律取最后一个实体会话 | rc=1 ✅ | rc=0 ✅ |

## 5. 未移植项 / 语言差异（登记）

1. **`当前目录` 内置名冲突**：`当前目录` 是编译器内置映射名（builtins `os.getcwd()`），编译器把源码里的 `当前目录` 无条件发射为 `当前目录()`（带括号调用）；import 会话格式的字典常量 `当前目录` 后使用会报 `'dict' object is not callable`。绕法：本模块内用 `造目录` + 标准链自行构造 `会话目录`（等价物），不 import 该名。
2. **`{1,4}` 花括号量词破坏**：光明字符串把 `{1,4}` 当重复语法（SyntaxWarning: 'int' object is not callable）。回放自身正则（会话令牌序号 `^[1-9][0-9]*$`）不用花括号量词；fromRequest 模式由调用方提供（测试中 `goal-([0-9]+)` 亦无花括号）。`{{session:1}}` / `{{fromRequest:...}}` 字面量花括号在源文本中安全（探针验证）。
3. **`捕获 错误 as 变量` 不支持**：用 `尝试/捕获 错误:` + 布尔标志实现判抛错。
4. **`转整数(x)` 无基数参数**：会话令牌序号为十进制字符串，`转整数` 直用（无十六进制场景）。
5. **v3 中文键兼容**：光明 v3 落盘事件数据用中文键（流/消息），上游夹具英文键（stream/message）；`取流` 双键兼容（优先英文、回退中文），事件类型名英文原样。
6. **投影行解析内置化**：上游投影行/打包行/dense seq 语义在 session-format-catalog 宿主接线层；光明侧在 `解析会话日志` 内实现（任务书边界：纯逻辑面独立交付）。
7. **序列化JSON 构造测试文本**：光明字符串 `{标识符}` 触发插值，测试内 JSON 字面量一律用 `序列化JSON(...)` 构造（探针验证，防插值破坏）。

## 6. 移交清单

- 新增（任务4 文件互斥表范围内）：`src/大模型回放.light`、`examples/test_大模型回放.light`、`_antirun_replay.py`、`_task4_大模型回放_交付报告.md`。
- **未触碰** `docs/功能对标/`（只读，路M 统一）：语言缺陷条目（`当前目录` 内置名冲突、`{1,4}` 量词、`捕获 错误 as` 不支持、字符串插值）在报告中登记，未写入 语言缺陷账.md，需路M 收口时统一落账。
- 无越界改其他域 src；`src/客户端.light` / `src/流.light` 只读未动。
- 后续接入点：回放服务器形态（HTTP/SSE）复用既有 HTTP 服务端 / mock 逻辑（只读），本轮仅新增回放逻辑、未复制 HTTP 实现；`解析覆盖文档` / `应用覆盖补丁` 可被 `loadSessionScripts` 装配面消费（宿主接线由路M 统一决策）。
