# 第12轮·任务2｜会话投影域：轮次大纲 + 检查点策略 —— 交付报告

- 分支：任务2（会话投影域），工作区 `G:\dswork\duan-light-merge\lightharness`
- 对照基准：上游 `G:\github\deepseek-harness` @ `a305303422`（0.1.5-rc.2，只读参考）
- 涉及文件：**新建** `src/会话轮次大纲.light`（123 行）+ `src/检查点策略.light`（60 行）+ `examples/test_会话轮次大纲.light`（87 行）+ `examples/test_检查点策略.light`（62 行）+ `_antirun_outline_ckpt.py`（63 行）
- 任务书：`复刻_第12轮_任务prompt分发.md` §任务2（会话投影域：turn-outline 轮次大纲 + checkpoint-policy 检查点策略）
- 只读遵守：`src/钩子.light` / `src/钩子协议.light` / `src/会话.light` / `src/持久化.light` / `src/会话格式.light` / `docs/功能对标/` / `scripts/` / `运行.py` / `stdlib/` 全部只读，零改动

## 1. 上游对应表

| 上游源文件（a305303422） | 上游语义 | 本路实现位置 |
|---|---|---|
| `packages/session/session-turn-outline/src/types.ts`（44 行） | `TurnOutlineEntry { turn, seq, prompt, response }`；`TurnOutlineState { turns, draft }`；整轮大纲投影键声明 | `src/会话轮次大纲.light`（空大纲 / 轮次大纲折叠 / 轮次大纲视图 / 轮次大纲定义） |
| `packages/session/session-turn-outline/src/projection.ts`（129 行） | `preview()`：空格连接文本块、折叠空白、限长省略（PROMPT_PREVIEW_LIMIT=50 一行、RESPONSE_PREVIEW_LIMIT=120 三行）；以 `turn/start` 为锚点（非 user/message）；user/message 仅 user 来源写 prompt、已写不覆盖；assistant/message 仅写 draft（不动 turns 引用）；turn/end 提交 draft 到末条 response 并清空；同轮回落 turn/start 忽略 | `src/会话轮次大纲.light`（预览文本收集 / 预览文本 / 提示预览上限 / 回答预览上限 / 轮次大纲折叠） |
| `packages/session/session-checkpoint-policy/src/index.ts`（75 行） | `abortedBeforeDispatchResult()`：`content=[{type:"text",text:"Error: tool call aborted before dispatch"}]`、isError、`error.message` 同文案、`info={name:"AbortError", code:TOOL_ABORTED_BEFORE_DISPATCH}`；llm/stream 请求首块前 flush；tools/execute 仅顶层（agent 有值且 parent 无值）flush + 已中止返回规范错误；agent/pre-step 每步前 flush；失败 fail-closed | `src/检查点策略.light`（中止未分发结果 / 是否临流检查点 / 是否顶层工具执行 / 工具是否已中止 / 工具执行策略 / 临流策略 / 预步骤策略） |
| （剔除）Cordis 插件壳 | `name/inject/apply` 注册、llm/stream 流包裹、ctx.sessions.flush/get 持久化副作用、signal 实际异步中止、zod schema、identity-gated 变更流 | 未移植（见 §5 未移植项） |

## 2. 实现要点

### 2.1 轮次大纲（对齐 projection.ts + types.ts 纯折叠逻辑）

- **限量常量**：`提示预览上限()=50`、`回答预览上限()=120`（对齐 projection.ts 顶部常量）。
- **预览（preview 语义）**：`预览文本收集` 只统计 `type=="text"` 块；任一块文本长度 ≥ 上限×2 视为未读完并停止追加（避免单块超大全文拼接）；块间空格连接；`预览文本` 去除首尾空白后若超 上限-1 截断加 `…`，未读完且未截断时补 `…`。
- **折叠（apply 语义）**：`轮次大纲折叠(状态, 事件)` 四分支——
  - `turn/start`：以事件 seq 开新条目 `{turn, seq, prompt:"", response:""}`；轮次 ≤ 末条时忽略（同轮回落）返回原状态；
  - `user/message`：仅 `data.source.kind=="user"` 且末条 prompt 为空时写入提示预览（上限 50）；无 source 键/非 user/已写/空预览均忽略；
  - `assistant/message`：预览回答（上限 120）写 `draft`；草稿为空或与当前 draft 相同则原样返回（**不动 turns 引用**，保持数组身份）；
  - `turn/end`：draft 为空或末条 response 已等于 draft 则清 draft 返回；否则提交 draft 到末条 response 并清空。
