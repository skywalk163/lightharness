# R87 任务分发 · Agent 执行 Prompt 集

> 轮次：R87 ｜ 上游 = 内网 fork `192.168.1.5:3000/skywalk/deepseek-harness`（`877717787c`，已合 `dsh-v0.1.7-alpha.1`）
> 锚点：`ddefc45fbc`（0.1.6-alpha.2）｜ 增量清单：`R87_上游0.1.7增量清单.md` ｜ 总控：`R87_任务分发书_上游增量对标_宿主面登记_三平台LM补位.md`
> 本文件每个 prompt 均为**自包含**——agent 无需任何会话上下文即可执行。

---

## 0. 分发总览（依赖顺序 / 文件面隔离）

| 编号 | 内容 | 依赖 | 是否动 `src/` | 是否 commit/push |
|---|---|---|---|---|
| **B1** | 移植：llm / core / api（核心协议层） | A 完成 | 是（限本包） | ❌ 不提交 |
| **B2** | 移植：session/context/compaction/schedule + typert/acp/mcp/lsp/sdk | A 完成 | 是（限本包） | ❌ 不提交 |
| **B3** | 移植：subagent/workflow/skill/goal/plan/jobs/experimental/boot | A 完成 | 是（限本包） | ❌ 不提交 |
| **B4** | 移植：shell/workspace/settings/preset/bundle/extensions/hooks/util/web/test-support + client 逻辑部分 | A 完成 | 是（限本包） | ❌ 不提交 |
| **C** | 宿主面登记清单文档（R85 遗留 + A 新登记） | A 完成 | 否（仅 docs） | ❌ 不提交 |
| **D** | 三平台 LM 门禁补位（Win 基线 / FreeBSD 复跑 / 矩阵脚本） | 无 | 脚本/报告 | ❌ 不提交 |
| **E** | flaky 根治（4 条旧账） | 无 | 是（限 flaky 相关） | ❌ 不提交 |
| **F** | 环境固化（0.82 初始化.sh / 0.86 venv 固化） | 无 | 脚本 | ❌ 不提交 |
| **M** | 收口（合流 + 差异清单回填 + 三平台复核 + push） | B/C/D/E/F 全完成 | 是（仅 docs/报告） | ✅ **唯一可 push** |

**铁律（所有 agent 共同遵守）**：
- ⛔ **外发 agent 只改文件 + 验证，绝不 commit / push**；合流与 push 由 **M 路（主 agent）** 统一执行。
- ⛔ `git add <显式文件>`，**绝不 `git add .` / `git add -A`**。
- ⛔ 密钥只进 `.env`，不写进代码/报告。
- ⛔ 不动宿主接线文件（`src/真实HTTP客户端.light`、`src/网页搜索.light` 等）；不把上游 HTTP 实现硬搬成光明网络调用。
- ⛔ 不擅自扩语言语法（先登记到 `docs/多平台差异清单.md` 再议）。
- ⛔ 0.82 / 0.86 只用 `/tmp` 副本与用户级 venv，不碰系统环境。
- ✅ 改完关键文件立刻 `grep` 复核落盘（本机 Edit 偶发"成功未落盘"，务必回读校验）。
- ✅ 幂等补丁必须用**哨兵串**判"已应用"，勿用 `new in text` 判重。
- ✅ light-merge 改动克制：语法核心零改动优先；必须改时回 M 记录并写明理由。

**环境约定（每个 bash 命令前加）**：
```bash
export PATH="/c/Users/skywalk/.workbuddy/binaries/PortableGit/versions/1.2.0/usr/bin:/c/Windows/System32:/c/Windows:$PATH"
```
- 本地仓库根：`G:\dswork\duan-light-merge`（含 `light-merge/` 与 `lightharness/`）
- LM 本机 python：`light-merge/.venv/Scripts/python.exe`
- FreeBSD 0.82：`ai@192.168.0.82`，python `/usr/local/bin/python3.12`；门禁三件套 `LIGHT_MERGE=<LH根>/light-merge PYTHONPATH=<LH根>/light-merge/src PATH=/tmp/r80b-shim:$PATH`
- gitea：`192.168.1.5:3000`（duan 项目 & harness `myrepo`）；github 已恢复可推

