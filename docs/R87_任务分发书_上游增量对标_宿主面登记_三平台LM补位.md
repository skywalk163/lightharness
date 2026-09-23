# R87 任务分发书：上游增量对标 + 宿主面登记 + 三平台 LM 门禁补位

> 轮次：R87 ｜ 日期：2026-09-22（**2026-09-23 v2 同步更新**：上游 0.1.7 增量已出现、内网 FreeBSD fork 已升级）｜ 上游锚点：deepseek-harness（0.1.6-alpha.2 = `ddefc45fbc` 之后的新增量）
> 用户指令：lightharness 复刻 deepseek harness，功能和架构上要向 deepseek harness 看齐；跨平台至少 Windows / Linux / FreeBSD。
> 前置状态：R86 已收口（24 failed 清零、三平台 LH 全量全绿、LM 15 条清零、台账销账、三远端 push 完成）。本任务书把 R85/R86 两轮遗留一次性收净；**v2 因上游/fork 升级，增量对标 scope 重新打开**。
> **上游现状（2026-09-23 v2 实机复核，推翻 2026-09-22 的「无增量」结论）**：
> ① 上游 gitcode 镜像已前进：`upstream/master` = `00102833df` = **`dsh-v0.1.7-alpha.2`**（2026-09-22 23:25）；另有新标签 `dsh-v0.1.7-alpha.1`（`c36a83ff`，09-22 12:12）、`dsh-v0.1.5-rc.3`（`a4c74a91`，09-22 13:26）。锚点 → 上游增量：**1461 commits / 4995 文件（+371557 / -118376）**，`git diff ddefc45fbc..upstream/master` 非空。**0.1.7 增量已出现**，A 路甄别必须重跑（fetch → diff → 逐包甄别 → 重产清单）。
> ② 内网 **FreeBSD fork（origin = `192.168.1.5:3000`）已升级**：HEAD = `877717787c`（2026-09-23 10:11），已合入上游 `dsh-v0.1.7-alpha.1`（merge `c6f6511e33`），并叠加 FreeBSD 构建对齐修复（settings-controller / process-inspector 对齐 0.1.7 API、`LinuxProcessInspector.foregroundPgid` 覆盖恢复、`resolver.internalModules` FreeBSD 分支）；**尚未合入 0.1.7-alpha.2**。fork 已含锚点 `ddefc45fbc`（0.1.6-alpha.2）。
> ③ 本地 `master` = `9d9035b7c1`（2026-09-11 的 37 条 FreeBSD 移植旧态）已过时：fork 已超它 3001 commits。B/M 复用时以 `origin/master`（fork）与 `upstream/master` 为准。
> ④ A 路交付物 `R87_上游0.1.7增量清单.md` 现有版本（"0 行"）已被推翻，需 A 路按新增量重产后覆盖。下游 B/C/M 按"增量存在"重新放开 scope（见各路"协同影响"注）。

---

## 0. 分路总览（执行者按路取用，互不重叠）

| 路 | 内容 | 类型 | 涉及仓库 |
|---|---|---|---|
| A | 上游 0.1.7 增量甄别（fetch + diff + 变更清单 + 功能/架构评估） | 只读调研 | 仅 deepseek-harness 本地对象 |
| B | 增量移植实施（A 判定为纯逻辑/需对齐的部分 → .light；宿主面 → 登记） | 代码 | light-merge / lightharness |
| C | 宿主面登记清单文档（R85 遗留 7 号，汇总成清单） | 文档 | lightharness docs |
| D | 三平台 LM 门禁补位（Windows LM 基线 + FreeBSD LM 复跑 + 矩阵脚本） | 实测/脚本 | light-merge / lightharness scripts |
| E | flaky 根治（4 条逐一手取证：修复或登记 flaky 台账） | 代码/取证 | lightharness |
| F | 环境固化（0.82 FreeBSD 初始化脚本 + 0.86 venv 依赖固化） | 脚本 | lightharness freebsd/ + scripts/ |
| M | 收口（合流 + 差异清单回填 + 三平台门禁复核 + push） | 收口 | 全 |

---

## A 路：上游 0.1.7 增量甄别（只读调研，不动代码）

**上游代码位置**：`G:/github/deepseek-harness`。**用户 09-23 指令：上游 = 内网 fork `192.168.1.5:3000/skywalk/deepseek-harness`（即本仓库 `origin`，HEAD=`877717787c`，已合 `dsh-v0.1.7-alpha.1` + FreeBSD 构建对齐）**；gitcode 官方镜像（`dsh-v0.1.7-alpha.2`=`00102833df`）作**参考镜像**（fork 滞后 162 提交，未合 alpha.2）。A 路 diff 基准 = `ddefc45fbc..origin/master`。
**对比锚点**（R85 已覆盖）：0.1.5-alpha.2 = `dd393c1820`；0.1.6-alpha.1 = `ea53423b60`；0.1.6-alpha.2 = `ddefc45fbc`。

