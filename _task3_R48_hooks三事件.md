# 任务3（R48）：hooks 三事件域深化（message/pause/resume）—— 交付报告

> 日期：2026-09-17 ｜ 轮次：第48轮 ｜ 优先级：P1 ｜ 对标号：#10
> 交付物：`src/钩子协议.light`（追加 events/runner/detached 三段）、`src/钩子.light`
> （追加三钩子点纯决策段）、`examples/test_R48_hooks三事件.light`、本报告
> 上游基线：deepseek-harness 0.1.5-rc.2（a305303422），上游源 `G:\github\deepseek-harness\packages\hooks\hook-protocol\src\`

---

## 1. 做了什么

#56 已做 matcher（甄别判定），R13 以来的钩子协议卡覆盖 codec/merge/两方言 config/扩展点映射。
0.1.5-rc.2 的 hook-protocol 尚有三个纯逻辑文件未对齐，本轮按任务书命名的三事件域补齐：

| 任务书域 | 上游文件 | 复刻位置 | 内容 |
|---|---|---|---|
| **message 事件（消息钩子）** | `hook-protocol/src/events.ts` | 钩子协议 §追加一 | 持久钩子消息对 hook/invoked + hook/result 的载荷构造 |
| （message 域配套） | `hook-protocol/src/runner.ts` | 钩子协议 §追加二 | runHook 的纯决策核：时长解析/退出码归一/基建故障产出 |
| **pause 事件（暂停钩子）** | `hook-protocol/src/detached.ts` | 钩子协议 §追加三 | emit 形钩子运行的静默跟踪：登记/落定/排水中止/续等 |
| **resume 事件（恢复钩子）** | detached 生命周期 + `core/agent-loop/src/agent.ts` 相位机（R47 §6.2 已复刻） | 钩子.light 三钩子点 | 排水后由新建跟踪器重新接纳；恢复三态词表对齐 循恢复决策 |

### 2.1 message 域 —— 持久钩子消息对（events.ts）

钩子事件本身是「消息」：只落日志、不落表面，必须轮内成对（invoked/result）：

- `概要上限默认 = 500`（DEFAULT_STDERR_SUMMARY_MAX_CHARS，两方言 config 同款参考默认）；
- `概要化标准错误`（summarizeStderr）：去首尾空白后为空 → 空；超上限在截断处加省略号 `…`；
- `造发起载荷`（appendHookInvoked）：`{turn, point, dialect, handlerId}`，甄别主体缺省时
  省略 matcher 键；
- `派生钩子裁定`：持久 decision 派生——已解析裁定优先；否则 续行标志:假 → `"stop"`；否则
  `"pass"`（output.decision ?? (continue === false ? 'stop' : 'pass') 逐行对齐）；
- `造结果载荷`（appendHookResult）：`{turn, point, handlerId, decision}` + 退出码存在才带
  `exitCode` + stderr 概要非空才带 `stderrSummary` + `durationMs` 必带。

### 2.2 运行纯核（runner.ts）

- `默认钩子时长 = 600000`（DEFAULT_HOOK_TIMEOUT_MS = 10 分钟，两方言同款）；
- `运行时长毫秒`：hook.timeoutSec 秒转毫秒覆盖方言兜底；
- `落码归一`：信号致死（null 退出码）与非数值 → 空（无干净退出码可依，非阻断错误）；
- `故障产出`：执行器基建拒绝 → `解析钩子产出(空, "", 消息, 空)`——无退出码、失败记 stderr、
  轮次照常推进（runHook 永不抛的契约）。

### 2.3 pause 域 —— 静默跟踪（detached.ts）

- `造跟踪器`：`{"在飞表": [], "已中止": 假, "排水中": 假}`；
- `跟踪登记`（track，重复幂等）/ `跟踪落定`（settled runs are pruned，长会话不积压）；
- `跟踪排水决策`（drain 纯决策面）：触发中止（挂起）后逐波观察——在飞非空 → 续等
  （缘由 in-flight）；本波排水中又有人登记 → 续等（缘由 late-track）；观察到清空且无迟到登记
  → 静默（逐波循环由调用方驱动，对齐上游 `while (inflight.size > 0)` 重查）；
- 真实执行/AbortController/ fiber 等宿主面剔除，中止效果由调用方落地。

### 2.4 resume 域 —— 恢复接纳与三钩子点（钩子.light）

上游无命名为 resume 的钩子；恢复面按上游实际生命周期对齐：
**排水后的恢复接纳 = 新建跟踪器**（bridge 处置后重新 apply；旧跟踪器已中止不再接纳），
由 `造恢复跟踪器` 提供；并在钩子决策层补齐三钩子点（纯决策面，全部新增段，零改既有）：

- **消息钩子点** `消息钩子判定`：对齐 agent.ts preStep 的 pre-step 瀑布——处理器可否决一批
  待办消息（返回 `{"裁定":"reject","缘由":…}`），无人否决即放行（enter）；首个否决的缘由浮出；
- **暂停钩子点** `暂停钩子决策`：在飞未清（in-flight）或排水中又有登记（late-track）→
  不可入暂停且需续等；静默 → 可暂停；
- **恢复钩子点** `恢复钩子决策`：恢复三态词表对齐 R47 `循恢复决策`——相位非 idle 或排水未清
  → 忙；处理器否决 → 待机（可恢复=假）；有待办或折算带待唤 → 续跑；否则待机；
  待唤重放由 `循相位收敛` 承担，本段不重复。

---

## 2. 验证结果

| 项 | 结果 |
|---|---|
| `python 运行.py examples/test_R48_hooks三事件.light` | **rc=0，全断言通过** |
| 测试规模 | 6 大组约 55 组断言 |
| 既有回归 | test_钩子 / test_钩子协议 / test_钩子深化 / test_agentE5钩子 / test_一次性监听器 / test_协议深化 / test_R34_集成测试 全 rc=0 |

关键断言组：
1. **消息对**：500 上限截断加省略号、空白 stderr 概要为空、matcher 缺省省略、
   decision 派生四分支、阻断产出载荷（exitCode 2 + stderrSummary）、干净退出载荷
   （exitCode 0 必带、空概要省略）；
2. **运行纯核**：30 秒覆盖 600000 兜底、信号致死无码、故障产出非阻断三断言；
3. **静默跟踪**：登记幂等、落定即清、排水触发中止、in-flight/late-track 续等、清空静默、
   恢复跟踪器重新接纳；
4. **三钩子点**：message 否决拒绝/首个缘由浮出/空缘由仍拒绝、pause 三态、
   resume 三态全分支（忙×2/待机×2/续跑×2）。

---

## 3. 铁律核对

- ✅ 不改 #56 已做的 hook-protocol matcher（甄别判定四段与既有全部段零改动，只追加）；
- ✅ 改后既有 hooks 测试不破（钩子/钩子协议/钩子深化/agentE5钩子/一次性监听器 全 rc=0）；
- ✅ 只改 `src/钩子.light` + `src/钩子协议.light`；
- ✅ 剔除真实子进程 exec/spawn 与文件 IO（沿用本模块既有纯逻辑化约定：钩子产出由调用方注入）；
- ✅ 全量 pytest 回归见路M收口记录（基线外零新增红）。

## 4. 已登记偏差

- **D-5**：上游 detached 用 AbortController/Promise 集合实现排水；光明无异步原语，改为
  「在飞标识表 + 决策函数」的纯决策面，逐波循环由调用方驱动（登记/落定语义逐行对齐）；
- **D-6**：消息钩子点把 pre-step 瀑布的 Cordis 组合语义简化为「任一否决即拒绝」的保守裁定
  （enter/reject 词表与默认放行对齐 agent.ts）；
- **D-7**：resume 无上游同名钩子；按 detached 生命周期（处置后重新 apply）+ R47 相位机
  恢复三态词表对齐，未臆造上游不存在的事件名。