---

## 1. B1 · 核心协议层移植（llm / core / api / typert / acp / mcp / lsp / sdk）

```
你是 R87「增量移植实施」的执行 agent（B1 子任务）。把你负责范围内的 deepseek-harness 0.1.7 增量【纯逻辑面】移植进 lightharness 的 .light 实现。

【背景与输入】
- 增量清单：G:\dswork\duan-light-merge\R87_上游0.1.7增量清单.md（§2-A 已列各包文件数；§0 含规模：fork 增量 1351 提交 / 4821 文件，纯逻辑包 1092 文件）
- 上游代码：G:/github/deepseek-harness，内网 fork HEAD=877717787c（已合 dsh-v0.1.7-alpha.1）；锚点 ddefc45fbc
- 本仓库：G:\dswork\duan-light-merge（含 light-merge/ 与 lightharness/）

【本次 scope（仅以下包，不得越界）】
- packages/llm(64) / packages/core(72) / packages/api(88) / packages/typert(23)
- packages/acp(8) / packages/mcp(4) / packages/lsp(4) / packages/sdk(7)
- 这些是「待移植」纯逻辑。宿主面包（host/subprocess/terminal/sandbox/fs/native/freebsd/patches/vendor）不在你 scope，禁止触碰。

【做法】
1. 对每个包：先读上游对应 .ts 源（G:/github/deepseek-harness/packages/<包>/src）理解语义；再在 lightharness 的 stdlib/ 或 light-merge/src/ 找到或新建对应 .light 模块。
2. 新语法/新语义先查 light-merge 语言能力（elastic_syntax 别名表、parser 支持面），不要为移植硬改语言核心。
3. 每个移植项配最小回归用例（.light 或 pytest），本机 Windows 全绿。
4. 若与 lightharness 语义冲突 / 上游是坏味道：拒绝并写明理由（落报告，不擅自删）。

【红线】见文件 §0 铁律。尤其：不动宿主接线文件、不硬搬 HTTP、不扩语法、不 commit/push、git add 显式文件。

【验收】本 scope 内每个待移植包都有对应 .light 模块或明确「需新建」记录；本机 Windows 全绿（lm 示例 + 对应 pytest）；light-merge 语法核心零改动（除非登记回 M）；产出 _taskB1_R87_核心协议层移植报告.md：逐包清单（移植/拒绝/暂缓 + 依据 + 回归用例路径）。

【环境】bash 前 export PATH（见 §0）；LM 用 light-merge/.venv/Scripts/python.exe。
```

---

## 2. B2 · 会话与上下文 / 协议序列化移植（session / context / compaction / schedule / session-query + typert 已含于 B1，此处仅会话族 + acp/mcp/lsp/sdk 若 B1 未覆盖）

```
你是 R87「增量移植实施」执行 agent（B2 子任务）。把 deepseek-harness 0.1.7 增量【纯逻辑面】中会话/上下文/压缩/调度及协议插件相关包移植进 lightharness 的 .light 实现。

【输入】同 B1（R87_上游0.1.7增量清单.md §2-A；上游 G:/github/deepseek-harness fork=877717787c）。

【本次 scope（仅以下包）】
- packages/session(21) / packages/session-query(1) / packages/context(17) / packages/compaction(12) / packages/schedule(12)
- 若 B1 未覆盖：packages/acp(8)/mcp(4)/lsp(4)/sdk(7)（先与 B1 报告核对避免重复）
- 纯逻辑；宿主面包禁止触碰。

【做法/红线/验收】同 B1：读上游 .ts → 找/建 .light → 配回归用例 → 冲突则拒绝落报告。不 commit/push，git add 显式文件。

【产出】_taskB2_R87_会话上下文移植报告.md：逐包移植/拒绝/暂缓 + 依据 + 回归用例路径；说明与 B1 的包边界。
```

---

## 3. B3 · 智能体与编排移植（subagent / workflow / skill / goal / plan / jobs / experimental / boot）

