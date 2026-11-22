# 更新日志

本项目的所有值得记录的变更都写在这里。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号以轮次发布 tag 为准（如 `r95-dev`）。

## [未发布] — 2026-11-23

### 模式分层：Agent 模式（4）与工作方法（4）分开呈现 + 运行轮数上调（T-0439）

- `src/预设组合.light`：`组合清单()` 每个条目新增 `类别`（`agent` / `method`）；新增
  `预设类别()` / `是代理模式()` / `是工作方法()` / `预设分组()`；`预设清单()` 新增可选
  `类别` 过滤（空串 = 全部 8 项，老调用点不用改）。类别只是呈现维度，会话里存的仍是单个预设 id。
- `src/设置页.light`：预设元数据新增 `类别` / `分组名`，新增 `造分组名()` 与 `预设分组按序()`；
  `src/设置预设页.light` 的 `分组列表()` 从「内置 / 自定义」改为「Agent 模式 / 工作方法 / 自定义」。
- `webui/`：主输入区下拉、新会话面板、设置页三处都按两组渲染（`<optgroup>`），值仍是单个预设 id。
- `src/步数上限.light`：单轮步数缺省 `25 → 96`（唯一真相仍是 `步数缺省`）；`src/代理.light`
  属性缺省改为从 `步数缺省` 取，不再抄第二份常量；
  `src/目标续跑.light`：`续默认最大轮数 8 → 64`（单目标 `maxGoalRounds` 仍可覆盖）。
  环境覆盖仍走 T-0425 的 `解析最大步数`（请求 > `HARNESS_MAX_STEPS` > 缺省，1..1000）。
  参考 DSH `tool-ralph` 的 `maxRounds` 默认 256，本仓一轮成本更高，故取 64。
- `docs/功能对标/模式规格.md` 增「0.1 分层」「0.2 轮数预算」两节；`docs/配置参考.md` 记
  `HARNESS_MAX_STEPS`；新增判据 `tests/test_T0439_模式分层与轮数.py`。

### 流式输出时允许切换会话：先中止当前流再切换（T-0422）

- `webui/app.js`：`selectSession` 与 `new-session-btn` 的 streaming 分支不再「弹提示 return」，
  改为先 `abortActiveTurnForSwitch()` 收口本轮再走「拉历史 + 回放」；同会话仍早返回不误伤。
- 新增 `abortActiveTurnForSwitch()`：`turnEpoch += 1` → 摘除并清空 `localQueue`（文本放回输入框，
  不静默吞字）→ `finalizeTurn()`（保留已渲染内容）+ `setStreaming(false)`（去 streaming class、
  停本地计时、放开按钮）→ `controller.abort()`。
- **abort 竞态（世代号 epoch）**：`sendMessage` 发起时快照 `myEpoch`，`resp.ok` 判定、`then`、
  `catch`（含 AbortError）、`finally` 全部先比对 `isTurnAlive(myEpoch)`，对不上就静默放弃；
  `readStream(resp, epoch)` 在 `handleFrame`/`pump` 同样校验，切走后残留 SSE 帧一律丢弃。
- **队列取舍**：切走时整队清空——老会话的排队消息不发到新会话；文本拼回输入框（输入框为空时），
  提示「N 条排队消息已放回输入框」。用户主动中止仍走 `AbortError → finalizeTurn`，不碰 `rollbackTurn`。
- 提示「已停止当前输出并切换会话。」由 `announceStreamAborted()` 在渲染完成之后发出
  （`renderHistory`/`newChatState` 会清屏，提前发会被吃掉）。
- 新增 `tests/test_T0421_流式切换会话.py`（7 passed）；`node --check webui/app.js` / `messages.js` 通过。
- 未动 `src/*.light`、`sidebar.js`、`messages.js`、`index.html`。

### 判据文件号对齐：T-0408 测试改名（T-0421）

`tests/test_T0410_会话读取三个缺陷.py` 更名为 `tests/test_T0408_会话读取三个缺陷.py`
（判据文件号与卡号对齐；T-0410 是 lightmem 的另一张卡）。用例、断言与 fixture 未变。
同步修正引用：`docs/API参考.md`、`tests/test_T0399_新会话对齐.py`、
`docs/功能对标/对标清单.json` 中 T-0408 证据路径。下文 T-0408 历史条目保留旧名作为当时记录。

### plan 模式闭环：/plan · exit_plan_mode · 投影（T-0420）

- 新增 `src/计划工具.light`：`exit_plan_mode` 工具规格 + 参数校验（空/非字典/空白计划 fail-loud，
  `title` 缺省取首个 markdown 标题、再回「计划」），回包 `concludesTurn:true`。
- `src/计划模式.light` 新增 `折叠计划状态`：把 `plan/mode` 与最后一次 `plan/submitted` 折成
  `{active,pending,text,title}`，供 HTTP 投影与前端共用。
- `src/web服务器.light`：新增 `/plan`、`/plan on`、`/plan off` 命令（不调模型、不走轮次；忙时 409），
  落 `command/run`/`command/done`/`plan/mode`；`active` 时只额外注册 `exit_plan_mode`，成功后落
  `plan/mode(false)` + `plan/submitted`；`GET /api/sessions/current` 与 `GET /api/sessions/:id` 新增 `计划` 键。
- **与 `topdown` 解耦**：计划模式不再由 `会话模式 == "topdown"` 自动打开，只认会话事件；
  `src/代理.light` 的计划模式拦写对 `exit_plan_mode` 放行。
- 提示注入：`src/预设组合.light` 的 `计划提示文本()` 取规划组 `plan-mode` section，
  `src/总入口.light` 在系统提示前置注入（人格与默认契约仍在其后）。
- 前端：`webui` 顶栏「📋 计划中」角标 + 计划面板（`applyPlanState`），SSE `种类:"计划"` 帧即时刷新；
  重启/切会话按 `计划` 键回填。
- 文档：API 参考补 `/plan` 命令面与 409；《模式规格》plan 段翻为「T-0420 已接线」并逐条列入口/出口/投影。
- 新增 `tests/test_T0420_计划模式闭环.py`（纯逻辑 + 真起服务的命令闭环 + 接线静态），
  `examples/test_计划模式.light` 补投影与出口工具判据。

### brainstorm 装配层写文件收口（T-0419）

- `src/总入口.light` 工具叶子映射：`读文件→tool-fs-read`、`写文件→tool-fs-write`。
- `src/预设组合.light`：standard / 编码(`ptc`) / 组装(`cordis`) 三张基底表把单行 `tool-fs` 拆成
  `tool-fs-read` + `tool-fs-write`；`brainstorm` 去掉写文件（只留读/搜索）。
- 判据同步：`test_T0403` 的期望行数/叶子数与断言改用新叶子名，
  `test_已知粒度缺口_写文件仍挂在tool_fs` 改名 `test_brainstorm装配层没有写文件` 并正向断言；
  `examples/test_预设组合`、`test_预设挂载过滤`、`test_设置预设页` 行数同步。
- 新增 `tests/test_T0419_工具叶子拆分.py`（映射层 + brainstorm 无写文件 + 读写落点不同）。

### 文档收口：T-0399 判据修正 + 对标台账 + 用户面文档（T-0418）

- 修 `tests/test_T0399_新会话对齐.py::test_文档与对标登记到位`：不再断言「尾部 5 条正好 #366~#370」，
  改为「编号升序无重复 + #366~#370 按编号存在 + 各自登记 T-0395~T-0399」。这条判据此前被
  T-0406 追加 #371~#376 打红（main 恒 1 failed），现已恢复；T-0399 整文件 8 passed。
