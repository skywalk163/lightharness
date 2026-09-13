# 任务4 交付报告：api 会话控制器纯逻辑（types/assistant-stream/remote-events → src/会话控制类型.light）

> 任务来源：`G:\dswork\duan-light-merge\复刻_第16轮_任务prompt分发 (1).md` 任务4
> 日期：2026-09-13 ｜ 上游：`G:\github\deepseek-harness`（本地 HEAD 9d9035b7c1）
> 目标模块：`lightharness/src/会话控制类型.light`（对标 #107；命名预检查通过——src/ 下无同名模块）

---

## 一、上游对应表（packages/api/session-controller/src/，纯逻辑 3 文件 727 行）

> **范围声明**：types.ts 611 行覆盖 Session RPC 全套请求/值对（Create/SelectModel/Rename/Fork/Prompt/
> UpdateQueue/Cancel/Status/Subagent 五组/Skill/ToolDisplay/Voice/内容块 journal/Profile/Q&A/
> FileSearch/FileRead/FileUpload/FileBox/Workspace 等 30+ 形状）。本模块复刻**可断言的纯逻辑核**：
> 状态枚举/错误种类表/判别函数/模型投影回退/助手流累加器算法；纯形状（请求/值对字段清单）在
> 交付报告本表登记，测试聚焦行为面（全部 RPC 形状逐字段罗列超出纯逻辑可测范畴，登记 §五）。

| 上游位置 | 光明段落/常量 | 核心语义 |
|---|---|---|
| types.ts 常量 | 会话搜索结果上限=20 / 搜索摘要最大码点=240 | SESSION_SEARCH_RESULT_LIMIT / SESSION_SEARCH_SNIPPET_MAX_CODE_POINTS 逐字 |
| types.ts SessionStatus | 会话状态表 / 是否会话状态 | 8 值逐字：idle/running/queued/steering/waiting/loading/degraded/orphaned（反跑 C 锚点） |
| types.ts SessionStatusValue | 造会话状态值 / 状态运行中 | {status, running}；running 仅 running 态为真；未知状态抛 `unknown session status: X`（自拟，登记） |
| types.ts RemoteErrorDetailsMap | 会话错误种类 | 13 kind 逐字（session/model-unavailable、session/conflict、session/agent-busy、session/invalid-time-zone、session/workspace-attach-failed、agent-preset/conflict、session/attachment-invalid、session/queue-item-not-found、session/steer-unavailable、session/title-invalid、session/fork-unavailable、subagent/not-found、subagent/catalog-diagnostic）→ 必选细节键表；未知 → 空 |
| types.ts PromptContentPart | 是否提示内容部件 | text{text} / image{mediaType, data} / file{receiptId} 三形态判别（含缺字段拒绝） |
| types.ts QueueAction | 是否队列动作 | edit{content 非空} / remove / steer（edit 空内容拒） |
| types.ts SessionAddress | 是否会话地址 | session{sessionId} / subagent{parentSessionId, childSessionId, mode: 'one-shot'\|'continuable'} |
| types.ts ModelSelection/ModelSelectionProjection | 造模型选择 / 模型投影回退 | {provider, model, reasoningEffort?}；投影 {lastUsed, next}，next 缺省回退 lastUsed（上游回退语义） |
| types.ts SessionAssistantStreamFrame | 造起始帧 / 造数据帧 / 造结束帧 / 是否流帧 | 'start'{attemptId, revision, startedAfterSeq, turn, step} / 'chunk'{+index, time, chunk} / 'end'{+index, outcome: committed{eventType: 'assistant/message'\|'assistant/attempt'}\|aborted\|failed{message}} 逐字 |
| assistant-stream.ts SessionAssistantStreamAccumulator | 造流累加器 / 接受流帧 / 流快照 | accept 算法四步：① start 且 revision==1 且 当前≠0 → 重置；② revision≠当前+1 → 丢活跃尝试、对齐版本、不折叠；③ start 建尝试（startedAfterSeq=持久游标、nextIndex=0）/ chunk 校验 attemptId+index 连续（缝隙或错 attemptId → 终止折叠）/ end 清尝试；④ 脏标记。snapshot：非脏返回缓存（身份稳定）、脏物化 {revision, activeAttempt?{attemptId, startedAfterSeq, turn, step, nextIndex, stream}}；EMPTY_BASELINE={revision:0}（B 判据空快照） |
| remote-events.ts（14 行） | 是远程事件种类 | `'api-session/activity' \| 'api-session/added' \| 'api-session/error' \| 'api-session/removed' \| 'api-session/status'` 逐字 |
| types.ts 其余（30+ RPC 请求/值对、SessionWireHeader/Event、Skill、内容块 journal、FileBox 等） | 形状登记 | 纯数据形状逐字段清单见上游源码（SessionSummary{sessionId, updatedAt, running, blank, parentSessionId?, origin?: 'subagent', cwd?, projections?}；SessionWireEvent{type, seq, time, data, ignorable?, sourceEventSeqs?, surfaceOp?}；SessionWireSurfaceOp='append'\|{op:'replace', startSeq, endSeq} 等），无运行时行为，登记 §五 |

## 二、实现要点

