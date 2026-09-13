# 任务5 交付报告 —— 预设深化与设置技能角色域（preset 深化 + settings 类型 + skill 徽章 + persona）

> 轮次：复刻 第15轮 ｜ 日期：2026-09-13 ｜ 对标卡：**#102（新增）** ｜ 差异编号 **R15-D5** ｜ 缺陷编号预分配 **L-129**
> 上游只读：`G:\github\deepseek-harness`（本地 HEAD `9d9035b7c1`；任务书标注 `a305303422`，差异见 §六）
> 本路可写文件（4 个，全部新增，零越界）：
> - `lightharness/src/预设深化.light`（542 行 / 53 段）
> - `lightharness/examples/test_预设深化.light`（253 行 / **150 断言**）
> - `lightharness/_antirun_t5_预设深化.py`
> - `lightharness/_task5_预设深化_交付报告.md`（本文件）
> 另：最小复现 `lightharness/examples/_repro_L129.light`（铁律 2 要求，缺陷 L-129）

---

## 一、上游对应表（文件 / 行号 / 核心语义）

| 上游 | 行 | 核心语义 | 本模块落点 |
|---|---|---|---|
| `preset/agent-presets/src/composition-inventory.ts` | 26 `CompositionRowEnablement` | `boolean \| 'conditional'` | §1 `是合法启用值` |
| `preset/agent-presets/src/composition-inventory.ts` | 33 `DisabledExpressionEvaluator` | 宿主求值能力（`!!js`） | §1 `禁用贡献` 的 `求值能力` 形参 |
| `preset/agent-presets/src/composition-inventory.ts` | 36–50 `AgentPresetCompositionRow` | `entryId`(可空)/`moduleName`/`enabled`/`condition?`/`fiberState?` | §1 `造组合行` / `是组合行` |
| `preset/agent-presets/src/composition-inventory.ts` | 53–66 `AgentPresetComposition` | `id`/`trust`/`name?`/`isDefault`/`broken?`/`rows` | §1 `是组合` |
| `preset/agent-presets/src/composition-inventory.ts` | 77–91 `disabledContribution` | `!!js`→问求值器；拒绝(throw)→`'conditional'`；否则按 `Boolean(value)` | §1 `是动态禁用标记` / `禁用贡献`（**L-129 命中点**） |
| `preset/agent-presets/src/composition-inventory.ts` | 101–108 `combineDisabled` | 任一字面真即真；否则任一条件即条件；否则假 | §1 `合并禁用` |
| `preset/agent-presets/src/composition-inventory.ts` | 128–148 `flattenRows` | 组行递归继承外层 `disabled`，叶子行产出；`enabled = 禁用三态→启用三态` | §1 `展平行` / `是否组行` / `行标识` / `启用取值` |
| `preset/agent-presets/src/composition-inventory.ts` | 162–178 `fileComposition` | 解析文件行列表 → 展平（解析为宿主面） | §1 `组合行`（解析能力剔除） |
| `preset/agent-presets/src/composition-inventory.ts` | 185–198 `mountedCompositionRows` | Loader 树项 → 行（`enabled=!disabled`；组行跳过；`fiberState` 可选） | §1 `挂载行` |
| `preset/agent-presets/src/types.ts` | 11–24 `AgentPresetRow` | `id`/`trust`/`isDefault`/`name?`/`description?`/`broken?` | §1.6 `是预设行` |
| `preset/agent-presets/src/types.ts` | 27–32 `AgentPresetRoster` | `presets` + `authorable` | §1.6 `是预设名册` |
| `preset/agent-presets/src/types.ts` | 34–45 `RemoteErrorDetailsMap` 四码 | `not-found`/`invalid`/`read-only`/`locked` | §1.6 `预设远程错误码表` / `是预设远程错误码` |
| `preset/agent-presets/src/types.ts` | 48–59 `AgentPresetDocument` | `agentPreset`/`trust`/`content`(+`name?`/`description?`) | §1.6 `是预设文档` |
| `preset/persona/src/index.ts` | 19·21 `PERSONA_PREFIX_SECTION` / `PERSONA_SUFFIX_SECTION` | 段名 `deployment:persona-prefix` / `deployment:persona-suffix` | §2 `角色前缀段名` / `角色后缀段名` |
| `preset/persona/src/index.ts` | 30–46 `Config` | `prefix` 必填；`suffix?`/`complete?`/`includeRuntimeContext?` | §2 `角色配置默认值` / `校验角色配置` / `是角色配置` |
| `preset/persona/src/index.ts` | 49–54 `Config` schema | `suffix` 默认 `''`、`complete` 默认 `false`、`includeRuntimeContext` 默认 `true` | §2 `角色配置默认值` |
| `preset/persona/src/index.ts` | 33–35·74 | 空前缀在渲染时丢弃该段（matching the registry） | §2 `段是否渲染` |
| `settings/settings/src/types.ts` | 15 `SettingsNamespace` | 品牌 id | §3 `是命名空间视图`（`ns` 判据） |
| `settings/settings/src/types.ts` | 18 `SettingsUpdateSource` | `'update' \| 'provider'` | §3 `设置来源表` / `是合法设置来源` |
| `settings/settings/src/types.ts` | 21–26 `SettingsSecretView` | `path: string[]` + `set: boolean` | §3 `是秘密视图` |
| `settings/settings/src/types.ts` | 33–54 `SettingsNamespaceView` | `ns`/`schema`/`value`/`base?`/`user?`/`applies`/`secrets`/`revision` | §3 `是命名空间视图` / `造命名空间视图` |
| `settings/settings/src/types.ts` | 45 `applies` | `'live' \| 'restart'` | §3 `设置应用时机表` / `是合法应用时机` |
| `settings/settings/src/types.ts` | 61–63 `SettingsPathOpView` | `{op:'set',path,value} \| {op:'unset',path}` | §3 `是路径操作` |
| `settings/settings/src/types.ts` | 66–73 `SettingsDescribeValue` | `writable`/`hasDocument`/`namespaces` | §3 `是描述值` |
| `settings/settings/src/types.ts` | 12 `JsonValue` | `null \| boolean \| number \| string \| [] \| {}` | §3 `是JSON值` |
| `skill/skill-badge/src/index.ts` | 17 `PROVIDER_NAME` | `'dsh-badge'` | §4 `徽章提供方名` |
| `skill/skill-badge/src/index.ts` | 23 `INVOCATION` | `{modelInvocable:true, userInvocable:true}` | §4 `徽章调用策略` |
| `skill/skill-badge/src/index.ts` | 24 `DESCRIPTION` | verbatim（含 U+201C/U+201D 弯引号） | §4 `徽章描述` |
| `skill/skill-badge/src/index.ts` | 19–22 `RESOURCE_BASE` | `{kind:'directory', path}` | §4 `是资源基` |
| `skill/skill-badge/src/index.ts` | 25–34 `CANDIDATE` | `name`/`description`/`invocation`/`provider`/`source`/`resourceBase`/`rank`/`locator` | §4 `造徽章候选` / `是徽章候选` |
| `skill/skill-badge/src/index.ts` | 30 `source: 'bundled'` / 32 `rank: BUNDLED_SKILL_RANK` | 来源与排名 | §4 `徽章来源` / `徽章排名`（600） |
| `skill/skill/src/index.ts:28 BUNDLED_SKILL_RANK` | 28 | 排名常量来源 | §4 `徽章排名` 注释锚点 |
| `preset/agent-presets/src/display.ts`（65 行） | — | `presetDisplayText` / `BUILT_IN_PRESET_KEYS` | **已覆盖 #72** `src/预设.light` → §5 只读回归 |
| `settings/settings/src/redact.ts`（109 行） | — | `redactSecrets` 走查 / 秘密位置 | **已覆盖** `src/设置.light` → §5 只读回归 |
| `skill/skill/src/index.ts`（869 行） | — | 技能名校验 / 渲染 / 候选校验 | **已覆盖** `src/技能清单.light` → §5 只读回归 |

