# _task1_repair域复刻_交付报告.md —— 第 10 轮任务 1（T2-G1：repair 域复刻）

> 日期：2026-09-12 ｜ 仓库：`lightharness` ｜ 上游：`G:\github\deepseek-harness`（0.1.5-rc.2）
> 上游依据：`packages/core/session/src/repair.ts`（interruptedTurnClosers，135 行）+ `tests/repair.spec.ts`（10 场景）
> 交付物：`src/会话格式.light` 新增 §13 repair 段 + `examples/test_修复_repair.light`（30 断言全绿，新增）+ `_antirun_repair.py`（3 判据全过）
> 铁律遵守：只改互斥表内 `src/会话格式.light`；新增一律 .light；无 Python 绕缺陷。

---

## 1. 上游依据

`interruptedTurnClosers(events)` 纯函数：扫描事件日志，为崩溃留下的未闭合 turn/step/tool-call 按序合成关闭事件，使恢复转写对 provider 合法。核心语义：

- 状态机：`openTurn` / `openStep` / `pendingCalls(Map<callId,{step,callSeq?}>)`；turn/start、turn/end、step/end 都清空 `pendingCalls`（早前轮调用不得泄漏到尾部修复）。
- `assistant/message` 收集 content 中 `type:'tool-call'` 块为待决；`tool/call` 回填 `callSeq`；`tool/result` 按 `data.message.source.callId` 消账。
- 合成序：未决调用先合成错误 `tool/result`（`callSeq` 存在 → `TOOL_OUTCOME_UNKNOWN`/`ToolOutcomeUnknownError`，否则 `TOOL_NOT_STARTED`/`ToolNotStartedError`，两段英文提示文案逐字对齐）→ `step/end`（若开启）→ `turn/end {reason:{kind:'interrupted'}}`。
- 序号从最后真实事件 seq+1 连续递增；时间戳复用最后真实事件；已启动的合成 result 带 `sourceEventSeqs:[callSeq]`；平衡/空日志返回空。

## 2. 实现要点（src/会话格式.light）

| 项 | 位置 | 说明 |
|---|---|---|
| 恢复码常量 | §13 头部 | `恢复码工具未启动 = "TOOL_NOT_STARTED"`、`恢复码结果未知 = "TOOL_OUTCOME_UNKNOWN"`（已导出） |
| `修复取值` 段 | §13 | 安全取值：光明 `turn/start` 常记 **空 数据**（`会话.记录轮次开始` 传 空），直接 `.获取` 会崩，统一走 `是字典` 守卫 |
| `中断轮闭合器` 段 | §13 | 状态机用字典 `待决调用`（插入序 = 转写序，对齐上游 Map 语义）；`字典删除` 消账（已有导入）；轮界重置用「重绑新字典」实现 `.clear()` |
| 合成 tool/result 数据 | §13 | `{"调用": callId, "成功": 假, "消息": {id="interrupted-tool-result-<callId>-<seq>", role:"user", "来源":{"kind":"tool","callId"}, "content":[{type:"tool-result", toolCallId, isError:真, content:[{type:"text", text:<上游文案>}]}]}, "错误": {"名称":…, "代码":…}}` ——**全部落在光明 tool/result 词汇（必选 调用/成功，可选 消息/错误/输出）内**，断言 13 实证可通过 `校验事件载荷` 严格校验、可经 V3 编解码回放 |
| 已启动标记 | §13 | `来源事件序号 = [callSeq]`（光明事件级键，经 `事件带来源` 同款形状），未启动不携带 |

**调用点核实（任务范围 4）**：通读 `持久化.light` 读入路径（`读入会话/读入会话宽容/读入会话带策略`）与 `会话.light`——**均无既有 repair 类逻辑**。按任务书「若未调用则仅新增段落不接入」，本轮仅新增段落 + 导出，**未接入恢复路径**（接入属增强，见 §5 未移植项）。

## 3. 测试与 CI