- 对标清单：`#369` 销掉「待合入」；`#371~#375` 由 `partial` 翻为 `done` 并追记「接线已由 T-0407
  落地（main 41ae48a）」；`#376` 文字「#371~#375」更正为「#371~#376」；新增 `#377`（T-0407 收口接线）
  与 `#378`（T-0408 会话读取三缺陷）。现 372 条、末号 #378。
- **API 参考**：补 `/goal`、`/compact` 命令面，忙时 `202` 排队 / `429` 满队 / `409` 压缩撞车，
  `X-LH-Interrupt: 1` 插话，统计帧 `开始时刻/完成时刻/耗时秒/速率/轮次数`，索引 `完成时间`；
  新建会话的 `模式` 字段改为 8 预设（以 `预设清单()` 为准）。
- **配置参考**：补 `HARNESS_MODEL_CONTEXT_WINDOW`（32768）、`HARNESS_COMPACTION_THRESHOLD_RATIO`
  （0.75）、`HARNESS_COMPACTION_KEEP_COUNT`（10），并写明默认窗口由 128000 统一为 32768 的口径。
- **快速开始**：补 8 模式对照表与《模式规格》链接、排队/插话/计时/tok/s 的预期现象与排查；
  **docs/README** 更新条数与索引（372 条、编号至 #378；加入《模式规格》）。
- `docs/功能对标/模式规格.md`：已随 T-0407 落地的「接线在 T-0407」翻成「已接线（T-0407，main 41ae48a）」；
  plan 三项（`/plan`、`exit_plan_mode`、前端投影）如实标注「仍未接线（卡 T-0420）」；
  brainstorm 拆叶子仍标「卡 T-0419」。
- 新增 `tests/test_T0418_文档收口.py`（文档口径防漂移：判据写法、台账状态、API/配置/快速开始必含键）。

### 补记：T-0401～T-0406（纯逻辑面，接线见 T-0407）

- **T-0401 目标续跑**：`续续跑决策` 三值（续跑/完成/停止）、`续记账`/`续合并目标变更` 台账、
  默认最大 8 轮 / 无进展阈值 2；`目标` 工具规格可注册。
- **T-0402 压缩升级**：checkpoint 框架消息 + 源序号表、token 口径尾部保留（tool 配对保护）、
  注入式摘要器、结构化 `检查并压缩详情`、单一 `压缩配置解析()`。
- **T-0403 四种新模式**：`topdown`/`bottomup`/`brainstorm`/`lazy` 由标准组合行表增删叶子派生；
  `模式系统提示`/`模式终止条件`/`模式开关表`/`需开源检索` 纯逻辑；设置页元数据与帮助正文补齐。
- **T-0404 会话细节**：`时算速率`/`时格式化时刻`/`时造细节行`/`时补统计字段`/`记完成时间`；
  旧索引缺键回空不报错。
- **T-0405 会话队列**：同会话串行、插话优先于排队、空队列与并发入队不丢件。
- **T-0406 模式规格**：`docs/功能对标/模式规格.md` 6 模式 × 7 小节契约；三条硬约束按判据写死。

### 修复：会话读取三缺陷（T-0408）

- `GET /api/sessions/current` 显式 `?session=` 优先于令牌绑定（多会话标题不再串）；
- 落库 `tool-result` 与 SSE 同口径下钻 `content` 子块并回填 `工具名`/`调用id`（重放不再恒空）；
- `会话存储.保存索引` 临时文件名加 pid + 随机后缀并加进程内可重入锁（并发落盘不再互踩）。
- `tests/test_T0410_会话读取三个缺陷.py`（3 条）在 base 上 3 failed、修复后 3 passed；
  T-0399 的 strict xfail 已转正向断言。

### 收口接线：四组前置模块接进 6 个热点文件（T-0407）

- **目标续跑**：`/goal <描述>` 建会话目标 → `web服务器` 的同步/流式两条路径都改成
  「`当` 循环：跑一轮 → `续记账`/`续续跑决策`」；模型调 `目标` 工具 `complete` 后由
  `goal/change` 事件收口。`目标` 工具只在「本会话有目标」时注册（`工具注册表.执行` 会裁掉
  `变更/新状态`，故 execute 用本会话闭包落事件 + 回写台账）。
- **压缩**：`压缩配置` 进入每轮代理选项（自动压缩从死代码变活）；新增 `/compact` 服务端命令入口
  （不调模型、走 `压缩策略.压判断触发(入口=手动)` + `压缩.light.压缩到最近`），SSE 与普通回包
  都能发「压缩」事件帧；`/compact` 与并发流式请求撞车时回 409 并复用 `压缩命令` 的排队文案。
- **四种新模式**：`预设清单()` 成为 400 文案与 CLI help 的唯一来源（5 处硬编码清除）；
  `预设.模式系统提示` 在 `跑一轮` 注入 `系统提示文本`；`topdown` 每轮重设 `计划模式`；
  前端下拉由 `MODE_NAMES` 运行时补齐（index.html 只留老四项，避免两处清单漂移）。
- **会话细节**：统计帧新增 `开始时刻/完成时刻/耗时秒/速率/轮次数`；前端顶栏实时计时 +
  `tok/s`；`状态.busy` 呼吸动画；完成后 `记完成时间` 落会话库。
- **排队/插话**：会话级闸门 + 同一 `当` 循环在轮末先看续跑、再取插话、再出队；忙时普通消息
  `202`（回位置/深度/上限）、插话走 `X-LH-Interrupt` 请求头、`/compact` 409；前端流式中本地
  排队 + 「排队中 N」角标 + 「立即插话」按钮。占位归属：非流式请求在 `处理对话` 里拿，
  流式请求由 `推流实现` 在真发帧时拿、发完在 `最终` 释放——直调处理器的自测不消费流，
  因此不会被误判成排队（保留旧的串行 200 行为）。
- 新增 `tests/test_T0407_收口接线.py`（10 条，真起服务 + 脚本化 mock LLM）；
  `tests/test_流式推流接线契约.py` 同步补 3 条接线契约（后台跑一轮仍是单参、轮末才关队列、
  压缩帧/计划模式/压缩配置在位）。反证：移除 `压缩配置` 一行后自动压缩用例立红（已还原）。

### 对齐验收：新会话五件事整链（T-0399）

- 新增 `tests/test_T0399_新会话对齐.py`：**真起服务进程、真走 HTTP**（不是直调处理器方法）——
  脚本化 mock LLM（纯标准库 `ThreadingHTTPServer`，零新依赖）驱动工具调用，
  一条链验完：建会话带目录 → 首条消息带 `preset`/权限/`attachments` → 两会话不同目录+不同权限
  **并发**隔离（工具放行/拒绝各按会话）→ `/compact` 后续聊 → 切回旧会话恢复模式/权限/目录。
  共 6 条正向用例 + 2 条 `strict xfail` 缺陷钉桩（见下）。中间态反证：只合入 T-0395 时 5/6 正向用例红。
- `docs/快速开始.md` 补「新会话落地页五件事」冒烟 checklist（目录/模式/权限/附件/压缩，含预期现象与排查），
  并修正三处与实测不符的说法：`自定义` 权限预设**会**落库；`cwd/check` 接受相对路径而**建会话**不接受；
  `HARNESS_ROOT` 是「会话级设置根」，会话 JSONL 在 `$HARNESS_HOME/sessions`（原表把两者混为一谈）。