---

## 二、实现要点

### §1 预设组合清单（`composition-inventory.ts`，L-129 命中点）
- `是合法启用值` 只接受**严格布尔**或 `"conditional"`（`0`/`1` 不算，靠 `是布尔值` 的类型判别，不用 `==`）。
- `禁用贡献` 逐句对照上游：`!!js` 节点（本模块以带标记字典 `{"js表达式": 文本}` 承载）→ 问 `求值能力`，**求值器拒绝（抛）→ `"conditional"`**；否则按 **JS 真值表** `布尔(value)`。
- `布尔` 显式实现 JS `Boolean(value)` 真值表：`空/0/0.0/空串/假` 判假；**空列表/空字典判真**（JS `Boolean([])===true`）——这就是 L-129 的绕法，直译上游 `Boolean(value)` 会静默翻转 `[]`/`{}`。
- `合并禁用` 三态优先级：`真` 优先 → `"conditional"` 次之 → 否则 `假`；`启用取值` 做三态反转（`真→假`、`"conditional"→"conditional"`、`假→真`），与上游 `flattenRows` 的三元表达式一致。
- `行标识`：`id` 非串或空串一律视作 `空`（null）（对齐上游 `typeof row.id === 'string' && row.id !== '' ? row.id : null`）。
- `展平行`：组行（`group === true`）**递归且继承外层 disabled**、自身不产出；叶子行产出 `造组合行`（`condition` 仅在 `!!js` 时落键，保键序）。
- `挂载行`：Loader 树项跳过组行，`enabled = 取反(disabled)`（**L-119：「非」为保留单字别名，故本地实现 `取反`**），`fiberState` 仅在存在 `fiber.state` 时落键。
- `是组合` 要求 `rows` 每行通过 `是组合行`。

