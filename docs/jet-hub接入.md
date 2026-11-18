# jet-hub 接入（本地提供商枢纽）

> 适用：lightharness 想和 DeepSeek Harness（DSH）一样，用 **jet hub 插件**（npm 包
> `dsh-providers-hub`，旧名 `dsh-codearts-auth`）背后的账号池来跑模型。

---

## 1. jet hub 是什么（读这一节就够了）

DSH 的 jet-hub 插件把十几个 AI 编码提供商的账号（codearts / trae / buddy / workbuddy /
zcode / raccoon / opencode / aggregate …）聚合成一个**本地 OpenAI 兼容网关**：

| 项 | 值 / 规则 |
|---|---|
| 监听地址 | `127.0.0.1:8326`（`DSH_OPENAI_GATEWAY_HOST` / `DSH_OPENAI_GATEWAY_PORT` 可改） |
| 网关密钥 | `<DSH_HOME>/openai-gateway/api-key`，43 位 base64url；`DSH_OPENAI_GATEWAY_API_KEY` 可覆盖 |
| 模型目录 | `GET /v1/models`，`id` 形如 `provider/model`（如 `codearts/GLM-5.2`） |
| 对话 | `POST /v1/chat/completions`，支持 `stream:true` 的 SSE |
| 账号态 | `<DSH_HOME>/jet-hub/state.json`（账号、禁用模型、网关开关） |

lightharness 不重写账号登录/签到（那是 DSH 插件的活），只消费这个网关 —— 与 DSH 自己
调 `llm` 服务是同一份模型目录、同一套 `provider/model` ID。

> 实测（2026-11-18，Windows 本机 DSH Desktop）：`/v1/models` 返回 **104 个模型 / 12 个提供商**，
> 推荐模型 `deepseek-official/deepseek-flash`。FreeBSD 192.168.0.88 上同样可用（见 §5）。

---

## 2. 几种用法

### 2.1 只看目录：`HARNESS_CMD=jet-hub`

```bash
# Windows PowerShell
$env:HARNESS_CMD='jet-hub'; python 运行.py examples/运行CLI.light
```

输出：网关地址与来源、密钥「有没有 + 来源」（**不回显明文**）、按提供商分组的全部模型、推荐模型。

### 2.2 直接跑 agent：`HARNESS_PROVIDER=jet-hub`

```bash
$env:HARNESS_PROVIDER='jet-hub'
$env:HARNESS_MSG='请只回复两个字：收到'
$env:HARNESS_MODEL='codearts/GLM-5.2'   # 可省；也可写裸模型名 GLM-5.2
python 运行.py examples/运行CLI.light
```

执行顺序：`HARNESS_PROVIDER=jet-hub` → 自动发现地址/密钥 → 拉 `/v1/models` → 选模型
→ 组装完整 `.../v1/chat/completions` 端点与 `客户端`。优先级**高于** `.env`（显式选择优先）。

Web 服务同理：

```bash
$env:HARNESS_PROVIDER='jet-hub'; $env:HARNESS_WEB_NO_OPEN='1'
python 运行.py examples/运行Web服务器.light
```

枢纽不可用时只警告并回落 `.env`，不拒绝启动 Web。

### 2.3 Web 设置页一键切换

「设置 → 模型」页顶部有一张 **jet-hub（本地提供商枢纽）** 卡片：

- 点「刷新」→ `GET /api/settings/providers/jet-hub` 探测（地址 / 密钥来源 / 模型数）；
- 下拉按提供商分组列出全部模型（默认选中推荐模型）；
- 点「使用此模型」→ `POST /api/settings/providers/jet-hub/apply`：
  写 `.env` 三行（`OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL`）并**热更新**客户端，无需重启。

接口形状：

```jsonc
// GET /api/settings/providers/jet-hub（⛔ 永不返回密钥明文）
{"可用": true, "地址": "http://127.0.0.1:8326/v1", "地址来源": "…",
 "有密钥": true, "密钥来源": "文件 C:\\Users\\…\\openai-gateway\\api-key",
 "模型": [{"id": "codearts/GLM-5.2", "名称": "GLM-5.2 · x0.7", "提供商": "codearts", "上下文窗口": 202752, "输入": ["text"]}],
 "总数": 104, "推荐": "deepseek-official/deepseek-flash", "错误": ""}

// POST /api/settings/providers/jet-hub/apply  body {"模型": "codearts/GLM-5.2"}（键名也接受 model）
{"ok": 1, "message": "已切换到 jet-hub 模型", "模型": "codearts/GLM-5.2", "地址": "…", "config": {…}}
```

### 2.4 chat 框下方：每个会话单独选模型（对齐 DSH）

输入框下方新增模型选择器：`◈ 模型名` = 本会话显式选择；`◇ 模型名` = 跟随全局 `.env`（名字显示全局模型）。
点开按「来源 · 提供商」分组列出 **内置 4 个 + jet-hub 全部模型**，选中即生效——**只影响当前会话**，
其它会话/新会话不受影响；列表首项「跟随全局默认」把该会话还原为跟随。

