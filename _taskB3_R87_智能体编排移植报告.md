# R87 任务 B3 交付报告：智能体与编排移植（subagent / workflow / skill / jobs / experimental / boot）

> 轮次：R87 路 B3　｜　日期：2026-09-23
> 上游增量：deepseek-harness `ddefc45fbc`（0.1.6 锚点）.. `877717787c`（fork HEAD，已合 0.1.7-alpha.1）
> 范围：packages/subagent / workflow / skill / goal / plan / jobs / experimental / boot 中纯逻辑面
> 结论：**12 项移植全部落地（9 新建模块 + 3 更新模块），11 个新增回归用例 + 1 个既有用例同步修正，全量 pytest 517 passed / 1 skipped / 0 failed，新增红 0。**

---

## 1. 结论速览

| 指标 | 结果 |
|---|---|
| 新建 .light 模块 | 9 个 |
| 更新 .light 模块 | 3 个（子智能体、代理团队、团队花名册） |
| 新增回归用例 | 11 个 |
| 同步修正既有用例 | 1 个（test_子智能体1.5.light:148，v1→v2 负向覆盖） |
| 拒绝/暂缓项 | 见 §5（goal/plan-mode/skill 仅类型变更；boot config-schema 第三方依赖；experimental 宿主面） |
| 全量回归（合流后） | **517 passed / 1 skipped / 0 failed**（180s） |
| commit/push | 未执行（红线） |

---

## 2. 逐模块移植表

### 2.1 jobs 族（5 项，全部新建）

| # | 模块 | 状态 | 对齐上游文件:行号 | 复刻要点 | 回归用例 |
|---|---|---|---|---|---|
| 1 | `src/任务视图.light` | 移植 | `jobs/jobs/src/view.ts` L48-135（JobStatus/JobChannel/JobChunk/JobView）<br>`jobs/tool-jobs/src/render.ts` L29-108（publicJob/jobDetail/statusLine/renderModelDelta） | 纯数据投影 + 4 个渲染纯函数；log 块不入模型、stderr 单节、丢失提示点名 spill；剔除终端 ANSI/插件宿主 | `examples/test_R87_B3_jobs_视图.light` |
| 2 | `src/输出环.light` | 移植 | `jobs/jobs-local/src/ring.ts` L21-137（RingChunk/utf8Tail/append/trim/readFrom） | 环形字节缓冲，绝对偏移永不移动、earliest 只前进；UTF-8 字节语义在码点层等价复刻（窗口落续字节不回退捞字）；剔除 Node Buffer | `examples/test_R87_B3_jobs_输出环.light` |
| 3 | `src/任务事件总线.light` | 移植 | `jobs/jobs-local/src/events.ts` L20-137（Subscription/JobLayer/JobEventHub） | 作用域分层订阅：全域表+全局层+作用域表；owner 过滤保留「无主报文可达 owner 订阅」；剔除 Cordis/Node EventEmitter | `examples/test_R87_B3_jobs_事件总线.light` |
| 4 | `src/任务拉取泵.light` | 移植 | `jobs/jobs-local/src/pump.ts` L33-121（PumpSink/入参校验/drain 轮询状态机） | pollMs 正有限校验；states 游标推进；按源序 read→报 spill→追加；终抽=末次 drain；剔除 setTimeout/Promise，轮次由调用方驱动 | `examples/test_R87_B3_jobs_拉取泵.light` |
| 5 | `src/任务不变式.light` | 移植 | `jobs/jobs/src/invariant.ts` L20-137（相位机 live→settled→removed）<br>`jobs/jobs/src/archive-admission.ts` L48-51（runningJobs 过滤） | 事件协议相位机各分支校验；身份四键+output.total 不领先；settled 三判据独立（终态/finishedAt/progress 已清）；归档准入 running/stopping 归属过滤 | `examples/test_R87_B3_jobs_不变式.light` |

### 2.2 编排族（3 项：1 更新 + 2 新建）