### §1.6 预设行/名册/文档 + 远程错误码（`agent-presets/types.ts`）
- `是预设行`/`是预设名册`/`是预设文档` 逐字段形状判据；`isDefault`/`authorable` 用**严格布尔**（`是布尔值`），拒绝 `1`/`0`（**规避 L-129 的 `0==假`、`1==真` 陷阱**）。
- `预设远程错误码表` 4 条与上游 `RemoteErrorDetailsMap` 键逐条一致。

### §2 角色行（`persona/index.ts`）
- 段名常量 verbatim：`deployment:persona-prefix` / `deployment:persona-suffix`。
- `角色配置默认值(前缀)` → `{prefix, suffix:"", complete:假, includeRuntimeContext:真}`，与 schema `.default()` 逐值一致。
- `校验角色配置` 复刻 schema：`prefix` 必填且须字符串；`suffix`(串)/`complete`(布尔)/`includeRuntimeContext`(布尔) 三个可选字段类型受限，返回中文诊断。
- `段是否渲染(文本) = 字符串长度 > 0`，对齐「空前缀在渲染时丢弃该段」。

### §3 设置类型（`settings/types.ts`）
- `是JSON值` 递归覆盖 `空/布尔/整数/浮点/字符串/列表/字典`；**字典键须为字符串**（上游 `JsonValue` 对象分支即此约束，测试 3o 用非串键 `{1:2}` 拒绝）；`0` 必须判真（测试 3h 钉死，避免被 `假` 分支吞掉）。
- `是路径` = 字符串列表（空列表即 section 根）；`是根路径` = 长度 0。
- `是命名空间视图` 六必填 + `base?`/`user?` 可选；`applies`/`revision`/`ns` 强校验。
- `是路径操作` 按 `op` 分派：`set` 须带 `value` 且为 JSON 值；`unset` 只需 `path`；其余 op 拒绝。