- `docs/API参考.md` 补 `POST /api/sessions` 新字段、`GET /api/cwd/check`、`GET /api/sessions/current` 新键、
  `POST /api/sessions/:id/模式权限`、`POST /v1/chat/completions` 的 `preset/权限预设/工作目录/attachments`，
  并新增「落库消息形状与已知缺口」「流式下的差异」两节。
- `docs/功能对标/对标清单.json` 末尾追加 #366~#370（T-0395~T-0399，旧条目与旧编号未动）。
- 本卡只改测试与文档，**不改业务代码**。走这条整链新暴露的业务缺陷已按红线单独开卡，本卡只如实
  文档化 + 用 `strict xfail` 钉住（修好后钉桩会变红，提醒改回正向断言）：
  1. `GET /api/sessions/current` 带认证令牌时忽略 `?session=`，返回该令牌最后创建的那个会话
     —— 受影响的是前端 `refreshSessionTitle()`（多会话会取到错标题）；
  2. 落库的 `tool-result` 消息 `结果` 恒为空串（事件层 `tool/result` 里有正文，落库路径只扫顶层
     `type=="text"`，扫不到嵌套的 `{type:"tool-result", content:[{type:"text"}]}`）—— 会话重放看不到工具输出；
  3. `会话存储.保存索引()` 的临时文件名固定为 `<索引>.tmp`，同进程两轮对话并发落盘时互踩
     → 偶发 500「会话持久化失败」；本卡改走「两个 HTTP 客户端并发」的真实形状绕开它。
- 其它既有边界（未变，已在文档写明）：文件类工具仍按进程根取根（未按会话 cwd）；
  `attachments` 未进模型消息；Web 层无独立压缩端点（`/compact` 只是一条消息）。

> **`src/web服务器.light` 拆分（T-0393）Phase 1**：先交方案再保守迁移，本轮零行为回归。

### 新增

- **拆分方案文档** `docs/web服务器拆分方案.md`：通读 121KB / 2238 行的 `web服务器.light`，
  划出 8 个关注点边界（B1 请求级纯辅助 / B2 流式推流 / B3 异步路由分派 / B4 静态资源 /
  B5 会话 CRUD+会话模型 / B6 配置设置快捷键 / B7 审批权限 / B8 提供商枢纽插件），
  逐函数归属 + 依赖方向（子模块 → 地基；入口 → 子模块；子模块间不互依、不依赖入口以避环）。
- **子模块 `src/web_请求辅助.light`**（边界 B1，无状态纯辅助下沉）：承载自 `web服务器.light`
  抽出的 9 个纯函数——`取环境变量` `自定义键表` `处理健康检查` `提取查询令牌` `解析查询参数`
  `分割字符串` `解析会话标识` `是回环地址` `加跨域`，全部 `导出`。判据：无状态（不碰
  `全局服务` 单例 / 不碰 `Web服务端` 类）、无反向依赖（全仓无 `从 web服务器 导入` 这 9 名）、
  依赖极简（仅 `JSON 序列化JSON`；`环境变量` 为地板内置）。

### 变更

- **`src/web服务器.light`（121141 → 119161 字节）**：删除上述 9 个函数体，原地改为
  `从 web_请求辅助 导入 …` 同名转发导入。导入即注入本模块命名空间，故类方法内 48 处
  `加跨域(…)`、`处理对话` 内 `解析会话标识(…)` 等**裸名调用一行未改**，对外 `导出 处理健康检查`
  照旧。**薄入口 + 同名转发**，每步可独立回滚。

### 明确不拆（有硬约束，详见方案文档 §0）

- **流式推流三件套**（`造流式响应`/`后台跑一轮`/`推流实现` + 实时流/线程/流发送 导入）
  **留在入口**：`tests/test_流式推流接线契约.py` 直接对 `web服务器.light` 源码文本断言，
  抽走任一即契约变红。
- **`路由处理器` + `全局服务` 单例**留在入口：互相引用，抽走会引入循环导入（R105 已踩坑）。
- **`Web服务端` 巨类 74 方法**：光明语不支持分文件定义同一类，需「组合 + 委托」结构性改造，
  违反「保守分阶段」，留作评审后 Phase 2（B4→B7→B5→B6→B8）。

### 验证

- 流式契约 `tests/test_流式推流接线契约.py`：**5 passed**。
- Web 真机冒烟 `python 运行.py examples/运行Web服务器.light`：能启动，`GET /health` →
  `{"status":"ok"}`、`GET /api/config` → 200、`加跨域` CORS 头经真实 HTTP 验证仍在。
- Web 端点 examples 全 rc=0：`test_web路由` `test_web服务器E5` `test_r108新端点`
  `test_会话导入导出` `test_审批API` `test_R42_真实webhook` `test_工作目录设置`
  `test_引导稍后配置` `test_会话模型选择`。
- `tests/unit/`：**无新增红**（686 passed / 13 skipped，与拆分前基线一致）。

## [v0.7.0-rc1] — 2026-11-19（发布收口）

> **CI 可信度修复 + 三远端发布收口**：补齐 pytest 插件硬依赖 + 两仓 CI 接入 lightplugin，
> 杜绝「假绿/假红」；合入 T-0393/T-0394 后按 `pyproject.toml` 的 `0.7.0rc1` 打正式 annotated tag。

### 修复（CI / 依赖）

- **`requirements.txt` 漏声明 pytest 插件**：`pytest.ini` 的 `addopts = --timeout=60 -n 4`
  依赖 `pytest-timeout`（`--timeout`）与 `pytest-xdist`（`-n`），但 requirements 只有 pytest 本体。
  GitHub Actions 用 `setup-python` 建干净环境，`pip install -r requirements.txt` 后跑 pytest 会直接报
  `unrecognized arguments`——公开 CI 从根上跑不起来。现补两行为硬依赖，两套 CI 均加「插件能力探针」
  （`pytest --help | grep -- --timeout` / `-n`），缺插件立即红，不再依赖 runner 恰好预装。
- **两套 CI 未接入 lightplugin**：`.github/workflows/ci.yml` 与 `.gitea/workflows/ci.yml`
  原先只检出编译器（light），但 `src/总入口.light` 的 `从 生产挂载 导入 挂载全部插件` 是硬依赖，
  缺它 `test_r111_e2e.light` / `probe_r3_挂载对账.light` / `test_r111插件启停.light` 必红——
  即 CI 此前显示的红有一部分是环境缺依赖的「假红」。现两仓均增加 lightplugin 检出步骤
  （含 `集成/生产挂载.light` 标志物校验）并设 `LIGHTPLUGIN` 环境变量；本地 Gitea CI 的
  venv 兜底安装改为 pytest / xdist / timeout 逐个装。

### 文档 / 工程卫生

- **文档失配修正**：`docs/CI.md` 更新为「light + lightplugin 双硬依赖 + 插件探针」流程，
  变量表补 `LIGHTPLUGIN_REPO`，测试数改为「以 `pytest --collect-only` 为准」不再写死 80；
  `docs/发布门禁E2E.md` 的 33 模块/574 用例、523 examples 等写死数字改为生成式描述；
  `pyproject.toml` 版本号真源注释明确「跳过 `[未发布]` 段取首个 `[vX.Y.Z]`」。
- **`.gitignore` 补规则**：忽略 `_push_github_*.py`（一次性推送脚本）、`G:/`（Windows 路径
  在 POSIX 下的误建残留）；`_m*.py` 与 `.tmp_*/` 此前已忽略。不改磁盘文件、只防误提交。

### 三远端发布

- 本条对应发布 tag `v0.7.0-rc1`；代码基线为合入 T-0393/T-0394 后的 `main`，
  `pyproject.toml` 版本字段 `version = "0.7.0rc1"`（PEP 440 写法）。
