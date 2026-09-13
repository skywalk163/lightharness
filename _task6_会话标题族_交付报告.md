# 任务6 交付报告 —— 会话标题域（session-title 族，纯逻辑面）

> 轮次：复刻 第14轮 ｜ 日期：2026-09-13 ｜ 对标卡：**#97（新增，title 族合并一路）**
> 上游只读：`G:\github\deepseek-harness` @ `a305303422`（0.1.5-rc.2）
> 本路可写文件（5 个，全部新增，零越界）：
> `lightharness/src/会话标题族.light`（405 行 / 39 段）
> `lightharness/examples/test_会话标题族.light`（362 行 / 159 断言）
> `lightharness/_antirun_title.py`
> `lightharness/examples/_repro_L119.light`、`examples/_repro_L120.light`（铁律 3 要求，缺陷 L-119/L-120）
> `lightharness/_task6_会话标题族_交付报告.md`（本文件）
>
> ⚠️ **模块命名偏差**（必须由路M 裁定）：任务书写作 `src/会话标题.light` / `examples/test_会话标题.light`，
> 但这两个文件**已被第49号对标卡（session-title/normalize）占用且已 done**（`src/会话标题.light` 238 行、
> `examples/test_会话标题.light` 4593 B，均属既有交付物）。按任务书原名落地会**直接覆盖既有交付物**，
> 违反「只改文件互斥表内文件」铁律。故本路新增 `会话标题族.light` / `test_会话标题族.light`，
> 并**只读导入** #49 的 `规范化会话标题` 复用规范化能力。详见 §七 移交清单。

---

## 一、上游对应表（文件 / 行号 / 核心语义）

| 上游文件 | 行 | 核心语义 | 本模块落点 |
|---|---|---|---|
| `session-title/src/types.ts` | 20 `SessionTitleModelProvenance` | `{provider, model}` 出处 | §1 `造来源提供方` |
| 同上 | 28–39 `SessionTitleSource` | 三值联合：`{kind:'fallback'}` \| `{kind:'provider', provider, model?}` \| `{kind:'user'}` | §1 `造来源回退` / `造来源提供方` / `造来源用户` / `是合法来源` |
| 同上 | 41–49 `SessionTitleEventData` | `session/title` 事件载荷：`{title, messageSeqs, source}`（**log-only**） | §1 `造标题载荷` / §6 `造标题事件` |
| 同上 | 51–58 `SessionTitleSnapshot` | 折叠后快照 = 载荷 + `{eventSeq, updatedAt}` | §1 `造标题快照` |
| 同上 | 62–68 `SessionTitleUserMessage` | `{seq, text}`（唯一暴露给标题提供方的人消息形状） | §1 `造标题用户消息` / §4 `消息序号表` |
| 同上 | 70–80 `TitleInputState` | `{first, count, lastSeq}` 有界聚合 | §1 `造标题输入` |
| `session-title/src/normalize.ts` | 1–74 `normalizeTitle` / `truncateTitleUtf8` | 终端安全清理 + UTF-8 安全截断 | **对标卡 #49**，本模块只读复用 `规范化会话标题` |
| `session-title/src/invariant.ts` | 32–35 | **`messageSeqs.length === 0` ⟺ `source.kind === 'user'`** | §6 `校验标题事件` 配对判据 |
| 同上 | 36–52 | 逐条校验：`SessionSeq` 合法（安全非负整数）/ 不重复 / `seq < event.seq` 且指向更早的 `user/message` 且其人消息 `source.kind === 'user'` | §6 `是安全序号` / `事件定位` |
| `session-title-llm/src/index.ts` | 50 `SESSION_TITLE_TIMEOUT_CODE` | 超时错误码 | §0 `超时码` |
| 同上 | 74–85 `SessionTitleLlmConfigFields` / `Schema` | 五字段：`targetWords` / `targetCjkCharacters` / `maxInputBytes` / `maxOutputTokens` / `timeoutMs`（均 `step(1).min(1)`，`timeoutMs.max(MAX_TIMER_DELAY_MS)`） | §2 `校验标题配置` / `造标题配置` |
| 同上 | 88 `CONFIG_KEYS` | 合法配置键集（含 `provider` / `model`） | §0 `配置键集` |
| 同上 | 99 `assertPositiveInteger` | 正整数断言文案 `session-title-llm: <名> must be a positive integer` | §0 `断言正整数` |
| 同上 | 110–131 `resolveSessionTitleLlmConfig` | 未知键拒绝 / 逐字段正整数 / `timeoutMs` 上限 / `provider`·`model` **成对**且非空 | §2 `校验标题配置` |
| 同上 | 143 `SessionTitleLlmMessageSelector` | 消息选择器签名 | §3 `按模式选消息` |
| 同上 | 174 `resolveRoute` | 配置优先 → 已记录请求路线回退 → 都无则抛 `no logged request route …` | §5 `解析路线` |
| 同上 | 188–196 `systemPrompt` | **逐字 4 行**系统提示（第 4 行注入 `targetWords` / `targetCjkCharacters`） | §3 `标题系统提示` |
| 同上 | 198–200 `frameMessages` | JSON 组帧，防用户文本破坏结构分隔符 | §3 `组帧消息` |
| 同上 | 203–230 `finishError` | `stop→无错`；`error`/`aborted→failure.message`；`max-tokens`；`tool-calls`；其它 → `unsupported finish reason "<kind>"` | §4 `结束原因错误` |
| 同上 | 231–296 `generateSessionTitleWithLlm` | 空消息校验 → 组帧 → 字节上限 → 路线 → 载荷 → 块拼接/工具块拒绝/规范化/空标题拒绝 | §5 `准备标题调用` + §4 `完成标题调用` |
| `session-title-first-prompt-llm/src/index.ts` | 18 `Config` / 34 `apply` | 首条消息选择器（`requires one human message`） | §3 `选首条消息` |
| `session-title-all-prompts-llm/src/index.ts` | 18 `Config` / 34 `apply` | 全部消息选择器 | §3 `选全部消息` |

