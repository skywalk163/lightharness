# API 参考

本文档列出 lightharness 各模块的公开接口。当前版本覆盖遥测模块。

---

## 遥测收集器（遥测.light）

### 构造

```light
设 遥测 为 新建 遥测收集器()
```

创建一个新的遥测收集器实例。所有属性初始化为默认值。

**参数：** 无

**返回值：** `遥测收集器` 实例

---

### 开始会话

```light
设 span 为 遥测.开始会话(会话ID)
```

开始一个会话级 span（kind=`session`），生成 trace_id，压入 span 栈。

**参数：**
- `会话ID`（字符串）：会话标识

**返回值：** span 字典 `{trace_id, span_id, parent_span_id, name, kind, start_time, end_time, duration_ms, attributes, status, error_message}`

**示例：**
```light
设 会话span 为 遥测.开始会话("sess_001")
打印 会话span["trace_id"]
```

---

### 开始轮次

```light
设 span 为 遥测.开始轮次()
```

开始一个轮次级 span（kind=`turn`），父 span 为当前栈顶。

**参数：** 无

**返回值：** span 字典

---

### 开始步骤

```light
设 span 为 遥测.开始步骤()
```

开始一个步骤级 span（kind=`step`），父 span 为当前栈顶。

**参数：** 无

**返回值：** span 字典

---

### 记录LLM调用

```light
设 span 为 遥测.记录LLM调用(模型, TTFT毫秒, 输入tokens, 输出tokens, 缓存tokens, 完成原因)
```

记录一次 LLM 调用，创建 kind=`llm` 的 span（不压栈，立即结束）。

**参数：**
- `模型`（字符串）：模型名称，如 `"deepseek-chat"`
- `TTFT毫秒`（数值）：首 token 延迟（Time To First Token）
- `输入tokens`（整数）：输入 token 数
- `输出tokens`（整数）：输出 token 数
- `缓存tokens`（整数）：缓存读取 token 数
- `完成原因`（字符串）：如 `"stop"` / `"tool_calls"` / `"max_tokens"`

**返回值：** span 字典，attributes 包含 `model, ttft_ms, input_tokens, output_tokens, cache_read_tokens, finish_reason`

**示例：**
```light
设 llmspan 为 遥测.记录LLM调用("deepseek-chat", 120.5, 500, 200, 50, "stop")
断言等于(llmspan["attributes"]["model"], "deepseek-chat")
```

---

### 记录工具调用详情

```light
设 span 为 遥测.记录工具调用详情(工具名, 参数hash, 成功, 错误类型)
```

记录一次工具调用，创建 kind=`tool` 的 span（不压栈，立即结束）。注意：此为新签名方法，旧方法 `记录工具调用(工具名, 延迟秒)` 仍保留用于向后兼容。

**参数：**
- `工具名`（字符串）：工具名称
- `参数hash`（字符串）：参数的哈希值（用于隐私保护，不记录参数正文）
- `成功`（布尔）：是否调用成功
- `错误类型`（字符串）：失败时的错误类型，如 `"timeout"` / `"auth"` / `"network"`

**返回值：** span 字典，attributes 包含 `tool_name, params_hash, success, error_type`

**示例：**
```light
设 toolspan 为 遥测.记录工具调用详情("bash", "abc123", 真, "")
断言等于(toolspan["status"], "ok")
```

---

### 结束当前

```light
设 span 为 遥测.结束当前()
```

结束栈顶 span，设置 `end_time` 和 `duration_ms`，弹出栈。

**参数：** 无

**返回值：** 已结束的 span 字典；栈为空时返回 `空`

**示例：**
```light
遥测.开始会话("s1")
遥测.开始轮次()
遥测.开始步骤()
遥测.结束当前()  # 结束 step
遥测.结束当前()  # 结束 turn
遥测.结束当前()  # 结束 session
```

---

### 聚合统计

