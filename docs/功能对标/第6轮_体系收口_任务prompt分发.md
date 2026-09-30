# 第6轮 任务书：体系收口第一轮 —— 让已移植单元真正跑成「系统」

> 对标窗口：上游 0.2.0-rc.1（`e5b5ccbfcb`，与 R103/R104 同一锚点）
> 现状（R104 已合流，LH `616c458`；前序五步工具接线已落地，commit `cd8079c` 推送 myrepo/origin，github 待代理好转续推）
> 本轮目标：**补齐「复刻了单元、没复刻体系」的缺口**——把已落地的单元接进运行链、建应用外壳、建宿主/OS 集成总线、接编排胶水。
> 派单方式：每段「—— 任务线 X ——」下方引号块整体作为派给执行代理的任务正文（`-Task` / 子代理 prompt）。

---

## 0. 实证比对结论（回答「再仔细比对」）

把 `对标清单.json`（254 卡）与 `lightharness/src/*.light`（214 文件）、上游 `packages/`（54）、`apps/`（4）、`docs/subsystems/`（62）做交叉核对，结论如下：

1. **单元已大量落地，但「体系」缺三块**：
   - **应用外壳 `apps/*` 整体缺失**：`apps/cli`、`apps/web`、`apps/desktop`、`apps/desktop-host` 无对应复刻。`总入口.light` 仅有 `交互循环/主/调度命令/执行运行` 的程序化入口，缺 `apps/cli` 的参数解析 / 斜杠命令派发 / 无头运行器；`webui/` 存在但远未覆盖 `apps/web` 全貌；desktop 系完全空白。
   - **宿主/OS 集成总线缺失**：47 张 `登记(不移植)` 卡里，**41 张的 `光明模块` 字段已指向真实存在的 `.light` 文件**——单元写好了却从未被调用方接上（纯逻辑岛屿）。
   - **编排胶水缺失**：`#240 agent-loop inbox 异步化`、`#241 session message projection 事件解释器`、`#88 goal-round-driver`、`#39 plan-mode 核心` 等卡仍是「登记」，单元在但没接进 `代理循环 ↔ 会话 ↔ 预设/团队/子代理` 的总装配链。

2. **关键数字**：57 张未收口卡中，**61 个目标 `.light` 文件已存在于磁盘（=> 接线即可），仅 6 张缺文件（=> 需新建/补移植）**。即本轮主体是「接线」而非「重写」。

3. **本轮不渝越红线**：宿主/OS 真实执行（真实子进程、真实沙箱 namespace、e2b 云端、凭据提供方）继续以「宿主桩 + 接口契约」形式存在，纯逻辑面接桩调用；不伪造 OS 能力。

---

## 1. 线别总览

| 线 | 类型 | 目标 | 落点（新建/接线） | 卡号 |
|---|---|---|---|---|
| A | 应用外壳 | `apps/cli` 复刻：参数解析 + 斜杠命令派发 + 无头运行器 | `src/cli外壳.light`（新）+ `总入口.light`（接线） | #255 |
| B | 宿主/OS 集成总线 | 让「登记」的宿主面单元真正接桩可调用 | `远端总线/抓取策略/真实抓取提供/webhook会话/钩子协议/宿主IO` 等接线 | #256–#262 |
| C | 编排集成 | agent-loop inbox / session 投影 / goal-plan / preset-team-subagent 装配链 | `代理循环/会话格式/目标轮驱动/计划模式/总入口` 接线 | #269–#274 |
| D | 应用外壳 | `apps/web` ↔ `webui/` 架构对齐 + 缺失客户端模块 | `webui/*` 增补 + `docs/功能对标/apps_web对齐.md` | #275 |
| E | 单元接线（第一批） | 已落地但未接入的纯逻辑单元批量接链 | `类型系统/会话冷读/搜索提供商/office转PDF/工具_写文件/附件准入/沙箱/反馈/审批/工作区变更/团队工具/目标折叠/代码运行时/子进程` 等 | #276–#289 |
| 路M | 收口 | 波及核对 + 全量回归门禁 + 对标清单回填 + 交付报告 | `docs/功能对标/第6轮_体系收口_交付报告.md` | — |