```
cd lightharness
python 运行.py examples/test_修复_repair.light   # 30 断言，RC=0
python _antirun_repair.py                        # 3 判据 + 字节级恢复，RC=0
```
`test_修复_repair.light` 覆盖 repair.spec.ts **全部 10 场景** + 恢复码常量导出 + V3 严格校验：
平衡返回空 / 空日志返回空 / 仅 turn 闭合（序号 1、原因 interrupted）/ step 先于 turn（[2,3]）/
TOOL_NOT_STARTED 全形状（三段 [3,4,5]、callId、错误码/名、提示文案、isError、无 sourceEventSeqs、消息 id）/
已答不合成 / 已闭步骤不合成（仅 turn/end，序号 4）/ 早前轮不泄漏（仅 new-call）/ 多调用按日志序（仅 call-b）/
TOOL_OUTCOME_UNKNOWN（错误码/名、sourceEventSeqs=[3]、两段提示文案）/ 孤儿 tool/call 优雅处理 / 常量导出。

回归全绿（RC=0）：`test_会话格式` / `test_会话` / `test_持久化` / `test_行为对照_会话持久化` / `test_修复_会话` / `_repro_L082` / `test_会话格式冒烟` / `test_会话V3迁移` / `test_持久化增量` / `test_会话深化` / `test_二分2`。
**用例数**：新增 `test_修复_repair.light` +1。
**既有红（与本路无关，沿用第 9 轮上报）**：`test_会话存储` 环境性红（「初始会话列表为空 实际=4」），其 src 不导入 会话格式、与本改动零引用交集。

## 4. 反跑判据（_antirun_repair.py，3 项，字节级备份/恢复 src/会话格式.light）

| 项 | src 变异 | 判红断言 | 实测 |
|---|---|---|---|
| A | 错误码改错：`错误["代码"] 为 恢复码工具未启动` → `恢复码结果未知` | 5d TOOL_NOT_STARTED | ✓ 红→恢复绿 |
| B | 序号基线改错：`最后事件["序号"] + 1` → `0` | 3b/4b/5b 序号续接 | ✓ 红→恢复绿 |
| C | 平衡返回空改错：去掉 `有开启轮次 == 假` 判断 | 场景1 平衡日志返回空 | ✓ 红→恢复绿 |
| — | 恢复后 sha256 一致 + 回归绿 | — | ✓ |

## 5. 未移植项（语义等价/词汇约束，非缺陷）

1. **恢复路径接入未做（增强）**：`读入会话带策略` 未调用 `中断轮闭合器`（上游在持久化契约端到端消费）；按任务书「仅新增段落不接入」处理，接入时机由路M/后续轮裁决。
2. **`surfaceOp:'append'` 未附加**：上游合成 result 带事件级 surface 标记；光明 surface 词汇是 `数据["表面操作"]`（system/message 专用），tool/result 在光明投影中天然上浮，语义等价故未附加。
3. **`data.turn`/`data.step` 未携带**：上游合成事件 data 含轮/步上下文；光明 tool/result 严格词汇封闭键集，携带即被 `校验事件载荷` 拒绝，为保「可经 V3 回放」放弃（上下文在日志前文）。
4. **`reason.kind` 展平**：上游 turn/end `data.reason={kind:'interrupted'}` → 光明 turn/end 词汇必选 `原因`，展平为 `原因="interrupted"` 字符串（与既有 `记录轮次结束("completed")` 形状一致）；step/end 同。
5. **tool/call 关联双键**：上游 `data.callId`；光明无统一「记录工具调用」段落，实现同时接受 `callId` 与 `调用` 键（assistant/message 块取 `type=='tool-call'` 的 `id`）。
6. **语言缺陷**：实现未遇新缺口（字典插入序遍历 / 字典删除 / 是字典守卫均可用），无新登记；`修复取值` 属对「空 数据」的防御式写法，非语言缺陷。

## 6. 移交清单

- 改 `src/会话格式.light`：新增 §13（恢复码常量 2 + `修复取值` + `中断轮闭合器`）+ 导出清单追加 1 行
- 新增 `examples/test_修复_repair.light`（30 断言 / 13 组，对照 repair.spec.ts 全部 10 场景）
- 新增 `_antirun_repair.py`（A/B/C 三判据）
- 未动：`src/会话.light`（repair 无调用点）、`src/持久化.light`（不在互斥表）、`docs/`（T2-G1 回填 ✅ 由路M 统一）
- CI 预期：230 + 1 = 231 passed（以路M 全量为准）