- 推送目标：`origin`（内网 Gitea）、`github`、`gitcode`，三处 `main` 与 tag 对齐同一提交。

## [未发布] — 2026-11-18

> **Web Chat 真流式推送**：服务端边跑边推 SSE，浏览器逐字渲染，不再等整轮跑完才出字。

### 新增（Windows 原生拉依赖）

- **`scripts/fetch-deps.ps1`**：`fetch-deps.sh` 的 Windows 原生 PowerShell 版，一键把
  `light` / `lightplugin` / `lightharness` 三仓拉到同一层并冒烟，**不再需要安装 Git Bash**。
  参数一一对应：`-Dir` / `-Mirror` / `-Depth` / `-Branch` / `-NoPull` / `-NoRun` / `-DryRun`；
  环境变量 `LIGHTHARNESS_DEPS_DIR`、`LIGHT_REPO` / `LIGHTPLUGIN_REPO` / `LIGHTHARNESS_REPO`
  同样生效。已存在仓走 `git pull --ff-only`，克隆失败清理半成品目录，退出码
  `0` 成功 / `1` 依赖或冒烟失败 / `2` 用法错误。
- **`README.md`**：环境准备段补 PowerShell 用法与双脚本参数对照表，删掉「Windows 必须用
  Git Bash」的说法。
- **`tests/unit/test_fetch_deps_ps1.py`**：静态契约测试钉住脚本参数、行为约定与 README 文案；
  本机有 `pwsh` / `powershell` 时实跑 `-DryRun` 断言 rc=0、打印三条 clone 命令、不落盘。

### 新增（实时推流链路）

- **上游增量**：`stdlib/HTTP.py` 新增 `HTTPPost流式` —— 逐行读 SSE、遇帧边界即回调，
  非流式 `HTTPPost` 行为零改动；`src/客户端.light` 的 `对话响应` 新增可选 `增量回调`，
  非空时走流式通道（逐帧翻译、只回调新增块），空时保持原「整段收完再翻译」。
- **agent 分发**：`src/代理.light` 新增 `增量回调` 属性，由 `跑一轮` 的选项注入并透传给
  客户端；测试桩/第三方客户端只接受 3 参时自动退回旧签名，语义不变。
- **服务端推流**：`src/web服务器.light` 流式请求走 `造流式响应` —— 后台线程跑完整轮、
  增量回调投帧进 `实时队列`；HTTP 协程侧 `推流实现` 边取边发 chunked。新增 `src/实时流.light`
  （线程安全队列 + SSE 帧构造）。`stdlib/HTTP服务端.light` 支持响应带 `流响应` 键按 chunked
  边发边收口，非流式响应零改动。
- **收尾帧**：流结束时补发统计 / 审批 / 会话 id / `[DONE]`，形状沿用 OpenAI delta，前端无需改解析。

### 修复（流式接线 500 / 断连）

- **chunked 分块长度用十进制 → 一对话就断连**：`stdlib/HTTP服务端.light` 的 `构造分块`
  曾输出十进制 `转字符串(长(字节))` 作 chunk size，而 RFC 7230 要求十六进制。
  帧长 <10 时碰巧一致，一旦 SSE 帧 ≥10 字节（多字节中文/长回复），浏览器按十六进制
  解析十进制长度就错位 → 流中途抛错 → 前端「连接中断：已保留已接收的内容，请重试」。
  改为 `hex(长(字节))[2:]`（去 `0x` 前缀，小写十六进制）。诊断见
  `docs/流式推流500报错诊断与修复-2026-11-18.md`。
- **`调用事件表 is not defined`**：E2 持久化分支引用的两张事件表原先只在 `生成SSE` 内定义，
  补上 `会话对象.查询事件("tool/call"|"tool/result", 保存前序号, 0)`。
- **三处接线必崩**：流式改造漏导入（`实时队列`/`编码SSE帧`/`流块转增量帧`/`线程`/`流发送`）、
  载具缺 `"服务": 己`、`流响应` 回调实参与 `推流实现` 形参不一致（1 参 vs 3 参）——全部补齐。
- 新增 `tests/test_流式推流接线契约.py`（5 项）与 `tests/test_HTTP分块十六进制.py`（2 项）钉死防复发。
  端到端：mock 服务真发 `stream=true` 请求，`Transfer-Encoding: chunked` + 收到 `[DONE]`，未断连。

> **WebUI 六项增强**：工作目录设置、会话导入导出/搜索、工具回放、Markdown 交互、配置收敛。

### 新增（WebUI 体验增强）

- **工作目录设置**（用户反馈缺口）：通用设置页顶部新增「工作目录」卡片，走 `GET/POST /api/cwd`。
  POST 校验目录存在/可读 → `切换工作目录`（令 bash/文件工具与零参 `取根目录()` 跟随）→ 落盘
  `~/.lightharness/settings.json`；新会话携带该 cwd，切换时清空会话缓存避免续用旧 cwd。
- **会话导入/导出**：`GET /api/sessions/:id/export` 导出 JSON 信封 `{格式版本,标题,消息}`；
  `POST /api/sessions/import` 新建会话并逐条追加。侧栏每会话「⇩」导出、顶部「⇧ 导入」按钮。
- **会话搜索过滤**：侧栏顶部搜索框按标题实时过滤（前端过滤，不增加后端负担）。
- **工具调用回放**：Web 对话落盘时把 tool-call / tool-result 事件也存进会话存储（结构化 JSON），
  前端 `renderHistory` 据此还原工具卡片与时间线；这些角色不发回 API（app.js 过滤）。
- **Markdown 交互增强**：零依赖代码高亮（字符串/注释/关键字/数字，占位符法防二次着色）；
  助手消息操作条「复制整条回复」「↻ 重新生成」（重新生成回退到最后一条 user 重发）。
- **配置引导收敛**：模型页「配置大模型」与原顶栏齿轮统一走新设置对话框 `LightSettings.open("models")`，
  旧配置面板仅作 settings.js 未加载时的兜底。

### 判据（新增回归测试）

- `examples/test_工作目录设置.light`（10 断言）：初始来源、无效目录 400、有效切换+持久化、
  GET 回读、settings.json 落盘、空 body 400，全绿。
- `examples/test_会话导入导出.light`（11 断言）：导出信封、导入消息数/标题、导入会话可读回、
  非法导入 400、导出不存在 404，全绿。
- 回归：`test_r108新端点` / `test_设置引导` / `test_引导稍后配置` / 两个持久化测试全绿；
  前端 5 个 JS `node --check` 通过；代码高亮/复制/重生成 Node 渲染验证通过；
  真机 HTTP：cwd 切换+回读、会话导出、会话历史重启保留均通过。

> **Web 使用体验三修**：会话跨重启持久化到用户目录、消息 Markdown 渲染、「稍后配置」真正生效。

### 修复（Web UI / 持久化）

- **问题 1：会话不持久化**。会话历史统一落到用户主目录 `~/.lightharness/sessions/`
  （`HARNESS_HOME` 可覆盖），与服务启动目录解耦，重启/换目录不丢历史。
  新增 `src/会话持久化根.light`（解析根 + `~` 展开 + 旧 `<项目根>/data/sessions`
  无损迁移到新目录，幂等不覆盖不删源）；`examples/运行Web服务器.light` 接线。
  ⚠ 修复入口传参 bug：`会话存储.构造(根)` 内部会自行拼一层 `sessions`，入口曾误传
  `持久化根/sessions` 导致历史落到 `sessions/sessions` 双层而分裂；现改传 `持久化根` 本身。
