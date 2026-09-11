# 路6(F)｜交付/文件/工具/MCP/压缩 1.5 增量 —— 交付报告

- 分支：`task-6-delivery-15`（worktree `wt-F6`，基 `4b0f77f`）
- 对照基准：上游 `a305303422`（0.1.5-rc.2），仓库 `G:\github\deepseek-harness`（只读参考）
- 涉及文件：新建 `src/交付.light` + `examples/test_交付.light`；改动 `工具.light`/`网页搜索.light`/`工作区.light`/`路径规则.light`/`mcp客户端.light`/`压缩.light`/`压缩配套.light`（`文件.light` 经核对无需改动，见 §5）

## 1. 上游对应表

| 上游增量提交 | 上游语义 | 本路实现位置 |
|---|---|---|
| `37d27fcdf9`（present immutable file deliveries with download cards） | 交付声明不可变（只记录源路径+描述，不复制内容；删除/移动使声明不可用） | `交付.light`：`判定声明可用`、`造交付事件`（文件表只含 路径/描述 的规整副本） |
| `7a0afea27f`（distinguish file changes & require explicit delivery） | 文件变更 ≠ 交付物；提及路径不替代 present；创建/更新的文件要交付必须显式 present | `交付.light`：`判定需交付`（改动表按已声明表划分 已交付/未交付） |
| `c9038b4b31`（declare and open workspace source files） | present 只声明源文件路径+描述，用户打开当前源文件，内容不保留不持久化 | `交付.light`：`规整交付项`（拒绝多余键，仅 路径/描述） |
| `00bfdfbce6`（follow session filesystem access for deliverables） | 边界从 workspace containment 改为「会话文件系统可访问」；lstat 预检 + stat 确认 regular file | `交付.light`：`判定交付文件`（查类别 + 判定可访问 入参投影；目录/缺失/界外 三种拒绝） |
| `9d6c964985`（#3853 scoped tools in filesystem/web guidance） | 指导段按工具可见性渲染；grep 段的 read 后续句、write 段的 edit 推荐句按目标工具可见性省略 | `工具.light`：`判定工具可见`/`过滤可见指导`/`裁交叉推荐`；`网页搜索.light`：`渲染Web指导`/`渲染作用域Web指导` |
| `e609fd73a3`（harden qualified path handling） | `isWindowsStylePath`/`isAbsoluteWorkspacePath`/`resolveWorkspacePath`（分隔符仅在 cwd 为 win 风格且含反斜杠时用反斜杠） | `工作区.light`：`判定Windows风格路径`/`判定绝对工作区路径`/`解析工作区路径` |
| `9656a1742b`（windows-root-workspace） | `fullyQualifiedWorkspacePath`：win32 须盘符根或 UNC，裸根 `\`/`/` 拒绝（依赖当前驱动器）；`defaultWorkspaceTitle`：basename 或根拼写 | `工作区.light`：`判定完全限定`/`默认标题`/`规范化路径平台`（win 盘符根保留）；`路径规则.light`：`判定盘符根`/`判定盘符头` + `上层路径` 盘符根终止 |
| `2b521b31f1`（#3846 fix mcp pagination cycles，子提交 594305ce19） | tools/list 分页 drain：seenCursors 去重，重复 continuation cursor 抛错拒绝（防无限翻页），无 nextCursor 终止 | `mcp客户端.light`：`消费分页工具表` |
| compaction 增量（compaction-basic region/summarizer + tool-result-pruner） | `summarizer.ts`：COMPACTION_INSTRUCTION（8 节检查点指令）、CHECKPOINT_PREAMBLE、frameSummary（`<compacted-summary>` 标签包裹）、summaryText（含图片抛错） | `压缩配套.light`：`造压缩指令`/`包摘要框架`/`检查摘要文本` + 常量；`压缩.light`：`造检查点消息`（摘要接入检查点框架） |

> `compaction-basic` 的 region（`选择可压缩区`）与 tool-result-pruner（`度量内容`/`裁剪内容`/`resolveConfig`）在 `压缩配套.light` 已有实现（既有模块），本路补齐 summarizer 缺口并接入 `压缩.light`。

## 2. 语义实现方式

### 2.1 交付纯逻辑（新建 `交付.light`）
- **交付参数校验**：1..maxFiles（默认 8），空表/超限抛 `present accepts 1 to N files`；空/全空白路径抛 `present requires a non-empty file path`；每项 `规整交付项` 仅保留 路径/描述（拒绝多余键，对齐原版 additionalProperties:false）。
- **会话文件系统边界跟随**：`判定交付文件` 三步——类别预检（目录 → `not a regular file`；缺失 → `file not found…`）、`判定可访问` 入参投影（界外 → `outside the session filesystem`）。不再要求 workspace containment。
- **不可变交付声明**：`判定声明可用` = 源文件当前仍为常规文件（内容不复制不保留）；`造交付事件` 产出 `{ 轮次, 调用标识, 文件表 }`（文件表为规整副本），对齐 `deliverables/presented` 事件形状；落盘由宿主 `会话.记录事件` 完成（胶水，测试不覆盖）。
- **文件变更 vs 交付物**：`判定需交付` 把本轮文件改动按已声明表划分为 已交付/未交付——改动未显式 present 即「未交付」，体现「显式交付要求」。

### 2.2 scoped tools（`工具.light` / `网页搜索.light`）
- `判定工具可见(允许表, 禁止表, 名字)`：允许表非空 → 白名单（须命中）；否则 禁止表 含 名字 → 不可见。
- `过滤可见指导(指导段表, 判定可见)`：指导段 = `{ 工具名, 文本 }`，只渲染可见工具段（保持顺序）。
- `裁交叉推荐(指导文本, 标记, 关联工具, 判定可见)`：关联工具不可见时截断 标记 起句（对齐 grep 段 read 后续句省略），可见时原文。
- `网页搜索.light`：`渲染Web指导` 按 search/fetch 可见性产出指导段；`渲染作用域Web指导` 以 允许表/禁止表 为入参（内嵌注入段落）。

### 2.3 workspace 路径加固（`工作区.light` / `路径规则.light`）
- `判定Windows风格路径`：盘符+冒号+斜杠（`C:/`/`C:\`）或 UNC（`\\` 开头）；`判定绝对工作区路径`：`/` 开头或 win 风格。
- `解析工作区路径(工作目录, 路径)`：绝对原样；相对 = 去尾斜杠基底 + 分隔符 + 去前导斜杠相对段；分隔符仅当 cwd win 风格且含反斜杠时用 `\`（对齐 e609fd73a3 防混合分隔符）。
- `判定完全限定(路径, 平台标识)`：win32 → 须 win 风格（裸根 `\`/`/` 因依赖当前驱动器被 `判定Windows风格路径` 排除）；否则 posix 绝对。
- `默认标题`：末段；无分隔符 → 根拼写。
- `规范化路径平台`：win32 盘符根保留（`C:\` → `C:/`，非 `/C:`）；**不改** `规范化路径` 既有行为（`test_工作区` 断言 `/C:/...` 为既有契约）。
- `路径规则.light`：`判定盘符根`（恰 3 字符 `X:`+斜杠）、`判定盘符头`（2 字符 `X:`）；`上层路径` win32 下取到盘符根/盘符头即返回 `""` 终止（不再把盘符根当需建目录、不参与 stat 身份回退向上）。

### 2.4 mcp 分页循环修复（`mcp客户端.light`）
- `消费分页工具表(页表, 服务器名)`：逐页合并 `工具表`；页含 `下一光标` 时先查 `已见光标`（重复 → 抛 `server repeated a tools/list continuation cursor — invalid tool list`）再记录；无光标即终止。纯逻辑入参化，宿主 drain 循环胶水不涉及。

### 2.5 compaction summarizer 增量（`压缩配套.light` / `压缩.light`）
- 常量：`压缩开启标签`/`压缩闭合标签`（`<compacted-summary>`/`</compacted-summary>`）、`检查点前导`（对齐 CHECKPOINT_PREAMBLE）。
- `造压缩指令`：8 节结构化检查点指令（Primary Request and Intent / Key Technical Concepts / Files and Code / Errors and Fixes / Pending Jobs / Current Work / Next Step / Critical Context）+ 6 条规则（保留精确路径/命令/错误串、不提压缩请求、只输出检查点、已有检查点合并）。
- `包摘要框架(摘要块表)`：`[前导+开标签, ...摘要, 闭标签]`（对齐 frameSummary）。
- `检查摘要文本(块表)`：含图片抛 `compaction summary cannot contain image output`；只留 text 块。
- `压缩.light`：`造检查点消息(会话对象, 尾号)` = 造摘要 → 包摘要框架 → 造用户消息，使压缩摘要落盘为「已确立背景」检查点（不改 `压缩到最近` 既有行为）。

## 3. 测试与验证

### 3.1 定向测试（新增）
`examples/test_交付.light` 全绿（`test_交付 PASS`），11 组用例覆盖：
1. 交付参数校验（规整/空表/超限/空路径抛错）
2. 交付文件判定（常规通过/目录/缺失/界外拒绝）
3. 不可变交付声明（存在可用/缺失不可用）
4. 交付事件构造（轮次/调用标识/文件表规整）
5. 显式交付划分（已声明=交付物、未声明=未交付）
6. scoped tool 可见性（白名单/黑名单）
7. 指导段过滤 + 交叉推荐句裁剪（read 不可见截断/可见保留）
8. web guidance 渲染（全可见 2 段/禁 search 1 段/作用域白黑名单）
9. workspace 路径加固（win 风格/绝对/解析/完全限定/默认标题/规范化平台/盘符根/上层终止）
10. mcp 分页（三页合并 4 工具/重复光标抛错/无光标终止）
11. compaction summarizer（指令节标题/框架三块/检查摘要文本/图片抛错/检查点接入）

### 3.2 反跑判据（机器验证 `_antirun_f6.py`）
6 项改反即红，全部 PASS（rc=1）：

| 判据 | 改反点 |
|---|---|
| 交付物判定 | 常规文件 有效 断言改反 |
| 文件变更 vs 交付物（显式交付） | 未交付数 断言改反 |
| scoped tool 豁免 | 过滤可见指导 段数 改反 |
| workspace qualified path | `判定完全限定("C:\\proj","win32")` 改反 |
| mcp 分页终结点 | 重复光标「应抛错」改反 |
| compaction summarizer | 框架块数 改反 |

### 3.3 既有用例回归（本路涉及模块，17 项全绿）
`test_工具`/`test_工具深`/`test_工具深化`/`test_工具系统`/`test_工具统计`/`test_文件`/`test_文件深`/`test_文件深化`/`test_网页搜索`/`test_工作区`/`test_路径规则`/`test_mcp`/`test_mcp_http`/`test_压缩`/`test_压缩自动`/`test_压缩配套` 全部通过；`test_压缩E5` 为既有预期红（见 3.4）。

### 3.4 全量 CI
`python scripts\ci_test.py`（LIGHT_MERGE 已设）：**197 passed + 2 failed**。失败清单与基线完全一致，无新增打红：
- `test_agentE5钩子.light`（既有）
- `test_压缩E5.light`（既有）
核心模块冒烟 5/5 通过。新增 1 例（`test_交付.light`）绿。

## 4. 修改文件清单

| 文件 | 变更 | 规模 |
|---|---|---|
| `src/交付.light` | 新建（tool-present 纯逻辑） | 约 120 行 |
| `src/工具.light` | 追加 scoped tools（可见性/过滤/裁剪/查找子串位置） | +95 行 |
| `src/网页搜索.light` | 追加 web guidance scoped | +40 行 |
| `src/工作区.light` | 追加 qualified path + win 根（导入补 字符转ASCII） | +110 行 |
| `src/路径规则.light` | 上层路径 盘符根/盘符头终止 + 判定盘符根/盘符头（导入补 字符转ASCII） | +40 行 |
| `src/mcp客户端.light` | 追加 消费分页工具表 | +28 行 |
| `src/压缩配套.light` | 追加 summarizer（指令/框架/文本检查） | +45 行 |
| `src/压缩.light` | 追加 造检查点消息 + 导入 包摘要框架 | +10 行 |
| `examples/test_交付.light` | 新建（11 组判据） | 约 260 行 |
| `_antirun_f6.py` | 新建（6 项反跑机器验证） | 60 行 |

## 5. 未移植项（宿主胶水/工程层，不在本路纯逻辑范围）

1. **真实文件系统 IO**：present 的 lstat/stat/resolve 与「会话文件系统可访问性」真实判定属宿主（`系统接口.light`/沙箱层），本路以 `查类别`/`判定可访问` 入参投影。
2. **事件落盘**：`deliverables/presented` 事件的真实追加（turnBoundary 追踪 + `会话.记录事件`）属宿主编排，本路只产出事件字典。
3. **mcp drain 循环**：真实 tools/list 网络往返与 cursor 传递属宿主连接层，本路提供纯逻辑分页消费（重复光标拒绝）。
4. **LLM 调用**：compaction 摘要生成走 LLM 的胶水未移植，本路复刻指令文本与框架包裹。
5. **`文件.light` 未改动**：任务书列其为涉及文件，但逐条核对后确认——交付边界跟随/判定逻辑全部落在 `交付.light`（本路新建），`文件.light`（基础文件 IO）无需承载交付语义，保持零改动以最小化回归面。
6. **`download cards`（37d27fcdf9 早期设计）**：已被 c9038b4b31「声明源文件」取代，未移植下载卡 UI 语义（上游最终行为即源文件打开）。

## 6. 移交清单（跨路）

- **给 路1/路5（会话/持久化/代理）**：交付事件 `deliverables/presented = { 轮次, 调用标识, 文件表 }` 形状已定，宿主在成功 final tools/result 后经 `会话.记录事件("deliverables/presented", …)` 落盘；`轮次` 取 turnBoundary.lastTurn。
- **给 路4（子智能体）/路3（agent-loop-goal）**：scoped tools 判定 `判定工具可见(允许表, 禁止表, 名字)` 与 `过滤可见指导` 可复用于任何工具指导渲染面；PTC 能力（wire 呈现 run_code）同规则适用。
- **给 路3/路5（工作区宿主）**：`判定完全限定(路径, 平台标识)`/`解析工作区路径(工作目录, 路径)` 为工作区构造的入口校验语义；`规范化路径平台` 提供 win 盘符根语义而**不破坏** `规范化路径` 既有契约（`test_工作区` 断言 `/C:/...` 属既有行为，若宿主后续要统一盘符根表示，请走 `规范化路径平台`）。
- **给 路2（agent-team，已提交）**：无交集。
- **语言层已知坑（复跑备忘）**：`查找子串` 与内置 2 参版本冲突（改 `查找子串位置`）；字符串单反斜杠须写 `"\\"`（补丁脚本 Python 源码里要四层转义）；压缩配套/会话族块字典键名两套并存（中文键 `类型/文本` vs 英文键 `type/text`），`包摘要框架` 用中文键，与 `消息` 族 `造用户消息` 兼容（块表直通）。

## 7. 结论

路6(F) 交付/文件/工具/MCP/压缩 1.5 增量完成：交付纯逻辑（交付物判定/显式交付/不可变声明/会话文件系统边界跟随）、scoped tools 判定、workspace qualified path 与 Windows 根语义加固、mcp 分页循环修复、compaction summarizer 增量全部落地；新增用例全绿、反跑判据 6/6 红、既有 17 项模块回归全绿、全量 CI 无新增打红。符合任务书 §4 验收口径。
