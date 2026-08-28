# 第15轮 lightharness · P2 生态层启动——MCP 客户端 —— 交付报告

> 仓库：`g:\dswork\duan-light-merge\lightharness`（独立 git 仓库）
> 承接：P0/P1 15 项全部 done（第 14 轮深化收口后）。本轮按用户指示**启动 P2 生态层**，首个模块落地 MCP 客户端。
> 日期：2026-08-28

---

## 1. P2 生态层启动规划

原版 `packages/` 生态模块探查结果，选定先做 **MCP 客户端**：

| 原版包 | 模块 | 选定理由 |
|---|---|---|
| **mcp/mcp-client** | MCP 客户端 | 生态层核心（连接外部工具的标准协议）、原版结构清晰（transport/connection/tools）、可离线验证（本地 MCP 服务器）→ **本轮落地** |
| subagent/ | 子智能体（多 agent） | 依赖 agent-loop，押后 |
| code-runtime/ | 代码执行运行时 | 依赖沙箱体系，押后 |
| e2b/ | e2b 云沙箱 | 需外部服务，押后 |
| feedback/ + interaction/ | 反馈收集 / 用户审批 | 轻量，可后续批量做 |
| apps/web | Web UI | 前端，押后 |

---

## 2. 本轮落地：MCP 客户端（#16 done）

### 2.1 实现（`src/mcp客户端.light`）
- **传输**：stdio——spawn 子进程 + JSON-RPC 2.0 over 逐行 JSON（复用 subprocess 管道 + 读线程缓冲，读循环/关闭 幂等设计对齐 `终端.light`）
- **协议**：初始化握手（`initialize` 等响应 → `notifications/initialized` 通知）；`tools/list` 发现工具；`tools/call` 调用（参数字典、`isError` 语义、超时）
- **工具集成**：注册进本地 `工具注册表`，命名 `mcp__<服务器名>__<原始名>`（对齐原版 `publicToolName` 干净路径）；执行函数用**光明嵌套段落闭包**把 `客户端+原始名` 绑进每个工具（本轮新验证的光明能力）
- **结果投影**：text 块拼接为文本（对齐原版 `extractText`），image/audio/resource 块降级为占位文本
- **顶层入口**：`注册MCP服务器(注册表, 命令, 参数表, 服务器名)` → `{客户端, 已注册}`，调用方可用 `注册表.注销(公开名)` 反注册
- **边界（v1）**：仅 stdio（streamable-http/SSE 押后）、串行请求一次一个在途、无重连策略（原版 reconnect 押后）

### 2.2 验证
- **本地 MCP 测试服务器** `examples/mcp_服务器.py`（Python 标准库实现，2 个工具 echo/add，协议已独立验证）
- `examples/test_mcp.light` → **PASS**：连接握手 + 发现 2 工具 / 注册命名正确 / 经注册表调用 echo→"hello mcp"、add(2,3)→"5" / 注销能力
- **反跑判据**：把 echo 期望改 `nope` → EXIT=1（红）✓
- pytest 回归门禁 → **69 passed 全绿**（新增 test_mcp 纳入，无副作用）

### 2.3 文档
- `对标清单.json` 新增 **#16 MCP 客户端**（状态 done，证据含 src/测试/服务器脚本，反跑判据注明）
- `README.md`：P2 生态层描述更新（mcp 客户端已落地，其余押后）

---

## 3. 光明语言新验证能力（本轮收益）

MCP 工具执行需要「每工具绑定各自 rawName 的回调」。本轮验证光明**嵌套段落闭包**可行：
`造绑定执行(前缀)` 返回内层段落函数并捕获外层参数，多个绑定实例互不干扰（`_probe_closure2` 探针：echo绑定/add绑定 各自捕获不同前缀）。这是 P2 生态层（尤其 subagent 回调、feedback 钩子）的地基能力。

---

## 4. 已知遗留 / 边界

1. MCP v1 仅 stdio；streamable-http、重连策略、并发通知分派留待后续。
2. 工具结果只投影文本块；图片/音频/资源块降级为占位文本（原版有完整 image 投影，依赖附件存储，押后）。
3. 命名规范化：原版超 64 字符或含非法字符时追加 SHA-256 截断哈希；本轮仅干净路径（`mcp__server__raw`），长名/非法字符规范化押后。

---

## 5. 复跑方式

```powershell
Set-Location G:\dswork\duan-light-merge\lightharness
python 运行.py examples/test_mcp.light       # MCP 客户端（连本地 mcp_服务器.py）
python -m pytest tests/ -q                   # 回归门禁（69 passed）
```
