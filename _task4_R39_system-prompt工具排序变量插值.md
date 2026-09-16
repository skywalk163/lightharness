# 第 39 轮 任务 4 交付报告 —— system-prompt 工具排序 + 变量插值 + 节顺序常量

> 日期：2026-09-16 ｜ 方向：上游复刻——@deepseek-ai/dsh-system-prompt 的 orderTools / renderPrompt / SECTION_ORDERS
> 上游基线：deepseek-harness 0.1.5-rc.2
> 上游源码：`packages/core/system-prompt/src/index.ts`（工具排序/变量插值/常量部分）
> 交付物：`src/系统提示.light`（工具排序/变量插值/常量部分，与任务 3 合并写同一文件）、`examples/test_R39_系统提示工具排序变量插值.light`（单元测试，rc=0）

---

## 一、上游源码精读

| 关键点 | 上游实现 | 语义 |
|---|---|---|
| `SECTION_ORDERS` | 30+ 位置常量字典 | 从 -1000 到 10200 的节顺序定位 |
| `CONTEXT_ORDERS` | `{SANDBOX_POLICY: 110, APPROVAL_POLICY: 115, SUBAGENT_DELEGATION: 120}` | 3 个上下文位置 |
| `TOOL_ORDER_REST` | `'<unlisted-tools>'` | 未列出工具标记 |
| `PERSONA_PREFIX_SECTION` | `'deployment:persona-prefix'` | 部署角色前缀节名 |
| `PERSONA_SUFFIX_SECTION` | `'deployment:persona-suffix'` | 部署角色后缀节名 |
| `VARIABLE_NAME` | `/^[a-z][a-z0-9_]*$/` | 变量名合法性正则 |
| `GROUP_AT` | `/^\{\{([^{}]*)\}\}/` | 变量引用匹配 |
| `validateToolOrder(toolOrder)` | 空→未配置；重复名抛错；必须含 REST | 严格 |
| `orderTools(tools, toolOrder, knownNames)` | 保留名检查；无配置→字典序；有配置→按顺序 + REST 位置插入未列出（字典序） | 未知配置名抛错 |
| `renderPrompt(assembly)` | 扫描 `{{variable}}`；替换变量表值；未知保留原样 | 合法/未知/非法三态 |

**关键设计**：
1. `SECTION_ORDERS` 定义从 -1000（HARNESS_IDENTITY，最早）到 10200（DEPLOYMENT_PERSONA_SUFFIX，最晚）的完整节位置布局。
2. `orderTools` 的核心：未列出工具落在 REST 位置，按 name 字典序插入；REST 位置本身按字典序处理已列出的位置。
3. `renderPrompt` 未知变量保留原样（不抛错）——变量可能后续才注册。
4. `VARIABLE_NAME` 严格小写字母开头，其余小写字母/数字/下划线。

---

## 二、光明适配设计

**模块名**：与任务 3 合并到 `src/系统提示.light`（分工边界：任务 3 写注册表/组装/瀑布流，任务 4 写工具排序/变量插值/常量）。

**分工边界**：
- 任务 3：§4 注册表构造+撤销、§5 排序+文本解析+complete+瀑布流、§6 导出。
- 任务 4：§0 常量、§1 变量名/引用校验、§2 工具排序、§3 变量插值渲染。

**导出（任务 4 部分，14 项）**：
1. `节顺序常量表`（30+ 位置字典）
2. `上下文顺序常量表`（3 个位置）
3. `工具排序未列出标记`（`'<unlisted-tools>'`）
4. `部署角色前缀节名`（`'deployment:persona-prefix'`）
5. `部署角色后缀节名`（`'deployment:persona-suffix'`）
6. `变量名合法字符集`（`'abcdefghijklmnopqrstuvwxyz0123456789_'`，37 字符）
7. `校验变量名(名字)` —— 对齐 VARIABLE_NAME
8. `扫描变量引用(文本)` —— 返回引用列表
9. `比较工具名字(名字甲, 名字乙)` —— -1/0/1
10. `校验工具排序(排序配置)` —— 重复名抛错 / 缺 REST 抛错
11. `排序工具(工具表, 排序配置=空, 已知名字=空)` —— 核心 orderTools
12. `插值(文本, 变量表)` —— `{{name}}` 替换
13. `渲染提示(组装结果)` —— 节文本按变量表插值
14. `渲染上下文快照(组装结果)` —— 上下文节按变量表插值 + 头部

