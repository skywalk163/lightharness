# lightharness 使用 MCP（对齐 deepseek-harness）

lightharness 像 deepseek-harness 一样，可以把外部 MCP server 的工具注册进模型工具表，
命名为 `mcp__<服务器名>__<原始名>`（与 Claude Code / Codex / DSH 同口径）。
支持两种传输：**stdio**（本地进程）与 **streamable-http**（HTTP 服务）。

## 1. 配置

在项目根放一个 `mcp.json`，或设环境变量 `HARNESS_MCP_CONFIG` 指向任意路径。
配置格式与 deepseek-harness 的 `mcpServers` 完全兼容（英文键），也兼容本仓历史中文键。

```json
{
  "mcpServers": [
    {
      "name": "github",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "..." }
    },
    {
      "name": "web",
      "transport": "streamable-http",
      "url": "http://127.0.0.1:3000/mcp",
      "headers": { "Authorization": "Bearer ..." }
    }
  ]
}
```

字段对照（英文 / 中文，两者等价、英文优先）：

| DSH 英文键 | 本仓中文键 | 含义 |
|---|---|---|
| `name` | `名` | 服务器名（`[A-Za-z0-9_-]{1,32}`，唯一） |
| `command` | `指令` | stdio 可执行文件，**必须绝对路径** |
| `args` | `参数` | stdio 参数数组 |
| `env` | `环境` | 环境变量，`[{名,值}]` 或 JSON 对象 |
| `transport` | `类型` | `stdio`（缺省）/ `streamable-http`（中文写 `http`） |
| `url` | `网址` | streamable-http 端点 |
| `headers` | `头表` | HTTP 请求头，`[{名,值}]` 或 JSON 对象 |

- 配置文件不存在或没有 `mcpServers` 字段 → 静默 no-op，不影响只挂核心工具。
- 单个 server 连接/握手失败只打印并跳过，不拖垮 agent 启动。
- 相对 `command` 会被拒绝（要求绝对路径）；FreeBSD/Linux 用 `/usr/local/bin/python` 之类，
  Windows 用 `C:\\...\\python.exe`。`运行.py` 会把当前解释器绝对路径注入 `HARNESS_PY`，
  `.light` 侧可用 `环境变量("HARNESS_PY")` 拿到它。

## 2. 自动挂载

`src/总入口.light` 的 `组装注册表()` 在挂载核心工具与插件后调用 `挂载MCP服务器(注册表)`，
无需手工接线。Web 面板里 MCP 工具与核心工具一视同仁地出现在模型工具表。

## 3. 运行层

- `src/mcp客户端.light`：`MCP客户端`（stdio，JSON-RPC 2.0 逐行）+ `MCPHttpClient`
  （streamable-http，SSE/JSON 响应解析）；初始化握手 → `tools/list` 发现 → `tools/call` 调用；
  含重连（指数退避）、图片块投影、分页重复光标拒绝、资源工具投影。
- `src/mcp接线.light`：`挂载MCP服务器(注册表, 路径=空)`，读配置 → 形状校验 →
  逐 server 注册；返回 `{"已注册","客户端表","服务器数","跳过数"}`。

## 4. 已知差异（相对 DSH）

- 握手方法内部名从「连接」改为「握手」：光明编译器把「连接」映射为 Python `str.join`，
  与用户自定义类方法撞名（详见 CHANGELOG）。这是内部实现名，不暴露给用户配置。
- `${credential:REF}` 模板展开：纯逻辑侧已具备（B8，见 `src/凭据链.light`），
  真实连接代次 / Cordis 作用域分层 / 插件热装配属宿主面，未移植。
- MCP prompt templates、资源订阅、音频/嵌入资源投影：DSH 本身也不支持或仅诊断展示，本仓对齐。

## 5. 验证

在 FreeBSD 0.88 真机（非桩）实测通过：

- `examples/test_mcp接线.light` —— stdio 真起 server，2 工具发现+调用。
- `examples/test_mcp_http_real.light` —— HTTP 真起 server，握手/3 工具/调用/注册。
- `examples/test_mcp_prod.light` —— 无参 `挂载MCP服务器` 自动读 DSH 格式 `mcp.json`。
- `examples/test_mcp.light` / `test_mcp_http.light` / `test_R51_mcp资源.light` —— 桩回归。
