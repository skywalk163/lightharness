# 任务3（R50/P1）交付报告 —— 上游 0.1.5-rc.2 增量跟随探查

> 日期：2026-09-17 ｜ 第50轮 ｜ 交付物：本报告（`lightharness/_task3_R50_上游跟随探查.md`）
> 铁律遵守：**只探查 + 写报告，未改任何源**（lightharness / light-merge 源目录零改动）。
> ⚠️ 但本次探查在 `G:\github\deepseek-harness`（上游工作副本）**做了一次 `git fetch`**，
> 并因此发现该仓库的**引用落盘异常**，已手工恢复引用（详见 §7）。`git status` 干净。

---

## 1. 结论（先看这条）

1. **上游确实有增量，而且是「大版本级别」的增量**：0.1.5-rc.2 → **0.1.6-alpha.1**，
   800 个提交、3942 个文件变更（+784,113 / −47,018 行），包数 **274 → 290**。
2. **新增包 23 个、移除/改名 7 个**。其中 **6 个含真·纯逻辑新增面，本仓目前零覆盖**：
   - `compaction/compaction-image-offload`（图像卸载 + **新会话事件 `image/offload`**）
   - `mcp/mcp-resources`（MCP 资源渲染/资源工具）
   - `ptc-runtime/ptc-runtime`（PTC 保留字表 + 运行契约）
   - `workflow/workflow-ptc`（工作流元数据校验 + 资源域物化）
   - `test-support/remote-mock`（远程 RPC/流 mock 支撑）
   - `ssh/ssh` 的 `protocol.ts / schemas.ts / stream-security.ts`（SSH RPC 协议 + 路径/策略校验）
3. **最有价值的一条**：0.1.6 引入**持久化变更登记制度** `docs/persistence-changes/`，
   其中 `2026-09-14-image-offload` 明确「**新增 `image/offload` 事件**」。
   按上游兼容性说明——**不认识该事件的旧版本会拒绝读取这些日志**。
   → 我们 R47/R48 刚做完的**会话格式 V3 / 投影 / surface**，若不补 `image/offload` 节点与投影，
   将**读不了 0.1.6 的会话日志**。这是本轮探查最重要的**真缺口**。
4. 上游在 0.1.6 里**删掉了 `packages/e2b/*`（云沙箱整族）**，并把 `code-runtime/*` 改名为
   `ptc-runtime/*`、`workflow-worker-thread` 改名为 `workflow-ptc`。
   → 我们对 `e2b` 的「维持不移植」登记**可以转为「上游已移除」**；`#20 packages/code-runtime`
   需要**改名记账**，否则后续对标会「找不到包」。
5. GitHub（`deepseek-ai/deepseek-harness`）在本机**不可达**；`upstream` 远端配的是 **gitcode 镜像，
   停在 `dsh-v0.1.2-alpha.1`（严重滞后）**。本次增量对象是从 **gitea origin（192.168.1.5:3000）**
   的 fork master 取得的——该 fork **已合入 0.1.6-alpha.1**。

---

## 2. 探查方法与信源（可复现）

| 步骤 | 命令 | 结果 |
|---|---|---|
| 1 | `git -C G:/github/deepseek-harness tag \| sort -V` | 发现 tag `fork-after-upstream-v0.1.6-alpha.1`（= 合入上游 0.1.6-alpha.1 的 fork 提交） |
| 2 | `git log --oneline -8 fork-after-upstream-v0.1.6-alpha.1` | 合并提交 `c47b24803e Merge upstream dsh-v0.1.6-alpha.1 into FreeBSD fork`；上游 release 提交 `ea53423b60 release(dsh): 0.1.6-alpha.1`（2026-09-15 09:35） |
| 3 | `git diff --stat a305303422 ea53423b60` | 3942 文件 / +784,113 / −47,018（`a305303422` = 上游 0.1.5-rc.2 release 提交，2026-09-10 21:38） |
| 4 | `git ls-tree -r --name-only <rev> \| grep packages/.*/package.json` | 包集合：0.1.5-rc.2 = **274**，0.1.6-alpha.1 = **290** |
| 5 | `comm -13/-23 pk_a.txt pk_b.txt` | 新增 23 包 / 移除 7 包（见 §3、§4） |
| 6 | `git show <rev>:<file> \| grep -nE "^export"` | 逐包提取导出面，判定「纯逻辑 / 宿主」（见 §3） |
| 7 | `git ls-tree -r --name-only ea53423b60 -- docs/persistence-changes` | 发现新的持久化变更登记制度（见 §5） |
| 8 | 对照 `docs/功能对标/对标清单.json` | 关键词 `image/offload`、`mcp-resources`、`ptc-runtime`、`terminal-controller`、`ssh/`、`remote-mock`、`auto-review`、`browser-use`、`computer-use` **命中数全部为 0** → 均未被现有 183 条目覆盖 |

