# _task71_report.md —— A 线交付小结：webhook 会话纯逻辑复刻（对标 #71）

- 交付人角色：lightharness 复刻开发工程师（A 线）
- 复刻对象：`G:\github\deepseek-harness\packages\webhook\webhook\src\`
  （`index.ts` 178 行 / `session.ts` 181 行 / `types.ts` 84 行 / `invariant.ts` 48 行 / `brand.ts` 39 行）
- 新增白名单文件：
  - `src/webhook会话.light`（核心会话构建纯逻辑，41 个导出）
  - `examples/test_webhook会话.light`（反跑测试，10 个正例用例 + 14 组反跑用例）
  - `_task71_entry.json`（对标清单条目）
  - `_task71_report.md`（本文件）
- 未触碰任何其它文件；未 commit / 未 merge / 未 push。

---

## 1. 原版文件 → 光明段落 对照表（函数级）

### index.ts（178 行）

| 原版函数 / 成员 | 行号 | 光明段落 | 说明 |
|---|---|---|---|
| `snapshotDelivery(delivery)` | 39 | `快照投递(投递)` | 拆成 kind / source / deliveryId / receivedAt 四道闸 + 可无损 JSON 闸，共 9 个抛点 |
| `WebhookRuntime.register(rule)` | 89 | `注册(规则)` | 关闭闸 → id 闸 → kind 闸 → run 可调用闸 → 重名闸；返回规则号作回收句柄 |
| `WebhookRuntime.dispatch(delivery)` | 126 | `派发(投递)` | 关闭闸 → 快照 → 按注册序遍历，跳过已回收登记，仅派发 `kind` 相同者 |
| `WebhookRuntime#startInvocation` | 136 | `发起调用(登记, 投递)` | 前置/后置中止检查 → `run()` → 非空则建会话 → catch 分流 debug/warn |
| 调用诊断串（模板字符串） | 151 | `造调用标签(投递, 规则号)` | `provider=… source=… delivery=… rule=…`，各字段 `JSON.stringify` |
| `WebhookRuntime#disposeRegistration` | 165 | `回收(规则号)` | 隐藏（删表）→ 置 `closing` → 中止信号 → 幂等 |
| `constructor` 的 `ctx.effect` 收尾 | 75 | `关闭运行时()` | 置关闭态并回收全部登记 |
| `static inject`（6 项服务） | 59 | 剥离 | 投影为「上下文」字典的能力键约定 |
| `rules: Map` / `RuleRegistration` | 68/30 | `运行时状态["规则表"]` / `["规则序"]` | 字典 + 顺序号列表（保注册序） |
| — | — | `造运行时(上下文)` / `取规则号表()` / `取登记(规则号)` / `是运行时关闭()` | 生命周期与只读观测入口（L-065：不直接暴露可变全局） |

### session.ts（181 行）

| 原版函数 / 成员 | 行号 | 光明段落 | 说明 |
|---|---|---|---|
| `requiredString(record, field)` | 33 | `必填字符串(记录, 字段)` | 非字符串闸 + 空白串闸，两个错误码 |
| `resolveRequest(ctx, input)` | 42 | `解析请求(上下文, 输入)` | 非对象闸 → 绝对路径闸 → 五字段必填闸 → model 对象闸 → maxTokens 正安全整数闸；默认模型 / 显式模型两分支分别产出 `agentOptions` / `modelSelection` |
| `reportRollbackFailure(ctx, subject, error)` | 86 | `报告回滚失败(上下文, 主题, 错误)` | `webhook: ${subject} rollback failed: ${errorChain(error)}` |
| `installInitialModelSelection` 监听器体 | 92 | `初始模型监听(载荷, 下一步)` | agent 缺失闸 → 已有持久请求头闸 → provider/model 不匹配闸 → 剥离 `reasoningEffort` 后按 selection 回填 |
| `createWebhookSession` 的 `setup` 回调 | 140 | `装配置(代理上下文)` | 挂载代理预设 + 注册 `agent/request` 监听器 |
| `createWebhookSession(...)` | 119 | `创建Webhook会话(上下文, 投递, 规则号, 请求, 信号)` | 完整事务：resolve → 权限预设解析 → 代理预设解析 → 常驻键 → 中止 → 工作区 → 中止 → 会话号 → `agents.create` → try{中止/挂载/权限设置/改名/注入提示} catch{摘除回滚/销毁回滚/原错重抛} |
| catch 内两段内层 try/catch | 168/174 | `回滚摘除(上下文, 工作区, 会话号)` / `回滚销毁(上下文, 句柄, 会话号)` | 拆成具名段落，避开嵌套 `尝试` 块 |
| `ResolvedWebhookSessionRequest` | 18 | `解析请求` 的返回字典 | 7 键形状完全一致 |