**光明适配点**：
1. **无原生正则**：`VARIABLE_NAME` 和 `GROUP_AT` 用 `字符串.查找` + 字符集 `包含` 手动实现。
2. **无 `Array.includes`**：用 `值在` 辅助函数遍历列表。
3. **无 `Array.sort` 稳定保证**：用「选择排序 + 比较器」自实现 `排序按`，语义等价。

---

## 三、实现细节

### 3.1 SECTION_ORDERS 完整常量（30+ 位置）
- HARNESS_IDENTITY=-1000 → DEPLOYMENT_PERSONA_SUFFIX=10200，全部 31 个位置齐全。
- 单调递增：HARNESS_IDENTITY < DEPLOYMENT_PERSONA_PREFIX < PLAN_POLICY < ... < DEPLOYMENT_PERSONA_SUFFIX。
- 上下文顺序：SANDBOX_POLICY=110 < APPROVAL_POLICY=115 < SUBAGENT_DELEGATION=120。

### 3.2 `校验工具排序`（对齐 `validateToolOrder`）
- 空（`None`/`空`）→ 视为未配置，返回 `空`。
- 重复名 → 抛错 `DUPLICATE_TOOL_ORDER`。
- 缺 REST → 抛错 `MISSING_REST`。

### 3.3 `排序工具`（对齐 `orderTools`）
1. 保留名检查：工具名不能是 `<unlisted-tools>`，否则抛错 `RESERVED_TOOL_NAME`。
2. 无 toolOrder（空）→ 按 name 字典序排序。
3. 有 toolOrder → 先 `校验工具排序` 校验。
4. 已知名字检查：toolOrder 中除 REST 外的名字必须存在于工具表（否则抛错 `UNREGISTERED_TOOL`）。
5. 未列出工具收集到 `休息` 列表，按字典序排序。
6. 按 toolOrder 顺序输出：REST 位置展开 `休息`，其它位置从工具表匹配。

### 3.4 `校验变量名`（对齐 `VARIABLE_NAME`）
- 空字符串 → 假。
- 首字符必须是小写字母（a-z）。
- 其余字符必须在小写字母/数字/下划线字符集内。

### 3.5 `扫描变量引用`（对齐 `GROUP_AT`）
- 逐字符扫描 `{{` 起始位置。
- 查找匹配的 `}}` 结束位置。
- 内层不得含 `{` 或 `}`（残缺的 `{{` 无 `}}` 时不匹配，也不抛错）。
- 返回 `[{名字, 起始, 结束}, ...]`。

### 3.6 `插值`（对齐 `renderPrompt` 的变量替换）
- 逐字符扫描 `{{...}}` 引用。
- 内层含 `{`/`}` → 抛错 `MALFORMED_VARIABLE_REF`。
- 变量名不合法（不符合 `VARIABLE_NAME`）→ 抛错 `INVALID_VARIABLE_NAME`。
- 变量名合法但不在变量表 → **保留原样**（不抛错）。
- 变量名合法且存在 → 替换为变量表值（空值也保留原样）。
- 非字符串值自动 `转字符串`。

### 3.7 `渲染提示`
- 遍历 `组装结果["节列表"]`。
- 每节调用 `插值` 变量替换。
- 非空节用 `\n\n` 拼接。
- `渲染上下文快照` 同上，头部固定为 `"Current runtime context. This snapshot supersedes earlier runtime-context snapshots.\n\n"`。

---

## 四、单元测试覆盖（examples/test_R39_系统提示工具排序变量插值.light，rc=0，19 组）

| 编号 | 覆盖点 |
|---|---|
| #00 | 断言助手自检 |
| #01 | 节顺序常量完整性（31 个位置全部匹配 + 单调递增） |
| #02 | 上下文顺序常量（3 个位置 + 单调递增） |
| #03 | 工具排序未列出标记 + 部署角色前后缀常量 |
| #04 | 工具排序：无配置按字典序（含空列表） |
| #05 | 工具排序：有配置按配置顺序 |
| #06 | 工具排序：未列出工具在 REST 位置（REST 开头/中间两种） |
| #07 | 工具排序：未知配置名抛错 |
| #08 | 工具排序：重复名抛错 / 缺 REST 抛错 / 保留名工具抛错 |
| #09 | 变量插值：简单替换 |
| #10 | 变量插值：多个变量（含同一变量多次引用） |
| #11 | 变量插值：未知变量保留原样（含空变量表/无引用/空文本） |
| #12 | 变量插值：非法引用抛错（大写名/内嵌 {} / 空名） |
| #13 | 变量名校验：合法（含下划线/数字）+ 非法（大写/数字开头/下划线开头/空/空格/连字符） |
| #14 | 扫描变量引用：合法引用/无引用/未闭合/内嵌 {} |
| #15 | 比较工具名字：字典序 -1/0/1 |
| #16 | 渲染提示：手动组装结果 |
| #17 | 端到端：注册变量+节 → 组装 → 渲染 |
| #18 | 变量名合法字符集完整性（37 字符 + 边界） |

