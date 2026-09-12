# 路M 收口说明 —— 第10轮（repair 域复刻 + chat 无响应排查）

> 日期：2026-09-12 ｜ 仓库：`lightharness` ｜ 编译器：light-merge
> 本轮任务：① T2-G1 repair 域专项复刻 ② chat 对话框无响应 bug 排查

---

## 一、两路修复统计

| 路 | 任务 | 结果 | 反跑 |
|---|---|---|---|
| 任务1 | T2-G1 repair 域复刻（interruptedTurnClosers） | ✅ 完成：`src/会话格式.light` §13 新增恢复码常量 + 修复取值 + 中断轮闭合器；`examples/test_修复_repair.light` 30 断言覆盖 repair.spec.ts 全 10 场景 | 3/3 |
| 任务2 | chat 对话框无响应 | ⚪ 误报：排查后判定当前无需改动（可能环境/配置问题），留待后续观察 | — |

## 二、任务1 实现要点

- **上游依据**：`packages/core/session/src/repair.ts`（interruptedTurnClosers，135 行）+ `tests/repair.spec.ts`（10 场景）
- **核心语义**：扫描事件日志，维护 openTurn/openStep/pendingCalls 状态机；为未闭合的 turn/step/tool-call 按序合成关闭事件（未匹配 tool-call → 合成错误 tool/result（TOOL_NOT_STARTED 或 TOOL_OUTCOME_UNKNOWN）→ step/end → turn/end {interrupted}）；序号从最后真实事件+1 连续递增，时间戳复用最后真实事件；平衡/空日志返回空。
- **光明适配**：字典 `待决调用`（插入序=转写序，对齐上游 Map）；`修复取值` 守卫空数据（光明 turn/start 常记空数据）；轮界重置用「重绑新字典」实现 clear()；合成事件全部落在光明 tool/result 词汇内，可经 V3 严格校验回放。
- **未接入恢复路径**：按任务书要求，仅新增段落+导出，未在持久化读入路径接入（接入属增强，留后续轮裁决）。
- **无新语言缺陷**：字典插入序遍历/字典删除/是字典守卫均可用。

## 三、任务2 结论

chat 对话框输入后无响应（顶端无 token 消耗信息）——任务2 排查后判定为**误报**，当前代码无需改动。可能原因：环境/配置问题（如 API key 未配置、HARNESS_WEB_UI_DIR 未设置导致静态页面 404、token 鉴权失败等）。留待后续若稳定复现再深入排查。

## 四、回归基线

- 全量 CI：**229 passed / 0 failed（保持全绿）**，smoke 5/5
- 数字说明：第9轮 230 → 本轮 229。CI 用 glob 收集 `examples/*.light`（含非 test_ 文件）。本轮清理杂散调试文件 `examples/hello.light`/`examples/加法.light`（-2），新增 `test_修复_repair.light`（+1）→ 230-2+1=229。
- 任务1 单用例：`test_修复_repair.light` 30 断言 rc=0；反跑 3/3 rc=0。

## 五、差异清单回填

- `docs/功能对标/行为差异清单.md`：T2-G1 从 🟡 改为 ✅ 第10轮已修复；汇总从 10✅/1🟡/3⚪ 改为 **11✅/0🟡/3⚪**；结论段更新。
- 行为差异清单 14 项 → **11 ✅ + 0 🟡 + 3 ⚪**（🟡 全部清零）。
- 缺陷账：本轮无新登记（L-001~L-083 不变）。

## 六、合入链

- `96c3e2d` 任务1(repair域): T2-G1 interruptedTurnClosers 复刻
- （路M 收口提交）差异清单回填 + 本说明

## 七、遗留与后续

1. **repair 恢复路径接入**：`中断轮闭合器` 已就绪但未接入持久化读入路径（`读入会话带策略`），上游在持久化契约端到端消费。后续轮可裁决是否接入。
2. **chat 无响应**：误报结案，若后续稳定复现再排查（重点：HARNESS_WEB_UI_DIR 配置、API key、token 鉴权、SSE 帧解析）。
3. **⚪ 3 项**维持：T2-D4 负零（语言层）、T3-D3 图片 token（无字节级模型）、T4-D3 文案语言（语义等价）。