### invariant.ts（48 行）

| 原版函数 / 成员 | 行号 | 光明段落 | 说明 |
|---|---|---|---|
| `installWebhookMessages` 判定体 | 18 | `校验Webhook准入(会话, 事件, 工作区表)` | 返回 `""` 通过 / 失败文案；事件类型闸 → webhook 消息过滤 → 缺 cwd 闸 → 归属数 ≠ 1 闸 → 路径不符闸 |
| `'internal/dispatch'` 入口过滤 | 22 | `内部派发检查(事件名, 会话, 事件, 工作区表)` | 先滤 `session/event`，再交准入校验 |

### brand.ts（39 行）

| 原版函数 | 行号 | 光明段落 |
|---|---|---|
| `WebhookRuleId(value)` | 19 | `规则标识(值)` |
| `WebhookSourceId(value)` | 28 | `来源标识(值)` |
| `WebhookDeliveryId(value)` | 37 | `投递标识(值)` |

> 三者编译期加品牌、运行时是恒等投射，光明无类型品牌，直接恒等返回，与原版运行时行为一致。

### types.ts（84 行，纯类型）

| 原版类型 | 光明落点 |
|---|---|
| `VerifiedWebhookDelivery` | `快照投递` 的四道字段校验 |
| `WebhookSessionRequest` | `解析请求` 的字段校验与「已解析」输出形状 |
| `WebhookModelSelection` | `解析请求` 的模型分支与 `agentOptions` 构造 |
| `MessageSourceMap['webhook']` | `造投递来源(投递, 规则号)`（kind/provider/source/deliveryId/ruleId/form=`'notice'`/summary） |
| `WebhookRule` | `注册` 的 id/kind/run 三道闸 |

### 被复刻的跨包纯逻辑（原版 import 而来，本仓必须自带）

| 原版 | 光明段落 |
|---|---|
| `dsh-llm` `boundContextSummary` | `绑定上下文摘要(摘要)`（120 字上限 + `…`） |
| `dsh-llm` `errorChain` | `错误链(值)` + `取错误文本(值)`（cause 链 `": "` 连接，逐字重复片段去重） |
| `dsh-llm` `createUserMessage` | `造用户消息(内容表, 来源, 编号)`（`role='user'`） |
| `dsh-session` `snapshotJsonValue` | `可无损JSON(根)`（栈式迭代，深度上限 32，环即假） |
| `node:path` `isAbsolute` | `是绝对路径(路径)` + `是盘符(字)`（POSIX 根与 Windows 盘符双形态） |
| `Number.isSafeInteger` | `是安全整数(值)`（±2^53−1 界） |
| `typeof x === 'function'` | `是可调用(值)`（光明无 callable 内建，用「非全部基本型」反推） |
| `deepFreeze` / `Object.isFrozen` | `深复刻(值, 层)` / `深冻结(值)` / `是冻结(值)` |

---

## 2. 剥离的宿主绑定 → 投影成什么