**运行命令**：
```
cd lightharness && python 运行.py examples/test_R39_系统提示工具排序变量插值.light
```

**运行结果**：
```
OK #00
OK #01
OK #02
OK #03
OK #04
OK #04b
OK #05
OK #06
OK #06c
OK #07
OK #08
OK #08b-08d
OK #08e
OK #09
OK #10
OK #11
OK #11c
OK #11d-11e
OK #12
OK #13
OK #14
OK #15
OK #16
OK #17
OK #18
系统提示工具排序变量插值 判据通过：19 组
```

---

## 五、铁律合规检查

- ✅ **与任务 3 合并到同一文件**：分工边界清晰（§0–§3 任务 4，§4–§6 任务 3），路 M 合并检查无冲突。
- ✅ **SECTION_ORDERS 完整复刻 30+ 位置**：31 个位置全部到位，#01 逐项验证。
- ✅ **orderTools 严格**：未知配置名抛错（#07），未列出工具在 REST 位置按字典序插入（#06），无配置字典序（#04）。
- ✅ **validateToolOrder 严格**：重复名抛错 / 缺 REST 抛错（#08），保留名工具抛错（#08e）。
- ✅ **变量名符合规则**：小写字母开头 + 小写字母数字下划线（#13 边界全覆盖）。
- ✅ **未知变量保留原样**：#11 明确验证（不抛错）。
- ✅ **测试用例 rc=0**：`python 运行.py examples/test_R39_系统提示工具排序变量插值.light` → EXIT=0。

---

## 六、光明适配差异（记录在案）

| 上游 | 光明适配 | 差异影响 |
|---|---|---|
| `/^[a-z][a-z0-9_]*$/` | 字符集 + 手动循环 | 语义等价 |
| `/^\{\{([^{}]*)\}\}/` | `字符串.查找` + 手动扫描 | 语义等价 |
| `Array.includes` | `值在` 辅助函数 | 语义等价 |
| `Array.sort` 稳定排序 | 选择排序 + 比较器 | 稳定但 O(n²)；本轮工具数少无性能影响 |
| 内嵌 `{}` 的引用：正则拒绝 | 手动扫描：内嵌 `{}` 时不匹配、`插值` 阶段抛错 | 语义等价 |

---

## 七、Bug 修复记录（本轮发现并修复）

- **变量名遮蔽**：`扫描变量引用` 中 `设 名 为 文本[...]` 后 `当 j < 长(名)` 触发 `int not callable`。原因：Light 变量遮蔽 —— `设 长 为 长(文本)` 已把 `长` 转成 int。修复：把外层 `长` 改名为 `文本长`，内层用 `内文`/`内文长`。
- **测试标签重复**：#06c 曾被误标为 #06，已修正。
- **部署角色后缀节名大小写**：测试期望值从 `"deployment:persona suffix"` 修正为 `"deployment:persona-suffix"`（对齐上游常量）。

---

## 八、遗留项 / 与任务 5 接口

- **任务 5 集成测试接口**：本模块导出 `节顺序常量表`、`上下文顺序常量表`、`排序工具`、`校验工具排序`、`渲染提示`、`插值`、`校验变量名`，供 scope+system-prompt 联动的集成测试使用。
- **agent-default-model 联动（R37）**：默认模型配置可注册为系统提示上下文节，走 `CONTEXT_ORDERS.SANDBOX_POLICY/APPROVAL_POLICY` 位置。
- **变量插值安全边界**：非法引用（内嵌 `{}`/大写名/空名）会抛错，这是上游行为；调用方需保证变量名合法（`校验变量名` 已在 `注册变量` 时调用）。
