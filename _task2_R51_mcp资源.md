# 任务2（R51/P0）交付报告 —— mcp-resources（资源渲染 + 资源工具请求构造）

> 日期：2026-09-17 ｜ 第51轮（上游 0.1.6-alpha.1 增量跟随）｜ P0
> 上游基线：`G:\github\deepseek-harness`，release 提交 `ea53423b60`，fork 合并 `c47b24803e`
> 交付物：`src/mcp客户端.light`（加性新增「v2 资源域」段）、`examples/test_R51_mcp资源.light`、本报告

---

## 1. 上游原位（3 个文件，逐句对照）

| 上游文件 | 纯逻辑面 | 宿主面（登记不移植） |
|---|---|---|
| `packages/mcp/mcp-resources/src/render.ts` | `renderResourceResult(server, value): ContentBlock[]` —— 带 replacer 的 JSON 序列化（`key === 'blob' && typeof item === 'string'` → 占位）+ `MCP server: <名>\n` 前缀 + 单 text 块 | — |
| `.../src/tools.ts` | 三个共享资源工具：`list_mcp_resources` / `list_mcp_resource_templates` / `read_mcp_resource` 的**参数模式 + 描述 + 请求构造** | `ctx.effect` / `ctx.tools.register` / `defineTool` / disposed 解绑器 |
| `.../src/index.ts` | `McpResourceRequest` 契约、系统提示段文案、作用域内不可用文案 | `Service` / `ScopedLayers` / `NamedEntries` / `createScope` / 连接代次 |

上游三个工具的请求构造（逐字）：

```ts
list_mcp_resources          → { method: 'resources/list',             ...cursor 存在才带 }
list_mcp_resource_templates → { method: 'resources/templates/list',   ...cursor 存在才带 }
read_mcp_resource           → { method: 'resources/read', uri: args.uri }
```

---

## 2. 做了什么（`src/mcp客户端.light` 末尾新增「v2 资源域」段，加性、不改既有函数）

| 函数 | 内容 | 对齐上游 |
|---|---|---|
| `资源二进制占位(原文)` | `[binary resource: <N> base64 characters; available to programmatic callers]` | `render.ts` 的 replacer 返回值 |
| `替换资源二进制(值)` | 递归（字典键 / 列表项）把**任意层级**的 `blob` 字符串置换成占位；非字符串 `blob` 不动；不原地改写 | `JSON.stringify(value, replacer)` 的作用域 |
| `紧凑JSON(值)` | JS `JSON.stringify` 默认分隔符（`{"a":1,"b":[1,2]}`，**无空格**）；非 ASCII 不转义；布尔/空 → `true`/`null` | 上游 `rendered` 文本逐字一致（本仓 `序列化JSON` 走 Python `json.dumps` 会带 `", "`，故此处自备） |
| `渲染资源结果(服务器, 值)` | `[{type:"text", text:"MCP server: <名>\n<紧凑JSON>"}]` | `renderResourceResult` |
| `资源工具名表 / 是资源工具名 / 资源工具项 / 资源工具描述 / 资源工具方法` | 三个工具的名称（含顺序）、描述、MCP 方法 | `tools.ts` 三个 `defineTool` |
| `资源工具参数模式(名)` | JSON Schema：`server` 必选；列表类另有可选 `cursor`；读取类另有必选 `uri`；描述文案逐字 | `listParameters` / `read_mcp_resource.parameters` |
| `造资源请求(名, 参数)` | 三分支请求构造；`cursor` **存在且非空**才带；未知工具名抛错 | 三个 `execute` 的请求字面量 |
| `排序名表 / 资源服务器系统提示段(名表)` | 名称升序（对齐 `[...names].sort()`）；空表 → `""`；文案 `## MCP resource servers\n\nUse list_mcp_resources, list_mcp_resource_templates, or read_mcp_resource with one of these names as the server argument: [...]` | `index.ts` 的 `systemPrompt.section` |
| `资源服务器不可用消息(服务器)` | `MCP resource server "<名>" is unavailable in this agent's scope` | `resolveRequest` 的拒绝文案 |
| `绑定资源调用 / 注册资源工具(注册表, 执行请求)` | 把三个工具注册进本地注册表；执行时 `执行请求(服务器, 造资源请求(名, 参数))` → `渲染资源结果` | `registerResourceTools`（宿主生命周期解绑器不移植） |