- **视图**：`轮次大纲视图(状态)` 返回 `turns`；`轮次大纲定义` 返回投影键声明（key=turnOutline、stateVersion=2）。
- **辅助**：`列表取` / `追加项` / `替换末项`（光明无直接下标替换，以复制实现不可变更新）。

### 2.2 检查点策略（对齐 checkpoint-policy 决策面，映射光明钩子体系）

- **规范中止结果**：`中止未分发结果()` 返回与上游逐字段一致的规范错误（text/message/info.name/info.code 全对齐）。
- **临流检查点判定**：`是否临流检查点(选项, 会话表)` —— 选项含非空 `sessionId` 且会话表包含该 id 才启用（对齐 llm/stream 绑定语义）。
- **顶层工具判定**：`是否顶层工具执行(执行上下文)` —— agent 有值且无 parent（对齐 tools/execute `exec.agent!==undefined && exec.parent===undefined`）；`工具是否已中止` 读 `signal.aborted`。
- **工具执行策略**：`工具执行策略(执行上下文)` —— 非顶层→直通；已中止→返回中止结果；否则→继续（刷新为 I/O 剔除，见 §5）。
- **临流/预步骤策略**：`临流策略(选项, 会话表)` 检查点后继续 / 直通；`预步骤策略(会话)` 刷新 / 跳过（对齐 agent/pre-step 决策面恒定）。

## 3. 测试与验证

### 3.1 定向测试（新增，全绿）

`examples/test_会话轮次大纲.light` → 输出 `test_会话轮次大纲 PASS`，RC=0，覆盖：

| 组 | 覆盖 |
|---|---|
| 空大纲 | turns 空、draft 空 |
| 预览 | 跳过非文本块 / 拼接 / 超长截断长度恰为上限 50、末尾 `…` |
| turn/start | 开新条目（turn/seq/prompt 初始值）/ 第二轮追加 / 同轮回落忽略 |
| user/message | user 来源写 prompt / 非 user 忽略 / prompt 已写不覆盖 |
| assistant/message | 写 draft / 未提交时 response 空 / 重复草稿不覆盖不新增 |
| turn/end | 提交 response / 清空 draft / 空草稿不回退 |
| 视图与常量 | 视图返回 turns / 上限 50 与 120 |

`examples/test_检查点策略.light` → 输出 `test_检查点策略 PASS`，RC=0，覆盖：

| 组 | 覆盖 |
|---|---|
| 中止结果形状 | text / isError / error.message / info.name / info.code 逐字段 |
| 顶层判定 | 有 agent 无 parent=顶层 / 有 parent=非顶层 / 无 agent=非顶层 |
| 中止判定 | aborted 真/假 / 无 signal 视作未中止 |
| 执行策略 | 已中止=中止携带错误结果 / 正常顶层=继续 / 非顶层=直通 |
| 临流判定 | 会话存在=启用 / 不存在=不启用 / 无 sessionId=不启用 |
| 临流/预步骤 | 检查点后继续 / 直通 / 刷新 / 跳过 |

### 3.2 反跑判据（机器验证）

`python _antirun_outline_ckpt.py` → **3/3 PASS（改反即红 rc=1，恢复即绿 rc=0），输出 ALL OK**：

1. **A｜turn/start 锚点**：源串 `如果 类型 == "turn/start":` 改反（改成 user/message）→ 断言红；恢复 → 绿
2. **B｜预览限长**：源串 `段落 提示预览上限 接收:\n  返回 50` 改反（50→99）→ 截断长度断言红；恢复 → 绿
3. **C｜中止规范错误**：源串 `"text": "Error: tool call aborted before dispatch"` 改反 → 中止结果断言红；恢复 → 绿