```light
设 结果 为 遥测.聚合统计(维度)
```

按指定维度聚合统计。

**参数：**
- `维度`（字符串）：`"轮次"` / `"步骤"` / `"模型"` / `"工具"`

**返回值：**
- 轮次/步骤维度：`{维度, 调用数, 总耗时, 平均耗时, 成功率, 错误数}`
- 模型/工具维度：`{维度, 分组: {键: {调用数, 总耗时, 平均耗时, 成功率}}}`

**示例：**
```light
设 模型聚合 为 遥测.聚合统计("模型")
设 分组 为 模型聚合["分组"]
设 项 为 分组["deepseek-chat"]
打印 项["调用数"]  # 1
打印 项["成功率"]  # 1.0
```

---

### 错误分类统计

```light
设 结果 为 遥测.错误分类统计()
```

按错误类型分组计数。

**参数：** 无

**返回值：** 字典 `{错误类型: 计数}`，如 `{"timeout": 1, "auth": 2}`

---

### 导出

```light
设 spans 为 遥测.导出()
```

获取全部 span 列表，供输出器使用。

**参数：** 无

**返回值：** span 字典列表

---

### 持久化

```light
设 路径 为 遥测.持久化(文件路径)
```

将全部 span 以 JSONL 格式写入文件（每行一个 span）。

**参数：**
- `文件路径`（字符串）：输出文件路径

**返回值：** 文件路径

---

### 配置选项

```light
遥测.配置选项(选项)
```

设置遥测收集器的配置选项。

**参数：**
- `选项`（字典）：支持 `capture_content`（布尔，默认 `假`）

**示例：**
```light
遥测.配置选项(["capture_content": 假])
```

---

### 向后兼容方法

以下 v1/v2 方法全部保留，可继续使用：

| 方法 | 说明 |
|------|------|
| `记录轮次开始(轮次)` | 记录轮次开始 |
| `记录步骤(轮次, 步骤, 延迟秒, 用量)` | 记录步骤延迟和 token 用量 |
| `记录工具调用(工具名, 延迟秒)` | 记录工具调用（旧签名） |
| `记录错误(错误描述)` | 记录错误并自动分类 |
| `记录轮次结束(轮次, 结果)` | 记录轮次结束 |
| `汇总()` | 返回统计字典 |
| `输出()` | 打印可读汇总 |
| `导出指标(格式)` | 导出指标（`"json"` 格式） |
| `持久化接口(文件路径)` | 写入 JSON 文件 |
| `获取全部span()` | 获取全部 span |
| `栈顶span()` | 获取当前栈顶 span |

---

## 遥测输出器（遥测导出器.light）

### 输出器基类接口

所有输出器实现以下接口：

| 方法 | 说明 |
|------|------|
| `输出(spans)` | 输出 span 列表 |
| `输出指标(metrics)` | 输出指标数据 |
| `刷新()` | 刷新缓冲区 |
| `关闭()` | 关闭输出器 |

---

### 控制台输出器

```light
设 输出器 为 新建 控制台输出器(选项)
```

将 span 格式化输出到控制台。

**构造参数：**
- `选项`（字典，可选）：支持 `capture_content`（布尔，默认 `假`）

**方法：**
- `输出(spans)`：打印每个 span 的 kind/name/span_id/parent/耗时/状态，返回 span 数量
- `输出指标(metrics)`：打印指标数据
- `过滤(span)`：隐私过滤，返回过滤后的 span（`capture_content=false` 时移除正文字段）

**示例：**
```light
设 输出器 为 新建 控制台输出器(空)
设 数量 为 输出器.输出(全部span)
```

---

### JSONL输出器

```light
设 输出器 为 新建 JSONL输出器(文件路径, 选项)
```

将 span 以 JSONL 格式写入文件（每行一个 span）。

**构造参数：**
- `文件路径`（字符串）：输出文件路径
- `选项`（字典，可选）：支持 `capture_content`