```
你是 R87「增量移植实施」执行 agent（B3 子任务）。把 deepseek-harness 0.1.7 增量【纯逻辑面】中智能体编排/工作流/技能/目标规划相关包移植进 lightharness 的 .light 实现。

【输入】同 B1。

【本次 scope（仅以下包）】
- packages/subagent(34) / packages/workflow(10) / packages/skill(10) / packages/goal(9) / packages/plan(4)
- packages/jobs(32) / packages/experimental(42) / packages/boot(42)
- 纯逻辑；宿主面包（host/subprocess/terminal/sandbox/fs）禁止触碰。注意 experimental/boot 含不少基础设施代码，甄别时只搬纯逻辑语义，平台相关部分登记不搬。

【做法/红线/验收】同 B1。

【产出】_taskB3_R87_智能体编排移植报告.md：逐包移植/拒绝/暂缓 + 依据 + 回归用例路径；标出 experimental/boot 中「逻辑 vs 宿主」的甄别结果。
```

---

## 4. B4 · 命令执行 / 配置扩展 / 客户端逻辑移植（shell / workspace / settings / preset / bundle / extensions / hooks / util / web / test-support / computer-use / browser-use + client 逻辑部分）

```
你是 R87「增量移植实施」执行 agent（B4 子任务）。把 deepseek-harness 0.1.7 增量【纯逻辑面】中命令执行、配置扩展、客户端纯逻辑部分移植进 lightharness 的 .light 实现。

【输入】同 B1。

【本次 scope（仅以下包）】
- packages/shell(75) / packages/workspace(7) / packages/computer-use(1) / packages/browser-use(1)
- packages/settings(23) / packages/preset(27) / packages/bundle(28) / packages/extensions(17) / packages/hooks(9) / packages/util(31) / packages/web(11) / packages/test-support(25)
- packages/client(339)：⚠️ 仅搬【纯逻辑部分】（状态管理/数据流/协议字段）；UI 渲染、DOM、样式等 web 宿主面部分【登记不搬】，在报告中明确标注哪部分跳过。
- 宿主面包（host/subprocess/terminal/sandbox/fs/native/freebsd/patches/vendor）禁止触碰。

【做法/红线/验收】同 B1。client 包务必区分逻辑/宿主，避免误搬渲染层。

【产出】_taskB4_R87_命令配置客户端移植报告.md：逐包（client 逐子目录）移植/拒绝/暂缓 + 依据 + 跳过项说明 + 回归用例路径。
```

---

## 5. C · 宿主面登记清单文档（R85 遗留 7 号 + A 新登记）

```
你是 R87「宿主面登记清单文档」执行 agent（C 路）。产出一份权威宿主面登记清单，汇总 R85 各路遗留 + A 路新登记的 0.1.7 宿主面。

【输入】
- 增量清单：G:\dswork\duan-light-merge\R87_上游0.1.7增量清单.md §2-B（宿主面包：host/subprocess/terminal/sandbox/fs/native/freebsd/patches/vendor/.gitea/.github/scripts/website）
- R85 各交付报告（工作区根 `_task*_R85_*.md`、lightharness 既有 docs）
- 上游宿主实现：G:/github/deepseek-harness 对应包（host/subprocess/sandbox/fs/native/freebsd/patches 等）

【任务】产出 lightharness/docs/宿主面登记清单.md，结构：宿主能力 / 上游实现面 / lightharness 现状（已实现|缺|部分）/ 三平台可行性（Win/Linux/FreeBSD）/ 状态（登记|已坐实|下轮）。

【必须收录的宿主面（A 路 §2-B）】
- FreeBSD jail 沙箱后端（sandbox 包 + freebsd/dsh-jail-run.c + patches/boxrun-dsh.patch）
- node-pty FreeBSD 编译补丁（patches/node-pty@1.2.0-beta.15.patch）+ process-inspector FreeBSD ps 语法（subprocess 包）
- ripgrep FreeBSD 回退（fs/tool-fs-search，@vscode/ripgrep 无 FreeBSD 二进制时回退系统 rg）
- terminal-bash 平台感知默认 shell（terminal 包）
- native flock 插件 + FreeBSD 预编译（native/system/packages/freebsd-x64）
- web crypto.randomUUID 无头 polyfill（apps/web）
- settings-controller 无头开配置（api/settings-controller）
- native-command path-opener 平台差异（util/native-command）
- Gitea Actions CI（.gitea/workflows）+ FreeBSD 构建脚本（freebsd/*.sh, dsh_web.rcd）
- R85 遗留 7 号：HTTP / files-api / pi-ai 装配 / git 执行 / LibreOffice / Node 安装 / Cordis / FFI 等

【红线】仅文档产出，不改代码；不 commit/push（git add 显式文件）。与 A-E 报告交叉核对，R85 宿主面 100% 收录、无遗漏。

【验收】清单覆盖 R85 遗留 + A 新登记全部宿主面；每条有现状与三平台列；本文件可入库（M 合流）。
```

