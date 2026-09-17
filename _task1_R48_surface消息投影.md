# 第48轮任务1交付：surface 折叠消息产生事件投影 + append/replace（#2）

> 日期：2026-09-17 ｜ 状态：**完成**
> 优先级：P0 ｜ 修改区：src/会话格式.light（§14b，加性）｜ 上游：deepseek-harness 0.1.5-rc.2

## 一、上游对照（只读）

- `packages/core/session/src/surface.ts`：
  - `isAppendSurfaceEvent(e)`：表面事件 且 `surfaceOp === "append"`。
  - `isReplacementSurfaceEvent(e)`：表面事件 且 `surfaceOp` 非 `"append"`（字符串 `"replace"` 或 `{"op":"replace",...}` 均判替换；log-only 事件不算表面事件）。
  - `validateSurfaceMetadata(e)`：表面可入类型缺 `surfaceOp` → 抛 `requires a surfaceOp marker`；非法 `surfaceOp` → `invalid surfaceOp`；replace 须含 `op/startSeq/endSeq` 且 `startSeq/endSeq` 为更早序号。
  - `assertProvenance(e)`（事件级部分）：`sourceEventSeqs` 须为数组、非空、全为更早的非负安全整数、无重复；`assistant/message` 不得携带 `sourceEventSeqs`。
  - `deriveEventMessage(e)`：单事件派生模型可见消息（即「消息产生」投影的原子单元，R47 §14 的 `投影节点消息` 已对齐）。
- 本轮补的是 **消息产生侧**：消息产生事件 → surface 投影的 append/replace 规则 + 标记校验，R47 已完成 #1 节点0 投影（非本次范围）。

## 二、修改（互斥区内：仅 src/会话格式.light §14b）

新增 §14b（行 917–1016），全部为**加性段落**，不触碰 R47 §14 的 `投影节点0`/`投影表面消息`/`投影节点消息`/`是表面事件`/`是替换操作`/`表面可入类型`/`表面操作取值`：

1. `是追加表面事件(事件项)`（align `isAppendSurfaceEvent`）：非表面事件→假；否则 `表面操作取值(事件项)=="append"`。
2. `是替换表面事件(事件项)`（align `isReplacementSurfaceEvent`）：非表面事件→假；否则 `表面操作取值(事件项)!="append"`。
3. `是非负安全序号(值)`（align `isEventSeq`）：`Number.isSafeInteger && >=0 && 非 -0`。
4. `校验表面标记(事件项)`（align `validateSurfaceMetadata` + `assertProvenance` 事件级）：
   - 非表面事件携带 `surfaceOp`/`来源事件序号` → 抛错；
   - 表面可入类型缺标记 → `requires a surfaceOp marker`；
   - 非法 `surfaceOp` → `invalid surfaceOp`；
   - `replace` 须含 `op/startSeq/endSeq`，`startSeq/endSeq` 须为更早非负安全序号；
   - append / replace 返回前均调用 `校验来源序号`（provenance 校验，上游 append+replace 都跑 `assertProvenance`）。
5. `校验来源序号(事件项, 种类)`（align `assertProvenance` 事件级）：`assistant/message` 不得携带；`来源事件序号` 须为数组/非空/全更早非负安全整数/无重复。
6. `投影消息产生(事件表)`（align `deriveMessages` over surface）：复用 `投影表面消息` 的「节点0 系统消息前置 + 逐节点投影 + 遮蔽跳过」，返回 `结果["消息表"]`。
7. 导出清单追加：`是追加表面事件, 是替换表面事件, 是非负安全序号, 校验表面标记, 投影消息产生`。

> **行为差异 R48-D1（本任务）**：光明投影层（R47 `投影表面消息`）仍**默认 append** 以兼容既有用例；但本任务新增的 `校验表面标记` 在**校验层强制要求显式 `surfaceOp` 标记**（对齐上游严格语义）。二者分层——投影宽容、校验严格，与上游「默认 append 但标记缺失即报错」一致。

## 三、新增测试

`examples/test_R48_surface消息投影.light`（rc=0）：

- **§1 追加/替换谓词**：1b system+append 非替换 / 1d system+replace 非追加 / 1f 缺省非替换 / 1h turn/start 非追加亦非替换。
- **§2 校验表面标记**：2a 显式 append 返回 `"append"`；2c/2d replace 字典 `op/startSeq/endSeq` 正确；2e 缺标记抛 `requires a surfaceOp marker`；2f 非法 op 抛 `invalid surfaceOp`；2g 区间非更早序号抛错；2h 非表面事件携带 `surfaceOp` 抛错；2i 非表面事件携带 `来源事件序号` 抛错；2j `来源事件序号` 引用非更早序号抛错；2k `来源事件序号` 重复抛错；2l `assistant/message` 携带 `来源事件序号` 抛错。
- **§3 消息产生事件投影**：3a 四消息投影；3b/3c 节点0 系统消息前置且文本正确；3d/3e/3f user/assistant/tool 角色正确；3g 空内容 assistant 被排除；3h 遮蔽节点不产消息；3i 可见节点为新节点。

## 四、回归

- 本任务既有会话格式测试**不破**（铁律满足）：
  - `test_会话格式.light` / `test_会话格式冒烟.light` / `test_会话V3迁移.light` / `test_R47_会话surface深化.light` 全 rc=0；
  - 全 `test_会话*.light` 家族（16 个）+ 依赖 `会话格式` 的 `test_修复_repair.light` / `test_修复_会话.light` / `test_行为对照_会话持久化.light` 全部 rc=0。
- 本任务新增测试 `test_R48_surface消息投影.light` rc=0。

## 五、铁律核对

- 零修改 R47 已做的节点0 投影 / 遮蔽跳过 / `投影节点消息` / `是表面事件` / `是替换操作`；
- 与任务4 分工：本任务只做 surface 消息产生侧（§14b），任务4 只做 V3 迁移 role 形状（§15），无同函数重复修改；
- 改后既有会话格式测试全绿。