- **问题 2：消息无 Markdown 渲染 / 输出不简洁**。`webui/messages.js` 零依赖轻量 Markdown：
  标题、列表、引用、表格、代码块（语言标 + 复制）、行内 `代码`/**粗**/*斜*/~~删~~/链接；
  连续文本行合并为一段（段内 `<br>`）减少 DOM 碎片，流式输出更干净；整体先转义再置换，
  链接仅放行 http/https/mailto，`javascript:` 注入被挡。`webui/style.css` 配套样式。
- **问题 3：首次引导「稍后配置」按钮无效**。根因：`设置引导.完成步骤("deepseek-official")`
  对齐上游「无持久化键、完成性从凭据派生」，本仓 Web 端点不落盘任何标记，前端 `load()`
  重读后当前步骤仍是该步，浮层反复弹出。现 Web 服务端落 `引导_deepseekOfficialSkipped`
  跳过标记并由 `引导已完成集` 派生纳入；显式请求（`?显式=`）仍可重新打开供主动配置。

### 判据（新增回归测试）

- `examples/test_会话持久化用户目录.light`：默认根=`~/.lightharness`、`HARNESS_HOME` 覆盖
  （含 `~` 展开）、旧数据无损幂等迁移，全绿。
- `examples/test_会话存储单层目录.light`（新增）：锁定会话落 `根/sessions` 单层、无双层嵌套。
- `examples/test_引导稍后配置.light`（新增）：稍后配置→当前步骤清空→重读不再弹→标记落盘→
  显式重入仍可打开，10 断言全绿。
- `webui/messages.js` Node 渲染验证：标题/段落合并/列表/引用/代码块/表格/粗斜体/代码/安全链接
  全通过，`<script>` 转义、`javascript:` 链接不渲染。
- 回归：`test_设置引导.light`（54 断言）、`test_r108新端点.light`（35 断言）全绿；
  Web 服务重启后 `/api/sessions` 读到全部历史、新建会话落点正确（真机 HTTP 验证）。

> **MCP 真链路打通**：像 deepseek-harness 一样用 MCP —— 修掉跨平台硬阻断，
> stdio + streamable-http 真端到端在 FreeBSD 0.88 实测通过。

### 修复（MCP）

- **跨平台硬阻断：握手方法名 `连接` 撞编译器保留字**（`src/mcp客户端.light`）。
  光明编译器把类方法「段落 连接」映射成 Python `str.join`（`code_generator.py:239`），
  但「`客户端.连接()`」这类**无参**调用因运行时特判（只接管单实参 `连接`，
  `code_generator.py:4712`）原样发射 `.连接()` → 两个传输类握手一律
  `AttributeError: 'MCP客户端' object has no attribute '连接'`。把 `MCP客户端` /
  `MCPHttpClient` 的握手方法统一改名「**握手**」并同步全部调用点与测试桩；
  `连接` 从此只作 stdlib 字符串方法，不再当 MCP 方法名。
- **配置口径对齐 DSH**：`解析MCP配置`（`src/协议深化.light`）新增 `归一MCP条目`，
  除本仓中文键（名/指令/参数/环境/网址/头表/类型）外，等价接受 DSH 标准英文键
  `name/command/args/env/url/headers/transport`；`env`/`headers` 既接受
  `[{名,值}]` 也接受 JSON 对象；`transport: streamable-http` 归一为 `http`。
  于是 `mcp.json` 可直接用 deepseek-harness 的配置格式。
- **跨平台路径**：`examples/test_mcp接线.light` 用 `文件系统.路径连接` 代替硬编码
  `\\`，FreeBSD 上不再拼出 `...lightharness\_tmp_xxx.json` 写不进去。

### 判据（0.88 FreeBSD 15.1 真机，非桩）

- `examples/test_mcp接线.light`：真 stdio 起 `mcp_服务器.py`，发现并调用 2 工具
  （`mcp__demo__echo` / `mcp__demo__add`），PASS。
- `examples/test_mcp_http_real.light`（新增）：真 HTTP 起 `mcp_http服务器.py`，
  握手/发现 3 工具/调用 echo/注册 3 工具，PASS。
- `examples/test_mcp_prod.light`（新增）：无显式路径 → 读 cwd 的 DSH 格式 `mcp.json`
  自动装配，PASS。
- 回归：`test_mcp.light` / `test_mcp_http.light` / `test_R51_mcp资源.light` /
  `test_交付.light` / `test_协议深化.light`（含新增英文键用例）本地全绿。

> **jet hub 接入**：把 DSH 的 jet hub 插件（`dsh-providers-hub` / 旧名 `dsh-codearts-auth`）
> 背后的**本地 OpenAI 兼容网关**当成 lightharness 的模型来源，模型 ID 与 DSH 完全一致。

### 新增

- **`src/提供商枢纽.light`**：地址/密钥发现（`JET_HUB_BASE_URL` / `JET_HUB_API_KEY` /
  `DSH_OPENAI_GATEWAY_*` / `<DSH_HOME>/openai-gateway/api-key`）、`/v1/models` 目录解析、
  按提供商分组、挑选模型（全名/裸名/显示名/默认偏好）、接入配置（`.env` 三行 + 完整端点）、
  真实探测（15s 超时，失败只降级不抛）。
- **CLI 子命令 `HARNESS_CMD=jet-hub`**：打印网关地址/密钥来源（不回显明文）/按提供商分组的模型目录/推荐模型。
- **`HARNESS_PROVIDER=jet-hub`**：CLI 与 Web 启动均可直接用枢纽当模型来源（优先级高于 `.env`；
  Web 侧不可用时只警告并回落）。
- **Web 端点**：`GET /api/settings/providers/jet-hub`（探测，永不含密钥明文）、
  `POST /api/settings/providers/jet-hub/apply`（选模型 → 写 `.env` → 热更新客户端）。
- **设置页 jet-hub 卡片**（`webui/settings.js` / `settings.css`）：模型页顶部显示连接状态、
  密钥来源、按提供商分组的模型下拉与「使用此模型」按钮。
- **chat 框下「每会话模型选择器」**（对齐 DSH）：内置 4 个 + jet-hub 全部模型按「来源 · 提供商」分组，
  选中只影响当前会话；`GET /api/models[?session=]`、`POST /api/sessions/:id/model`，
  存 `<会话根>/session-models.json`，`GET /api/sessions/:id` 回 `模型`；
  每轮按「请求 model > 会话已存 > 全局 .env > 内置默认」解析，同端点/密钥只换 model 构造客户端。
- **文档**：`docs/jet-hub接入.md`（含 Windows / FreeBSD 0.88 联调记录与 DSH 差异登记）。

### 修复

- **网关错误帧被吞成「空完成」**：`客户端.翻译流` 现在识别 jet-hub 网关的
  `data: {"choices":[],"error":{"message","type","code","status"}}` 帧并抛出可读的
  「上游错误: …」，不再退化成 `EMPTY_RESPONSE`（实测 opencode 账号 401 场景）。

### 判据

- `examples/test_提供商枢纽.light`（离线自测：地址/密钥形状/目录解析/挑选/分组/接入配置/缺省主目录，PASS）。
- `examples/test_客户端_网关错误.light`（正常帧出块 / 对象与字符串两种 error 帧都抛可读错误，PASS）。
- `examples/test_会话模型选择.light`（模型目录/会话模型读写/首轮落盘/清空跟随全局，PASS）。
- 联调：Windows 本机 → 104 个模型 / 12 个提供商；FreeBSD 0.88 → 71 个模型 / 7 个提供商；
  两边 `HARNESS_PROVIDER=jet-hub` 单轮回复正常；Web 应用 `codearts/GLM-5.2` 后 `/api/config` 热更新正确。