卡号自 254 续：A=#255，B=#256…，路M 不占卡号（回填既有卡状态）。

---

## 2. 文件互斥表（合入零冲突约束）

| 线 | 独占文件 | 共享只读（不得改控制流） |
|---|---|---|
| A | `src/cli外壳.light`（新）、`examples/test_cli外壳.light`（新） | `总入口.light`（仅加 `主()` 分叉一行调用 + 帮助行表一行；不得改 `交互循环/执行运行/调度命令` 既有逻辑） |
| B | `src/远端总线.light`、`src/抓取策略.light`、`src/真实抓取提供.light`、`src/webhook会话.light`、`src/钩子协议.light`、`src/宿主IO.light` | `src/钩子.light`、`src/acp内容.light`、`src/acp转码.light`、`src/真实HTTP客户端.light`、`src/沙箱.light`、`src/子进程.light`、`src/文件.light`、`src/存储.light`（仅加「接桩调用」出口段，不改既有纯逻辑） |
| C | `src/代理循环.light`、`src/会话格式.light`、`src/目标轮驱动.light`、`src/计划模式.light` | `总入口.light`（同 A 约束，A/C 不得同时改同一段落；A 负责 `主()` 入口、C 负责 `跑一轮` 装配，分区明确） |
| D | `webui/*`（独立目录，与 src 零冲突） | — |
| E | `src/类型系统.light`、`src/类型注册.light`、`src/typert协议.light`、`src/会话冷读.light`、`src/会话日志增量.light`、`src/会话持久化JSONL.light`、`src/会话标题族.light`、`src/会话引用深化.light`、`src/搜索提供商.light`、`src/office转PDF.light`、`src/工具_写文件.light`、`src/附件准入.light`、`src/沙箱.light`（B 已占则 E 不碰）、`src/反馈.light`、`src/审批.light`、`src/交互命令.light`、`src/工作区变更.light`、`src/交付呈现.light`、`src/团队工具.light`、`src/代理团队.light`、`src/目标折叠.light`、`src/代码运行时.light`、`src/子进程.light`（B 已占则 E 不碰） | 各自既有纯逻辑段落只读复用 |

> 约定：B 与 E 都涉及 `沙箱.light`/`子进程.light` 时，B 负责「宿主桩出口」、E 负责「纯逻辑段接线」，文件按段落分区，互不覆盖；若冲突风险高，E 该文件改挂 `src/沙箱深化.light`/`src/子进程深化.light` 新文件。

---

## —— 任务线 A：apps/cli 复刻（参数解析 + 斜杠命令 + 无头运行器） ——

