# 第17轮 lightharness · MCP v2 深化（streamable-http + 重连 + 图片投影）—— 交付报告

> 仓库：`g:\dswork\duan-light-merge\lightharness`
> 承接：第 15 轮 MCP v1（stdio 传输）落地。本轮按用户指示深化 v2：streamable-http、重连策略、图片块投影。
> 日期：2026-08-28

---

## 1. 本轮目标

MCP v1 边界（仅 stdio、串行、无重连、文本投影）深化为 v2：
1. **streamable-http 传输**：对齐原版 StreamableHTTPClientTransport，支持 HTTP JSON-RPC
2. **重连策略**：请求失败/服务器退出时自动重连（指数退避）
3. **图片块投影**：tools/call 返回 image 块时投影为可识别文本，不再是"未支持"占位

---

## 2. 实现

### 2.1 streamable-http（`MCPHttpClient` 类，追加到 `src/mcp客户端.light`）
- 构造：`(URL, 服务器名, 请求头=空)`，支持 Authorization 等请求头
- `连接()`：initialize 握手 → notifications/initialized 通知（同 stdio 版协议）
- `请求(方法, 参数)`：POST JSON-RPC 到 URL → `解析响应(响应体)`
- `解析响应`：支持两种响应格式——
  - **SSE**：逐行找 `data:` 前缀，提取 JSON（兼容 `[DONE]` 哨兵）
  - **直接 JSON**：整体解析
- `列工具()` / `调用工具(名字, 参数)` / `提取文本(结果)`：同 stdio 版逻辑（v2 图片投影）
- `关闭()`：HTTP 无状态，空操作（幂等）
- 顶层 `注册MCPHTTP服务器(注册表, URL, 服务器名, 请求头=空)`：连接+发现+注册（命名 `mcp__<服务器名>__<原始名>`）

### 2.2 重连策略（`MCP客户端` stdio 类增强）
- 新增属性：`最大重连次数`(默认 3)、`重连退避秒`(默认 1.0)、`重连次数`(0)
- `请求(方法, 参数)`：写入失败或等响应返回"服务器已退出"/"写入失败"时，调 `尝试重连()`，成功后递归重试请求
- `尝试重连()`：关闭现有连接 → 指数退避（`退避秒 × 2^(重连次数-1)`，循环计算避用 `^`）→ 重置状态 → 重新 spawn + 握手 → 返回是否成功
- 超过最大重连次数返回错误，不无限重试

### 2.3 图片块投影（`提取文本` v2）
- text 块：原样拼接
- **image 块**：投影为 `[图片 <mimeType>: <data预览>]`（data 截断 80 字符 + `...`），不再是"未支持"占位
- 其余块（audio/resource 等）：仍为 `[MCP <type> 块未支持]` 占位
- stdio 版和 HTTP 版的 `提取文本` 同步更新

### 2.4 光明语言坑记录
- `转字符串()` 返回原生 Python str，**没有 `.取子串()` 方法** → 改用 Python 切片 `[a:b]` / `[a:]`
- `^` 不是光明支持的字符 → 指数用循环乘法计算

---

## 3. 验证

### 3.1 HTTP 测试服务器（`examples/mcp_http服务器.py`）
- Python http.server 实现，监听 127.0.0.1:18765（可参数化端口）
- 工具：echo(text) / add(a,b) / **get_image()**（返回 image/png 块，用于图片投影测试）
- 独立验证（`_verify_http.py`）：initialize/tools/list/echo/add/get_image 全部正确 ✓

### 3.2 `examples/test_mcp_http.light`（PASS）
- 启动本地 HTTP 服务器（subprocess 后台）→ 等待就绪
- MCPHttpClient 连接握手 ✓
- tools/list 发现 3 个工具 ✓
- tools/call echo → "hello http mcp" ✓
- tools/call add(7,8) → "15" ✓
- tools/call get_image → 返回 `[图片 image/png: iVBORw0KGgo...]` ✓
- 顶层 `注册MCPHTTP服务器` → 注册 3 个工具（mcp__srv__echo/add/get_image）✓
- 关闭客户端 + 终止服务器

### 3.3 反跑判据
- 把工具数断言 3 改 4 → EXIT=1（红）✓

### 3.4 回归
- stdio 版 `test_mcp.light` 不回归（v2 修改不影响正常流程）✓
- pytest 全量门禁 → **69 passed 全绿**（test_mcp_http 纳入，68→69）

---

## 4. 文档
- `对标清单.json` #16：`done` → `done(v2: streamable-http+重连+图片投影)`，证据补 test_mcp_http/mcp_http服务器，目标/反跑判据更新
- `README.md`：MCP 描述更新为 v2（双传输+重连+图片投影）

---

## 5. 已知遗留 / 边界

1. **streamable-http v2 简化**：无 SSE 长连接（每次请求独立 POST）、无会话 cookie 透传、无 server-initiated 请求/通知分派。原版完整 streamable-http 需先 GET /sse 建立流再 POST /message，留待后续。
2. **重连仅 stdio 版**：HTTP 版无状态，重连意义不大（每次请求独立）；stdio 版重连已实现。
3. **图片投影为文本描述**：非真实图片附件（原版 image 块可存为附件并在 UI 渲染），v2 仅文本投影足以让 LLM 感知图片存在。
4. **长名规范化**：原版超 64 字符或含非法字符时追加 SHA-256 截断哈希，本轮仍仅干净路径（`mcp__server__raw`），留待后续。

---

## 6. 复跑方式

```powershell
Set-Location G:\dswork\duan-light-merge\lightharness
python 运行.py examples/test_mcp.light        # stdio 版（不回归）
python 运行.py examples/test_mcp_http.light   # HTTP 版（v2 三特性）
python -m pytest tests/ -q                     # 回归门禁（69 passed）
```