- 服务端权威：`GET /api/models[?session=<id>]` → `{"当前": "<生效模型>", "会话": "<会话显式选择；空=跟随全局>",
  "全局": "<.env 模型>", "模型": [{id,名称,提供商,上下文窗口,来源}]}`
  （来源 = `内置` / `jet-hub`；jet-hub 目录缓存 120 秒，`?refresh=1` 强制重拉）。
- 写入：`POST /api/sessions/<id>/model` body `{"模型": "<id>"}`（空串 = 跟随全局 `.env`）。
- 存储：`<会话根>/session-models.json`（`{会话id: 模型id}`）；`GET /api/sessions/<id>` 也回 `"模型"`。
- 每轮请求 body 带 `model`；服务端按「请求 model > 会话已存模型 > 全局配置 > 内置默认」解析，
  同端点/密钥只换 model 临时构造客户端（jet-hub 多 provider 共用一个网关）。
- 首轮新对话没带 `session_id` 时，按服务端生成的会话 id 落盘（SSE 绑定帧回的就是这个 id），
  绑定后再查 `/api/models?session=` 不会退回全局默认。

---

## 3. 环境变量与发现顺序

| 变量 | 作用 | 缺省 |
|---|---|---|
| `HARNESS_PROVIDER` | `jet-hub` = 以本地枢纽为模型来源 | 空（走 `.env`） |
| `HARNESS_MODEL` | `provider/model` 全名、裸模型名或显示名 | 模块推荐 |
| `JET_HUB_BASE_URL` | 显式整址（可只写到端口，自动补 `/v1`） | — |
| `JET_HUB_API_KEY` | 显式网关密钥（优先于文件） | — |
| `DSH_OPENAI_GATEWAY_HOST` / `_PORT` | 与 DSH 同名，改监听地址/端口时同步 | `127.0.0.1` / `8326` |
| `DSH_OPENAI_GATEWAY_API_KEY` | 与 DSH 同名，网关密钥 | — |
| `DSH_HOME` | DSH 主目录（找 `openai-gateway/api-key`） | `~/.dsh` |

地址：`JET_HUB_BASE_URL` > `DSH_OPENAI_GATEWAY_HOST/PORT` > 默认。
密钥：`JET_HUB_API_KEY` > `DSH_OPENAI_GATEWAY_API_KEY` > `<DSH_HOME>/openai-gateway/api-key`。

密钥形状校验与插件一致：**43 位 `[A-Za-z0-9_-]`**；文件内容异常时只报「格式异常」，不静默换 key。

---

## 4. 安全边界

- 网关默认只绑 `127.0.0.1`；跨机使用需在 DSH 设置页打开「允许局域网访问」，
  或显式设 `JET_HUB_BASE_URL`（此时是你自己承担暴露面）。
- 本仓所有面板/日志返回都**不含密钥明文**；只有 `构造接入`/`解析密钥` 这两个显式出口带明文，
  且只直接喂给 `客户端`。
- 「使用此模型」会把 `.env` **覆盖式**写成三行（与既有 `POST /api/config` 行为一致）；
  自定义的 `.env` 其他行请事先备份。

---

## 5. 联调记录

### Windows（本机 DSH Desktop，2026-11-18）

1. `GET /v1/models`（Bearer 网关密钥）→ 200，104 个模型。
2. `POST /v1/chat/completions`（`deepseek-official/deepseek-flash`，非流式）→ `OK`。
3. `HARNESS_CMD=jet-hub` → 列出 12 个提供商、104 个模型。
4. `HARNESS_PROVIDER=jet-hub` 跑单轮 → `--- jet-hub 接入: http://127.0.0.1:8326/v1/chat/completions  模型: deepseek-official/deepseek-flash ---`，回复「收到」。
5. Web：`GET /api/settings/providers/jet-hub` → 可用 / 104 模型 / 推荐正确；
   `POST .../apply {"model":"codearts/GLM-5.2"}` → 200，`/api/config` 热更新为
   `codearts/GLM-5.2` + `http://127.0.0.1:8326/v1/chat/completions`。
6. **会话级模型选择（Playwright 实拍，2026-11-18）**：
   - `GET /api/models` → 108 个（4 内置 + 104 jet-hub），当前 = `deepseek-official/deepseek-flash`；
   - chat 框下 ◈ chip 显示 `DeepSeek-V4.1-Flash`，点开 popover 109 项（含「跟随全局默认」）；
   - 选 `codearts/GLM-5.2` → chip 与顶栏徽标变为 `GLM-5.2 · x0.7`；
   - 发「请只回复两个字：收到」→ 真回复「收到」，统计按 GLM-5.2 记账；
   - 新建会话 → chip 回到 `DeepSeek-V4.1-Flash`（该会话无记录 → 跟随全局）。