```
你在 G:\dswork\duan-light-merge\lightharness 工作。把上游 apps/cli 复刻为光明 CLI 外壳，让 lightharness 从「库」变成「可从命令行用的产品」。

【先读】
- 上游 apps/cli/src/args.ts（参数 schema：--model / --preset / --prompt(无头) / --resume / --list / --config / --help）、bin.ts（入口装配）、profile-boot.ts（配置加载）、process-shutdown.ts（优雅退出）。
- 光明既有：src/总入口.light（已有 交互循环:253 / 主:519 / 调度命令:498 / 执行运行:312 / 解析模型:302 / 取默认模型 链路）。确认 总入口.交互循环 已是 REPL 主循环，本线**只在外围包一层 CLI 参数与斜杠命令**，不重写交互循环。
- 上游 docs/subsystems/commands.md（斜杠命令语义表）。

【复刻内容】新建 src/cli外壳.light
1. 段落 解析参数(命令行表) -> 字典：对齐 args.ts 字段；未知参数 -> 抛错并打印用法；--help 短路返回特殊标记。
2. 段落 斜杠命令表() -> 字典：/help /clear /model /compact /save /resume /exit 的「命令名->处理函数名」映射（处理函数在 总入口.调度命令 已部分存在，复用之，不得重复实现）。
3. 段落 运行对话循环(客户端对象, 注册表, 根, 配置字典)：包 总入口.交互循环；在每轮用户输入前打印提示符；识别以 "/" 开头的输入走 斜杠命令表 派发。
4. 段落 无头运行(客户端对象, 注册表, 根, 提示文本)：--prompt 模式，跑一轮(总入口.跑一轮) 后取 总入口.取最终文本 直接输出并退出，不进 REPL。
5. 段落 列会话并选择(根)：--list 打印会话清单（复用 总入口.列出会话）；--resume <id> 载入指定会话进 REPL。
6. preset 解析：--preset 取值映射到第5轮四预设（standard/ptc/minimal/cordis），未知 -> 报错打印四键（复用 总入口 既有报错文案风格）。

【接线】src/总入口.light
- 主()（:519）新增分叉：解析命令行 -> 无头模式走 无头运行；否则 运行对话循环。仅加这一行分支 + 帮助行表追加一行说明 CLI 参数。
- ⚠️ 不得改动 交互循环 / 执行运行 / 调度命令 既有控制流；本线只在外围。

【测试】examples/test_cli外壳.light
- 正例：解析参数 各旗标取值正确；斜杠命令表 含 7 命令且映射非空；无头运行 给定提示返回最终文本非空；列会话 接 列出会话 形状一致；preset 未知 -> 抛错且文案含四键。
- 既有 examples/test_总入口.light、test_cli深化.light 等回归绿（先跑一遍定位有哪些）。
- 反跑 3 组：① 解析参数 去掉未知参数报错 -> 脏参数用例立红；② 无头运行 改成「进 REPL」-> 无头用例立红；③ preset 未知改「回落 standard」-> 报错用例立红。逐组记「改了什么 -> 哪条红 -> 已还原」。

【门禁】python 运行.py examples/test_cli外壳.light 退出码 0；对标清单.json 追加 #255 卡（原版包=apps/cli + bundle/headless-runner；光明模块=src/cli外壳.light + src/总入口.light；状态=done；本轮目标=CLI 参数解析+斜杠派发+无头运行器；反跑判据=上述 3 组）。不 commit。
```

---

## —— 任务线 B：宿主/OS 集成总线（让「登记」宿主面真正接桩可调用） ——

```
你在 G:\dswork\duan-light-merge\lightharness 工作。上游大量宿主面能力在光明侧已有纯逻辑 `.light` 但从未被调用方接上（卡状态停在「登记不移植」）。本线把下列宿主面单元**接上宿主桩/接口契约**，使它们从「死代码」变「可被运行链调用」。

【统一先读】
- 各卡 原版包 指向的上游 packages/<pkg>/src/*.ts（纯逻辑面逐行读，真实 OS 面只读不改、登记为宿主面）。
- 光明既有宿主桩：src/宿主IO.light（IO 结果统一形状+取消令牌+超时重试原型）、src/子进程.light、src/沙箱.light、src/真实HTTP客户端.light、src/真实抓取提供.light、src/钩子.light、src/acp内容.light、src/acp转码.light。
- 上游 docs/subsystems/{web,webhook,hooks,sandbox,subprocess,ssh,credentials,storage}.md 取语义与契约。

【逐卡接线（每张独立成段，落点文件见卡）】
- #256 远端 API 总线（api/remotes）：src/远端总线.light 新增「经 宿主IO 转发到宿主 HTTP/RPC 总线」出口段；纯逻辑转发白名单/通知封装保留。
- #257 ACP 内容准入/投影（acp/content）：src/acp内容.light 接 宿主IO 提供 prompt 抓取/投影；保留纯逻辑准入判定。
- #258 ACP 转码（acp/codec）：src/acp转码.light 接 宿主IO 做 harness 轮次终结帧编解码出口。
- #259 hooks 协议 + 触发（hooks/hook-protocol + core/hooks）：src/钩子协议.light 保留纯逻辑映射；src/钩子.light 新增「经 宿主IO 真正触发宿主钩子」出口（事件域：pre-tool/PostTool/Stop 三域）。
- #260 本地 HTTP(S) 抓取（web/web-fetch）：src/抓取策略.light + src/真实抓取提供.light 接 宿主IO/真实HTTP客户端 做 URL 校验+内容类型分类+实际抓取出口。
- #261 webhook 会话构建（webhook）：src/webhook会话.light 接 宿主IO 做会话构造/消息注入/错误链出口。
- #262 宿主 IO 抽象层提升：src/宿主IO.light 从「原型」提升为正式集成层（补齐取消令牌传播、超时重试、文件 IO 统一形状），供 B 线各单元与 C/E 线复用。

【约束】
- 真实 OS 执行（真实子进程 spawn、真实沙箱 namespace、e2b 云端、凭据提供方）继续以宿主桩 + 接口契约存在；纯逻辑面接桩调用，**不伪造 OS 能力**。
- 每张卡：在对应 `.light` 仅加「接桩出口」段，不改既有纯逻辑段落（与文件互斥表一致）。

【测试】每张卡至少 1 个 examples/test_<模块>_接线.light：纯逻辑段回归绿 + 接桩出口在「宿主桩 mock」下返回预期形状（用 真实HTTP客户端 的 mock 能力入参，同 R103 求值能力手法）。
【反跑】每张卡 2 组：① 接桩出口改成「静默返回空」-> 调用方断言用例立红；② 纯逻辑段改坏 -> 既有用例立红。记「改->红->还原」。
【门禁】各 test 退出码 0；对标清单.json 回填 #256–#262 卡状态=done（本轮目标/反跑判据填写）。不 commit。
```