---

## 6. D · 三平台 LM 门禁补位（最大缺口）

```
你是 R87「三平台 LM 门禁补位」执行 agent（D 路）。补齐 LM 全量在 Windows 与 FreeBSD 的基线与矩阵对拍能力。

【背景】R86 收口后 LH 三平台全绿，但 LM 全量仅 0.86 Linux 有（8191/0/94）；Windows 本机无基线、FreeBSD 自 R45 后未复跑。

【任务】
1. Windows LM 基线：本机 light-merge 全量 pytest（.venv），落基线 JSON 到 lightharness/reports/本机lm基线_latest.json（复用 scripts/回归基线.py 口径）。
2. FreeBSD LM 复跑：用 scripts/同步0.82.py sync --with-git 后跑 light-merge 全量（0.82 python3.12；LM 示例修复 3b09301e 后首次全量），落基线到 reports/；注意 e2e_chain 缺第三方库自动 skip 逻辑（_missing_third_party_lib），FreeBSD devpi 缺包属环境欠账非回归。
3. 矩阵脚本：把 scripts/多平台矩阵.py（现 core 模式）扩展或新增 --mode lm-full，一键对拍三平台 LM 全量失败集合（新增红=0 判据，参照 ci_judge_env_reds.py 语义）。

【红线】⛔ 0.82 复跑只用 /tmp 副本，不动远端源仓库；⛔ 0.86 无 sudo，只用 /tmp/r85-venv；不 commit/push。

【环境】bash 前 export PATH（见总控 §0）；0.82 三件套：LIGHT_MERGE=<LH根>/light-merge PYTHONPATH=<LH根>/light-merge/src PATH=/tmp/r80b-shim:$PATH；0.86 用 /tmp/r85-venv。

【验收】三平台 LM 全量数字入库（reports/），失败集合对拍新增红=0；Windows/FreeBSD LM 无新增平台红（相对 0.86 基线，缺依赖 skip 不算红，需逐条归因）；矩阵脚本可一键跑通。产出 _taskD_R87_LM门禁补位报告.md。
```

---

## 7. E · flaky 根治（4 条旧账）

```
你是 R87「flaky 根治」执行 agent（E 路）。对 4 条已知 flaky 用例逐条一手取证，按结果二选一（根治 or 登记）。

【清单与已知线索】
- test_终端PTY.light（FreeBSD）：全量偶发红，单跑恒绿；PTY 轮询计时，R68「累积+轮询(15s)」已免疫大部分。
- test_R21_词法确定性_超集.py（FreeBSD）：全量偶发 ERROR(FileNotFoundError)，单跑恒绿；git archive 子进程偶发，0.82 有 git 2.54.0。
- test_子进程后台.light（Windows）：全量偶发红，单跑 rc=0；R44「后台子进程时序敏感」。
- test_async_await.light（0.86 Linux）：xdist 高负载偶发抖动(0.26s vs 阈值)；R86-C 阈值已放宽 0.18→0.35，本质未根治。

【做法】逐条实机多轮复跑 + 抓失败时上下文：
- 根治：修实现/测试（PTY 轮询加宽松 / R21 超集 git 子进程加重试降级 / 子进程后台加等待握手 / async 断言改相对判据）。
- 登记：确证环境 flaky（隔离恒绿 + 全量偶发）→ 写入 lightharness/tests/flaky_registry.txt（参照台账格式：文件名/平台/现象/取证记录/处置），并保证门禁判据把 flaky 从「新增红」豁免有据可查。

【红线】不 commit/push；git add 显式文件；只动 flaky 相关用例/台账，不扩大改动面。

【验收】每条有取证记录（复跑次数/失败样例/单跑对照）；修复项本机或对应平台连续全量 2 次无复发；登记项有完整证据链且不影响门禁判定（新增红判据明确排除已登记 flaky）。产出 _taskE_R87_flaky根治报告.md。
```