**铁律遵守**：**不接真实 MCP 网络 IO** —— `执行请求` 是被注入的普通段落，用例注入桩实现；
`MCP客户端 / MCPHttpClient` 既有代码一行未动。

### 本地适配（登记为行为差异）

| 项 | 上游 | 本仓 | 影响 |
|---|---|---|---|
| 参数描述符形状 | 自有描述符 `{ name: { type, required: true, description } }` | JSON Schema（`"properties"` + `"required"` 数组），与本仓 `工具_bash`/`工具_读文件` 一致 | 参数名/描述/必选集逐字一致，仅容器形状不同 |
| `read` 缺 `uri` | `uri: undefined`（JSON 序列化时该键消失） | 取 `""` | 上游靠工具 schema 保证必选；本层给空串（已登记） |
| 数值形态 | JS `JSON.stringify(1.0)` → `1` | Python `json.dumps(1.0)` → `1.0` | 既有工程层「数值兼容」已登记的同类差异，MCP 资源值一般来自 JSON 解析（整数即整数），影响面窄 |
| `string.length` | UTF-16 code unit 数 | 码点数 | base64 为 ASCII 时一致 |

---

## 3. 实测证据

### 3.1 新用例（51 条断言，全绿）

```
cd G:/dswork/duan-light-merge/lightharness
../light-merge/.venv/Scripts/python.exe 运行.py examples/test_R51_mcp资源.light
→ test_R51_mcp资源: 全部用例通过   rc=0
```

覆盖矩阵：

| 组 | 判据 |
|---|---|
| §1 二进制占位 | 顶层 `blob` 替换、`uri` 不动、**嵌套**（字典内 / 列表内）`blob` 替换、非字符串 `blob` 不替换、原值不被就地改写 |
| §2 紧凑 JSON | 字典+列表无空格、字符串带引号、布尔小写、空 → `null`、非 ASCII 不转义 |
| §3 渲染结果 | 单块 / `type=="text"` / 前缀与紧凑体**逐字**相等 / blob 出历史（占位文本整串比对） |
| §4 元数据 | 三工具名**及顺序**、识别/非识别、三条描述与三个方法逐字 |
| §5 参数模式 | 列表类 `required==["server"]`、`server`/`cursor` 描述逐字；读取类 `required==["server","uri"]`、`uri` 描述逐字 |
| §6 请求构造 | 无光标 / 带光标 / 模板方法 / 读取请求 / 无参数 / **光标为空时省略** / 未知工具名抛错 |
| §7 系统提示段 | 空表不渲染（`""`）；`["zeta","alpha"]` → **升序**且整段文案逐字 |
| §8 不可用文案 | 逐字 |
| §9 装配与端到端 | 假注册表收到 3 个定义（名/描述/参数）、`execute(参数)` → 请求字典正确 → 渲染块表逐字、桩调用计数正确、可重复调用 |

### 3.2 既有 MCP 用例回归

```
examples/test_mcp.light        rc=0
examples/test_mcp_http.light   rc=0
examples/test_R51_image卸载.light  rc=0
examples/test_R51_mcp资源.light    rc=0
---- 失败 0 / 共 4 ----
```

---

## 4. 回归

- **examples 全量门禁**（`pytest tests/test_回归.py -q -rf -n 4`）：**4 failed, 412 passed**，
  4 条红全部是**存量词法红**（`test_R22_嵌入关键字冗余验证` / `test_R26_词首并入反向` /
  `test_R26_词首并入混合` / `test_R27_词首并入反向`，均无 import、与本轮改动面零交集），**新增 0 条红**。
  详见任务1报告 §5.1。
- **MCP 面既有用例**：`examples/test_mcp.light` rc=0、`examples/test_mcp_http.light` rc=0。
- 本轮改动面：`src/mcp客户端.light` **仅追加**「v2 资源域」段（既有类/函数一行未动），
  `examples/` 新增 1 个用例。

---

## 5. 结论

上游 `mcp-resources` 的**全部纯逻辑面**（结果渲染的二进制出历史策略、三工具的参数模式与请求构造、
系统提示段、作用域不可用文案）已逐字/逐字段对齐并落测；
宿主面（Cordis Service / 作用域分层 / 工具注册生命周期 / 真实连接）维持登记不移植。
既有 MCP 用例零回归。验收标准第 2 项达成。