---

## —— 任务线 C：编排集成（agent-loop / session 投影 / goal-plan / 总装配链） ——

```
你在 G:\dswork\duan-light-merge\lightharness 工作。把「单元」粘成「系统」：让代理循环、会话消息投影、目标轮驱动、计划模式、预设/团队/子代理装配真正串起来。

【先读】
- 上游 core/agent-loop src/index.ts（inbox 异步化语义）、core/session src/surface.ts（message projection 事件解释器）、packages/goal/goal-round-driver、packages/plan/plan-mode、packages/preset/agent-preset-registry。
- 光明既有：src/代理循环.light（轮次/步骤/检查点/中止 状态机）、src/会话格式.light（V3/V4 catalog）、src/目标轮驱动.light（已存在）、src/计划模式.light（已存在）、src/预设切换.light + src/预设挂载过滤.light（R103/R104）、src/代理团队.light、src/子代理核心.light、src/总入口.light（跑一轮:217）。

【复刻/接线】
- #269 agent-loop inbox 异步化：src/代理循环.light 新增「inbox 缓冲 + 异步入队」段（光明用 任务事件总线.light / 双端队列.light 承载，不引线程），跑一轮 前先排空 inbox；保留既有状态机。
- #270 session message projection 事件解释器：src/会话格式.light 新增「事件->消息投影」段（对齐 surface.ts 的 projected message 解释器），供 代理循环 每轮后刷新消息表。
- #271 goal-round-driver 接 目标折叠：src/目标轮驱动.light 接 目标折叠.light 的 判定模型可恢复（R5 已移植），goal 暂停/恢复走同一闸门。
- #272 plan-mode 接 代理循环：src/计划模式.light 暴露「是否计划模式 + 首轮标题抽取 + 配置校验」给 跑一轮，计划模式下禁止写操作（沿用 权限.light 闸门）。
- #273 总装配链：src/总入口.light 的 跑一轮 改为「解析预设 -> 装配挂载集(R103/R104) -> 注入团队/子代理注册表 -> 代理循环按 inbox 驱动 -> 每轮后 会话格式 投影刷新」。⚠️ 仅扩展装配次序，不改 交互循环/执行运行 既有路径（与 A 线分区）。

【测试】examples/test_编排装配.light：① 标准预设跑一轮后消息表含投影刷新；② 目标暂停后恢复走 判定模型可恢复 闸门；③ 计划模式下写工具被 权限 拦；④ inbox 异步消息被下一轮消费。既有 test_代理循环.light、test_预设*.light、test_目标*.light 回归绿。
【反跑】3 组：① 代理循环 去掉 inbox 排空 -> 异步消息丢失用例立红；② 会话格式 投影解释器改坏 -> 消息表形状用例立红；③ 计划模式 去掉写拦截 -> 写拦截用例立红。记「改->红->还原」。
【门禁】python 运行.py examples/test_编排装配.light 退出码 0；对标清单.json 回填 #269–#273；#274（事件循环×套接字，light-merge stdlib 侧）若本轮动手则一并回填，否则登记为 第7轮。不 commit。
```

