# _task6_审批对照_交付报告.md —— 第 12 轮任务 6（审批域：user-approval + tool-ask-user 对照收口）

> 日期：2026-09-12 ｜ 仓库：`lightharness` ｜ 上游：`G:\github\deepseek-harness` @ `a305303422`（0.1.5-rc.2）
> 上游依据：`packages/interaction/user-approval/src/{index.ts(278), invariant.ts(101), types.ts(84)}` + `packages/interaction/tool-ask-user/src/index.ts(97)`
> 交付物：`src/审批.light` 对照收口扩展 + `examples/test_审批对照.light`（36 断言全绿，新增）+ `_antirun_approval.py`（3 判据全过）
> 铁律遵守：只改互斥表内 `src/审批.light`；`src/权限.light` / `src/交互命令.light` 零改动；新增一律 .light。

---

## 1. 上游依据（文件:函数）

| 上游 | 位置 | 语义 |
|---|---|---|
| `ApprovalOutcome` 闭集 | types.ts:32、index.ts:48 `OUTCOMES` | `allowed-once / rejected / cancelled / unavailable` 四结果；`allowed-once` 唯一授权；`unavailable` fail-closed |
| `ApprovalPolicy` | index.ts:60/63 `APPROVAL_POLICIES` | `ask`（缺省，委派应答者链）/ `never`（不询问一律拒绝） |
| `NEVER_SENTENCE` / `ASK_SENTENCE` | index.ts:66/68 | 模型面策略文案（never：审批禁用、需审批动作自动拒绝、勿请求沙箱提权；ask：无应答者 fail-closed） |
| `hasOpenTurn` | index.ts:77-84 | 倒序扫描事件日志，先遇 `turn/start` → 开轮；先遇 `turn/end` → 无开轮；审计对必须被轮封闭（轮间裸事件重载时与崩溃尾不可区分） |
| `ApprovalService.request` | index.ts:207-226 | 开轮前置（不满足抛错）→ `approval/asked` 审计（id/toolName/callId?/reason?）→ 裁决 → `approval/decided` 审计（id/outcome）→ 返回闭集结果 |
| `decide` 策略裁决 | index.ts:258-283 | `never` 在任何分派**前**确定性拒绝（:266，与监听器注册顺序无关）；无应答者 → waterfall 兜底 `unavailable`；应答者异常/词汇外返回 → 归一 `unavailable` |
| `setApprovalPolicy` | index.ts:92-97 | 非法策略先抛 `TypeError('approval policy must be one of "ask" or "never"')` 再落状态 |
| invariant.ts | :27-56 | `asked`/`decided` 同 id 配对、`toolName` 非空、`decided` 必有匹配 `asked`、结果/策略词汇闭集校验 |
| tool-ask-user | index.ts:16-99 | `ask_user_question`：入参 `questions[{id,question,header?,options?,multi_select?}]`（`multi_select`→`multiSelect`，可选缺省不落键）；输出 `answers[{id,selected,custom?}]`（selected 复制、custom 仅携带时出现）；description 提示一次多问 + 稳定 id 回显 |

## 2. 差异清单（上游 vs 光明 审批.light 对照）