### §4 技能徽章（`skill-badge/index.ts`）
- 常量 verbatim：`徽章提供方名="dsh-badge"`、`徽章来源="bundled"`、`徽章排名=600`（`BUNDLED_SKILL_RANK`，`skill/src/index.ts:28`）、`徽章描述`（含 U+201C/U+201D 弯引号，测试 4g 以子串钉死）。
- `造徽章候选` 按上游 `CANDIDATE` 键序构造（name/description/invocation/provider/source/resourceBase/rank/locator，**规避 L-116 键序对拍假红**）；宿主面事实（资源目录绝对路径 / 正文 URL）由调用方注入。
- `值是合法徽章名` 本地实现 kebab-case 规则（对齐 `skill` 包 `isSkillName`；**本地实现以规避跨模块同名段**）：非空、仅小写字母与单个连字符、不以连字符开头/结尾、无连续连字符。

### 本地工具
`字段齐备` / `是非负整数` / `是布尔值`（`type(值) == bool`） / `取反` —— 全部本地实现，规避跨模块同名段与保留字（L-119）。

---

## 三、验证结果

### 测试（150 断言，高于铁律 7 的「≥10」）
```
cd lightharness && python 运行.py examples/test_预设深化.light
===== 第 15 轮任务 5：preset 深化 + persona + settings 类型 + skill 徽章域（纯逻辑面）=====
test_预设深化 PASS
RC=0
```

### 反跑 3/3（`python _antirun_t5_预设深化.py`）
```
✓ A 布尔 退回 Python 真值 (判红运行 rc=1)
✓ B 合并禁用 丢条件分支 (判红运行 rc=1)
✓ C 徽章排名改错 (判红运行 rc=1)
✓ 字节级恢复校验 (sha256 c4d83f887e53)
✓ 恢复后回归绿 (rc=0，PASS 已打印)
ALL OK
```
- **A**：`布尔` 实现换成 Python 原生真值（`如果 值: 返回 真`）→ 空列表/空字典判假 → 1k/1l/1s 红（与 1m 的 `0 == 假` 判据共同锁定 L-129 的两面）。
- **B**：`合并禁用` 删去两条 `== "conditional"` 分支 → 条件态丢失 → 1z/1A 红。
- **C**：`徽章排名` `返回 600` → `返回 601` → 4c/4t 红。
- 三判据均**真变异立红**，恢复走 `finally` 并做逐字节 sha256 校验。

### 复现
```
python 运行.py examples/_repro_L129.light   → RC=0
```

---

## 四、语言缺陷登记

### L-129（新增）条件真值沿用 Python 语义，与 JS `Boolean()` 不一致；且 `==` 混同 `0/假`、`1/真`
- **证据（两面同根）**：
  - ① 条件真值：`如果 空列表:` / `如果 空字典:` 判**假**（JS `Boolean([])`/`Boolean({})` 均为**真**）；内建 `布尔(空字典)` 亦返回 False。
  - ② 相等语义：`0 == 假` 为真、`1 == 真` 为真（JS `0 === false` 为假、`true === 1` 为假）——故**不能用 `== 真/假` 判布尔**，必须用类型判别（`type(值) == bool`）。
- **触发面**：上游 `composition-inventory.ts:83·90` 的 `Boolean(value)`（组合行 `disabled` 节点真值判定）直译会静默翻转 `[]`/`{}` 两种取值；任何 `f(x) === false` 风格的 JS 布尔严格比较同样命中。
- **绕法**：显式实现 JS `Boolean(value)` 真值表（`布尔`）；布尔判别一律 `type(值) == bool`。
- **复现**：`examples/_repro_L129.light`（含前提断言：若空列表/空字典已判真、或 `0 == 假` 不再成立，则主动报错复核）。

> **L-129 为本任务唯一预分配编号**（任务书「缺陷编号预分配：L-129」）。本路未再发现其他独立缺陷；**L-130 留待任务6**（任务书标注任务6 预分配 L-130）。

---

## 五、上游面剔除与偏差登记