---

## 二、实现要点

### §0 常量与通用读取
`事件类型标题="session/title"`、`事件类型标题请求="session/title-llm-request"`、来源种类集 `fallback|provider|user`、
自动模式集 `first-prompt|all-prompts`、`超时码`、`最大定时器毫秒=2147483647`、`安全整数上限=9007199254740991`、
`配置键集`；通用读取 `取字段(表, 候选键表, 默认值)`（中文键优先、英文键回退）、`有字段`、`连接文本`、
`是正整数`、`断言正整数`、`是安全序号`。

### §1 类型形状
按上游 `types.ts` 逐字段对齐；`造来源提供方(提供方, 模型)`：`模型` 非空串时才挂 `model:{provider, model}`（上游 `model?` 可选）；
`是合法来源` 校验 `kind ∈ {fallback, provider, user}`；`造标题快照` 为载荷浅拷贝 + `eventSeq` / `updatedAt`。

### §2 配置校验（上游 `resolveSessionTitleLlmConfig`）
未知键 → `unknown config key "<键>"`；五字段逐个正整数断言；`timeoutMs > 最大定时器毫秒` → `must not exceed 2147483647`；
`provider` 与 `model` **必须同时给出**（只给一个 → `provider and model must be supplied together`），且均须非空串
（`provider and model overrides must be non-empty strings`）；通过后返回**副本**。

### §3 提示构造与消息选择
`标题系统提示` 逐字复刻上游 4 行并以 `\n` 连接；`组帧消息` = 固定前缀 + `序列化JSON(消息表)`；
`选首条消息`（空/非表 → `first-prompt title provider requires one human message`）、`选全部消息`（浅拷贝）、
`按模式选消息`（未知模式 → `unknown automatic mode <模式>`）。

### §4 请求/响应形状
`消息序号表`、`造标题请求载荷`（`titleProvider` / `messageSeqs` / `route` / `system` / `messages` / `maxTokens`）、
`结束原因错误`（五分支 + 兜底）、`拼接文本块`（仅 `type==="text"`，以空格连接）、`含工具调用块`、
`造标题结果`、`完成标题调用`（结束原因错误 → 工具块拒绝 → 规范化 → 空标题拒绝 → 结果装配）。

### §5 调用准备
`解析路线`（配置 → 请求视图 `route/路线` 回退 → 抛错）；
`准备标题调用`（空消息校验 → 组帧 → `字节长度` 上限校验 → 路线 → 载荷，返回 `{组帧, 字节数, 路线, 载荷}`）。

### §6 比较/更新 + 事件形状 + 不变量
`标题同值`（双方 `规范化会话标题(…, 安全整数上限)` 后比较）、`需更新标题`、`造标题事件`、`事件定位`、
`校验标题事件`（配对判据 + 逐条安全序号 / 去重 / 更早人消息引用）。

### §7 与会话格式词汇表衔接
`标题事件词汇内` = `会话格式.已知事件类型("session/title")`。**实测结果为假** —— `session/title` 未登记入
`src/会话格式.light` 的 `事件词汇表`，故 `标题事件处置` 按 v2 语义返回 `未知可忽略`（上游 `known-event-types`
同样未收录 `session/title`，行为一致）。

---

## 三、测试验证

命令：`cd lightharness && python 运行.py examples/test_会话标题族.light`

