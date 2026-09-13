# 任务1 交付报告：会话引用域（session-reference 纯逻辑面 → src/会话引用深化.light）

> 任务来源：`G:\dswork\duan-light-merge\复刻_第15轮_任务prompt分发 (1).md` 任务1
> 日期：2026-09-13 ｜ 上游：`G:\github\deepseek-harness` @ a305303422（0.1.5-rc.2）
> 目标模块：`lightharness/src/会话引用深化.light`（对标 #98）

---

## 〇、模块命名变更声明（铁律6 命名预检查）

任务书给定名 `src/会话引用.light` **与既有模块冲突**（`src/会话引用.light` 已存在，120 行，早期覆盖 #33：uri.ts 全部四个函数 编码会话引用URI/解码会话引用URI/格式化会话提及/解析会话引用文本 + 转义标签/去转义标签）。铁律1 明确「禁止修改任何既有 src/ 模块」，铁律6 要求命名预检查——按任务4/5「深化」命名先例改用 **`src/会话引用深化.light`**，只复刻未覆盖的 config/serialization/projection/spill/types 纯逻辑面；URI 编解码经 `从 会话引用 导入` 复用（不重复实现）。

## 一、上游对应表（packages/context/session-reference/src/）

| 上游位置 | 光明段落/常量 | 核心语义 |
|---|---|---|
| config.ts 常量 | 最大引用数=3 / 默认候选上限=50 / 默认引用字节上限=65536 | MAX_REFERENCES / DEFAULT_CANDIDATE_LIMIT / DEFAULT_MAX_REFERENCE_BYTES 逐字 |
| config.ts Config（仅 JSDoc 约束，无校验函数体） | 校验引用配置 | 补充实现：maxReferences 1..3 / candidateLimit 正整数 / maxReferenceBytes ≥65536 / referenceContextFraction 0..1；错误前缀 `SESSION_REFERENCE_INVALID_CONFIG`（错误码表 7 码逐字对齐，文案自拟登记 R15-D1） |
| config.ts SessionReferenceErrorCode | 错误前缀承载 | 7 码：INVALID_CONFIG/INVALID_REFERENCE/SELF_REFERENCE/TOO_MANY/READ_FAILED/BUDGET_EXCEEDED/CANCELLED（结构化 code 未复刻，登记） |
| serialization.ts stringifyTagSafeJson | 标签安全序列化 | 序列化后 `<` 全部 → `\u003c`（逐字）；输出不含字面 `<`；round-trip JSON 语义等价；不可序列化文案 `session-reference data is not JSON-serializable`（光明 序列化JSON 无 undefined/循环引用，该分支不可达，登记 R15-D1） |
| types.ts SessionReferenceSource/…Candidate | 造引用来源 / 造引用项 / 造引用候选 / 造提及候选 | kind='session-reference'/form='recall'/version=1 三层字面量；引用项 11 字段（capturedFormatVersion 可选键缺省不落，省略非 null）；候选 sameWorkspace=cwd 已记录且相等；提及候选 mention=`@[label](dsh-session:…)`，label 缺省回退 sessionId（`??` 语义：仅键不存在回退，空串不回退） |
| uri.ts invalidUri/escapeLabel | 无效引用URI文案 / （转义标签复用） | `invalid session reference URI ${JSON.stringify(uri)}` 逐字；label 转义 `\` 与 `]` 复用既有 转义标签 |
| uri.ts canonical 回验 | 校验引用URI规范 | 编码→解码→重编码全等组合（解码侧校验既有模块已含，本模块补组合断言） |
| projection.ts projectSessionConversation | 投影会话对话 / 保留对话条目 | user/message 保留（compact-checkpoint 来源或 user 来源）、assistant/message 保留 content、system/message 与 tool/result 丢弃；text 块 `\n` join、空文本丢弃、保持事件序 |
| projection.ts retainReferencedSession | 保留引用会话 | 两阶段保留：①超限整条丢弃（从头找第一个非 checkpoint 且非最新条，omittedMessages+1、droppedOmittedBytes 累计）②仍超限截断最长条（originalText，目标=上限−其余量）；异常文案逐字 `session-reference retention selected a missing message`（光明重建式移除不触发，保留语义）；stats {compacted(含检查点来源), originalMessages, retainedMessages, omittedMessages, omittedBytes, truncated(消息数或字节>0)}；返回 {数据, 完整数据, 统计}；数据 {sessionId, label, cwd:null, capturedThroughSeq, conversation(仅 role/text)} |
| projection.ts truncateWithNotice | 截断带占位 | 整体 ≤ 上限原样（省略 0）；超限收缩+占位 `\n[… omitted N UTF-8 bytes …]` 逐字；占位计入预算、省略数为被省略字节数 |
| spill.ts REFERENCE_WARNING | 引用警示文案 | 三行逐字（含行内换行） |
| spill.ts prepareReferenceOmission | 准备引用溢出 | truncated 假→空；store 缺省→`storage-not-configured`；保存抛→`save-failed`（不阻断）；成功→saved+SpillRef 键拷贝；suggestedName `session-reference-{inputIndex+1}.txt` 逐字 |
| spill.ts renderTranscript | 渲染快照文本 / 切片每行 | Markdown：标题/声明/警示/JSON 元数据（capture 去 conversation + capturedFormatVersion，缩进 2）/两行说明逐字/`### Message N: role` + 每行一个 JSON 字符串字面量（≤64 Unicode code points） |
| uri.ts 其余（scheme 常量/ParsedSessionReferenceText） | 既有模块已覆盖 | 不重复（解析文本**不去重**——上游去重在服务层，既有模块注释「去重保留首次」与上游差异登记 R15-D1，属既有模块范围本轮不改） |