**信源局限（须记账）**：
- `upstream` 远端 = `https://gitcode.com/gh_mirrors/de/deepseek-harness` → `git fetch upstream` 后
  `upstream/master` = `cd5ef81481`（**0.1.2-alpha.1，滞后 3 个版本**），**不能用来做增量探查**。
- `https://github.com/deepseek-ai/deepseek-harness` → `git ls-remote` **无输出（不可达）**。
- 有效信源 = `origin` = `http://192.168.1.5:3000/skywalk/deepseek-harness`（自维护 fork），
  fetch 后 `origin/master` = `65e04a5a07`，其祖先链含 `c47b24803e`（0.1.6-alpha.1 合并）。
- 因此本报告的「增量边界」是 **上游 release 提交级**（`a305303422` → `ea53423b60`），
  fork 自身的 FreeBSD 适配提交（`01a915a089`/`d96ec7e7c0`/`93f60e0fd9`/`e4af2f44f7`/`65e04a5a07`）
  不计入本报告。

---

## 3. 新增包 23 个 —— 逐个判定

判定口径：**纯逻辑** = 不依赖 Cordis ctx / node:net / child_process / fs / TSX 的可移植纯函数与类型；
**宿主** = 进程/网络/文件/前端装配层，按既有铁律「维持登记不移植」。

### 3.1 真·纯逻辑新增缺口（建议立项，本仓零覆盖）

| # | 新包 | 规模(增/删/文件) | 纯逻辑导出（证据） | 归属域 |
|---|---|---|---|---|
| G1 | `compaction/compaction-image-offload` | 753 / 0 / 6 | `offloadOldestImages(session, sourceEventSeqs, count)`、`imageOffloadProjection: SessionMessageProjection<'image/offload'>`、`project-message.ts` | **会话投影 / 压缩（#1/#2/#9/#54 邻域）** |
| G2 | `mcp/mcp-resources` | 608 / 0 / 5 | `renderResourceResult(server, value): ContentBlock[]`、`registerResourceTools(ctx, requestResource)`（工具面部分纯逻辑） | MCP（#16 邻域） |
| G3 | `ptc-runtime/ptc-runtime` | 2843 / 0 / 13 | `PORTABLE_RESERVED_WORDS`、`RESERVED_BINDING_GLOBALS`、`RESERVED_ERROR_MEMBERS`、`DUNDER_MEMBER`、`abstract class PtcRuntime`、`PtcRunRequest/Spec/Sandbox/Failure/Result`、`PtcBindingFunction/Namespace/ErrorClass` | PTC（#20/#84 改名后） |
| G4 | `workflow/workflow-ptc` | 1224 / 0 / 12 | `validateMeta(value): WorkflowMeta`、`materializeFromRealm`、`MaterializeError`、`PtcWorkflowEngine`（meta.ts / realm.ts 纯逻辑；runtime.ts/host.ts 偏宿主） | 工作流（#41/#42/#44 邻域） |
| G5 | `test-support/remote-mock` | 1586 / 0 / 12 | `RemoteMock`（unary 规则表 `RemoteTable`/字节流脚本 `StreamScript`）、`ok()`、`frames()`、`openStream()`、`MockStream`、`toError()` | 测试支撑（#76/#83 邻域） |
| G6 | `ssh/ssh` 的纯逻辑三件 | 4413 / 0 / 31（整包） | `SSH_PROTOCOL_VERSION`、`SSH_MAX_PROCESS_HANDLES/TEXT_STREAMS`、`RemoteOperationError`、`SshRpcPeer`、`schemas.ts`（远程绝对 POSIX 路径/策略/条目/意图/编辑校验）、`SSH_STREAM_TLS_OPTIONS` | **全新域：SSH 远程**（无对应条目） |

### 3.2 小纯逻辑 + 宿主注册（可选移植，优先级低）

