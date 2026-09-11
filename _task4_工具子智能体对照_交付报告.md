# 任务4 交付报告：工具/子智能体/预设行为对照

- 轮次：第8轮（行为对照）任务4
- 分支：`task-8-toolsub`（worktree `wt-R8T4`，基 `547ad56`）
- 上游 spec 根（只读）：`G:\github\deepseek-harness\packages\{core\tools, subagent\subagent, preset\agent-presets}\tests\`
- 铁律执行：**src 全部只读、零改动**（`git status` 确认仅 examples/_ 产物新增）

---

## 1. 交付物清单

| 产物 | 路径 | 状态 |
|---|---|---|
| 对照测试 | `wt-R8T4/examples/test_行为对照_工具子智能体.light` | ✅ 12 节全绿 |
| 反跑脚本 | `wt-R8T4/_antirun_toolsub_contrast.py` | ✅ 2 项判据 PASS |
| 交付报告 | `wt-R8T4/_task4_工具子智能体对照_交付报告.md` | 本文档 |
| 临时探查脚本 | `wt-R8T4/_spec_titles.py` | 🗑️ 提交前删除 |

## 2. 场景对照表（上游 spec → 光明节）

36 个 spec 约 13k 行，宿主面/协程/Cordis 装配占比高，按任务书「聚焦光明已有实现域」筛选出可断言的纯逻辑场景，共 12 节：

| # | 上游 spec | 上游场景（it 名） | 光明节 | 判定 |
|---|---|---|---|---|
| 1 | `tools/tools.spec.ts` | flags a missing required key / type-checks primitives / allows extra keys / checks enum membership / recurses into nested objects / validates arrays element-wise / does not apply defaults (validation only) | 节1 参数 JSON Schema 校验 | ✅ 语义一致 |
| 2 | `tools/tools.spec.ts` | schemas() drops host callbacks / excludes timeoutMs —— must never reach the model | 节2 描述表净化 | ✅ 语义一致 |
| 3 | `tools/tools.spec.ts` | a non-HarnessError throw retains only its message / a schema-invalid call surfaces the structured error | 节3 执行错误收敛 | ✅ 语义一致 |
| 4 | `subagent/assistant-output.spec.ts` | selects the last non-empty message past a later empty usage-only message / prefers a non-empty message over text streamed before and after it | 节4 最后非空消息 | ✅ 语义一致（投影形态差异见 §5-D1） |
| 5 | `subagent/assistant-output.spec.ts` | treats textless assistant content as a non-empty message / returns undefined when the child produced neither messages nor text | 节5 边界差异 | ⚠️ 差异登记（§5-D1） |
| 6 | `subagent/catalog.spec.ts` | preserves event order across chunk rollover and checkpoint restoration | 节6 分块翻转保序（64 上限） | ✅ 语义一致 |
| 7 | `subagent/catalog.spec.ts` | materializes every label variant in event order / refuses to restore a catalog containing an invalid fact | 节7 标签变体与非法事实 | ✅ 语义一致 |
| 8 | `subagent/catalog.spec.ts` | ignores unrelated and inherited events without changing state | 节8 无关/继承事件忽略 | ✅ 语义一致 |
| 9 | `subagent/control.spec.ts` | catalogView 纯逻辑面：live child → running、settled siblings 完整 | 节9 目录视图活动 | ✅ 语义一致 |
| 10 | `preset/metadata.spec.ts` | ignores fields that are not text / ignores blank text / trims whitespace / ignores a non-finite order / cannot carry identity or trust | 节10 显示元数据纯逻辑 | ✅ 语义一致 |
| 11 | `preset/discovery.spec.ts` | puts declared order first, then everything else by id / breaks a tie between equal declared orders by id | 节11 扫描排序 | ✅ 语义一致 |
| 12 | `preset/display.spec.ts` | keeps user-authored metadata untranslated | 节12 user 元数据不翻译 | ✅ 语义一致（shipped 字典翻译缺失见 §5-D4） |

**已覆盖不重复**（既有 `test_工具` / `test_子智能体` / `test_预设` 已含同域断言，回归抽查确认全绿）：
- tools.spec.ts：注册 round-trip（注册/名单/描述表/执行/统计）、`get()` 未知返回空、执行未知工具 → TOOL_NOT_FOUND、HarnessError 名称+代码
- tools/execution-mode.spec.ts：`执行策略` 默认 parallel（上游默认差异见 §5-D2）
- preset/discovery.spec.ts：跨根去重保留首现（`发现预设`）
- preset/authoring.spec.ts：越界/相对标识拒绝（`校验预设标识`）

## 3. 翻译要点

- **导入惯例**：光明模块无 `导出` 语句亦可被 `从 X 导入 a, b` 引用（沿用 `test_子智能体.light` 先例）。
- **投影形状差异处理**：目录投影用 `重建父属目录(事件表, 继承序号)` → `.条目()`（行表：标识/创建时间/模式/标签?）、`.校验状态()`；断言键名为光明中文键。
- **assistant 输出**：`子智能体(客户端, 注册表, [], 名字).取会话().记录事件("assistant/message", …)` 构造事件流，`取最后回答()` 断言文本。
- **校验错误表**：`校验参数(模式, 参数字典)` 返回错误表（空=通过），按 `项["原因"]` 分类断言（missing/type/additionalProperties/enum/const）。
- **元数据**：`提取显示元数据(字典)` 以字典为输入（上游 metadata.spec 的 YAML 文件 IO 属宿主面，剔除），语义等价断言。
- 外部测试自带 `断言相等/断言真/断言抛/含原因` 辅助段；嵌套段落（如抛错工具执行体）与 `test_工具` 同构。

## 4. 测试与 CI

- 新测试：`python 运行.py examples\test_行为对照_工具子智能体.light` → **PASS（12 节）**
- 回归抽查（src 只读未改）：`test_工具` rc=0 ✅、`test_子智能体` rc=0 ✅、`test_预设` rc=0 ✅
- 全量 CI：由路M统一跑，期望 **222 passed / 0 failed**（218 基线 + 4 路新测试，本路贡献 1 个）。

## 5. 差异清单（供路M汇总至 `docs/功能对标/行为差异清单.md`）

> 原则：凡光明行为与上游断言数值/语义不一致即登记；测试文件断言光明实际行为使测试全绿，**不改 src**。

| ID | 域 | 上游断言 | 光明实际行为 | 影响面 |
|---|---|---|---|---|
| D1 | assistant-output | `finalAssistantOutput` 返回**内容块表** `[{type:"text",text:"step two"}]`；无输出→`undefined`；reasoning-only 消息视为**非空输出** | `取最后回答` 返回**拼接文本字符串**；无输出→`""`；reasoning-only 消息被**跳过**（不产出文本） | 投影形态 + 边界语义差异；对「最后回答」文本消费方等价，对块级消费方与 undefined 判空方不等价 |
| D2 | execution-mode | 上游 `isConcurrencySafe` 未声明 → **exclusive** | 光明 `执行策略` 未注册/缺省 → **"parallel"** | 默认并发语义差异（既有 `test_工具` 亦断言 parallel） |
| D3 | 校验文案 | 上游英文 `"value" must be a string` / `missing required property "value.file"` | 光明中文 `期望 string 实际 整数` / `缺少必需字段`，错误项结构 `{路径, 原因, 细节}` | 语义等价、文案语言差异（结构不同：光明为结构化错误表） |
| D4 | display | 上游 `presetDisplayText` 对 shipped preset 走**字典键解析**（`t:presetStandardName`），无元数据回退 id | 光明无 `presetDisplayText`；显示文本由 `提取显示元数据`/`造显示元数据记录` 承担，**无 shipped 字典翻译**（user 元数据原样保留 ✓） | 功能缺口：shipped 预设显示文案无 i18n 字典键 |

## 6. 移交清单

- 提交范围：仅 `wt-R8T4`；`git add -A` + commit（`_spec_titles.py` 已删除）。
- 全量 CI 与差异清单汇总：路M统一执行。
- 反跑判据证据：见 §4（A 改断言期望值 → rc=1 红、B 删节11 场景定义 → rc=1 红；均字节级恢复后 rc=0 绿）。