| # | 差异点 | 上游 | 光明修复前 | 本轮处置 |
|---|---|---|---|---|
| D1 | 裁决结果集 | 四结果闭集（allowed-once/rejected/cancelled/unavailable） | 「批准」真/假 二值 + 状态（已批准/已拒绝/超时） | ✅ 新增四结果常量与 `审批结果词汇` 闭集；既有 批准/状态 字段保留（向后兼容） |
| D2 | 策略 ask/never | `ApprovalPolicy` + 会话级覆盖 + 缺省 ask | 无策略概念（权限分类三值：放行/审批/拒绝） | ✅ 审批管理器 增 `策略` 字段（缺省 ask）+ `设置审批策略`（词汇校验同上游 TypeError 文案）+ `取审批策略` |
| D3 | never 自动拒绝 | decide 分派**前**确定性 rejected（不落应答者） | 无 | ✅ `请求审批审计` never 分支直接 rejected，应答者不被调用（断言 4a） |
| D4 | 无应答者 fail-closed | waterfall 兜底 `unavailable` | 等待结果 超时拒绝（近似） | ✅ ask 策略 + 应答者为空 → `unavailable`；超时拒绝路径保留 |
| D5 | 词汇外归一 | 词汇外返回 → `unavailable`（rogue normalization） | 无 | ✅ `规范审批结果` |
| D6 | 开轮前置 + hasOpenTurn | request 前置，非开轮抛错；倒序扫描判定 | 请求审批 无轮上下文校验 | ✅ `是开轮`（倒序扫描，语义同上游）+ `请求审批审计` 开轮外抛错（文案要点对齐） |
| D7 | 审计对（approval/asked + approval/decided） | 光明会话日志持久审计事件，id 配对、可选字段条件携带 | 无审计落盘 | ⚠️部分：`请求审批审计` 返回 审计包（asked/decided 字典，形状对齐 types.ts），由调用方落盘——光明 会话.light 事件词汇无 `approval/*` 注册（事件词汇表在 会话格式.light，只读），词汇注册移交路M（见 §5） |
| D8 | 策略文案 | NEVER_SENTENCE / ASK_SENTENCE 逐字 | 无 | ✅ `从不文案` / `询问文案` / `策略文案`（逐字对齐） |
| D9 | 提问工具 | ask_user_question 输入/输出形状 | 无 | ✅ `造提问调用`（multi_select→multiSelect、可选缺省不落键）+ `规范提问答案`（selected 复制、custom 条件携带）；**不注册进 工具.light 注册表**（注册点移交路M） |
| D10 | 权限 4 预设 | 上游无此面（policy 只 ask/never） | 放行/按类别/全拒绝/自定义 | ✅保持不动（src/权限.light 只读）；never 策略与 权限分类拒绝 正交（never 是「问询层」语义，权限是「工具准入层」语义），对照登记不合并 |

## 3. 实现要点（src/审批.light）

- 常量区新增（对齐上游闭集）：`结果允许一次/结果拒绝/结果撤回/结果不可用` + `审批结果词汇`；`策略询问/策略从不` + `审批策略词汇`；`从不文案/询问文案/策略文案`；`提问工具描述`。
- `是开轮(事件表)`：倒序遍历（`i = 长度-1` 递减），先 `turn/start` → 真，先 `turn/end` → 假，空表 → 假——与上游 `hasOpenTurn` 逐分支等价。
- `规范审批结果(结果)`：词汇内透传，词汇外（含空）→ `结果不可用`（fail-closed 归一）。
- `审批管理器`：`策略` 属性缺省 "ask"；`设置审批策略`（非法值先抛错再落状态，文案逐字对齐）；`取审批策略`；`请求审批审计(事件表, 工具名, 应答者, 调用id, 理由)`——开轮前置抛错（文案要点对齐上游 index.ts:209-215）→ asked 审计（id/工具名 + 可选 callId/reason）→ 策略裁决（never→rejected；ask+无应答者→unavailable；ask+应答者→委派并归一）→ decided 审计 → 返回 `["审批id","结果","询问审计","决定审计"]`。
- `造提问调用` / `规范提问答案`：tool-ask-user 输入/输出纯形状规范化（无 IO）。
- 类体约束遵守（文件头注「if/否则 分支后不接同级语句，多分支用提前返回写法」）：新增类方法均为平铺提前返回形态。

## 4. 测试与 CI（本路范围）

```
cd lightharness
python 运行.py examples/test_审批对照.light   # 36 断言，RC=0（新增）
python _antirun_approval.py                   # 3 判据 + 字节级恢复，RC=0
```
回归抽查（只读未改，均 RC=0）：`test_审批` / `test_审批API` / `test_审批钩` / `test_审批深化` / `test_权限`。
**用例数**：新增 `test_审批对照.light` +1。
**说明**：任务书回归清单中的 `test_审批钩深化` 在当前工作区不存在（examples/ 仅 5 个审批相关测试，如上）；非本轮删除。

测试断言覆盖：开轮判定 4（空/turn-start/turn-end/多轮最近）+ 四结果闭集与词汇外归一 5 + 策略闭集/缺省/切换/非法拒绝 5 + request 流程 12（never 分派前拒绝、审计对 id 配对与可选字段、无应答者 fail-closed、allowed-once、rogue 归一、开轮外抛错）+ 文案 4 + 提问工具形状 8。