```
===== 第 14 轮任务 6：会话标题域（纯逻辑面）=====
test_会话标题族 PASS
```

`rc=0`，159 条断言全绿，覆盖 §0 通用读取与正整数/安全序号边界、§1 三来源与载荷/快照/输入形状、
§2 配置校验 8 类失败分支 + 成对/非空/上限通过路径、§3 系统提示 4 行 + 组帧 + 三种消息选择、
§4 请求载荷六字段 + 结束原因五分支 + 文本块拼接/工具块 + 完成调用 4 类失败分支、
§5 路线解析与调用准备（字节数 = 组帧 UTF-8 字节长、空消息/超字节上限抛错）、
§6 同值/需更新 + 事件形状 + 不变量 7 类失败分支、§7 词汇表衔接。

---

## 四、反跑结果（3/3 ALL OK）

命令：`python _antirun_title.py`

```
=== 第 14 轮任务 6 反跑判据（会话标题域）===
✓ A 标题比较不规范化 (判红运行 rc=1)
✓ B 不变量不再校验 messageSeqs ⟺ user 配对 (判红运行 rc=1)
✓ C 系统提示不再注入目标词数/汉字数 (判红运行 rc=1)
✓ 字节级恢复校验 (sha256 f442f743bf53)
✓ 恢复后回归绿 (rc=0，PASS 已打印)
ALL OK
```

判据细节（变异点均在 `src/会话标题族.light`）：
- **A**：`标题同值` 的 `返回 规范化会话标题(甲, …) == 规范化会话标题(乙, …)` → `返回 甲 == 乙`
  （任务书判据 A「规范化不去除内部空白折叠」在本模块的等价可变异点 —— 规范化实现位于只读的 `src/会话标题.light`，
  故把「比较侧不规范化」作为本模块的可控变异点）→ 首尾/内部空白断言红；
- **B**：`校验标题事件` 的配对判据 `如果 (序号数 == 0) != 用户改:` → `如果 假:` → 「user 来源须无序号 / provider 来源须有序号」断言红；
- **C**：`标题系统提示` 第 4 行 `"Aim for about " + 转字符串(配置["targetWords"]) + …` → 静态串 → 目标词数/汉字数断言红。
恢复走 `finally`，逐字节 sha256 校验通过。

---

## 五、未移植项（宿主面登记）

| 上游位置 | 内容 | 处置 |
|---|---|---|
| `session-title/src/client.ts`（10 行） | Cordis 客户端 / 服务总线 / 设置注册 | 剔除 |
| `session-title/src/index.ts`（833 行）大部 | 投影订阅、事件 append、`SessionTitleProviderId` 品牌构造、调度与去抖 | 剔除；只留类型形状与不变量 |
| `session-title-llm/src/index.ts:231+` 实调部分 | `ctx.llm.stream` 实际调用、`deadline` / `timeoutMs` 真实定时器、`SESSION_TITLE_TIMEOUT` 抛出 | 剔除；以「块表 + 结束种类」入参投影 |
| 同上 `registerSessionTitleLlmProvider` | 提供方注册到宿主注册表 | 剔除；本模块以 `按模式选消息` 纯函数表达 |
| `session-title-first-prompt-llm` / `-all-prompts-llm` | `apply(ctx, config)` 插件安装、会话读写、消息订阅 | 剔除；只留消息选择器语义 |
| `BlockAssembler` 流式装配 | 流式文本块聚合 | 剔除；本模块以「块表」入参投影 |

---

## 六、语言差异（新缺陷）

### L-119 —— v4.0「L0 单字别名」是静默保留字，且误用报错完全误导

**现象**：任务书「命名避坑」系列之外，本轮实测发现 v4.0 的 L0 单字别名**在词法层把常见中文词吞成关键字**。
实测：
```
设 配 为 [10, 20]      ← 合法，不报错
打印 配[0]             ← 词法把 `配` 判为 K_MATCH（`匹配` 的单字别名）→ 本行被解析成「匹配 [0]:」
                          codegen 产出 `print()` + `match [0]:` 空体
                          → 运行期报：错误: 缩进错误  expected an indented block after 'match' statement
```
**病根是保留字冲突，报错文本却指向「缩进」**，且第一句合法、第二句才炸 —— 排查代价极高
（本轮实际耗时即由此产生，先后误判为「字符串转义问题」「字典迭代 codegen 缺陷」）。

**L0 单字别名全表**（`antlrparser/LightLangLexer.g4` 的 `K_*` 单字分支 + `src/keywords.py` 实测）：
`若/则/否/是/段/出/导/遍/对/跳/过/试/捕/抛/终/返/配/己/自/设/为/从/当/空/长/首/末/余/父/常/并/与/且/或/的/在/到/现/例/步/断/接/承/宏/引/掷/跃/非/真`