1. **累加器算法忠实度**：accept 的四步顺序（重置→版本连续守卫→按形态折叠→脏标记）不可乱；chunk 折叠双校验（attemptId 相符 + index==nextIndex）任一失败即**终止折叠**（丢活跃尝试）而非跳过——对齐上游「缝隙/错 attempt → 终止折叠」语义；快照缓存身份稳定（非脏直返）。
2. **空基线**：EMPTY_BASELINE={revision:0} 无 activeAttempt 键（B 判据）；重置语义（start revision==1 且当前≠0）与版本跳变对齐（revision=frame.revision）分两条路径。
3. **接口合并投影**：上游 SessionEventMap/MessageSourceMap/RemoteErrorDetailsMap 为 TypeScript 声明合并——以种类判定表（会话错误种类 返回必选细节键表）承载。
4. **绕法**：无 且/或 行内链（L-043）、标识符避关键字与单字别名切分（L-119/L-120/L-084）、无花括号文案（L-089）、可选键先 字典包含键（L-103）、双层赋值用 字典设置（L-123）。

## 三、测试验证

```
cd G:\dswork\duan-light-merge\lightharness
$env:LIGHT_MERGE="G:\dswork\duan-light-merge\light-merge"; python 运行.py examples/test_会话控制类型.light
test_会话控制类型 PASS   （rc=0）
```

`examples/test_会话控制类型.light` 覆盖 7 组 ≥70 断言：状态枚举（8 值+未知+构造+运行判定+非法抛）、错误种类表（13 kind 键表逐字+未知空）、内容部件（text/image/file/缺字段/未知形态）、队列动作（edit 非空与空拒/remove/steer/未知）、会话地址（session/subagent 两模式/非法模式/缺父拒）、模型选择与投影回退（努力度可选键/回退/待定优先）、助手流（三形态构造与校验/A 判据 round-trip/累加器：空基线、revision 推进、chunk 入流、nextIndex、startedAfterSeq、快照缓存稳定、index 缝隙终止、attemptId 不符终止、版本跳变对齐、end 清尝试、重置语义）、远程事件 5+1。

## 四、反跑结果（3/3 ALL OK）

`lightharness/_antirun_t4_会话控制类型.py`（BASE 自定位；字节级备份→变异→跑本路测试→断红→恢复→断绿；恢复置于 try/finally）：

```
PASS C=变异 会话状态枚举 idle 改错 -> 红 (变异后运行 rc=1（期望非 0，真红）)
PASS 字节级恢复校验 (sha256 665ecf7520b6)
PASS A/B 判据（round-trip + 空快照判别）回归绿 (rc=0)
ALL OK
```

A=正常（会话类型构造→序列化→反序列化 round-trip）与 B=边界（空会话快照 {revision:0} 判别不崩溃）为测试内场景，随回归绿验证；C=变异（状态表 `idle`→`IDLE`，状态判定与构造断言立红）恢复后绿。

## 五、未移植项（宿主面登记）与任务书/上游差异

- **宿主面剔除**（任务书剔除清单全部 14 文件）：agent/commands/control/history/list/index（cordis+node）、catalog/file-references/media-references/model-selection-projection/skill-catalog（cordis）、client/ 子目录。
- **纯形状登记**（无运行时行为，未逐字段建构造器）：30+ 组 Session RPC 请求/值对形状、SessionWireHeader/SessionWireEvent/SessionWireSurfaceOp/SessionHistoryRecord/SessionPageRequest/SessionFollowRequest、SessionListMetadata/SessionProjectionHints/SessionProjectionBaseline、SessionSummary/SessionSearchItem、ModelCatalog 族、SkillEntry、SessionContentBlockJournalRecord、FileSearch/FileRead/FileUpload/FileBox/Workspace/AgentPresetInfo/QnA/Profile/ToolDisplay/VoiceTranscribe/Subagent 五组——字段清单以上游 types.ts 为准（本报告不逐字段重复）。
- **dsh-llm 依赖**：AssistantStreamAccumulator（chunk 推入/文本提取算法）在 dsh-llm 包内，本层 chunk 以 {time, chunk} 透传（登记 R16-D4）。
- 声明合并（SessionEventMap/MessageSourceMap/RemoteErrorDetailsMap/SessionProjectionMap）以判定表承载；Branded 品牌（session-request-id/file-upload-receipt-id）以字符串承载。

## 六、语言差异（本轮新缺陷登记）

- **L-137（按任务4预分配区间）**：局部变量名以关键字「尝试」开头时，后续下标赋值/读取在关键字边界被断开——`尝试["甲"] 为 1` 报「期望 '='、':' 或 '为' 在类型别名定义中」（`尝试` 被当关键字语句、`["甲"]…` 悬空）。绕法：变量名完全避开「尝试」等关键字字样（本模块改 活动项）。最小复现 `examples/_repro_L137.light`（绕法形态 rc=0）。与 L-120/L-101 同族。L-138 空缺顺延。

## 七、移交清单

- `lightharness/src/会话控制类型.light`（新增，≈330 行）
- `lightharness/examples/test_会话控制类型.light`（新增，PASS rc=0）
- `lightharness/_antirun_t4_会话控制类型.py`（反跑 3/3 ALL OK，BASE 自定位）
- `lightharness/examples/_repro_L137.light`（L-137 绕法形态复现，rc=0）
- 本报告。
- 移交路M：对标清单新增 **#107**（api session-controller 纯逻辑）；缺陷账 **L-137** 登记（L-138 空缺顺延）；行为差异清单 **R16-D4**（dsh-llm 累加器透传/unknown status 文案自拟/RPC 形状登记不建构造器）；CI 增 1 个 test_ 文件 + 1 个 repro（292+ 占 2）。
