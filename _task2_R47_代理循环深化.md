# 第47轮任务2交付：agent-loop 请求头四原因 + 暂停恢复 + 轮次驱动（#7）

> 日期：2026-09-17 ｜ 状态：**完成**

## 一、上游对照（只读）

- `packages/core/agent-loop/src/agent.ts`（ReactLoopAgent）：
  - **请求头四原因**（buildRequest 562-582，`RequestHeaderReason` 定义于 core/session types.ts）：
    `initial`（日志首个头）/ `resume`（循环实例首请求但日志已有头事件：进程重启、fork 种子）/
    `change`（后续头与基线不同，携带 startsSeries）/ `series`（头未变但显式开启新消息系列）；
    头相同且无系列边界 → **不追加** header 事件。
  - **相位机**（Phase idle/running/maintenance + wakeDriver 闩锁 187-197）：非 idle 相位的唤醒
    不丢失——闩为 `wakeRequested`，收敛到 idle 时重放（暂停→fold→恢复 的宿主机制）。
  - **轮次驱动**（turn() 283-349）：`max-tokens` 粘滞——"once any step hits the ceiling, later
    steps that complete normally must not downgrade the turn outcome"（305-310）；
    步骤终因非空且待办 nextStep 队列空 → 轮次跳出（315-319）。

## 二、修改（src/代理循环.light 追加 §6，全部 循 前缀，纯决策面）

1. **请求头四原因**：
   - `请求头原因表 = ["initial","resume","change","series"]`；
   - `循环请求头原因(已登记, 有基线, 头变化, 系列边界)` → `{"原因", "记录", "开始系列"}`，
     判定序列逐行对齐 agent.ts:570-581（含"头同无边界 → 不记录"）；
   - `循头相等(甲, 乙)`：嵌套 config/tools 深比较（对齐 headerEquals 语义）。
2. **暂停恢复（相位机）**：
   - `相位表 = ["idle","running","maintenance"]`；`循建相位机(上轮次=0)`；
   - `循相位可转/循相位转`：合法转换 idle→running/maintenance，running/maintenance→idle，
     非法转换抛 `[ILLEGAL_PHASE_TRANSITION]`；
   - `循暂停决策`（仅 running 可暂停）、`循折算状态`（fold 快照）、
     `循恢复决策`（忙/续跑/待机——有待办或折算带待唤即续跑）、
     `循请求唤醒`（idle 直接开跑；非 idle 闩待唤）、`循相位收敛`（回 idle + 重放待唤 + 清闩）。
3. **轮次驱动深化**：
   - `步骤终因表 = ["completed","max-tokens"]`（上游 StepEndReason 的 Extract 子集）；
   - `循终因合并(现终结, 步骤终因)`：max-tokens 粘滞，completed 不得降级；
   - `循轮次续跑(现终结, 有待办步骤)`：无终结恒续跑；有终结+待办续跑；有终结+无待办跳出。

不接真实事件总线/真实 LLM（R40/R43 已接真）；决策输入全部显式传参。

## 三、新增测试

`examples/test_R47_代理循环深化.light`（rc=0），19 组断言覆盖：
- 四原因全分支（initial/resume/change±系列边界/series/不记录）+ 组合验证（头相等深比较驱动 头变化 入参）；
- 相位机：可转表、running 可暂停 / idle·maintenance 拒绝、fold 折算、闩锁-收敛-重放、
  恢复三态（待机/续跑/忙）、maintenance→running 非法转换抛错；
- 轮次驱动：粘滞四例、续跑判定四例、未知步骤终因抛错。

## 四、回归

- 既有 `test_代理循环.light`、`test_R34_集成测试.light`、`test_R37_集成测试.light`、
  `test_agentE5钩子.light` 全 rc=0；
- 本机全量 pytest 基线外零新增红（见收口记录）。

## 五、铁律核对

- 零修改 代理循环.light 既有 §0-§5（只追加 §6 与导出表）；
- 未接真实事件总线；既有 agent-loop 测试不破。