---

## —— 任务线 D：apps/web ↔ webui/ 架构对齐 ——

```
你在 G:\dswork\duan-light-merge\lightharness 工作。上游 apps/web 是完整 React 客户端；lightharness webui/ 已有 app.js/index.html/messages.js/sidebar.js/tool-card.js/style.css 但覆盖不全。本线做「架构对齐 + 缺失模块补完」。

【先读】
- 上游 apps/web/src 模块树（conversation list / settings / model picker / streaming render / attachment upload / slash command palette / session resume）。
- 光明 webui/ 现有 5 个 js + html + css，以及 src/web服务器.light（R5 第5步已接 取预设注册表，presets=standard/cordis/ptc/minimal）。

【复刻内容】
1. 比对表：逐模块列出 apps/web 功能点 vs webui/ 现状（覆盖/缺失/差异），写入 docs/功能对标/apps_web对齐.md。
2. 补完缺失客户端模块（优先：会话清单+恢复、模型/预设选择器（复用 R5 mode-select）、附件上传、流式渲染增强、斜杠命令面板）。
3. 与 B 线 真实抓取提供 / C 线 预设装配 对齐：前端 preset 选择须命中 总入口 取预设注册表 四键。

【测试】浏览器手测清单（Playwright，沿用 R5 第5步验证手法）：四预设切换、会话恢复、附件上传、流式输出。附 手测记录 到交付报告。
【门禁】webui/ 改动不破坏既有；apps_web对齐.md 产出；对标清单.json 追加 #275（原版包=apps/web；光明模块=webui/*；状态=done/已核对；本轮目标=架构对齐+缺失模块补完）。不 commit。
```

---

## —— 任务线 E：已落地单元批量接线（第一批） ——

```
你在 G:\dswork\duan-light-merge\lightharness 工作。下列 `.light` 单元已存在但未接入运行链（卡停在「登记不移植」）。本线把它们接到对应调用方，使其真正生效。第一批优先清单（其余登记为 第7轮）：

【接线清单（卡号 -> 文件 -> 调用方）】
- #276 typert 类型系统/协议/注册（packages/typert）：src/类型系统.light + src/typert协议.light + src/类型注册.light -> 接 客户端.light 类型推断 / 工具参数 schema 校验。
- #277 会话冷读（session-query cold-read）：src/会话冷读.light -> 接 总入口.列出会话 / 会话存储。
- #278 会话日志增量（session-log-deepseek）：src/会话日志增量.light -> 接 会话.light 事件落盘。
- #279 会话持久化 JSONL：src/会话持久化JSONL.light -> 接 会话存储.light 读写路径。
- #280 会话标题族：src/会话标题族.light -> 接 会话标题.light。
- #281 会话引用深化（session-reference）：src/会话引用深化.light -> 接 会话引用.light。
- #282 web 三提供商搜索（web/web-search）：src/搜索提供商.light -> 接 工具注册表（search 工具）。
- #283 Office→PDF 队列：src/office转PDF.light -> 接 工具注册表（office 工具）。
- #284 tool-fs 行级 LCS 块差异：src/工具_写文件.light 补 行级 LCS 段 -> 接 写文件 工具结果信封。
- #285 attachment 等比/长边投影：src/附件准入.light 补 投影段 -> 接 消息.light 附件块。
- #286 sandbox 失败签名匹配：src/沙箱.light 补 失败分类段（⚠️ 与 B 线 沙箱 段落分区，冲突则本线挂 src/沙箱深化.light）。
- #287 feedback 命令/消息反馈 + 乐观锁 CAS：src/反馈.light -> 接 交互循环 反馈记录。
- #288 interaction 审批/权限预设（interaction + permission-presets）：src/审批.light + src/交互命令.light -> 接 权限.light 闸门。
- #289 deliverables 工作区变更 / tool-present：src/工作区变更.light + src/交付呈现.light -> 接 交付.light。
- #290 experimental 团队/代理团队工具：src/团队工具.light + src/代理团队.light -> 接 代理团队.light 注册。

【约束】每张卡仅加「接线出口」段到调用方，改既有纯逻辑须先 grep 确认无重复实现；与 B/C 线文件重叠按 §2 互斥表分区。

【测试】每张卡至少 1 个 examples/test_<模块>_接线.light：纯逻辑段回归绿 + 接线后调用方拿到预期结果。
【反跑】每张卡 2 组（接线断 -> 调用方用例红；纯逻辑改坏 -> 既有用例红），记「改->红->还原」。
【门禁】各 test 退出码 0；对标清单.json 回填 #276–#290。不 commit。
```