脚本自含字节级备份/恢复 src，恢复后源文件与备份逐字节一致。

### 3.3 既有回归（任务书指定，全绿）

- `examples/test_钩子.light`（PASS）
- `examples/test_会话.light`（通过）
- `examples/test_持久化增量.light`（PASS）
- `examples/test_会话查询1.5.light`（PASS）
- `examples/test_会话查询过滤.light`（通过）

### 3.4 CI 说明

按铁律 6 只跑本路新增测试 + 直接相关既有回归（上列 5 项），未跑全量 CI（由路M 统一执行）。

### 3.5 收尾修复（接手时发现并已修）

初始交付的两个测试文件**缺少末尾 `主()` 调用与 PASS 打印**，运行静默空跑（rc=0 无断言执行）。已补 `主()` 调用 + 主函数体内末尾 `打印 "test_xxx PASS"`（对齐仓库既有测试惯例，如 test_钩子.light），重跑后断言真实执行、输出 PASS。

## 4. 光明语言适配（本任务实测记录）

- **不可变更新**：光明无直接"替换列表末项"原语，以 `追加项`/`替换末项` 复制实现（对齐上游不可变折叠语义，保持 turns 数组身份——重复草稿/同轮回落不新增引用）。
- **「映射」保留字**：全程用「表/字典」，规避保留字。
- **空参数传 {}**：空字典传 `{}` 而非 `[]`（list 无 `.获取`）。
- **本次未触发新语言缺陷**：`字典包含键`、`是列表`、`是字典`、`是字符串`、`字符串长度`、`截取` 均可用；闭包（L-078）未强制使用（本路折叠为纯函数，无需回调闭包）。

## 5. 未移植项（明确保留）

- **Cordis 插件壳**：`name/inject/apply` 注册、zod schema、SessionSeq 类型、sessionProjections 注册与 identity-gated 语义化变更流（宿主面）不移植；`轮次大纲定义` 以键名 + stateVersion 声明投影键，供宿主接线参考。
- **持久化副作用**：上游 `ctx.sessions.flush/get` 是 I/O 副作用；光明侧以判定函数（是否临流检查点 / 是否顶层工具执行 / 工具是否已中止 / 工具执行策略 / 临流策略 / 预步骤策略）表达决策面，**刷新动作由宿主在钩子处接线执行**（本路不注入 I/O）。
- **llm/stream 流包裹**：上游以生成器包裹流实现"首块前检查点"，本路以 `临流策略` 判定暴露决策点，包裹由宿主接线。
- **signal 实际异步中止**：上游 signal.aborted 由 AbortController 驱动，本路读取 `signal.aborted` 字段判定（字段形状对齐上游 exec.signal）。

## 6. 移交清单

- `src/会话轮次大纲.light`（新建，123 行）——任务2 轮次大纲纯逻辑（导出 空大纲 / 预览文本收集 / 预览文本 / 提示预览上限 / 回答预览上限 / 轮次大纲折叠 / 轮次大纲视图 / 轮次大纲定义）
- `src/检查点策略.light`（新建，60 行）——任务2 检查点策略决策面（导出 中止未分发结果 / 是否临流检查点 / 是否顶层工具执行 / 工具是否已中止 / 工具执行策略 / 临流策略 / 预步骤策略）
- `examples/test_会话轮次大纲.light`（新建，87 行）——13 组断言，`test_会话轮次大纲 PASS`
- `examples/test_检查点策略.light`（新建，62 行）——6 组断言，`test_检查点策略 PASS`
- `_antirun_outline_ckpt.py`（新建，63 行）——反跑判据 3/3 PASS（ALL OK）
- 临时文件：无残留（本路未产生 _tmp 系列；根下既有 _t2_检查点*.log / _verify_test_*.log 为上一执行留痕，未动）

## 7. 语言缺陷账判定

**无新缺陷，未新增 L-0xx 登记**。本任务用到的语言特性（字典包含键 / 是列表 / 是字典 / 是字符串 / 截取 / 列表长度 / 遍历）均已可用；未触发闭包（L-078）、副本（L-082）等新原语依赖（纯函数实现）。docs/功能对标/ 保持只读，未改动。