**绕法**：标识符完全避开上表（改用 `配置结果` / `目标表` 等词）。
**最小复现**：`examples/_repro_L119.light`（绕法形态，rc=0）。

**建议修复方向**：① 单字别名在**非语句首位置**不做关键字判定（或仅在 `:` / 表达式起始处生效）；
② 词法判定为关键字后若后续 token 无法构成合法语句，报错文案应显式提示「疑似保留字冲突」而非「缩进错误」。

### L-120 —— 标识符可被关键字序列「完全切分」时仍被切碎（L-084 同族，触发面不同）

**现象**：标识符**并不等于**关键字，但若整串可被关键字序列完全覆盖切分，词法器仍会切开它。实测：
```
尝试:
  抛出 新建 错误("boom")
捕获 异常 错误己:       ← `错误己` 被切成 `错误`(关键字) + `己`(K_SELF 单字别名)
                          解析报：期望'为'或'等于'，但得到「:」
捕获 异常 错误甲:       ← 正常（`错误`+`甲`，而 `甲` 不是关键字 → 整串不可全切分）
```
即判定条件是「整串可被关键字全覆盖切分」，而非 L-084 的「含有关键字字样」：
- 安全：`错误甲` / `文本长` / `首条表` / `异常甲` / `占位A`（不可全切分）
- 被切碎：`错误己`（错误+己） / `异常己`（异+常+己）—— 注意 `异常` 本身**不是**关键字，但 `异`/`常` 是单字关键字

**绕法**：标识符后缀不用单字别名/关键字（本轮改用拉丁字母后缀 `错误A`…`错误V`）。
**最小复现**：`examples/_repro_L120.light`（绕法形态，rc=0）。

**建议修复方向**：与 L-119 同源 —— 词法不应把「一个连续标识符」切开；应整体最长匹配为 `IDENTIFIER`，
仅在整串恰好等于关键字时才给出关键字 token（即升级计划 P0-A「词法确定性切词重构」要解决的问题）。

> 任务书预分配的 **L-119 / L-120 本路均已占用**（如上）。
> 本路其余摩擦命中既有登记项：L-089（字符串 `{标识符}` 插值）、L-061/L-093（跨模块未捕获异常位置块错配）、
> L-045（`写` 只接受字面量串/变量）。

---

## 七、移交清单（→ 路M）

| # | 事项 | 说明 |
|---|---|---|
| 1 | **模块命名偏差（需裁定）** | 任务书指定 `src/会话标题.light` / `examples/test_会话标题.light`，但该两文件属**第49号对标卡**且已 done。本路落地为 `src/会话标题族.light` / `examples/test_会话标题族.light`，**只读导入** #49 的 `规范化会话标题`。若路M 裁定应合并进 #49 模块，请指示（会改动已 done 交付物，本轮未做）。**#49 的 `examples/test_会话标题.light` 本轮已回归验证仍为绿，未被触碰。** |
| 2 | 对标卡 #97 | session-title 族 → `src/会话标题族.light`，建议状态 `done`（映射按 §一 表） |
| 3 | 缺陷编号 | **L-119**（L0 单字别名静默保留 + 误导报错）、**L-120**（标识符被关键字全切分）；各附 `examples/_repro_L1xx.light` |
| 4 | 行为差异 | R14-D6 —— ① 任务书 §1 提的 `source: 'first-prompt'\|'all-prompts'\|'llm'\|'manual'` 与「version v1/v2 / createdAt / updatedAt ≤ 上限」不变量**上游无对应**：上游实际是 `kind: fallback\|provider\|user` + 快照 `eventSeq/updatedAt`，不变量是 `messageSeqs 空 ⟺ kind=user`。本模块按**上游忠实**实现；② 任务书反跑判据 B「不变量不再检查长度上限」在本模块不存在（长度约束属 #49 `normalize`），已改用等价的配对判据 B；③ `session/title` 未登记入 `会话格式` 词汇表 → §7 返回「未知可忽略」 |
| 5 | 提交文件 | `src/会话标题族.light`、`examples/test_会话标题族.light`、`_antirun_title.py`、`examples/_repro_L119.light`、`examples/_repro_L120.light`、本报告（6 个新文件） |
| 6 | 只读引用 | `src/会话标题.light`（#49）、`src/会话格式.light`、`src/溢出.light`（`字节长度`）均**只读未改** |
| 7 | 建议 | L-119/L-120 与升级计划 P0-A「词法确定性切词重构（最长匹配优先、标识符内部不拆分）」同一根因，建议在 P0-A 中一并收口 |
