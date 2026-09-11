# 路2（T）交付报告 —— agent-team 1.5：持久信箱 + 发送定向 + 公开导出

> 任务书：`0.15复刻_第4轮_任务prompt分发.md` 路2（T）
> 对照原版：`G:\github\deepseek-harness` @ `a305303422`（0.1.5-rc.2）
> worktree：`G:\dswork\duan-light-merge\wt-T2`（分支 `task-2-agent-team`）
> 提交：`bbcb27b`（8 files，+688/−189）
> 完成日期：2026-09-11

---

## 1. 交付清单

| 文件 | 类型 | 说明 |
|---|---|---|
| `src/团队服务.light` | 修改 | 1.5 核心升级：删除 delivery/quiet/wakeup/活跃投递/判先后 旧语义；新增 `投递链`（dispatchThrough 按 durable 队列序派发目标全部未送达）；根目标走 `能力定向根`（send steer）；持久目标已录改 `readPersistedSession` 形状；queued/delivered 事件版本 2；信箱恢复删 quiet 分支 |
| `src/团队折叠.light` | 修改 | 事件版本 2；排队载荷校验删除 delivery 字段 |
| `src/团队花名册.light` | 修改 | team/member 事件版本 2；协调供给改 `readPersistedSession` 头形状（isSeeded） |
| `examples/test_团队服务1.5.light` | 新增 | 9 个定向用例：无 delivery / steer 定向 / 派发链顺序 / 持久头形状 / 版本 2 / 恢复无安静 等（全过） |
| `examples/test_团队服务.light` | 修改 | 对齐 1.5 语义（废弃 判先后/注入根 用例） |
| `examples/test_团队折叠.light` | 修改 | 对齐 1.5 语义 |
| `examples/test_团队日志.light` | 修改 | 对齐 1.5 语义 |
| `examples/test_团队花名册.light` | 修改 | 对齐 1.5 语义 |

## 2. 上游依据与对应实现

| 上游增量（0.1.5-rc.2） | 实现 |
|---|---|
| durable-inbox-recovery（#2672 `b0a7d2ce3b`）：claimed-pre-step inbox 生命周期、信箱持久化恢复 | `投递链` 按 durable 队列序派发目标全部未送达；任一失败即停（保持排队不丢）；恢复重建信箱状态、删 quiet 分支（不静默丢弃）；持久目标已录改 `readPersistedSession` 形状 |
| send-steer（#3333 `f7cee2c888`）：team-send-message-steer 发送定向 | 根目标走 `能力定向根`（steer）——发送消息可定向到指定队友/目标 |
| 公开发布（#3884 `16953f2b8e`）：agent-team 包导出面调整 | 事件版本 1→2（queued/delivered/team/member）；团队折叠/花名册 同步版本 2；排队载荷校验删 delivery |
| mailbox 确认刷盘等待（`44008a79ca`）、CI（`2c21c7a03e`） | 投递链失败即停保持排队（未确认不丢）语义覆盖 |

## 3. 语义要点实现方式

| 要点 | 实现 |
|---|---|
| 持久信箱（durable inbox） | 信箱恢复删除 quiet 分支；已认领/未送达状态在恢复时重建；认领后不丢消息 |
| 发送定向（send steer） | `能力定向根`：根目标走定向投递路由，对齐 team-send-message-steer |
| 派发链顺序 | `投递链` 按 durable 队列序派发目标全部未送达事件；任一失败即停（其余保持排队） |
| 事件版本 2 | queued/delivered 事件版本 2；团队折叠/花名册 team/member 版本 2 |
| 持久头形状 | `readPersistedSession` 返回 头（isSeeded）/继承数/事件 切片形状；花名册协调供给对齐 |

## 4. 测试与验证

### 4.1 定向用例（rc==0）
- `examples/test_团队服务1.5.light` —— 9 个定向用例全过（无 delivery / steer / 派发链顺序 / 持久头形状 / 版本 2 / 恢复无安静）
- 既有测试对齐 1.5 后全绿：`test_团队服务` / `test_团队折叠` / `test_团队日志` / `test_团队花名册`

### 4.2 全量 CI
`python scripts/ci_test.py`（LIGHT_MERGE=light-merge）：
- 198 passed / 2 failed，2 个失败均为**既有失败**（`test_agentE5钩子.light`、`test_压缩E5.light`，main 分支基线同样失败，非本路引入）
- 结论：**无新增打红**，本路全部新增/改动用例 rc==0。

## 5. 未移植项（登记缺口）

| 上游能力 | 理由 |
|---|---|
| 未认领 pre-step 信箱的宿主侧定时回收 | 纯逻辑层只保证恢复语义与排队顺序；定时回收属宿主调度，登记不移植 |
| 公开导出面（index.ts 包级导出） | lightharness 模块间走 `导出` 语句，无包级发布面，等价导出已覆盖（团队六模块接口） |

## 6. 移交清单（跨路接口）

| 接口 | 提供方 | 消费方（登记） |
|---|---|---|
| 持久信箱恢复原语（`投递链`/恢复重建） | `团队服务.light` | 会话控制器 / 团队调度侧如需 durable 队列消费可引用 |
| 发送定向原语（`能力定向根` steer） | `团队服务.light` | agent-loop / 调度侧定向投递路由 |
| 事件版本 2 约定（queued/delivered/team/member） | 团队六模块 | 事件订阅/投影消费方按版本 2 解析 |
| `readPersistedSession` 头形状（isSeeded/继承数） | `团队服务.light` | 跨路：与路1(S) 的 SessionFormatHeader（isSeeded/inheritedEventCount）形状对齐 |