> 注意：网关**冷启动**第一次拉目录可能超过 5 秒（要逐个 provider 建目录），本仓探测超时设为 15 秒。

### FreeBSD 192.168.0.88（DSH `web` profile + `dsh-providers-hub` 2.20.261109）

环境：`skywalk` 运行 DSH，网关 `127.0.0.1:8326`，密钥在 `/home/skywalk/.dsh/openai-gateway/api-key`；
lightharness 树放在 `/tmp/lh_jet`（只读），可写副本 `/tmp/lh_srv`，编译器用仓库自带 `light-merge`
（`LIGHT_MERGE=/tmp/light-merge`，`LIGHTPLUGIN=/tmp/lightplugin`）。

1. `HARNESS_CMD=jet-hub` → **可用，71 个模型 / 7 个提供商**（deepseek-official / codearts / buddy /
   raccoon / opencode / aggregate / jet-hub-auto），推荐 `deepseek-official/deepseek-flash`。
2. `HARNESS_PROVIDER=jet-hub` + `HARNESS_MODEL=deepseek-official/deepseek-flash` 单轮 →
   `--- jet-hub 接入: http://127.0.0.1:8326/v1/chat/completions  模型: deepseek-official/deepseek-flash ---`，
   回复「收到」。
3. 反向验证：`opencode/deepseek-v4.1-flash-free`（账号已失效）→ 现在报
   `上游错误: opencode: HTTP 401 — {"error":{"type":"authentication_error","message":"Invalid credential"}}`，
   而不是之前的「空完成 [EMPTY_RESPONSE]」。
4. Web：`GET /api/settings/providers/jet-hub` → 可用 / 有密钥 / 模型目录正确；
   `POST …/apply {"model":"codearts/GLM-5.2"}` → 200，`.env` 写成
   `OPENAI_BASE_URL=http://127.0.0.1:8326/v1` + `OPENAI_MODEL=codearts/GLM-5.2`。

踩到并修掉的坑：

- **空串 `DSH_HOME` 必须归一成 `空`**：`主目录路径.解析主目录` 的「配置为空则取默认」判定对 `""` 不成立，
  直接传空串会解析出空路径。Windows 上因为进程继承了 `DSH_HOME` 掩盖了这个坑，FreeBSD 干净环境一跑就暴露。
- **网关冷启动可能 > 5s**（逐个 provider 建目录），探测超时统一设 15s。
- 以 `workbuddy` 跑时要读 `skywalk` 的密钥：用 `sudo -u skywalk`（HOME 跟着变）或把密钥经
  `JET_HUB_API_KEY` 注入；`/home/skywalk` 是 700，不要指望普通用户直读。
- Web 入口的「项目根」由 `sys.argv[0]` 推导（`light/..`），所以 Web 测试要在**可写的工作目录/副本**里跑，
  否则会在只读树上创建 `data/sessions` 失败（与 jet-hub 接入无关）。

---

## 6. 与 DSH 插件的差异（如实登记）

| 项 | DSH jet-hub 插件 | 本仓 |
|---|---|---|
| 账号登录 / 签到 / 额度领取 | 有（插件 UI） | **不做**，仍由 DSH 插件负责 |
| 模型目录 | 宿主 `llm.listModels` | `GET /v1/models`（同一套 ID） |
| 账号池内部路由（aggregate/降级） | 插件内决定 | 网关决定，本仓不干预 |
| 网关密钥保存 | `<DSH_HOME>/openai-gateway/api-key` | 同文件；接入时写进本仓 `.env` |

---

## 7. 代码位置

| 文件 | 职责 |
|---|---|
| `src/提供商枢纽.light` | 地址/密钥发现、模型目录解析、挑选、接入配置、探测（唯一权威） |
| `src/总入口.light` | `jet-hub` 子命令 + `HARNESS_PROVIDER=jet-hub` 的 run 分支 |
| `src/客户端.light` | 识别网关的 SSE 错误帧（`{"choices":[],"error":{…}}`），报可读上游错误 |
| `src/web服务器.light` | `GET /api/settings/providers/jet-hub`、`POST …/apply`；`GET /api/models`、`POST /api/sessions/:id/model`（会话级模型） |
| `examples/运行Web服务器.light` | Web 启动时的 `HARNESS_PROVIDER=jet-hub` 装配 |
| `webui/app.js` / `index.html` / `style.css` | chat 框下「每会话模型选择器」 |
| `webui/settings.js` / `settings.css` | 模型页 jet-hub 卡片 |
| `examples/test_提供商枢纽.light` | 离线自测（地址/密钥形状/目录解析/挑选/接入/缺省主目录） |
| `examples/test_客户端_网关错误.light` | 离线自测（正常帧出块 / error 帧抛可读错误） |
| `examples/test_会话模型选择.light` | 离线自测（目录/会话模型读写/首轮落盘/清空跟随全局） |