| # | 模块 | 状态 | 对齐上游文件:行号 | 复刻要点 | 回归用例 |
|---|---|---|---|---|---|
| 6 | `src/子智能体.light` | 更新 | `subagent/subagent/src/catalog.ts` L55-133（catalog v1/unknown、mode!=='continuable'、stateVersion 2→3）<br>`archive-admission.ts` L49-56（runningDescendants BFS）<br>`control-types.ts`（SubagentCatalogRow/unknown 地址） | catalog 载荷版本 union[0,1]，v1 新增 unknown 模式；entries 一行式规则；`目录阶段版本()=3`；runningDescendants 按 parentSession+origin BFS（fork 不入谱、成环只访一次）；SubagentAddress 扩 unknown | `examples/test_R87_B3_编排_子智能体目录.light` |
| 7 | `src/工作流记录镜像.light` | 新建 | `workflow/tool-workflow/src/record.ts` L37-61（runId→JobHandle 映射+log 通道镜像）<br>`index.ts` jobOutcomeOf | runId→作业登记面（start/stop 幂等、迟到事件丢弃）；四类 log 行格式（phase/log/agent-start/agent-end）；jobOutcomeOf 结局映射（completed/cancelled→killed/error→failed/未知→abnormal）；渲染截断 | `examples/test_R87_B3_编排_工作流镜像.light` |
| 8 | `src/工作区依赖.light` | 新建 | `skill/tool-workspace-dependencies/src/index.ts` L82-153（parsePrimaryRuntime + workspaceDependencyPaths） | payload JSON 校验/legacy 归一化/分布名归一；语义化版本、平台/架构枚举、pnpm 需 node、payloadDigest 64hex；win32/darwin/linux 路径解析（python.exe vs bin/python3；Lib vs lib/pythonX.Y） | `examples/test_R87_B3_编排_工作区依赖.light` |

### 2.3 基础设施族（3 项：2 更新 + 2 新建）

| # | 模块 | 状态 | 对齐上游文件:行号 | 复刻要点 | 回归用例 |
|---|---|---|---|---|---|
| 9 | `src/插件注册表计划.light` | 新建 | `boot/plugin-manager/src/registry.ts` L25-120（normalizeRegistry/registryPlan/attributeFailure）<br>`install-spec.ts` L51（gitHost） | 注册表归一化（小写宿主、路径补尾斜杠）；询问顺序计划（公开/回退/自身源/私有单独问/未知源单独问）；失败归因（network/timeout/not-found/no-matching-version）；git 宿主解析（简写/scp/URL） | `examples/test_R87_B3_基建_插件注册表计划.light` |
| 10 | `src/团队花名册.light` | 更新 | `experimental/agent-team/src/roster.ts` L492（availability）<br>`types.ts`（TeamMemberView.status 收敛） | availability 三值→二值收敛（running/inactive，去 idle）；新增 `收束可用`，4 处调用点改用；返回类型收敛 | `examples/test_R87_B3_基建_团队状态收敛.light` |
| 11 | `src/代理团队.light` | 更新 | `experimental/agent-team/src/projection.ts` L33-45（contentBlockSchema） | 头注释去 idle；新增 `判内容块`/`列内容块`（text/reasoning 带文本、image 带 attachment、tool-call 带 id/name/arguments；tool-result 退役拒绝；未知非空 type 按引用保留） | 同上 |
| 12 | `src/打包导出判定.light` | 新建 | `experimental/webworker-packer/src/pack.ts` L353-420（isDeclarationOnlyExport + sweepImage） | isDeclarationOnlyExport 递归判定（非对象/空→假；数组→全子声明-only；对象→条件键 types/types@* 或目标声明-only）；运行时导出面过滤（挑 . 开头、不含 *、目标非仅声明的子路径） | `examples/test_R87_B3_基建_打包外露判定.light` |

---

## 3. 关键语义对齐说明

1. **输出环 UTF-8 字节偏移**：光明字符串按码点索引，`utf8Tail` 改为「找第一个字节边界 ≥ totalBytes-maxBytes 的切分点」，对 ASCII/中文/窗口落续字节三种情形与原版逐字节一致。
2. **事件总线 owner 过滤**：无主报文（ownerId=空）对 {owner:X} 订阅仍可达——与原版 `if ('owner' in filter && ownerId !== undefined && ...) continue` 逐字保留。
3. **拉取泵**：只搬 drain 纯动作与 pollMs 校验；轮询间隔的 sleep/until 等待属宿主，调用方以多次 `抽一轮` + 末次 `终抽` 驱动。
4. **不变式 settled 三判据独立**：终态/finishedAt≥startedAt/progress 已清三条独立失败，与原版 switch 后三条顺序判定一致。
5. **子智能体 stateVersion 落点**：`子智能体.light` 新增 `目录阶段版本()=3`；另一并行端口 `子代理核心.light::目录状态版本()=2` 被其自身测试钉死，按 scope 未越界改动，列为待对齐项。
6. **团队 availability 二值收敛**：idle 统一收敛为 inactive；既有 `test_团队花名册.light` 1 条断言同步更新（idle→inactive）。
7. **contentBlockSchema**：以独立纯谓词落地并被用例直测，未回改消息发送面（避免与既有串语义冲突），与上游 zod schema 语义等价。

---

## 4. 回归结果

### 4.1 新增用例（全部 rc=0）