## 5. 反跑判据（_antirun_approval.py，3 项，字节级备份/恢复 src/审批.light）

| 项 | src 变异 | 判红断言 | 实测 |
|---|---|---|---|
| A | never 分支改 ask 语义（`结果拒绝`→`结果允许一次`） | 4a never 自动拒绝 | ✓ 红→恢复绿 |
| B | `审批结果词汇` 去掉 `结果不可用` | 2a 四结果闭集 | ✓ 红→恢复绿 |
| C | `是开轮` 的 `turn/start` 分支改返回 假 | 1b/1d 开轮判定 | ✓ 红→恢复绿 |
| — | 恢复后 sha256 一致 + 回归绿 | — | ✓ |

（注：src/审批.light 为 CRLF 换行，反跑脚本的变异串按实际换行字节编码，避免变异未命中假绿。）

## 6. 未移植项（登记，非缺陷）

1. **`approval/*` 事件词汇未注册**：上游把 `approval/policy`、`approval/asked`、`approval/decided` 注册进 SessionEventMap 并由 invariant 校验配对；光明事件词汇表在 `src/会话格式.light`（本路只读），本轮以「审计包返回值」承载审计语义，持久落盘与词汇注册交路M 统一决策（若注册，可复用 `校验事件载荷` 严格模式，需在 定词汇 表加三行：`approval/policy`(["策略"])、`approval/asked`(["id","工具名"],["callId","reason"])、`approval/decided`(["id","结果"]))。
2. **cordis waterfall / AbortSignal 竞态**：上游 decide 的应答者瀑布（`ctx.waterfall` + `next()` 委托）与 signal 竞态（abort → cancelled，晚到答案丢弃）属宿主异步面；光明 `等待结果` 轮询 + 超时拒绝近似覆盖超时语义，cancel 竞态未移植（光明无 AbortSignal）。
3. **invariant.ts 伴随校验器**：审计流不变量（重复 id、decided 无 asked、toolName 空串拒绝）为宿主 invariant 框架插件；其校验逻辑已部分内化到 `请求审批审计`（同 id 配对由构造保证），独立不变量插件未移植。
4. **tool-ask-user 注册**：`造提问调用`/`规范提问答案` 为纯逻辑段，未注册进 `src/工具.light` 工具注册表（互斥表不许可）；注册接入点 = `src/工具.light` 注册表增 `ask_user_question` 条目（name/description/参数 schema 如 §1），由路M 决策时机。
5. **setPolicy 的模型通知注入**：上游 `ApprovalService.setPolicy` 会 `agent.inject(createUserMessage(...))` 注入策略变更通知（"The approval policy changed from ..."）；光明 agent.light 只读，未接线（`设置审批策略` 已返回真/抛错，调用方可在切换后自行追加通知消息）。
6. **新原语使用情况**：`副本`/`深拷贝`/闭包 均已验证可用（`制造应答者` 闭包即用于 mock 应答者），但本路修复未需要简化既有绕法（审批.light 原无拷贝绕法）；无新语言缺陷登记。

## 7. 移交清单

- 改 `src/审批.light`：头注对照说明 + 常量区（四结果/两策略/两文案/描述）+ 模块级段（是开轮/规范审批结果/策略文案/造提问调用/规范提问答案）+ 类增 `策略` 属性与 3 段落（设置审批策略/取审批策略/请求审批审计）+ 导出清单 +17 行
- 新增 `examples/test_审批对照.light`（36 断言 / 6 组，节头标注对标上游文件:行）
- 新增 `_antirun_approval.py`（A/B/C 三判据，CRLF 兼容）
- 零改动：`src/权限.light`、`src/交互命令.light`、`src/agent.light`、`src/工具.light`、`src/会话.light`、`src/会话格式.light`、`docs/`
- 移交路M：① 差异清单回填（上表 D1~D10，#85 对标卡）；② `approval/*` 事件词汇注册决策（§6.1）；③ ask_user_question 注册点决策（§6.4）；④ 全量 CI（预期 237 + 1 = 238 passed）