## 二、实现要点

1. **分工**：既有 会话引用.light 覆盖 uri.ts；深化模块 import 复用其 编码会话引用URI/解码会话引用URI/转义标签，自身聚焦配置校验/形状/投影/溢出策略。
2. **上游行为对齐细节**：`label ?? sessionId` 仅 nullish（键不存在）回退，空串不回退（测试专条）；capturedFormatVersion 可选键省略而非 null；`<` 只转义开标签字符（`>` 原样）。
3. **字节→码点近似**：truncateWithNotice/保留预算按码点计数近似 UTF-8 字节（TextRetainer 宿主实现剔除，登记 R15-D1）。
4. **checkpoint 来源 kind 约定**：上游 isCompactCheckpointSource 实现在外部包，本层以 `"compact-checkpoint"` 种类约定投影（登记 R15-D1）。
5. **绕法**：无 且/或 行内链（L-043）、标识符避关键字与单字别名（L-119/L-120/L-084）、无花括号文案（L-089）、可选键先 字典包含键（L-103）、副本（L-082）。

## 三、测试验证

```
cd G:\dswork\duan-light-merge\lightharness
$env:LIGHT_MERGE="G:\dswork\duan-light-merge\light-merge"; python 运行.py examples/test_会话引用深化.light
test_会话引用深化 PASS   （rc=0）
```

`examples/test_会话引用深化.light` 覆盖 9 组 ≥55 断言：配置常量与默认值/六类非法校验、标签安全序列化（转义/无字面 </round-trip/空引用不丢字段）、URI canonical（构造带前缀/round-trip/幂等/无效文案逐字）、类型形状（引用项 11 字段/可选键省略/来源三层字面量/同工作区三态/提及格式/label 回退/标签转义）、投影（丢弃 system+tool+空 assistant/多块拼接/检查点保留+标记）、截断占位（未超限/预算内占位/省略字节）、两阶段保留（整条丢弃计数/compacted/未截断/数据形状/conversation 双键）、溢出三态（无存储/未截断空/保存成功 saved+建议名/保存失败）、快照渲染（标题/声明/警示/切片说明/消息标题/元数据版本）+ 64 码点切片（边界 64 恰单片段、90 字两片段）。

## 四、反跑结果（3/3 ALL OK）

`lightharness/_antirun_t1_会话引用深化.py`（BASE 自定位；字节级备份→变异→跑本路测试→断红→恢复→断绿；恢复置于 try/finally）：

```
PASS C=变异 URI 括号分隔符改错 -> 红 (变异后运行 rc=1（期望非 0，真红）)
PASS 字节级恢复校验 (sha256 249d3ac6dd13)
PASS A/B 判据（URI round-trip + 空引用序列化）回归绿 (rc=0)
ALL OK
```

A=正常（URI 构造→解析 round-trip）与 B=边界（空引用序列化→反序列化不丢字段）为测试内场景，随回归绿（rc=0）验证；C=变异（造提及候选 的 `](` 分隔符改 `)(`）立红、恢复后绿。

## 五、未移植项（宿主面登记）

- index.ts Cordis 服务装配面、file-reference-local/tmux-context 宿主面（任务书剔除清单）。
- spill.ts SpillStore.saveText 实际存储——以注入段落 `保存文本` 承载。
- projection.ts TextRetainer（宿主 UTF-8 headTail 截断器）与精确 UTF-8 字节统计——码点近似（R15-D1）。
- isCompactCheckpointSource 实现与 SessionSeq 品牌化（外部包）——以来源 kind 约定 + 裸数值投影。
- config 校验为补充实现（上游无校验函数体）；服务层引用去重/上限拒绝（TOO_MANY/SELF_REFERENCE/READ_FAILED/BUDGET_EXCEEDED/CANCELLED 抛出点）属服务装配面未复刻。

## 六、语言差异（本轮新缺陷登记）

- 无新缺陷（L-121~L-122 编号空缺，路M 顺延）。
- 行为差异（R15-D1）：码点近似 UTF-8 字节预算；序列化JSON 无 undefined/循环引用（不可序列化分支不可达）；既有 会话引用.light 解析文本去重与上游「去重在服务层」的差异（既有模块范围，本轮不改）；checkpoint 来源 kind 约定值。

## 七、移交清单

- `lightharness/src/会话引用深化.light`（新增，≈430 行）
- `lightharness/examples/test_会话引用深化.light`（新增，PASS rc=0）
- `lightharness/_antirun_t1_会话引用深化.py`（反跑 3/3 ALL OK，BASE 自定位）
- 本报告。
- 移交路M：对标清单新增 **#98**（session-reference 深化，注：模块名因命名冲突改用深化名）；行为差异清单 **R15-D1**；CI 增 1 个 test_ 文件（282+ 占 1）。