---

## 路M：收口元任务（波及核对 + 全量回归门禁 + 对标清单回填 + 交付报告）

```
你在 G:\dswork\duan-light-merge\lightharness 工作，负责第6轮合流收口。

【波及核对】
- 复用 _taskM_波及核对.py（v2，TOUCHED 集合更新至第6轮：cli外壳/总入口/代理循环/会话格式/目标轮驱动/计划模式/远端总线/抓取策略/真实抓取提供/webhook会话/钩子协议/宿主IO/类型系统/typert协议/类型注册/会话冷读/会话日志增量/会话持久化JSONL/会话标题族/会话引用深化/搜索提供商/office转PDF/工具_写文件/附件准入/沙箱/反馈/审批/交互命令/工作区变更/交付呈现/团队工具/代理团队 + webui/*）。
- 预计算上游 git diff 增量包路径（e5b5ccbfcb 锚点），逐卡判定覆盖；输出 _taskM_波及核对_out_r6.txt。

【合入零冲突】
- A/C 共享 总入口.light 但分区（A 改 主() 入口、C 改 跑一轮 装配），合并前用 git diff 复核无段落交叠。
- B/E 重叠文件（沙箱/子进程）按 §2 新文件兜底（沙箱深化/子进程深化）。

【回归门禁】
- 全量：LIGHT_MERGE=light-merge 跑 scripts/ci_test.py（或等价全量），记录 passed/failed，既有失败（test_agentE5钩子 / test_压缩E5）维持基线口径，新增用例须全绿。
- 各线 test 文件退出码 0。

【对标清单回填】
- 第6轮各线追加/回填卡（#255–#290），字段齐：编号/功能/原版包/光明模块/状态(=done)/证据/本轮目标/反跑判据/语言缺陷。
- 47 张「登记(不移植)」中本轮接线者状态翻 done；仍宿主绑定的（真实沙箱 namespace/e2b/凭据提供方/desktop 系）维持登记并在 状态 注明「第6轮确认：宿主面持续登记」。

【交付报告】
- 写 docs/功能对标/第6轮_体系收口_交付报告.md（沿用第5轮结构：目标结果一览/各线摘要/改动文件/回归门禁/路M 合入/波及核对）。
- 含「第7轮展望」：剩余未接线单元、desktop/desktop-host 外壳、事件循环×套接字集成回归、bulk 单元第二批。
```

---

## 3. 本轮不做 / 后续轮展望

- **apps/desktop、apps/desktop-host**：Electron 原生壳 + 原生能力桥，体量巨大且强宿主绑定，留待独立轮（第8轮级）。
- **真实 OS 执行内核**（真实子进程 spawn、真实沙箱 namespace/seccomp、e2b 云端、凭据提供方 OS 集成）：持续以宿主桩 + 接口契约存在，不伪造；接桩出口本轮回填，真内核留平台侧。
- **事件循环 × 套接字集成回归（#206/#207）**：属 light-merge stdlib 侧，跨仓，登记第7轮。
- **E 线未列的剩余「登记」单元**：批量接线第二批，第7轮。
- **github 合流续推**：代理通畅后用 `python _push_github_api.py` 续推（保留脚本）。

> 第6轮定位为「体系收口第一轮」：把已落地的 61 个单元从岛屿接成系统，并建起应用外壳（CLI）与宿主/OS 集成总线骨架。完整体系复刻仍需第7–8轮。