**方法：**
- `输出(spans)`：写入文件，返回 span 数量
- `输出指标(metrics)`：将指标写入 `{文件路径}.metrics.json`
- `过滤(span)`：隐私过滤

**示例：**
```light
设 输出器 为 新建 JSONL输出器("./telemetry/s1.jsonl", 空)
输出器.输出(全部span)
```

---

### OTLP输出器（接口层预留）

```light
设 输出器 为 新建 OTLP输出器(端点, 请求头, 选项)
```

OTLP（OpenTelemetry Protocol）导出器。当前为接口层预留，仅组装 OTLP HTTP 请求结构，不实际发送网络请求。

**构造参数：**
- `端点`（字符串）：OTLP HTTP 端点 URL
- `请求头`（字典）：HTTP 请求头，如 `["Authorization": "Bearer xxx"]`
- `选项`（字典，可选）：支持 `capture_content`

**方法：**
- `输出(spans)`：组装 OTLP 请求体，返回 `{endpoint, headers, format, resource_spans, 注意}`，打印预留提示
- `输出指标(metrics)`：组装指标请求体
- `过滤(span)`：隐私过滤

**示例：**
```light
设 输出器 为 新建 OTLP输出器("https://otlp.example.com/v1/traces", ["Authorization": "Bearer xxx"], 空)
设 请求体 为 输出器.输出(全部span)
打印 请求体["注意"]  # "OTLP输出为接口层预留，未实际发送HTTP请求"
```

---

### 输出器管理器

```light
设 管理器 为 新建 输出器管理器()
```

管理多个输出器，广播输出到所有已注册输出器。

**方法：**
- `注册(输出器)`：注册一个输出器，返回当前输出器数量
- `输出(spans)`：广播输出到所有注册输出器，返回 `[{名称, 结果}]` 列表
- `输出指标(metrics)`：广播输出指标
- `刷新()`：刷新所有输出器
- `关闭()`：关闭所有输出器

**示例：**
```light
设 管理器 为 新建 输出器管理器()
管理器.注册(新建 控制台输出器(空))
管理器.注册(新建 JSONL输出器("./out.jsonl", 空))
设 结果 为 管理器.输出(全部span)  # 同时输出到控制台和文件
管理器.关闭()
```

---

## Span 数据结构

每个 span 是一个字典，包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `trace_id` | 字符串 | 追踪 ID（会话级生成，全链路唯一） |
| `span_id` | 字符串 | span ID（每个 span 唯一） |
| `parent_span_id` | 字符串 | 父 span ID（会话级为空字符串） |
| `name` | 字符串 | span 名称，如 `"session:sess_001"` / `"turn"` / `"llm:deepseek-chat"` |
| `kind` | 字符串 | 类型：`session` / `turn` / `step` / `llm` / `tool` |
| `start_time` | 数值 | 开始时间戳（秒） |
| `end_time` | 数值 | 结束时间戳（秒） |
| `duration_ms` | 数值 | 持续时间（毫秒） |
| `attributes` | 字典 | 附加属性（LLM/工具 span 含详细指标） |
| `status` | 字符串 | 状态：`"ok"` / `"error"` |
| `error_message` | 字符串 | 错误信息（成功时为空） |

### LLM span attributes

| 字段 | 说明 |
|------|------|
| `model` | 模型名称 |
| `ttft_ms` | 首 token 延迟（毫秒） |
| `input_tokens` | 输入 token 数 |
| `output_tokens` | 输出 token 数 |
| `cache_read_tokens` | 缓存读取 token 数 |
| `finish_reason` | 完成原因 |

### 工具 span attributes

| 字段 | 说明 |
|------|------|
| `tool_name` | 工具名称 |
| `params_hash` | 参数哈希（隐私保护） |
| `success` | 是否成功（布尔） |
| `error_type` | 错误类型 |