**任务**：
1. `git fetch upstream` 拉最新；确认上游 master 当前 HEAD 与 0.1.6-alpha.2 之间的新 release 标签 / PR 合并记录（`git log --oneline ddefc45fbc..upstream/master`）。
2. `git diff --stat ddefc45fbc..upstream/master` 出增量全貌；按包/模块分类（llm 系列、subprocess 系列、tool 系列、agents、cli、common 等）。
3. 逐包甄别三类：
   - **纯逻辑面**（消息/协议/序列化/数据形状/状态机/令牌计量语义）→ 标记"待移植"；
   - **宿主面**（真实 HTTP 流、undici、FFI/koffi、系统调用、文件监听、shell/terminal 平台实现）→ 标记"登记不移植"；
   - **架构面**（模块拆分、装配方式、配置项、生命周期、插件机制）→ 单独列"架构对齐建议"，评估 lightharness 是否需要跟随。
4. 产出 `R87_上游0.1.7增量清单.md`：表格 = 变更面 / 上游文件 / 类别（逻辑|宿主|架构）/ lightharness 现状 / 处置建议（移植|登记|暂缓|拒绝）。

**判据**：清单覆盖 diff 全貌（变更文件 100% 落到表内一行）；每条处置建议有依据（逻辑面必须能指出对应 `.light` 模块或"无对应需新建"；宿主面必须给出登记的宿主能力名）。

**红线**：⛔ 本路只读，不提交任何代码；⛔ 不联网猜上游内容，一律以本地对象 diff 为准。

**本轮回基线（2026-09-23 v2 实机复核，推翻 2026-09-22 的「无增量」结论）**：
- 参考镜像（gitcode）已存在 0.1.7 增量：HEAD = `00102833df`（`dsh-v0.1.7-alpha.2`），新标签 `dsh-v0.1.7-alpha.1` = `c36a83ff`、`dsh-v0.1.5-rc.3` = `a4c74a91`。
- **A 路基准（内网 fork = 用户指定上游）**：`git diff --stat ddefc45fbc..origin/master` = **4821 文件（+356575 / −108915）**，`git rev-list --count` = **1351 commits**（纯逻辑包 1092 文件）。参考镜像 gitcode `0.1.7-alpha.2` 为 4995 文件 / 1461 提交（fork 滞后 162）。
- 增量分布（按顶层目录）：packages 3093（其中 client 1324 / experimental 228 / api 172 / session 135 / llm 129 / preset 97 / core 88 / shell 85 / subagent 73 / host 46 / util 39 / sandbox 24 / fs 22 / subprocess 16 等）、apps 591、snapshots 261、docs 190、scripts 128、.agents 640。
- 内网 FreeBSD fork（origin）已合入 0.1.7-alpha.1（`c6f6511e33`），HEAD `877717787c`，尚未合 alpha.2；fork 自带 FreeBSD 构建对齐提交（见顶部"上游现状"②）。
- 上游 CI 无 FreeBSD 平台（gitlab-ci 矩阵仅 linux-x64/arm64、macos-x64/arm64、win-x64），FreeBSD 相关仅存在于宿主面测试守卫（subprocess / sandbox / native-command 等 tests 内 `process.platform === 'freebsd'` 分支）。

**A 路任务恢复执行**：按上文任务 1–4 重跑（2026-09-23 已 fetch 拉平 → `git log --oneline ddefc45fbc..origin/master` 逐包甄别 → 逻辑/宿主/架构三类分类 → 重产 `R87_上游0.1.7增量清单.md` 覆盖旧版本）。fork 的 0.1.7-alpha.1 合并适配（settings-controller / process-inspector / resolver.internalModules）可作为移植判读的参考实现。

---

## B 路：增量移植实施（A 清单的"待移植"项）

> **协同影响（2026-09-23 v2 更新）**：A 已确认 0.1.7 增量存在（1461 commits / 4995 文件），B **恢复为按新 A 清单逐项移植纯逻辑面**，不再收敛为"仅复核"。另注意：内网 FreeBSD fork 已先行合入 0.1.7-alpha.1 并完成三处构建对齐（settings-controller 构造器、process-inspector `foregroundPgid`、resolver.internalModules FreeBSD 分支）——B 移植同类改动时可直接参考 fork 实现，避免重复踩坑。R85/R86 已移植项的收口复核仍保留在任务 1 内。