- 会话级模型选择：Playwright 实拍（Chromium）——跟随全局 ◇ / 显式 ◈ / 真实回复 / 切回跟随 / 新建会话回默认，全通过。
- 全量门禁 `pytest tests/test_回归.py`：**633 passed / 1 skipped / 1 既有红**
  （`test_agentE5工具.light`，在干净 HEAD 上同样红，与本次改动无关）。

## [v0.7.0-rc1] — 2026-11-17

> **R221 收口（0.2.2-rc.3 对齐）**：上游锚点 `dsh-v0.2.2-rc.1`（`66491b05e3`）→ **`dsh-v0.2.2-rc.3`（`38a6a5c965`，2026-11-13）**。
> 版本自 `v0.6.0-rc1` 走 minor 位升 **`v0.7.0-rc1`**（上游 rc.2 / rc.3 特性移植 + 插件面板缺陷修复）。

### 新增

- **HarnessError 基类**（B-f2 T-0367）：稳定机器码 `code` 与人类消息分离、`cause` 链、`name` 取子类名；rc.2 起 20+ 包新错误类统一继承（`src/错误增强.light`）。
- **forge 变更请求三条**（B-f1 T-0366）：#9 快照概览 / #10 diff 定 head / #11 评审读取码（`src/变更请求.light`）。
- **插件更新方式**（B-f3 T-0368）：#12 registry/git 双通道 + 安装结果核对（`src/插件注册表.light`）。
- **搜索按计费三态选凭据**（B-f3 T-0368）：#18 credential 来源 + 延迟失败语义（`src/网页搜索.light`）。
- **会话批量追加 + 运行时上下文提醒**（B-f4 T-0369）：#14 批量追加去重、#13 提醒完整模型（`src/会话.light` / `src/会话日志深化.light`）。
- **子代理中断默认关**（B-f4 T-0369）：#15 中断两层次语义（`src/子代理预设选择.light` / `src/代理团队.light`）。

### 修复

- **插件面板异常**（T-0385）：`造卡片` 透传 `工具表`、MCP 桥接补只读原因；修复启动后全部插件显示「异常 / 不包含任何组件」（`src/插件面板.light` / `src/web服务器.light`）。

### 变更

- **llm-deepseek 凭据与模型增补**（B7 T-0364）：新增 `credential.ts` + 模型/凭据增补，补 R220 漏项（`src/模型目录.light` / `src/模型列表缓存.light`）。
- **工作树清理判定**（B-f2 T-0367）：retainOnArchive / 未归档引用 / 只读（`src/工作区变更.light`）。
- **终端 CLEANUP_FAILED + 17 附件码**（B-f2 T-0367）：错误码归类（`src/终端.light` / `src/附件准入.light`）。
- **宿主面登记**（C T-0365）：§11 append，登记 126 → 148。

### 判据

- `examples/test_R221_B7模型增补.light`（119 断言）
- `examples/test_R221_Bf1变更请求快照.light`（76 断言）
- `examples/test_R221_Bf2错误与清理.light`（69 断言）
- `examples/test_R221_Bf3更新与计费.light`（67 断言）
- `examples/test_R221_Bf4会话与子代理.light`（117 断言）
- `examples/test_r221插件面板e2e.light`（10 断言）

### 已知限制（M 收口记录）

- **全量回归门禁（判据 2）**：本机 Windows 主控复跑 `python -m pytest tests/test_回归.py -q`（`pytest.ini` 默认 `-n 4`）：
  **628 passed / 1 skipped / 1 failed**，唯一真红是 `test_agentE5钩子.light` —— 已在基线 `reports/本机lh基线_latest.json`
  （2103 total / 6 failed）里登记，属既有红。另一次 `test_联调CLI.light` 记红是 xdist `gw0` worker 被打崩（`node down`），
  隔离复跑 1 passed，不是真实回归。**新增红 = 0**。
- **门禁环境前提**：复跑必须带 `LIGHTPLUGIN=<仓根>/../lightplugin`（第 4 仓）。worktree 里没有同级 `lightplugin` 时，
  `src/总入口.light` 的 `从 生产挂载 导入` 会连片报「No module named '生产挂载'」，一次造假红 **32 条**（并行与串行口径一致，
  串行 35:50 复现）；那是环境缺仓，不是产物坏。历史坑见 `docs/多平台差异清单.md` 与 `scripts/fetch-deps.sh`。
- **三远端推送（判据 5）**：origin（gitcode）/ myrepo（Gitea）/ github 三处 `main` 已对齐同一 head（见 `summary.md`）。

## [v0.6.0-rc1] — 2026-11-16

> **R220 收口（0.2.2-rc.1 对齐）**：上游锚点 `dsh-v0.2.1-rc.3`（`1f81c047fc`）→ **`dsh-v0.2.2-rc.1`（`66491b05e3`，2026-11-04）**。
> 七路并行（B1 主控先落地 + B2–B7 hive 卡 T-0254~T-0258）+ C/D/E 路登记与门禁。版本自 `v0.5.0-rc1` 走 minor 位升 **`v0.6.0-rc1`**（上游 0.2.2 特性移植）。

### 新增

- **B1（主控）apply_patch 全链路**：`src/应用补丁.light`（391 行）+ `examples/test_应用补丁.light`（61 断言）。Add/Delete/Update(+Move to)、`@@` 锚点、`+/-/空格` 行、`*** End of File`、三种 heredoc 包装、CRLF 归一、四遍规范化定位、锚点推进、末尾空行重试、纯插入/纯删除/EOF 语义、稳定排序逆序回放、失败形状（阶段/块行号/搜索起点）。反跑 A/B 双红后复绿。
- **B2（T-0254）消息引用**：`src/消息引用.light`（对标 `session/message-quotes`）——引文解码（行尾归一、`≤3 空格 + >` 前缀只剥一层）、引文区间（连续显式引用行并段、原文偏移）、引文规则匹配（`引用` 节点 + `\n\n` 降级显示空格）、投影标记、引用准入/插入时序、八语文案表。判据 `examples/test_消息引用.light`。
- **B3（T-0255）LiveShare 协议**：`src/共享协议.light`（对标 `experimental/liveshare-protocol`）——隧道协议 / viewer 状态机 / 承载语义纯逻辑层。判据 `examples/test_共享协议.light`。
- **B4（T-0256）变更请求**：`src/变更请求.light`（对标 `experimental/forge` + `forge-session`）——CR 注册表 / key / 轮询调度 / CR↔Session 绑定投影。判据 `examples/test_变更请求.light`。
- **B5（T-0257）推荐决策与行动卡**：`src/推荐决策.light`（对标 `plugin-recommendations` + `creation-recommendations` + `action-cards` + `plugin-detail` + `official-bundles`）——推荐决策 + 用户激活态 + 卡片状态机。判据 `examples/test_推荐决策.light`。
- **B6（T-0258）apply_patch 呈现形状**：`src/补丁呈现.light`（对标 `tool-fs` 的 `apply-patch-output` + `apply-patch-presentation`）——调用前预览（不读盘投影 diff 卡）、结果后呈现（opaque meta 收窄已知差异）、终止文案（成功摘要 + 逐操作状态 + diff 摘要）。判据 `examples/test_补丁呈现.light`。
- **B7（T-0258 原计划）llm-deepseek 增补：未落地**。T-0258 分支实际只交了 B6（`git show --stat 072c841` 仅 `src/补丁呈现.light` + 其判据），B7 的 `llm-deepseek` 对增补（`0.2.1-rc.3..0.2.2-rc.3` 12 文件 / +280−32）转为 R221-B7 卡补做，不并入 #349/#350 记账。