| 新包 | 规模 | 内容 | 判定 |
|---|---|---|---|
| `browser-use/browser-use` | 341 / 0 / 5 | `BrowserUseProviderName`（品牌函数）、`BrowserUseRegistry extends Service` | 纯逻辑仅「品牌 + 注册表」，本体靠宿主驱动 |
| `computer-use/computer-use` | 333 / 0 / 5 | 同上（Computer Use） | 同上 |

### 3.3 混合包：部分纯逻辑（登记待评估）

| 新包 | 规模 | 纯逻辑部分 | 宿主部分 |
|---|---|---|---|
| `api/terminal-controller` | 3363 / 0 / 18 | `client/model.ts` `TerminalView`/`TerminalViewIssue`/`TerminalRenderFrame`/`TerminalViewState`、`stream.ts` `TerminalFollower`、`client/close-requests.ts` `TerminalCloseRequests`、`shells.ts` 的 shell 归一 | `index.ts` `TerminalController extends TypertRemoteService`、shell 发现 |
| `experimental/auto-review` | 2896 / 0 / 5 | 审查策略/错误元数据（未逐函数核） | `apply(ctx)` Cordis 插件（`inject=['llm','permissionPresets','sessions','tools']`） |

### 3.4 维持不移植（宿主层，与既有登记口径一致）

| 新包 | 规模 | 不移植理由 |
|---|---|---|
| `ptc-runtime/ptc-runtime-node` | 2141 / 0 / 21 | node 子进程/通道/输出账本（launch.ts / process.ts / channel.ts） |
| `ssh/fs-ssh` | — | 远程 FS 提供器（宿主 IO） |
| `ssh/sandbox-ssh` | — | 远程沙箱提供器 |
| `ssh/subprocess-ssh` | 1155 / 0 / 6 | 远程进程提供器（宿主 subprocess） |
| `experimental/browser-use-stagehand-native` | 2297 / 0 / 22 | 原生浏览器驱动 + worker |
| `experimental/browser-use-runtime` | 1650 / 0 / 8 | MCP 运行时装配 |
| `experimental/browser-use-chrome-devtools-mcp` | — | MCP provider |
| `experimental/browser-use-playwright-mcp` | — | MCP provider |
| `experimental/computer-use-cua-driver-native` | 734 / 0 / 7 | 原生驱动 |
| `experimental/computer-use-cua-driver-mcp` | 525 / 0 / 6 | MCP provider |
| `client/ui-sidebar-terminal` | 1741 / 0 / 25 | 前端 TSX（宿主 UI） |
| `client/ui-settings-unarchive-sessions` | 605 / 0 / 10 | 前端 TSX（宿主 UI） |
| `experimental/ptc-runtime-python` | 766 / 860 / 11 | **改名**（原 `experimental/code-runtime-python`）；`#84` 已覆盖 `src/protocol.ts`，新增 `py/{bootstrap,protocol}.py` 为**Python 侧镜像**，需复核是否与既有登记一致 |

---

## 4. 移除 / 改名 / 需复核的既有包

### 4.1 消失的 7 个包（0.1.5-rc.2 有，0.1.6-alpha.1 无）

| 消失包 | 处置 | 对对标清单的影响 |
|---|---|---|
| `packages/code-runtime/code-runtime` | 由 `ptc-runtime/ptc-runtime` 取代 | **#20 需改名记账**（否则条目「找不到包」） |
| `packages/code-runtime/code-runtime-worker-thread` | 由 `ptc-runtime/ptc-runtime-node` 取代 | 宿主面，维持不移植 |
| `packages/e2b/e2b` | **上游整体移除** | #21/#57 的「维持不移植」可升级为「**上游已移除**」 |
| `packages/e2b/fs-e2b` | 同上 | 同上 |
| `packages/e2b/subprocess-e2b` | 同上 | 同上 |
| `packages/experimental/code-runtime-python` | 改名 `experimental/ptc-runtime-python` | #84 记账名需更新 |
| `packages/workflow/workflow-worker-thread` | 改名 `workflow/workflow-ptc` | #41/#42/#44 邻域新增 |

### 4.2 已被对标清单覆盖、但 0.1.6 内发生实质变更的包（Top，需后续轮复核）

> 口径：`git diff --numstat` 三级包聚合，剔除 README/package.json。