**任务**：
1. 按 A 清单逐项移植纯逻辑面进对应 `.light`（light-merge 的 src/ 或 lightharness 的 stdlib/，以 A 清单指定为准）。
2. 移植原则：
   - 新语法/新语义先查 light-merge 语言能力（elastic_syntax 别名表、parser 支持面），**不要**为了移植硬改语言核心；
   - 宿主面不移植（登记即可）；架构面按 A 建议，仅在有明确收益且不破坏现有三平台门禁时实施；
   - 每个移植项配最小回归用例（.light 或 pytest）。
3. 若 A 判定某增量"与 lightharness 语义冲突/上游是坏味道"，可拒绝并写明理由（回 M 收口记录）。

**判据**：移植项 100% 有对应测试且本机 Windows 全绿；三平台 LH/LM 全量不劣化（见 D 路矩阵）；light-merge 语法核心零改动（除非 A/B 共同裁定必要且回 M）。

**红线**：⛔ 不动宿主接线文件（`src/真实HTTP客户端.light`、`src/网页搜索.light` 等）；⛔ 不把上游 HTTP 实现硬搬成光明网络调用；⛔ 不擅自扩语言语法（先登记到差异清单再议）。

---

## C 路：宿主面登记清单文档（R85 遗留 7 号）

> **协同影响（2026-09-23 v2 更新）**：A 的 0.1.7 甄别重启后，凡判为"宿主面"的增量项（真实 HTTP 流、undici、FFI/koffi、系统调用、文件监听、shell/terminal 平台实现等；初步看 subprocess / sandbox / native-command 等包均有改动）一律并入本清单；fork 已做的 FreeBSD 构建对齐若属宿主面也一并登记。C = R85 遗留 7 号 + A 新登记的 0.1.7 宿主面。

**任务**：把 R85 A-E 各路登记的宿主面（HTTP / files-api / pi-ai 装配 / git 执行 / LibreOffice / Node 安装 / Cordis / FFI 等）汇总成一份权威清单文档：
`lightharness/docs/宿主面登记清单.md`。

**结构**：宿主能力 / 上游实现面 / lightharness 现状（已实现|缺|部分）/ 三平台可行性（Win/Linux/FreeBSD）/ 状态（登记|已坐实|下轮）。

**判据**：R85 各交付报告中登记的宿主面 100% 收录（与 A-E 报告交叉核对，无遗漏）；每条有现状与平台列；新增 A 路登记的 0.1.7 宿主面一并并入。

---

## D 路：三平台 LM 门禁补位（最大缺口）

**现状**（R86 收口后）：
- LH 三平台全量：Windows 1371/0/4 ✅、0.86 Linux 1371/0/4 ✅、0.82 FreeBSD 1372/0/0 ✅
- LM 全量：仅 0.86 Linux 有（8191/0/94，full 口径）✅；**Windows 本机无基线**、**FreeBSD 未复跑**（R45 时代 1238 用例旧数据，R85/R86 后未验证）

**任务**：
1. **Windows LM 基线**：本机 light-merge 全量 pytest（venv `.venv`），落基线 JSON 到 `lightharness/reports/本机lm基线_latest.json`（复用 `scripts/回归基线.py` 口径；参考 LH 基线命名）。
2. **FreeBSD LM 复跑**：`scripts/同步0.82.py sync --with-git` 后跑 light-merge 全量（0.82 python 3.12；LM 示例修复 3b09301e 后首次全量），落基线；注意 e2e_chain 的缺第三方库自动 skip 逻辑（`_missing_third_party_lib`），FreeBSD devpi 缺包属环境欠账非回归。
3. **矩阵脚本**：把 `scripts/多平台矩阵.py`（现 core 模式）扩展或新增 `--mode lm-full`，一键对拍三平台 LM 全量失败集合（新增红=0 判据，参照 `ci_judge_env_reds.py` 语义）。

**判据**：三平台 LM 全量数字入库（reports/），失败集合对拍新增红=0；Windows/FreeBSD LM 无新增平台红（相对 0.86 基线，差异需逐条归因：缺依赖 skip 不算红）。

**红线**：⛔ 0.82 复跑不要动远端源仓库（只用 /tmp 副本）；⛔ 0.86 无 sudo，只用 `/tmp/r85-venv`。

---

## E 路：flaky 根治（4 条旧账）

