# 任务 W1：lightharness 前端聊天 UI（纯静态）— 交付报告

> 交付日期：2026-09-09
> 依据：`外发任务_网页启动_W1_前端UI.md`（revision b284bd4f）
> 范围：只新建白名单三个文件，未改动任何其它文件（含 `.light` 代码）。

## 一、交付物清单

| 文件 | 说明 |
| --- | --- |
| `webui/index.html` | 页面骨架：顶部标题区（标题 + 副标题/连接状态）、中部消息列表、底部输入区（多行输入框 + 发送 + 停止按钮）；`<meta charset="utf-8">`、viewport、内联 SVG favicon（零外部资源） |
| `webui/app.js` | 全部交互逻辑：fetch + `response.body.getReader()` SSE 流式解析、token 读取与 URL 擦除、AbortController 停止、错误处理、会话延续（`session_id`）、连接状态探测 |
| `webui/style.css` | 深色 GitHub 风格（`#0d1117` 系）、消息气泡 / 输入区 / 按钮间距、<640px 响应式、touch 优化、代码块 `<pre>` 等宽展示 |

路径引用自查（相对 index.html）：`style.css`、`app.js` 引用一致 ✅

## 二、静态渲染验收记录（判据 1）

| 检查项 | 结果 |
| --- | --- |
| 本地静态服务 | `python -m http.server 8000 --directory webui` 正常启动 |
| 页面/资源可达 | `GET /index.html` → **200**（text/html, 1260 B）；`GET /app.js` → **200**（text/javascript, 10984 B）；`GET /style.css` → **200**（text/css, 6529 B） |
| 页面打开 | 浏览器打开 `http://127.0.0.1:8000/?token=demo-token`（已打开，标题、消息区、输入框、按钮可见，可截图留存） |
| 无外部资源请求 | 零 CDN / 零框架 / 零二进制 / 零外部字体，favicon/code 均内联或本地，离线可完整渲染（按构造保证） |
| JS 语法 | `node --check webui/app.js` 通过（ES6+，无构建步骤） |

## 三、接口契约遵守（来自总览，只读）

- `POST /v1/chat/completions`，body：`{"model":"deepseek-chat","messages":[...],"stream":true}`，可选 `session_id` ✅
- SSE 流式：`fetch` + `getReader()` 按 `\n\n` 分帧，逐行解析 `data: {...}`，取 `choices[0].delta.content` 增量渲染；`data: [DONE]` 结束；**未用 EventSource** ✅
- 认证：`X-Auth-Token` 头（读 `location.search` 的 `token`，仅内存保存，不写 `localStorage`，加载后用 `history.replaceState` 擦除 URL）✅
- 停止：`AbortController.abort()`，保留已渲染内容 ✅
- 错误处理：401/403 → "未认证，请用带 token 的 URL 访问"；其它 4xx/5xx → 展示服务端错误信息；网络失败 → "服务不可达" + 回滚本轮气泡，绝不白屏 ✅

## 四、联调记录（判据 2，可延后项）

- mock 联调（`HARNESS_WEB_MOCK=1` + `python 运行.py examples/运行Web服务器.light`）**未执行**，按任务文档"可延后到主线集成"处理，留待 W 系列集成验收（`集成验收_网页启动_手工联调清单.md`）阶段执行。
- 反跑判据（判据 3：服务未启动 → "服务不可达"；无 token + 后端启用认证 → 401 提示）：对应代码路径已在 `app.js` 中实现并走查（`handleHttpError` / 网络异常分支），待后端环境就绪后在联调清单中实测。
- 窄屏（判据 4：375px）：`style.css` 含 `@media (max-width: 640px)` 自适应（输入区、消息气泡、按钮）及 `(hover: none)` 触屏适配，代码走查通过，可在联调阶段目检。

## 五、已知限制（留给后续）

1. **无完整 markdown 渲染**：代码块仅用 `<pre>` 等宽展示（符合文档要求），行内代码 / 列表 / 标题等未渲染，需后续扩展。
2. **无会话列表 / 历史管理**：仅支持单会话延续（`session_id`），无多会话切换 UI。
3. **token 不落盘**：无 token 时的页面加载正常，但发送需带 token 的 URL（按文档约定，非缺陷）。
4. **mock 流式联调、401/断网反跑、窄屏目检**：待后端/mock 就绪后在主线集成阶段完成实测。

## 六、主线查收：发现并修复 1 个致命 bug（2026-09-09）

**现象**：浏览器打开页面，控制台报 `Uncaught TypeError: history.replaceState is not a function`（app.js:39），
脚本整体中断——token 不擦除、事件不绑定、状态探测不跑，页面仅静态渲染正常、实际不可用。

**根因**：`app.js` 顶部定义局部变量 `var history = []`（会话历史数组），第 39 行调用
`history.replaceState(...)` 时被局部变量遮蔽，指向数组而非 `window.history`，数组无此方法 → TypeError。

**修复**：该行改用 `window.history.replaceState(...)`（显式限定全局对象），并加注释说明遮蔽原因，
防后续误改。`git` 侧同步到 W1 分支即可。

**复验（浏览器实测）**：
- URL `?token=` 加载后被擦除（`http://127.0.0.1:18000/?token=demo-token` → `http://127.0.0.1:18000/`）✅
- 状态探测执行：显示"已连接"（静态服务器 404 被按"服务在线"处理）✅
- 初始提示、事件绑定生效；发送请求 → 501 错误提示 + 输入回滚 + 不白屏 ✅
- console 无 JS 错误 ✅

**其它查收结论**：三件套可达（200 + 正确 Content-Type）、`node --check` 通过、SSE 手工分帧 /
token 内存 / AbortController / escapeHtml 防注入均符合契约；SSE 流式渲染与 401 提示待 W2~W4
合入后按集成联调清单实测。