| 上游面 | 处置 | 理由 |
|---|---|---|
| `agent-presets/display.ts`（65 行） | **剔除** | **已覆盖 #72** `src/预设.light`（`造显示文本`/`行启用`/内置预设文案） |
| `agent-presets/` 的 specifier/preset/metadata/session/discovery/mount/authoring | **剔除** | **已覆盖 #72** |
| `agent-presets/index.ts` / `invariant.ts` | **剔除** | 装配面 / Cordis 不变量安装器（宿主面） |
| `settings/settings/src/redact.ts`（109 行） | **剔除** | **已覆盖** `src/设置.light`（`脱敏值`/走查） |
| `settings/index.ts` / `invariant.ts` / `settings-file/` | **剔除** | 装配面 / 不变量安装器 / 文件持久化（宿主面） |
| `skill/skill/src/index.ts`（869 行） | **剔除** | **已覆盖** `src/技能清单.light`（`是技能名` 等） |
| `skill/skill-filesystem/` / `tool-skill/` | **剔除** | 文件系统 watcher / 工具定义（宿主面） |
| `composition-inventory.ts` 的 `readFile`/`js-yaml load`/`entryListProblem` 解析链 | **剔除** | 宿主 IO 与 Loader 方言解析；本模块只做「解析后的行列表 → 展平」纯逻辑 |
| `skill-badge/index.ts` 的 `provider.get()`（读正文文件）与 `ctx.skills.registerProvider` | **剔除** | 宿主 IO 与 Cordis 装配；本模块只做候选描述符的纯逻辑构造与判据 |
| `Branded<'...'>` / `z.ZodType` / `FiberState` 类型品牌 | **简化** | 光明无类型品牌机制；保留同一性语义与字段域判据 |
| `值是合法徽章名`（kebab-case） | **本地实现** | 上游复用 `skill` 包 `isSkillName`；为规避跨模块同名段而本地重写，语义对齐 |
| 徽章名/技能名校验 | **加强（本研究新增）** | 上游 `SkillCandidate.name` 无独立校验函数；按上游 kebab-case 规则补可测判据 |

---

## 六、待路M裁定 / 移交清单

1. **对标卡 #102**：本路新增，建议登记为「agent-presets(composition-inventory/types) + persona/index + settings/types + skill-badge/index 纯逻辑面」，并注明 `display.ts`→#72、`redact.ts`→`设置.light`、`skill/src/index.ts`→`技能清单.light` 三面已覆盖，避免边界被误读为重复。
2. **行为差异 R15-D5**：建议记录两条 ——（a）`禁用贡献` 的 `!!js` 节点在光明以带标记字典 `{"js表达式": 文本}` 承载，宿主求值能力以函数形参注入（等价上游 `isJsExpr` + evaluator）；（b）徽章名 kebab-case 判据为本研究加强项（上游无独立校验函数）。
3. **常量锚点**：`PERSONA_PREFIX_SECTION` / `PERSONA_SUFFIX_SECTION` 来自 `dsh-system-prompt`，`BUNDLED_SKILL_RANK=600` 来自 `skill/src/index.ts:28`——两者本路均已本地落常量并注释来源，供后续跨模块引用。
4. **文档/上游版本差异**：任务书头部标注上游 `a305303422`，本地工作副本 HEAD 为 `9d9035b7c1`。本路以**目录布局与文件内容**为对齐依据（任务书列出的 composition-inventory/display/types/persona/settings(redact,types)/skill(index)/skill-badge 全部存在且语义吻合），未发现内容漂移；如路M有权威 pin，请以 pin 复核。
5. **未移植项**（供 #102 备注）：composition 文件解析与 Loader 求值、settings 的 Remote 视图装配与持久化、skill 注册表服务、skill-badge 的正文读取与 provider 注册。
6. **L-130 归属**：本任务只预分配 L-129（已占用）；L-130 属任务6（见任务书 §任务6 标注），本路未占用。