---

## 8. F · 环境固化（运维债）

```
你是 R87「环境固化」执行 agent（F 路）。把 FreeBSD 0.82 与 Linux 0.86 的环境恢复步骤固化为幂等脚本。

【任务】
1. freebsd/初始化.sh：一键恢复 0.82 FreeBSD 环境（重启后失效项）——sudo kldload nullfs（幂等）、dsh-jail-run setuid 安装/校验（test -u）、venv/垫片校验、/tmp/test-sandbox 预建。判据：0.82 上执行后 jail e2e 5/5 全绿。
2. scripts/同步0.86.py ensure_venv 固化依赖：aiohttp、sympy（R86 手工补装过，重建 venv 会丢）写进 venv 初始化步骤（pip install 幂等）。判据：删 venv 重建后 test-lm full 仍 0 failed（或 e2e 缺依赖 skip 与 R86 基线一致）。
3. 台账注释里「0.82 全量偶发（终端PTY/R21超集）」与 E 路处置结果互引（E 登记后，台账注释更新指向 flaky_registry）。

【红线】⛔ 0.82 只用 /tmp 副本与用户级 venv，不碰系统环境；不 commit/push。

【验收】两脚本可重复执行（幂等）；执行后环境门禁结果与 R86 收口一致。产出 _taskF_R87_环境固化报告.md。
```

---

## 9. M · 收口（唯一可 commit/push）

```
你是 R87「收口」主 agent（M 路）。在 B/C/D/E/F 全部完成后，合流、回填差异清单、三平台门禁复核并 push。

【前置】必须等 B1–B4、C、D、E、F 全部交付（各自独立 commit/报告已就绪，但均未 push）。

【任务】
1. 合流 A–F 各路提交的显式文件（各自独立 commit；M 只写 docs/报告，不混改 src/ 逻辑）。
2. 差异清单回填：docs/多平台差异清单.md 补 R87 增量对标结论（A/B）、LM 三平台数字（D）、flaky 处置（E）、环境固化（F）。
3. 三平台门禁复核：LH 三平台 + LM 三平台全量各 1 次，数字入库 reports/。
4. push：lightharness（origin=gitcode / myrepo=内网 gitea / github 三远端）；light-merge（gitcode/gitea/github/origin 四远端，注意 origin 是本地镜像 g:\github\light）。
5. 产出 _taskM_R87_收口报告.md：增量清单摘要 / 移植项与拒绝项 / 三平台 LM 矩阵表 / flaky 取证表 / 遗留更新。

【判据】三平台 LH+LM 全量 0 新增红；远端全部同步；报告数字与 reports/ 基线 JSON 一致。

【红线】M 是【唯一允许 commit/push】的路；其余路产物须显式 git add 各自文件。push 前核对 git status / git ls-remote 确认远端状态，避免误覆盖。密钥只经 .env。
```

---

## 附：agent  dispatch 建议
- **并行安全**：B1–B4 按包拆分、文件面不重叠，可并行；C/D/E/F 相互独立，可并行；**M 必须最后**。
- **B 路总量提示**：1092 文件纯逻辑，建议 B1–B4 各 agent 再按子包拆 commit，勿一轮吞下；优先级 llm/core/api > session/context > subagent/workflow/skill。
- **D/E 需真机**：D 的 FreeBSD 复跑、E 的多平台复跑需要真实 0.82 / 0.86 / Windows 环境，确保 agent 有对应环境访问权再派。
- **fork 滞后提醒**：内网 fork 滞后 gitcode dsh-v0.1.7-alpha.2 共 162 提交；B 路若发现清单未覆盖的 alpha.2 差量，登记到报告「待 R88 追 gitcode alpha.2 差量」，不要擅自扩 scope。