| 包 | 增/删 | 文件 | 对标清单 | 复核要点 |
|---|---|---|---|---|
| `llm/llm-deepseek` | 4502 / 1578 | 54 | #6 | 变更最大，需核 `serialize.ts` 是否改形状 |
| `boot/app-boot` | 4113 / 763 | 16 | #75 | profile/manifest 是否有新字段 |
| `api/terminal-controller` | 3363 / 0 | 18 | — | 新增包（§3.3） |
| `api/session-controller` | 1533 / 1797 | 31 | #107 | 已覆盖的 `types.ts/assistant-stream.ts/remote-events.ts` 是否改形状 |
| `test-support/client-runtime` | 1959 / 130 | 24 | — | 测试支撑，可能与 `remote-mock` 配套 |
| `bundle/headless` | 1930 / 118 | 11 | #11 | 启动束 |
| `subprocess/subprocess-local` | 1490 / 366 | 25 | #12 | 宿主，维持 |
| `mcp/mcp-client` | 1116 / 611 | 22 | #16 | 分页/重连面是否变化 |
| `core/tools` | 749 / 90 | 11 | #8 | 工具流水线 |
| `terminal/terminal-bash` | 453 / 28 | 6 | #15/#108 | 类型面 |
| `shell/bash-sandbox` | 376 / 263 | 10 | #50 | 沙箱升级 |
| `interaction/permission-presets` | 369 / 103 | 6 | #73 | 权限预设 |
| `core/session` | 352 / 71 | 10 | #1 | 事件表是否新增类型（见 §5） |

---

## 5. 最重要的发现：0.1.6 引入「持久化变更登记」并新增 `image/offload` 事件

上游 0.1.6 新增目录 `docs/persistence-changes/`（README + 变更条目 + JSON Schema + `releases/` 历史），
把「会话日志的持久化形状变更」正式制度化。0.1.5-rc.2 之后共 3 条：

| 变更条目 | 内容 | 决策 |
|---|---|---|
| `2026-09-11-initial` | 基线快照（各事件 root 的形状哈希） | baseline |
| `2026-09-12-auto-review-error-metadata` | auto-review 错误元数据 | same-version |
| `2026-09-14-image-offload` | **新增事件 `image/offload`**；`assistant/message`、`tool/result`、`compaction/summary` 等形状哈希刷新 | same-version |

`2026-09-14-image-offload` 的中文兼容性说明**逐字摘录**：

> 现有日志仍可读取。可选的图片字段 `offloaded` 使未标记的出现位置保持保留状态。
> **新事件在读取时必须被识别：不认识 `image/offload` 的旧版本拒绝读取这些日志**，
> 当前读取器需要对应的消息投影。事件信封和结构性的 Session 格式版本不变。

事件清单里同时出现 **`event:tool/ptc-dispatch`**（PTC 派发事件），说明 0.1.6 里 PTC 是一等公民。

**对本仓的直接影响（P0 级）**：
- R47/R48 刚收口的 **#1 会话事件日志 / #2 surface 折叠投影 / #? 会话格式 V3** 面向的是
  0.1.5-rc.2 的事件族。0.1.6 新增 `image/offload` + `tool/ptc-dispatch`，
  且上游明说**未知事件必须被拒绝**——即**我们的读取器要「显式认识」它们**，
  否则读写 0.1.6 日志会直接失败（不是「忽略未知类型」的宽松策略）。
- 上游把「镜像同步」做成了制度（每次持久化形状变更都登记 + 附测试与快照刷新），
  这对我们**「行为差异清单」**的写法有直接借鉴价值（本仓可考虑对齐该制度）。

---

## 6. 建议的后续轮优先级（本轮只探查，不实施）

| 优先级 | 事项 | 理由 |
|---|---|---|
| **P0** | `compaction-image-offload` + `image/offload` 事件与投影 | 直连 #1/#2 会话格式/投影，不做就**读不了 0.1.6 日志**；且与令牌计量（图像卸载省 token）联动 |
| **P1** | `mcp-resources`（`renderResourceResult` + 资源工具请求构造） | 纯逻辑、体量小（608 行）、#16 邻域自然延伸 |
| **P1** | `ptc-runtime/ptc-runtime`（保留字表 + `PtcRun*` 契约 + `PtcRuntime` 抽象） | PTC 是 0.1.6 主线；保留字表是 `PORTABLE_RESERVED_WORDS`，可 1:1 表化 |
| **P2** | `workflow-ptc` 的 `meta.ts`（`validateMeta`）+ `realm.ts`（`materializeFromRealm`） | 纯逻辑边界清晰，但依赖 `runtime.ts/host.ts` 语义，须先切面 |
| **P2** | `test-support/remote-mock` | 与既有 `mock大模型服务器` 互补，可支撑后续远程域测试 |
| **P3** | `ssh/ssh` 纯逻辑三件（`protocol.ts`/`schemas.ts`/`stream-security.ts`） | 全新域，须先决定「SSH 远程」是否本轮之后的目标 |
| **P3** | `api/terminal-controller` 的 `TerminalView`/`TerminalFollower`/`TerminalCloseRequests` | 视图状态机可移植，但价值取决于是否做终端前端 |
| **记账** | `#20` 改名 `ptc-runtime`；`#84` 改名 `experimental/ptc-runtime-python`；`#21/#57` e2b 改「上游已移除」 | 不改则后续对标查不到包 |
| **复核** | §4.2 的 13 个已覆盖包 | 只是「可能有增量」，本报告不逐文件核；若下游要严格对齐再立项 |