| 原版宿主设施 | 投影形态 |
|---|---|
| `@deepseek-ai/cordis` `Context` / `Service` / `ctx.effect` | 普通字典「上下文」+ 模块级全局 `运行时状态` / `装配槽` |
| `ctx.logger.warn` / `logger.debug` | `上下文["日志警告"]` / `上下文["日志调试"]`（入参能力函数） |
| `ctx.permissionPresets.resolve` / `.set` | `上下文["权限预设解析"]` / `上下文["权限预设设置"]` |
| `ctx.agentPresets.resolve` / `.standingKeyFor` / `.mount` | `上下文["代理预设解析"]` / `["代理预设常驻键"]` / `["代理预设挂载"]` |
| `ctx.workspaceRegistry.create` / `.list` | `上下文["工作区创建"]`（返回 `{"path","挂载会话","摘除会话"}`）/ 不变式校验的 `工作区表` 入参列表 |
| `ctx.agents.create` | `上下文["会话创建"](选项)`，选项含 `sessionId`/`signal`/`meta`/`agentOptions`/`setup` |
| `ctx.sessionTitle.rename` | `上下文["会话标题改名"]` |
| `ctx.agentDefaultModel.currentSelection` | `上下文["默认模型"]()` |
| `agentCtx.on('agent/request', listener)` | `上下文["监听"](代理上下文, 事件名, 监听器)` |
| `SessionId(\`webhook-${randomUUID()}\`)` | `"webhook-" + 上下文["唯一标识"]()` |
| `AbortController` / `AbortSignal` / `throwIfAborted()` | 字典 `{"已中止": 真假, "原因": 串}` + `检查未中止` / `中止信号` / `存活信号` |
| `Promise` / `await` / `async`（含 `Promise.allSettled` 排空） | 光明同步模型：`await` 点折叠为顺序调用；注册回收为同步幂等操作 |
| `node:crypto` `randomUUID` | `上下文["唯一标识"]()` |
| `node:path` `isAbsolute` | `是绝对路径()`（见上表） |
| octokit / github webhook handler（`webhook-github` 包） | **完全剥离**；本模块零 github/octokit 专有逻辑 |

### 光明侧的三处降级口径（已写入 `src/webhook会话.light` 文件头注释）

1. **undefined / null 同体**：光明只有 `空`。原版 `model === undefined`（走默认）与 `model === null`（报 `model must be an object`）改由「键是否存在」（`字典包含键`）区分：命中键且值为 `空` 视作 `null` → 抛 `[WEBHOOK_MODEL_NOT_OBJECT]`，与 `session.spec.ts` 的 `model: null` 用例一致。
2. **`Object.freeze` 无对应物**：`deepFreeze` 投影为「深复刻（断共享引用）+ 根级 `"冻结"` 标记键」，递归冻结降级为深复刻；`是冻结()` 只认带标记的根字典。`runtime.spec.ts` 的 `isFrozen(seen)` / `isFrozen(seen.event)` 对应为 `是冻结(快照)` 与「派发后篡改原投递，规则收到的快照不随之变」两条断言。
3. **错误对象不是字典**：探针实测 `是字典(错误对象) == 假`，故 `错误链()` 主路径面向「含 `message`/`cause` 键的字典形错误」，非字典值回退 `转字符串`；`报告回滚失败` 用 `转字符串(e)` 取原文，行为与原版一致。

---

## 3. 跑过的命令、rc 与输出摘要

```bash
cd G:/dswork/duan-light-merge/lightharness

# ① 门禁（最终态）
python 运行.py examples/test_webhook会话.light
# stdout: --- 测试webhook会话 通过 ---
# rc=0

# ② 反跑变异批量驱动（改 src/ → 跑测试 → 记录 rc → 还原）
python _task71_mutate.py     # 13 组变异，13/13 RED
python _task71_mutate2.py    # 2 组补充变异（模型闸取反 / 关闭闸改派发闸），2/2 RED
python _task71_mutate3.py    # 1 组补充变异（派发加去重），1/1 RED

# ③ 还原核验
diff _task71_backup.light src/webhook会话.light   # 无差异
python 运行.py examples/test_webhook会话.light    # --- 测试webhook会话 通过 ---  rc=0
```