### 宿主面登记

- **R220-C 补登 §10**（`docs/宿主面登记清单.md`）：client 渲染层/统一右键菜单/桌面外壳/快照基线、LiveShare 宿主侧（relay+授权+UI）、CUA（macOS 原生）、Forge GitHub（gh CLI）、PTC 运行时内核、tool-executor-ptc、session-controller、plugin-manager 受保护清单、OAR 子代理桥、personalized-recommendations 壳、file-drag、tool-testkit、5 个实验性 client-ui 壳 —— 登记 113 → 126 条。ui-deepseek-model-label-1017 上游删除（stale 壳），删除即正确。

### 验证

- R220 五张卡判据全绿（`test_消息引用` / `test_共享协议` / `test_变更请求` / `test_推荐决策` / `test_补丁呈现` 均 `--- 测试 … 通过 ---` rc=0）；B1 `test_应用补丁` 复核绿。
- 反跑判据：各卡值反 + 抛反各 1 处必须红，还原后 sha256 校验一致并复绿（卡内留痕）。

---

## [未发布]

### 2026-10-30 · T-0180 合流 + 编译器路径探测

- **合流 GitCode `23f7cfa`**（T-0180 工作目录集中化：cwd 收拢为会话状态 + originCwd 派生 + 运行时断言）。
  与本地 `e097a99`（stdlib 同步：`原子写入` / `皆空` 自包含 / 删重复定义）改动的文件集合不重叠
  （`src/*.light` vs `stdlib/*`），`--no-ff` 合并零冲突。
- **`运行.py` / `scripts/互举反跑.py`：`LIGHT_MERGE` 默认值改为探测链。**
  原默认值是写死的 `G:\dswork\duan-light-merge\light-merge`，只有原作者那台 Windows 恰好命中；
  换机器（Linux / CI / 别人的 Mac）只要不显式设环境变量，就一律「找不到光明编译器」退出 ——
  表现是整套 `.light` 用例集体飘红，**看着像代码坏了，其实只是路径不属于这台机器**
  （本次合流后 `tests/test_T0180_工作目录集中化.py` 5 条全红就是这么来的）。
  现在按顺序探测 `$LIGHT_MERGE` → `../light` → `../light-merge` → `../duan-light-merge/light-merge`
  → `../../light` → 原 Windows 路径（兜底），显式环境变量仍最优先。
- **`tests/conftest.py`（新增）：收集前统一探测编译器路径。**
  13 个词法/回归测试文件各自写了 `LIGHT_MERGE = os.environ.get(..., r"G:\dswork\...")`
  + `sys.path.insert(0, <LM>/src)`，缺环境变量时在**收集期**就
  `ModuleNotFoundError: No module named 'lexer'`，21 个测试模块集体 ERROR。
  这 13 个文件写法本身没错（只是默认值不该写死），所以不改它们：conftest 在收集前
  把探测结果写回 `os.environ`，它们原样读到正确值。探测口径与 `运行.py` 一致。
- **`stdlib/列表工具.light` 同步（`builtins.求和` 的转发目标）。**
  `builtins.求和(数据)` 转发时传 **4 个位置参数**（数据 / 长整上限 / 启用补偿 / 整数进补偿），
  而本仓那份是 **3 参旧版**，于是 `求和() takes from 1 to 3 positional arguments but 4 were given`。
  只要 example 里出现 `求和([...])` 就炸 —— `test_R72_C_推导式`、`test_R20_词法边界综合`
  两条**由绿转红**（用 `git worktree` 在 `be7da46` 上对照确认，不是环境问题）。
  修法不是手改这份拷贝：把 `列表工具.light` 加进 light 侧 `sync_builtins.py` 的
  `LH_LIGHT_SYNC`（原先只登记 `内置核心判型.light`），由脚本机械同步；自检也改成
  **按文件各自的「必须含」判据**（原来一份判型判据套所有同步文件，加文件必误报）。
  教训：`builtins` 的**转发目标**签名必须与真源刚性咬合，这类关系要机械化，不能靠人记。

### 环境说明（不是代码问题）

- **缺 `lightplugin` 仓会让几十个 example 集体红**：`src/总入口.light` 的
  `从 生产挂载 导入 挂载全部插件` 报 `No module named '生产挂载'`，而 `运行.py` 对缺
  `LIGHTPLUGIN` 是**静默容忍**的（路径表返回空），不会告诉你缺的是哪个仓。
  已在本仓 README 的「环境准备」写明目录布局与该症状。
- 补齐依赖后仍红的 6 条属**平台能力差异**（`沙箱统一` 缺 landlock/bwrap、
  `事件循环` 的同 fd 读写派发顺序依赖 selector 实现），在基线 `be7da46` 上同样红。
- **装了 safe-delete 钩子的环境里，`test_启动配置.py` 会整片假红**（本次实测 12 条）。
  `run_in_repo` 在仓根写 `_unit_tmp_*.light` 并在 `finally` 里 `os.remove` 它；当运行环境
  装了「批量删除确认」守卫（`sitecustomize.py` 里 `SAFE_DELETE_BULK_CONFIRM_REQUIRED`，
  阈值 50 次/轮）时，一轮全量累计到 90 次删除就抛 `SystemExit(1)`，
  表现为 `SystemExit: 1` 且**单跑该文件必过、混跑必红**——因为计数按进程/turn 重置。
  判定方法：看 `Captured stderr` 里有没有 `[safe-delete][...]`。
  这是**执行环境的守卫**，不是本仓缺陷；无守卫的 CI runner 上不会出现。

---

> **R110 收口（2026-10-03，维持 `v0.4.0-rc2`）**：A/C/D 文档交付、B 核实 0 移植、E Windows 本机双全量 0 新增红。零可执行代码改动 → 不 bump 版本号、不新建 tag。lightharness 三远端已推；light-merge 无 R110 改动未推。

### 新增

- 对齐 deepseek-harness 上游 `dsh-v0.2.0-rc.2`（`639ed01539`）相对 rc.1 的增量（**187 commits / 1022 真增量文件 / +33253 / -6141**，三点基准 `rc.1...rc.2`，merge-base `4878cdabd8`）。
- B 路经核实为 **0 移植**（lightharness 无对应纯逻辑层承载 A 清单 §4 的 4 组候选：schedule framing / user-questions 状态机 / tool-ask-user timed / shell 提示词文案）；`对标清单.json` 末位仍 #313，无 R110 新增。

### 修复

- 宿主面增量 15 条 append 进 `docs/宿主面登记清单.md` §7（44→59）：Windows ACL 修复链 / web-desktop UI / whale perf / Cordis inspect / desktop installer / llm pi-ai 升级 / CI 等。
- fork FreeBSD 脚本对账：上游 rc.2 无 freebsd/ 目录，fork 侧 `e5b5ccbfcb..8bf6c9250f` 零改动 → 零同步（`R110_D路_FreeBSD脚本对账.md`）。

### 验证

