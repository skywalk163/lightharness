# 第48轮任务4交付：会话 V3 迁移链 + 节点0 前置 role 形状补验（#1）

> 日期：2026-09-17 ｜ 状态：**完成**
> 优先级：P1 ｜ 修改区：src/会话格式.light（§15，加性）｜ 上游：deepseek-harness 0.1.5-rc.2

## 一、上游对照（只读）

- `packages/session/session-format-v2-to-v3/src/validation.ts`：
  - `restoreReleasedV3Artifact`：节点0 必须是 `system/message` 且其派生消息 `role === "system"`；首条 surface 事件须为**受保护系统头**；`system/message` 须落在开启的 step 内（与 `step/start` 的 turn/step 匹配）；`replace`（system 或非 system）不得错误遮蔽 head（system replace 须**精确覆盖**当前 head；非 system replace 不得触碰 head）；`assertReleasedV3Header`：`version === 3`。
  - `emitSystem`（migration.ts）：系统提示在**写入期**提升为节点0 `system/message` 事件（role `"system"`，source 标注插件，`surfaceOp` append/replace）。本轮不重复注入（R47 已在记录侧落节点0），只补**迁移补验**的完备性检查。
- 本轮补的是 **V3 迁移链的 role 形状前置 + 系统头保护 + 迁移补验**，与任务1 的 surface 消息产生侧语义衔接但**不重复改同函数**。

## 二、修改（互斥区内：仅 src/会话格式.light §15）

新增 §15（行 1018–1124），全部为**加性段落**，不与任务1 §14b 任何函数重名/重叠：

1. `校验节点0角色形状(事件表)`（align 节点0 role 形状）：跳过遮蔽节点，首个非遮蔽表面事件必须是 `system/message`；其 `投影节点消息` 派生的消息 `角色` 必须 `== "system"`；否则抛错（缺表面事件 / 类型非 system/message / 不产消息 / role 非 system）。
2. `校验V3系统头(事件表)`（align `restoreReleasedV3Artifact` 系统头保护）：
   - 跟踪开启 step（turn/step）；`system/message` 须与开启 step 的 turn/step 匹配，否则 `system/message does not match an open step`；
   - 首个 surface 须为受保护系统头（`requires a protected first surface head`）；
   - `system/message` 的 append 设 head；其 replace 须 `startSeq==endSeq==head` 精确覆盖 head（`must replace exactly the current system head`）；
   - 非 system 的 replace 若 `startSeq/endSeq` 命中 head → `surface replacement cannot shadow the protected system head`。
3. `补验V2V3迁移(源头, 源事件表, 目标头, 目标事件表)`（align `assertReleasedV3Header` + 系统提示提升完备性）：
   - 目标头 `版本.主==3 && 版本.次==0`，否则 `must be format v3`；
   - 目标事件序号须密集 `0..n-1`（`must emit dense seqs`）；
   - 调用 `校验V3系统头(目标事件表)`；
   - 若源 v2 在 `request/header` 携带系统提示（`系统提示` 或 `header.system` 非空），目标节点0（`投影节点0`）须等于该提示，否则 `must promote system prompt to node 0`。
4. 导出清单追加：`校验节点0角色形状, 校验V3系统头, 补验V2V3迁移`。

## 三、新增测试

`examples/test_R48_会话V3迁移.light`（rc=0）：

- **§1 节点0 role 形状**：1a 合法通过（首个表面=system/message 且 role 为 system）；1b 首个表面非 system/message 抛错；1c 派生 role 非 system 抛错；1d 无表面事件抛错。
- **§2 V3 系统头保护**：2a 仅 head 的 append 通过；2b 首条 surface 非 head 抛 `requires a protected first surface head`；2c system replace 未精确覆盖 head 抛 `must replace exactly the current system head`；2d 非 system replace 命中 head 抛 `cannot shadow the protected system head`。
- **§3 V2→V3 迁移补验**：3a 合法 v3 + 密集序号 + 节点0 反映源系统提示 通过；3b 目标头非 v3 抛 `must be format v3`；3c 源含系统提示但目标节点0 未反映 抛 `must promote system prompt to node 0`。

## 四、回归

- 本任务既有会话格式测试**不破**（铁律满足）：
  - `test_会话格式.light` / `test_会话格式冒烟.light` / `test_会话V3迁移.light` / `test_R47_会话surface深化.light` 全 rc=0；
  - 全 `test_会话*.light` 家族（16 个）+ 依赖 `会话格式` 的 `test_修复_repair.light` / `test_修复_会话.light` / `test_行为对照_会话持久化.light` 全部 rc=0。
- 本任务新增测试 `test_R48_会话V3迁移.light` rc=0；任务1 新增 `test_R48_surface消息投影.light` 仍 rc=0（两任务互不干扰）。

## 五、铁律核对

- 与任务1 分工明确：任务1 做 surface 消息产生侧（§14b），任务4 做 V3 迁移 role 形状（§15），**无同函数重复修改**；
- 不改 R47 已做的节点0 投影 / 遮蔽跳过；
- 改后既有会话格式测试全绿。
