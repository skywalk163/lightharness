# apps/web ↔ webui/ 架构对齐（第6轮 任务线 D，卡 #275）

> 上游锚点：0.2.0-rc.1（e5b5ccbfcb，与 R103/R104 同锚）。
> 范围：上游 `apps/web`（完整 React 客户端）vs lightharness `webui/`（零依赖原生 JS，无构建链）。
> 原则：不引入 React/打包链，用原生 ES6 模块对齐功能点；后端契约只读遵守 `src/web服务器.light`。

## 1. 模块逐点比对

| 上游 apps/web 模块 | webui/ 现状 | 状态 | 说明 |
|---|---|---|---|
| 会话清单 conversation list | `sidebar.js`（GET/POST/PUT/DELETE `/api/sessions`，倒序、角标、相对时间、双击重命名、删除） | **覆盖** | 侧边栏新建/切换/重命名/删除齐备 |
| 会话恢复 session resume | `app.js selectSession()`（GET `/api/sessions/:id` 回放历史 + 同步 history） | **覆盖** | 切会话拉全量消息回放，流式中禁切 |
| 设置 settings | `app.js` config 面板 + `GET/POST /api/config`（apiKey/baseUrl/model，热更新，未保存保护） | **覆盖** | 三字段配置、未配置自动弹出、mock 模式不弹 |
| 模型/预设选择器 model & preset picker | `index.html #mode-select`（standard/cordis/ptc/minimal 四键）+ 发消息带 `body.preset` | **覆盖（本线对齐）** | 四键与后端 `是已知预设`（standard/ptc/minimal/cordis）一致；localStorage 记忆上次选择 |
| 流式渲染 streaming render | `app.js readStream()`（fetch + reader 按 `\n\n` 切 SSE，delta.content 增量，工具帧混排） | **覆盖** | 文本/工具调用/工具结果/统计/压缩/审批/会话绑定帧全识别 |
| 附件上传 attachment upload | `index.html #attach-btn` + `app.js onFiles/renderChips`（FileReader 读 dataURL，chip 可删，随 `body.attachments` best-effort 上送） | **本线补完** | 原按钮 disabled「即将支持」；本线启用多选附件选择 + chip + 请求体附件字段 |
| 斜杠命令面板 slash command palette | `slash-palette.js`（输入首位 `/` 弹候选，↑↓/Enter/Tab/Esc，七命令集对齐 `src/cli外壳.light 斜杠命令表`） | **本线补完** | 原 WebUI 无斜杠面板；本线新增纯前端浮层，选中回填输入框，/clear 触发新对话 |
| 工具调用面板 tool call timeline | `tool-card.js` + `app.js` 右面板（时间线/统计，自动展开） | **覆盖** | 工具卡片 + 时间线 + token/花费统计 |
| 审批队列 approvals | `app.js` approvals 面板（轮询 + SSE 推送，批准/拒绝） | **覆盖** | E4 已落地 |
| 权限预设 permission presets | `#perm-preset` + `GET/POST /api/permissions` | **覆盖** | 全放行/按类别/全拒绝/自定义 |

## 2. 与 B/C 线对齐

- **预设四键命中**：前端 `#mode-select` 选项值 `standard / cordis / ptc / minimal` 与 `总入口 取预设注册表`（经 `web服务器.取预设注册表(预设标识)` 缓存装配）的合法四键完全一致；`body.preset` 随每条消息上送，后端 `是已知预设` 校验通过即按挂载集装配，未知值后端报错。本线不改后端（D 独占 webui/），四键契约已对齐 C 线 `预设切换/挂载过滤`。
- **真实抓取提供（B 线）**：附件 dataURL 经 `body.attachments` 上送，后端抓取/投影出口属 B 线宿主面，前端只负责采集与展示，不伪造抓取能力。

## 3. 本线改动文件

- 新增 `webui/slash-palette.js`（斜杠命令面板）
- `webui/index.html`：启用 `#attach-btn`、加 `#attach-input`/`#attach-chips`、引入 slash-palette.js
- `webui/app.js`：附件采集/chip/随请求上送 + SlashPalette 初始化
- `webui/style.css`：斜杠面板与附件 chip 样式

## 4. 浏览器手测清单（沿用 R5 第5步 Playwright 手法，待人工/CI 跑）

1. 四预设切换：`#mode-select` 选 standard/cordis/ptc/minimal，下一条消息起系统提示「已切换…」，localStorage 记忆。
2. 会话恢复：左侧新建会话 → 发一轮 → 侧边栏点回旧会话 → 历史消息完整回放。
3. 附件上传：点 📎 选文件 → 输入框上方出现 chip → 可点 × 移除 → 发送后 chip 清空。
4. 流式输出：发送消息 → 助手气泡逐字流式、工具调用出现在右侧面板。
5. 斜杠面板：输入框敲 `/` → 弹出七命令列表 → ↑↓ 高亮、Enter 选中回填、Esc 关闭；选 `/clear` 触发新对话。

> 注：真实 LLM 联调需 `DEEPSEEK_API_KEY`；纯前端行为（面板弹出/chip/回放）可在 mock 模式下验证。