| 用例 | 覆盖 |
|---|---|
| `test_R87_B3_jobs_视图.light` | JobView 投影、renderModelDelta、statusLine |
| `test_R87_B3_jobs_输出环.light` | append/trim/readFrom、UTF-8 字节偏移、earliest/lossy/total |
| `test_R87_B3_jobs_事件总线.light` | 作用域分层 subscribe/emit、owner 过滤、无主报文 |
| `test_R87_B3_jobs_拉取泵.light` | pollMs 校验、drain 轮询、终抽、spill 报告 |
| `test_R87_B3_jobs_不变式.light` | 相位机校验、settled 三判据、archive-admission |
| `test_R87_B3_编排_子智能体目录.light` | catalog v1/unknown、stateVersion=3、runningDescendants BFS、浏览地址 |
| `test_R87_B3_编排_工作流镜像.light` | runId 映射、四类 log 行、jobOutcomeOf、渲染截断 |
| `test_R87_B3_编排_工作区依赖.light` | parsePrimaryRuntime、legacy 归一、平台路径解析 |
| `test_R87_B3_基建_插件注册表计划.light` | 归一化、计划生成、失败归因、gitHost |
| `test_R87_B3_基建_团队状态收敛.light` | availability 二值收敛、contentBlockSchema |
| `test_R87_B3_基建_打包外露判定.light` | isDeclarationOnlyExport、导出面过滤 |

### 4.2 全量回归（合流后）

```
lightharness> python -m pytest tests/test_回归.py
================= 517 passed, 1 skipped in 180.28s (0:03:00) =================
```

- **新增红 0**。各组单独运行时出现的临时红（_probe_r87 探针、编排工作区依赖顺序抖动、子智能体1.5 v1 变更）在合流后全部消除。
- 1 skipped = `test_env_red_baseline_report`（环境基线报告，非 B3 范围）。

---

## 5. 拒绝/暂缓/登记项

| 上游项 | 处置 | 理由 |
|---|---|---|
| goal / plan-mode / skill 各包 | 登记不搬 | 仅 MessageSource/版本/类型变更，无运行时纯逻辑增量 |
| jobs/index.ts、jobs-local/index.ts | 登记不搬 | 注册表服务本体（cordis/agents 宿主耦合），叶语义已由任务系统.light + 本组 5 模块覆盖 |
| boot config-schema/pattern.ts + projector.ts | 暂缓 | 依赖 regexpp/Ajv 第三方库，超出零第三方纯逻辑面 |
| boot package-meta.ts、profile-resolution | 登记不搬 | node:fs 宿主面 |
| experimental speech-to-text / api-speech-to-text / webworker-runtime / inspector / ptc-runtime-python / auto-review | 登记不搬 | 原生进程/webworker/CDP/会话深耦合宿主 |
| 子代理核心.light stateVersion=2 对齐 | 暂缓 | 该模块为 0.1.5 冻结结构化端口，测试钉死 v0-only/stateVersion=2；建议下轮裁决统一 |
| 预设旧 wire 形（trust/authorable/read-only） | 暂缓 | 被 test_预设深化.light 锁定，新形并列保留，建议后续清型卡退役 |

---

## 6. 文件清单

### 新建模块（lightharness/src/）
1. `任务视图.light`
2. `输出环.light`
3. `任务事件总线.light`
4. `任务拉取泵.light`
5. `任务不变式.light`
6. `工作流记录镜像.light`
7. `工作区依赖.light`
8. `插件注册表计划.light`
9. `打包导出判定.light`

### 更新模块（lightharness/src/）
1. `子智能体.light`（catalog v1/unknown + stateVersion 3 + runningDescendants BFS + 浏览地址）
2. `团队花名册.light`（availability 二值收敛）
3. `代理团队.light`（contentBlockSchema + 头注释去 idle）

### 回归用例（lightharness/examples/）
11 个新增 + `test_子智能体1.5.light`（1 条断言 v1→v2）+ `test_团队花名册.light`（1 条断言 idle→inactive）

### 分组报告（过程产物）
- `_taskB3_G1_jobs族_报告.md`
- `_taskB3_G2_编排族_报告.md`
- `_taskB3_G3_基建族_报告.md`

---

## 7. 红线自检

- ⛔ 未 commit / push；未 `git add` 任何文件。
- ⛔ 未写宿主接线文件（host/subprocess/terminal/sandbox/fs）。
- ⛔ 未硬抄 HTTP。
- ⛔ 未扩 .light 语法。
- ✅ 产物全部在 `G:\dswork\duan-light-merge` 下。
- ✅ 新模块头注释均标注上游文件:行号。
- ✅ 每个移植项配最小回归用例，可独立复现语义。