- LH 本机 Windows 全量 **2074 用例 / 0 failed / 0 new_red**（`reports/R110_lh_windows_latest.json`）。
- LM 本机 Windows 全量 **8489 用例 / 0 new_red**（1 为已知 flaky `test_进程类` 单跑复绿；R55 时代 5 红全清）。
- 锚点修正：分发书 `e5b5ccbfcb..rc.2` 两点口径有误（`e5b5ccbfcb` 是 fork 合流提交，会冒 freebsd 假删除）；真基准三点 `rc.1...rc.2`（merge-base `4878cdabd8`）。
- 遗留：0.86 Linux / 0.82 FreeBSD 基线 JSON 未生成（B=0 代码改动 ⇒ 逻辑上无 R110 新红风险，待补）。

---

## [v0.5.0-rc1] — 2026-10-28

> **0.2.1-rc.3 对齐收口（M 路 T-0179 合流）**：上游 `dsh-v0.2.0-rc.2 → dsh-v0.2.1-rc.3` 增量甄别（A 路）+ 纯逻辑移植（B1-B4 路）+ 宿主面登记（C 路）+ FreeBSD fork 同步（D 路）+ 三平台门禁回归（E 路）+ 新红取证处置（F 路），七路并行、M 路统一收口。版本自 `v0.4.0-rc2` 走 minor 位升 **`v0.5.0-rc1`**（B 路为上游 minor 特性移植，非 patch）。交付报告见 `docs/功能对标/0.2.1-rc.3对齐_交付报告.md`。

### 新增

- **A 路（T-0170）上游增量甄别**：`rc.2...rc.3` 实为「架构收敛 + 平台面扩张」——1487 条非 merge commit 中 feat 仅 146 条；真实代码增量 1047 个 src 文件（+50788/−15773）；纯逻辑可移植面收敛为 **14 项 / 47 文件**；宿主面（登记不移植）约 640 个 src 文件。产出 `docs/功能对标/0.2.1-rc.3增量清单.md`。
- **B1 路（T-0173）llm 簇纯逻辑复刻**：模型列表解码（`src/模型目录.light` +200 行，7 判据）、模型列表缓存（`src/模型列表缓存.light` 新建 142 行：分作用域/单飞/后台刷新/失败保留，6 判据）、令牌计量折叠（`src/令牌计量.light` +200 行：plan/commit 两段式 + O(1) 折叠 + 语境拆解投影，3 组判据）。
- **B2 路（T-0174）会话与存储面**：`src/智能体指令.light` agent-instructions 0.2.1 增量（442→589 行：双用户全局根与候选组去重、dshHome 不可覆盖、项目路径作用域转义等 6 点，19 组判据）。
- **B3 路（T-0175）subagent/workspace 簇**：`src/子代理预设选择.light`（175 行，12 例）、`src/子代理活化.light`（126 行，5 例）、`src/工作区成员.light`（66 行，5 例），端到端判据 `examples/test_R175_B3复刻.light`（34 断言）；B3 簇其余增量定性为 invariant.ts 批量退场 / locale i18n / 注释级，不移植。
- **B4 路（T-0176）typert/credentials/ptc-runtime/jobs 等 12 簇纯逻辑复刻**（对标清单 #334-#345）。
- **C 路（T-0171）宿主面登记扩容**：0.2.1 增量 append 进 `docs/宿主面登记清单.md`。
- **D 路（T-0172）FreeBSD fork 脚本同步**：`lightharness/freebsd/` ↔ fork 16 文件逐一对账（`freebsd/对账记录_rc3.md`），fork 侧 3 文件变动均判定 fork 专属 → 结论零同步（需重编 setuid 0）。

### 修复

- `stdlib/builtins.py`：`列表工具.求和` 调用实参由 1 退化为 4 的同步遗漏补回（E 路，消 `test_R20_词法边界综合` / `test_R72_C_推导式` 两红）。
- `src/钩子.light` 消息钩子判定：空字符串缘由被 `是空(缘由)` 误判为「无拒绝」而放行，改独立 `已拒绝` 标志位（F 路，消 `test_R48_hooks三事件`）。
- `src/字符串替换编辑器.light`：`执行编辑命令` 的 `path=""` 被误判缺参、`必填参数` 的空串 `值` 被误判必填缺失，两处改键存在性 / None 判断（F 路，空文件 `allowEmpty=真` 语义恢复）。
- `tests/test_R21_词法确定性_超集.py`：`者种类` 误报白名单（旧基线 d2857dd5 把形参 `接收者种类` 截头登记，非 lexer 丢名；F 路复核确认为有意豁免）。

### 验证

- **Windows LH 全量**：初刷 2103 用例 / 6 failed（`reports/本机lh基线_latest.json`，R177 首刷）；E 路修复 2 处后复跑绝对红 6 → 3（真红 3 + Windows 环境飘红 5，隔离复跑绿，`R177_E路_三平台门禁回归报告.md`）；F 路修复后 run2 **2085 passed / 1 failed**（唯一余红 `agentE5钩子` 为越界红：根因在 light-merge 编译器 R128 起 `段落 调用()` → `__call__` 映射，非本仓 B 线引入，开卡跟踪）。
- **FreeBSD 0.88 LH 全量** 2103 用例：修复前 6 failed（`R177_LH_0.88基线_20261027-212754.json`，Windows 侧同源）；E 路修复后真红 3，均已修。
- **Windows LM 全量** 9433 用例 / 23 红（`reports/本机lm基线_latest.json`，passed 9276）：21 条新增红经取证与 B 线无因果（lightmem 仓），移交 LM 专项卡。
- **新增 flaky 登记**（`tests/flaky_registry.txt` F-03~F-09）：5 条 Windows xdist 偶发（隔离复跑恒绿）+ 2 条 PTY 环境红（无 console session 下 `CreatePseudoConsole` 稳定 E_INVALIDARG）。
- **Linux 0.86 腿**：机器不可达，本轮阻塞未跑（遗留，见交付报告）。

---

## [r95-dev] — 2026-09-25

R95 收口：**根因战场闭环**（LH `61e004a`，分支 `release/r95`，tag `r95-dev`）。

### 新增

- 发布分支 `release/r95` 与 tag `r95-dev`。
- Job Object 与创建时间闸门：为进程树治理提供可复用的根治判据。

### 修复

- 进程树根因类问题闭环：从"现象修补"推进到"根因可验证"，同类问题不再反复复发。

### 验证

- Job Object 闸门 + 创建时间闸门双证据链，为进程树的根治结论提供端到端验证。
- 远端 FreeBSD 门禁机三平台回归通过。

---

## [r94-dev] — 2026-09-25

R94 收口：**开发冻结收口**（LH `eae81f1`，分支 `release/r94`，tag `r94-dev`）。

### 新增

- 发布分支 `release/r94` 与 tag `r94-dev`，把本轮开发面冻结在一个可回溯的提交上。

### 修复

- 本轮开发面冻结，此后不再接受散乱改动，变更一律走新的发布分支。

### 验证

- 冻结面对应的回归门禁通过，作为 R95 根因战场的基线。

---

## [r87] — 2026-09-23

R87 收口：**上游 0.1.7 纯逻辑面移植**（HEAD `7cc0fa8`）。

### 新增

- 对齐 deepseek-harness 上游 0.1.7 的纯逻辑增量，完成对应区域的移植与落位。
- 移植过程产生的语言侧需求登记进 `docs/功能对标/语言缺陷账.md`。

### 修复

- 移植暴露的 flaky 用例完成根治处置（见 `_taskE_R87_flaky根治报告.md`）。
- 门禁补位：修正 light-merge 侧与本仓之间的回归门缺口（见 `_taskD_R87_LM门禁补位报告.md`）。

### 验证

- 三平台 LH 全量回归：**1400 用例 0 失败**。
- 环境固化项入档（见 `_taskF_R87_环境固化报告.md`），确保不同机器跑出同一结果。