**清单与已知状态**：
| 用例 | 平台 | 现象 | 已知线索 |
|---|---|---|---|
| test_终端PTY.light | FreeBSD | 全量偶发红，单跑恒绿 | PTY 轮询计时；R68 记录"累积+轮询（15s）"已免疫大部分 |
| test_R21_词法确定性_超集.py | FreeBSD | 全量偶发 ERROR（FileNotFoundError），单跑恒绿 | git archive 子进程偶发；0.82 有 git 2.54.0 |
| test_子进程后台.light | Windows | 全量偶发红，单跑 rc=0 | R44 记录"后台子进程时序敏感" |
| test_async_await.light | 0.86 Linux | xdist 高负载偶发抖动（0.26s vs 阈值） | R86-C 阈值已放宽 0.18→0.35，本质未根治 |

**任务**：逐条一手取证（实机多轮复跑 + 抓失败时上下文），按结果二选一：
- **根治**：修实现/测试（如 PTY 轮询加宽松、R21 超集 git 子进程加重试/降级、子进程后台加等待握手、async 断言改相对判据）；
- **登记**：确证为环境 flaky（隔离恒绿 + 全量偶发）→ 写入 `lightharness/tests/flaky_registry.txt`（参照台账格式：文件名/平台/现象/取证记录/处置），并保证门禁判据把 flaky 从"新增红"中豁免有据可查。

**判据**：每条有取证记录（复跑次数/失败样例/单跑对照）；修复项本机或对应平台连续全量 2 次无复发；登记项有完整证据链且不影响门禁判定（新增红判据明确排除已登记 flaky）。

---

## F 路：环境固化（运维债）

**任务**：
1. `freebsd/初始化.sh`：一键恢复 0.82 FreeBSD 环境（重启后失效项）——`sudo kldload nullfs`（幂等）、dsh-jail-run setuid 安装/校验（`test -u`）、venv/垫片校验、/tmp/test-sandbox 预建。判据：0.82 上执行后 jail e2e 5/5 全绿。
2. `scripts/同步0.86.py` ensure_venv 固化依赖：`aiohttp`、`sympy`（R86 手工补装过，重建 venv 会丢）写进 venv 初始化步骤（pip install 幂等）。判据：删 venv 重建后 test-lm full 仍 0 failed（或 e2e 缺依赖 skip 与 R86 基线一致）。
3. 台账注释里已记录的"0.82 全量偶发（终端PTY/R21超集）"与 E 路处置结果互引（E 路登记后，台账注释更新指向 flaky_registry）。

**判据**：两个脚本可重复执行（幂等）；执行后环境门禁结果与 R86 收口一致。

---

## M 路：收口

> **协同影响（2026-09-23 v2 更新）**：A 本轮增量对标结论 = **0.1.7 增量已出现**（上游 `dsh-v0.1.7-alpha.1/alpha.2`；fork 已合 alpha.1 未合 alpha.2）。M 报告「增量清单摘要 / 移植项与拒绝项」按新 A 清单据实填写（移植项/拒绝项/架构对齐建议均按 A 实际输出，不再预填 0）；差异清单回填新增"上游 0.1.7 增量对标 + fork 升级对齐"条目；三平台 LM 矩阵表、flaky 取证表、环境固化照常。

**任务**：
1. 合流 A-F 各路提交（各自独立 commit，M 只写 docs/报告）。
2. 差异清单回填：`docs/多平台差异清单.md` 补 R87 增量对标结论（A/B）、LM 三平台数字（D）、flaky 处置（E）、环境固化（F）。
3. 三平台门禁复核：LH 三平台 + LM 三平台全量各 1 次，数字入库。
4. push：lightharness（origin=gitcode / myrepo=内网 gitea / github 三远端，github 已恢复可推）+ light-merge（gitcode/gitea/github/origin 四远端，注意 light-merge 的 origin 是本地镜像 `g:\github\light`）。
5. 产出 `_taskM_R87_收口报告.md`：增量清单摘要 / 移植项与拒绝项 / 三平台 LM 矩阵表 / flaky 取证表 / 遗留更新。

**判据**：三平台 LH+LM 全量 0 新增红；远端全部同步；报告数字与 reports/ 基线 JSON 一致。

---

## 全局红线

- 上游对比一律以 `G:/github/deepseek-harness` 本地对象为准（`git diff ddefc45fbc..HEAD`），不联网猜；增量甄别以锚点 → `upstream/master` 为主、内网 fork（`origin/master`）合入记录为辅，两条线都过一遍再下结论。
- 判据逐条可验收、根因一手证据（实机取证，不推断）。
- light-merge 改动克制：语法核心零改动优先；必须改时回 M 记录并写明理由。
- 0.82 / 0.86 只用 /tmp 副本与用户级 venv，不碰系统环境。
- 各路交付物路径明确，M 统一入库。
