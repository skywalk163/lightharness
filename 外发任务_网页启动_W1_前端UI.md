# 外发任务 W1：lightharness 前端聊天 UI（纯静态）

> 定位：本任务是 "lightharness 网页启动" 四路并行中的 
>
> **W1 前端**
>
> 。后端 API 已可用
> （
>
> `POST /v1/chat/completions`
>
>  \+ SSE 流式，见 
>
> `总览.md`
>
>  契约 1~6），本任务只产出
> **静态前端文件**
>
> ，不碰任何 
>
> `.light`
>
>  代码。
> 交付后体验目标：浏览器打开页面 → 输入 "你好"→ 发送 → agent 回复
>
> **逐字流式**
>
> 渲染出来。

## 白名单文件（只新建这三个，不许动任何其它文件）



* 新建 `webui/index.html`

* 新建 `webui/app.js`

* 新建 `webui/style.css`

（`webui/` 是仓库根下新目录，与 `运行.py` 同级。目录不存在就创建。）

## 功能要求



1. **页面结构**（index.html）：

* 顶部：标题 "lightharness"，副标题显示服务地址与连接状态（已连接 / 未认证 / 服务不可达）。

* 中部：消息列表（用户消息右侧气泡、助手消息左侧气泡）。

* 底部：多行输入框 + 发送按钮 + 停止按钮。

1. **交互**（app.js）：

* 发送：`fetch POST /v1/chat/completions`，body `{"model":"deepseek-chat","messages":[...],"stream":true}`，

  携带 `X-Auth-Token` 头（token 来源见第 3 点）。

* **SSE 流式解析**：用 `fetch` + `response.body.getReader()` 按 `\n\n` 分帧，逐行解析

  `data: {...}`，取 `choices[0].delta.content` 增量渲染到当前助手气泡；

  `data: [DONE]` 结束。**不得用 EventSource**（它只支持 GET，本接口是 POST）。

* 停止：`AbortController.abort()` 中止当前流，保留已渲染内容。

* 错误处理：401 → 提示 "未认证，请用带 token 的 URL 访问"；4xx/5xx → 显示服务端错误信息；

  网络失败 → 显示 "服务不可达"，**绝不白屏**。

* 会话延续（可选但推荐）：若响应 JSON 里带 `session_id`，保存并在下次请求的 body 里带上

  （后端已支持按 `session_id` 续写会话）。

1. **token 登录**（对齐 deepseek-harness 的 URL 带 token）：

* 页面加载时读 `location.search` 的 `token` 参数，存入内存变量；所有 API 请求带

  `X-Auth-Token: <token>` 头。

* 无 token 时：仍可打开页面（静态资源已放行），发送时后端若要求认证会返回 401，按错误处理提示。

* 不要把 token 写进 `localStorage`（本机回环场景无必要，且少一个落盘面）。

1. **样式**（style.css）：

* 深色或浅色均可，但**不要大面积 indigo/purple 配色**；简洁、无外部字体。

* 消息气泡、输入区、按钮间距清晰；移动端（窄屏 <640px）输入区与消息区自适应（参考

  light-merge `playground/static/style.css` 的响应式思路）。

* 流式输出中的代码块用 `<pre>` 等宽展示即可（不做完整 markdown 渲染，保持轻量）。

1. **零外部依赖**：不引 CDN、不引框架、不加载任何二进制资源（favicon 用内联 SVG data URI 或省略）。

   页面必须在**离线 / 断网**时也能完整渲染（静态资源全部本地）。

## 接口契约（来自总览，只读遵守，不得改动）



* 静态路由（由 W3 提供）：`GET /` → index.html、`GET /app.js`、`GET /style.css`。

* API：`POST /v1/chat/completions`（OpenAI 兼容；`stream` 支持 `true/false`）。

* 认证：`X-Auth-Token` 头 或 `?token=` query（URL 由启动器打印）。

* CORS：后端会带 `Access-Control-Allow-Origin: *`（前端本地起静态服务器联调时靠它）。

## 验收判据



1. **静态渲染**：本地 `python -m http.server` 起 `webui/`，浏览器打开 `http://localhost:8000`：

   页面完整可见（标题、消息区、输入框、按钮），无控制台报错，无外部资源请求（Network 面板零外域）。

2. **流式渲染（mock 联调，可延后到主线集成）**：lightharness mock 模式启动

   （`python 运行.py examples/运行Web服务器.light`，`HARNESS_WEB_MOCK=1`），前端页面联调发 "你好"，

   agent 回复**逐字增量出现**（不是一次性整块出现），`[DONE]` 后停止按钮恢复。

3. **反跑判据**：服务未启动时发送 → 页面显示 "服务不可达" 错误提示（非白屏）；无 token 且后端启用认证时

   发送 → 显示 401 提示。

4. **窄屏**：窗口缩到 375px 宽，输入框与消息不溢出、按钮可点。

## 语言 / 环境无关提醒（本任务不写光明代码）



* 纯 HTML/CSS/JS，UTF-8 编码，`<meta charset="utf-8">` 必须有（中文界面）。

* JS 用标准 ES6+，不要依赖构建步骤；文件按 index.html 中 `<script src="app.js">` 引用。

* 提交前自查：三个文件之间路径引用一致（`app.js`/`style.css` 相对 index.html）。

## 交付物



* `webui/index.html`、`webui/app.js`、`webui/style.css` 三个文件。

* 交付报告：页面截图（或截图路径）+ 静态渲染验收记录 + 联调记录（若已联调）+ 已知限制

  （如未做 markdown 完整渲染、无会话列表 —— 列出留给后续）。

## 运行通道



```
cd G:\dswork\duan-light-merge\lightharness

python -m http.server 8000 --directory webui   # 仅静态验收；API 联调需 mock 服务同时跑
```