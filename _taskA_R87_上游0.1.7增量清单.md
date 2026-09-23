# R87 上游 0.1.7 增量清单（A 路交付物，v3 订正版）

> 轮次：R87 ｜ 2026-09-23 ｜ 产出路：A（只读调研，未提交任何代码）
> **上游源（用户指令订正）**：`http://192.168.1.5:3000/skywalk/deepseek-harness`（本仓库 `origin` = 内网 FreeBSD fork）
> **参考镜像**：gitcode 官方镜像 `dsh-v0.1.7-alpha.2` = `00102833df`（fork 尚未合入，滞后 162 提交）
> 对比锚点：0.1.6-alpha.2 = `ddefc45fbc7f8e46dd73185e68295696d1297887`
> 仓库本地路径：`G:/github/deepseek-harness`

---

## 0. 一句话结论（v3，已用权威 ls-remote 复核）

**上游源按用户指令订正为内网 fork 后，0.1.7 增量真实存在且规模巨大**：内网 fork（`877717787c`，已合入 `dsh-v0.1.7-alpha.1` + FreeBSD 构建对齐）相对锚点 `ddefc45fbc` 有 **1351 提交 / 4821 文件 / +356575 −108915 行**；gitcode 真实上游 `dsh-v0.1.7-alpha.2`（`00102833df`）为 **1461 提交 / 4995 文件**（fork 滞后 162 提交）。

⚠️ **前两轮错判已作废说明**：09-22 曾误用 gitcode 镜像得出"无增量"；09-23 初又因 shell shim 污染本地引用、读到过期的 `518bcf5b` fork 旧态而误报"47 提交/0 纯逻辑/882 滞后"。本次用 `git ls-remote` 直查两端权威 HEAD + 显式 SHA diff，结论以本 v3 为准。

---

## 1. 核验证据（权威，可复现）

| 步骤 | 命令 | 结果 |
|---|---|---|
| 内网 fork 权威 HEAD | `git ls-remote origin \| grep HEAD` | `877717787c435cc3ee8187b62a0b39110f70ad69` |
| gitcode 权威 HEAD | `git ls-remote upstream \| grep HEAD` | `00102833dfaee1da9f48a3a8eae9d34005a75218` = `dsh-v0.1.7-alpha.2` |
| 锚点是否 fork 祖先 | `git merge-base --is-ancestor ddefc45fbc 877717787c` | YES（fork 含 0.1.6-alpha.2） |
| 锚点是否 0.1.7 祖先 | `git merge-base --is-ancestor ddefc45fbc 00102833df` | YES（0.1.7 含 0.1.6-alpha.2） |
| fork 增量提交数 | `git rev-list --count ddefc45fbc..877717787c` | **1351** |
| fork 增量规模 | `git diff --shortstat ddefc45fbc 877717787c` | **4821 files, +356575 / −108915** |
| gitcode 0.1.7 增量 | `git diff --shortstat ddefc45fbc 00102833df` | **4995 files, +371557 / −118376** |
| fork↔0.1.7 滞后 | `git rev-list --count 877717787c..00102833df` | **162 commits**（fork 未合 alpha.2） |
| fork 纯逻辑包文件数 | `grep packages/(llm\|core\|api\|client\|shell\|subagent\|…)` | **1092 files**（占 1264 包文件 86%） |

---

## 2. 增量清单（按包/能力分类，覆盖 packages 下 100% 变更包）

> 类别：逻辑面 = 消息/协议/序列化/状态机/令牌计量/会话/上下文/编排/配置语义；宿主面 = 原生插件/系统调用/shell/平台实现/CI；架构面 = 模块拆分/装配/生命周期/插件机制。
> 处置：移植 = 搬进 `.light`；登记 = 宿主能力登记（C 路）；架构建议 = 评估是否跟随。

### A. 纯逻辑面（待移植 — lightharness 功能/协议对齐，共 1092 文件）

| 主题 | 上游包（文件数） | lightharness 对应 / 处置 |
|---|---|---|
| 核心运行时与协议 | `core`(72)、`llm`(64)、`api`(88)、`typert`(23)、`interaction`(6)、`acp`(8)、`mcp`(4)、`lsp`(4)、`sdk`(7)、`ssh`(8)、`webhook`(7)、`credentials`(10)、`storage`(5)、`document`(6)、`identity`(1)、`attachment`(2)、`deliverables`(4)、`spill`(3)、`guard`(3)、`ptc-runtime`(2)、`runtime-diagnostics`(1)、`feedback`(2)、`todo`(2) | 高优先：llm/core/api 是语言层核心，需逐包对齐（多数"需新建 .light 模块"） |
| 会话与上下文 | `session`(21)、`session-query`(1)、`context`(17)、`compaction`(12)、`schedule`(12) | 会话/上下文压缩/调度语义，对齐 lightharness 会话与上下文模块 |
| 智能体与编排 | `subagent`(34)、`workflow`(10)、`skill`(10)、`goal`(9)、`plan`(4)、`jobs`(32)、`experimental`(42)、`boot`(42) | 子智能体/工作流/技能/目标规划——lightharness 已有对应概念，需增量对齐 |
| 命令与执行 | `shell`(75)、`workspace`(7)、`computer-use`(1)、`browser-use`(1) | shell 命令语义、workspace 操作——对齐 lightharness 执行/工具层 |
| 配置与扩展 | `settings`(23)、`preset`(27)、`bundle`(28)、`extensions`(17)、`hooks`(9)、`util`(31)、`web`(11)、`test-support`(25) | 预设/打包/扩展/钩子——评估 lightharness 配置与扩展机制 |
| 客户端/UI 逻辑 | `client`(339) | 部分属 web 宿主面；纯逻辑部分（状态管理/数据流）待移植，UI 渲染部分登记 |