期间还跑过两个根目录临时探针（`_task71_探针.light` / `_task71_探针2.light`，均已删除），用于确认：
段落引用可入字典字面量并被索引调用、`抛出 e` 可原样重抛且消息保留、嵌套 `尝试/捕获` 可用、`继续` 在 `当` 循环内可用、
递归可用、`7 / 2 == 3`（向零截断）、`长度` / `截取` / `开头` / `去除空白` 可用、`列表弹出` 必须带索引参数。

按约定**未跑全量回归**（留给主线独占机器）。

---

## 4. 反跑：改反了哪几处、实测 RED 输出、已还原复绿

共 **14 组反跑命名用例**，执行 **16 次实测突变，全部 rc=1（RED）**；每组突变后立即 `write(SRC, original)` 还原，
全部跑完后 `diff _task71_backup.light src/webhook会话.light` 无差异，复跑 `rc=0` 变绿。

| # | 反跑组 | 突变手法 | 实测 RED 首条失败 |
|---|---|---|---|
| ① | `反跑_投递闸` | 删 `快照投递` 的 kind 空串闸 | `期望抛错但未抛: 反跑_投递_空种类` |
| ② | `反跑_路径闸` | 删 `workspacePath` 绝对路径闸 | `期望抛错但未抛: 反跑_路径_相对` |
| ③ | `反跑_模型闸` | 闸取反：`是字典(模型) == 假` → `是字典(模型) == 真` | `webhook Session request model must be an object`（合法模型被拒） |
| ③b | `反跑_模型闸`（变体） | 直接删闸 | `错误码不符[反跑_模型_空]：实际=argument of type 'NoneType' is not iterable` |
| ④ | `反跑_令牌闸` | 删 maxTokens 的 `NOT_POSITIVE` / `NOT_SAFE` 两闸 | `期望抛错但未抛: 反跑_令牌_零` |
| ⑤ | `反跑_必填闸` | 空串闸改成 `返回 值` | `期望抛错但未抛: 反跑_必填_空标题` |
| ⑥ | `反跑_回滚闸` | 删 `回滚摘除(…)` 调用 | `断言失败[反跑_回滚_permission-set: 必摘除会话]：实际=False 期望=True` |
| ⑦ | `反跑_原错闸` | `抛出 e` → `抛出 新建 错误("rollback swallowed")` | `断言失败[反跑_原错闸: 抛的是原始错误]：实际=False 期望=True` |
| ⑧ | `反跑_中止闸` | 删 `检查未中止` 的 `抛出` | `期望抛错但未抛: 反跑_中止_信号` |
| ⑨ | `反跑_种类闸` | `规则["kind"] == 快照["kind"]` → `真 == 真` | `断言失败[运行时: 仅同种类 2 条被调用]：实际=3 期望=2` |
| ⑩ | `反跑_快照闸` | `返回 深冻结(投递)` → `返回 投递` | `断言失败[反跑_快照闸: 规则看到派发时刻的旧值]：实际=2 期望=1` |
| ⑪ | `反跑_去重闸` | 给 `派发` 增加 deliveryId 去重表（原版明确保持不去重） | `断言失败[运行时: 两次派发注入 2 次]：实际=1 期望=2` |
| ⑫ | `反跑_不变式闸` | 缺 cwd 闸返回值改成 `""` | `断言失败[反跑_不变式: 缺 cwd]：实际=False 期望=True` |
| ⑬ | `反跑_注册闸` | 删重名闸 | `期望抛错但未抛: 反跑_注册_重复` |
| ⑭ | `反跑_关闭闸` | 删 `派发` 的 `运行时状态["关闭中"]` 抛出 | `期望抛错但未抛: 关闭后派发` |
| ⑭b | `反跑_关闭闸`（变体） | `派发` 遍历守卫改成 `假 == 真` | `断言失败[运行时: 仅同种类 2 条被调用]：实际=0 期望=2` |

### 变异选取纪律（本轮踩到的假绿陷阱）