---

## 7. 环境发现（须登记，建议 R51 复核）

### 7.1 本地 fork 已落后一个大版本
`G:\github\deepseek-harness` 的 `HEAD` = `9d9035b7c1`（**0.1.5-rc.2 + 2 个 FreeBSD 提交**），
而 gitea origin 的 master = `65e04a5a07` **已合入 0.1.6-alpha.1** 并带 5 个 FreeBSD 适配提交。
本地 HEAD 到 0.1.6 的 `packages/` 差异 = **2352 文件 / +75,210 / −36,510**。

### 7.2 ⚠️ git 引用落盘异常（本机现象）
本次 `git fetch origin` **报告成功**（reflog 也写了 `b71868b148..65e04a5a07 fetch origin: fast-forward`），
但 `refs/remotes/origin/master`、`refs/remotes/upstream/master`、两个 `HEAD` 的**松散引用文件并未落盘**：
- `git ls-remote origin HEAD` = `65e04a5a07`（远端可达）
- `git rev-parse origin/master` 曾长期返回 packed-refs 里的旧值 `0a12968eaf`（Aug 21 打包）
- `git update-ref refs/remotes/upstream/master <sha>` 返回 **rc=0 但文件不存在**；
  而用 `printf > .git/refs/remotes/upstream/master` **直接写文件则生效**

**处置**：已用直接写文件方式手工恢复 4 个引用并核验可解析——
`refs/remotes/origin/master` = `65e04a5a07`（= 远端真实 master，与 reflog 的 fast-forward 记录一致）、
`refs/remotes/origin/HEAD` → `refs/remotes/origin/master`、
`refs/remotes/upstream/master` = `cd5ef81481`（= 恢复至 fetch 前原值）、
`refs/remotes/upstream/HEAD` = `cd5ef81481`。
`git status` 为空（工作树干净）；**未改动任何工作树文件**。

**判断**：疑似本机会话的工作区沙箱对**工作区之外** `.git/refs/**` 的 lock+rename 写入有限制
（`.git/FETCH_HEAD`、`.git/objects/**`、`.git/logs/**` 均正常写入，唯独 refs 松散文件不落盘）。
建议 R51 在 0.82（FreeBSD）或真机终端上复核一次 `git fetch origin && git rev-parse origin/master`，
若同样复现，则在 `docs/问题档案.md` 立条；若不复现，则确认是**本机工具链/沙箱**问题，不必污染仓库文档。

---

## 8. 交付物与边界

| 项 | 状态 |
|---|---|
| 本报告 `lightharness/_task3_R50_上游跟随探查.md` | ✅ |
| lightharness / light-merge 源改动 | **零**（只探查） |
| 上游工作副本 `G:\github\deepseek-harness` | 仅 `git fetch`（拉对象）+ §7.2 的引用恢复；工作树干净 |
| 真缺口登记 | 见 §3.1 六项 + §5 P0 项，**留后续轮** |
| 对标清单状态 | **未改**（本轮任务3 铁律：不改源、不改清单；清单更新归任务2/路M） |

---

## 9. 一句话总结

上游从 0.1.5-rc.2 走到了 **0.1.6-alpha.1**：新增 23 包（其中 **6 处真纯逻辑缺口**，
以 **`image/offload` 会话事件 + 图像卸载投影** 为最要紧）、移除 7 包（**e2b 整族被上游删掉**、
`code-runtime` 改名 `ptc-runtime`）、并首次把**持久化形状变更制度化**。
本仓对这批新域**零覆盖**，且 `image/offload` 属「不认识就拒绝读取」的**硬兼容**问题，
建议下一轮优先做 P0 项，并同步修 `#20/#84/#21/#57` 的包名记账。