### B. 宿主面（登记不移植 — C 路，共约 12 个包/顶层目录）

| 宿主能力 | 上游位置（文件数） | 登记说明 |
|---|---|---|
| 宿主层平台适配 | `host`(38)、`subprocess`(3, process-inspector FreeBSD)、`terminal`(7, terminal-bash 平台)、`sandbox`(17, jail 后端)、`fs`(24, ripgrep 平台回退) | 平台相关：lightharness 走光明 stdlib，不搬 Node 实现；登记能力名 |
| 原生插件/构建 | `native`(13)、`freebsd`(15)、`patches`(6, node-pty 等)、`vendor`(23) | FreeBSD 原生插件/补丁：lightharness 无对应 Node 层 |
| CI / 构建 / 站点 | `.gitea`(7)、`.github`(8)、`scripts`(113)、`website`(11) | 上游 CI 无 FreeBSD（仅 linux/macos/win 矩阵）；lightharness CI 已在 192.168.1.5 gitea，`.gitea` 可作参考 |

### C. 架构面（架构对齐建议 — 评估 lightharness 是否跟随）

| 架构点 | 上游变化 | lightharness 建议 |
|---|---|---|
| 核心装配 | `core`(72) 装配/生命周期变更 | 评估是否跟随；不破坏三平台门禁前提下实施 |
| 沙箱隔离选型 | `sandbox` 引入 FreeBSD **jail 后端** | lightharness 已在 0.82 自建 sandbox（非 jail）；登记为"上游 FreeBSD 隔离选型=jail"，评估是否对齐（暂缓） |
| 协议插件机制 | `mcp`/`lsp`/`acp` 扩展 | 评估 lightharness 插件/协议层是否需对齐 |
| 技能/工作流装配 | `skill`/`workflow`/`experimental`/`boot` | 评估模块拆分与装配方式差异 |
| 前端架构 | `client`(339) 重大重构 | 仅参考，不移植渲染层 |

---

## 3. 对 R87 其它路的影响（协同结论）

| 路 | 结论（v3） | 协同调整 |
|---|---|---|
| **A** | 0.1.7 增量真实存在（fork 1351 / gitcode 1461 提交），逻辑面占 86% | 本清单即为交付物；全量文件级移植规划本身是大型子项目 |
| **B（增量移植）** | fork 增量含 **1092 文件纯逻辑** → 移植 scope 巨大，非"仅复核" | 建议**按包拆子任务**（优先 llm/core/api/session/context/subagent/workflow/skill），逐包出 A 子清单→移植→测试；不要一轮全吞 |
| **C（宿主面登记）** | 宿主面包（host/subprocess/terminal/sandbox/fs/native/freebsd/patches/vendor/CI）须登记 | C 并入上述宿主能力；尤其 jail 沙箱、node-pty 补丁、ripgrep 回退、Gitea CI |
| **M（收口）** | 增量对标结论=0.1.7 已出现（fork alpha.1 + FreeBSD 对齐；gitcode alpha.2 滞后 162） | M 报告据实：移植项按 B 实际进度；架构对齐建议 5 项；标注 fork 滞后 162 提交风险 |
| D / E / F | 独立 | 不受影响，按原计划推进 |

---

## 4. ⚠️ 必读：内网 fork 滞后 gitcode 0.1.7-alpha.2 共 162 提交

内网 fork（`877717787c`）已合 `dsh-v0.1.7-alpha.1` 但**未合 `dsh-v0.1.7-alpha.2`**，差 **162 提交**。因此：

- 以内网 fork 为上游的 A 甄别（本清单）覆盖到 alpha.1 + FreeBSD 对齐；alpha.2 的 162 提交（含 gitcode 后续修复/特性）未含。
- 真正"功能/架构看齐"的完整标的应是 gitcode `dsh-v0.1.7-alpha.2`（1461 提交）。建议 B 路在 fork 口径移植之外，**另立项追 gitcode 0.1.7-alpha.2 的 162 提交差量**（或等 fork 合入 alpha.2 后重跑 A）。

---

## 5. 后续建议

1. **B 路立即开工但按包拆分**：先出 `llm/core/api` 三包的子清单与移植排期（最大风险/最高价值），不要试图一轮吃下 1092 文件。
2. **C 路开工宿主面登记**：把 §2-B 的宿主能力登记进 `lightharness/docs/宿主面登记清单.md`。
3. **上游源已订正**：分发书「上游代码位置」改为内网 fork；gitcode 作参考镜像。锚点 `ddefc45fbc` 有效（两端均含）。
4. 若内网 fork 日后合入 alpha.2，重跑 `git diff ddefc45fbc..origin/master` 即可，本清单结构可复用。