`③b` 是典型的「换个姿势仍被兜底拒绝」：删掉 `model must be an object` 闸后，`model: 空` 会落到
`必填字符串(空, "provider")`，由 `字典包含键(None, …)` 抛 `NoneType is not iterable` —— 虽然 **RED**，
但红的理由不是被测闸，属于「假红」。因此本轮把该组的主变异改成 **闸取反 + 正向放行断言** 双向锁定
（`③` 会命中「合法模型放行」断言），确保红得其所。其余 13 组均为「期望抛错但未抛 / 值改错」的直接判据反转，无兜底干扰。

---

## 5. 新发现的语言缺陷

**无新触发缺陷。** 本轮复用的既有编号（已写入 `_task71_entry.json` 的 `语言缺陷` 数组）：

| 编号 | 本轮用法 |
|---|---|
| L-036 / L-041 | 所有可能缺键的字典访问先 `字典包含键` 守卫（`必填字符串`、`注册`、`回收`、`校验Webhook准入` 等） |
| L-037 | `断言(条件,标签)` 是 no-op，一律 `断言相等` / `检查抛码` |
| L-051 | 所有字典/列表字面量单行书写 |
| L-054 | 嵌套字面量内不写 `\n` |
| L-055 | `打印` 只吃字面量串，文件末尾为 `打印 "--- 测试webhook会话 通过 ---"` |
| L-056 | `新建 错误(...)` 一律作为 `抛出` 的直接操作数，从不赋给变量 |
| L-057 | 不用 class 实例封装，改「顶层段落 + 模块级全局状态」 |
| L-063 | 所有字典字面量键一律带引号 |
| L-065 | 跨模块只读观测走 `取规则号表()` / `取登记()` / `是运行时关闭()`，不直接暴露可变全局 |

### 两条「不是缺陷但值得记一笔」的实测事实

1. **`列表弹出(列表)` 缺索引会硬报错**：`TypeError: 列表弹出() missing 1 required positional argument: '索引'`，
   必须写 `列表弹出(列表, 长度(列表) - 1)`。这是内置签名没有默认值，不是语言缺陷。
2. **`错误` 对象不是字典**：`是字典(错误对象) == 假`，`转字符串(错误对象)` 可拿到完整消息。
   所以 `错误链()` 只能以「字典形错误」为主路径、非字典值回退 `转字符串`。已在模块头注释写明。

---

## 6. 遗留与建议

1. **`deepFreeze` 递归冻结降级**：光明无 `Object.freeze`，嵌套层只做深复刻、只有根字典带 `"冻结"` 标记。
   若后续要严格断言「嵌套对象也冻结」，需要语言层补一个 `冻结(值)` 原语（本轮不阻塞）。
2. **`可无损JSON` 把 `空` 一律判非无损**：原版 `null` 是合法 JSON、`undefined` 才拒绝。光明二者同体，
   本轮按「原版唯一用例 `{invalid: undefined}` 为拒绝」取严格口径。若要放宽，需要先有区分 undefined/null 的语言层手段。
3. **`错误链` 未实现 `AggregateError` 分支**：原版会 `[e1; e2]` 括号展开。光明无 `AggregateError`，
   当前以「含 `message`/`cause` 键的字典形错误」为主路径即可覆盖 `session.ts` / `index.ts` 的全部调用点（诊断文案用途）。
4. **运行时排空（drain）语义折叠**：原版 `disposeRegistration` 会 `await Promise.allSettled(active)` 等活跃调用结束。
   光明同步模型下「发起调用」返回即已完成，排空退化为 no-op，语义等价。
5. **`webhook-github` 未纳入**：按任务口径 octokit handler 不可复用，整体剥离。若后续开 B/C 线，
   建议单独开一张卡对标 `packages/webhook/webhook-github/src/{body,handler,types,invariant}.ts` 的可提取部分
   （`body.ts` 的 payload 归一化与 `invariant.ts` 的 source 校验是明显可剥的纯逻辑）。
6. **建议主线合流时跑一次全量回归**：本轮只跑了 `examples/test_webhook会话.light`（rc=0），
   未触碰任何既有文件，理论上不影响 169+ 既有测试，但仍以主线全量回归为准。
