# T10-05 · 工具执行流水线深对齐 —— 交付报告

> 仓库：`g:\dswork\duan-light-merge\lightharness`（独立 git 仓库）
> 任务书：`light-merge/任务书/任务T10_05_工具流水线深对齐.md`
> 运行：`python 运行.py examples/xxx.light`
> 日期：2026-08-27

## 1. 改了哪些文件（逐个 + 一句意图）

| 文件 | 动作 | 意图 |
|---|---|---|
| `src/工具.light` | 修改（本任务独占） | 新增 JSON Schema 校验器 `校验参数(模式,参数)`（列表路径错误）；`执行` 内接入 `准备→校验→派发→收尾` 三阶段流水线；`造工具定义` 加 `准备`/`收尾` 可选钩子；**返回结构不变**。 |
| `examples/test_工具深.light` | 新建 | 任务书 §4 验收：嵌套 schema 通过、缺必填→isError+列表路径+missing、type/enum/pattern/数字范围、prepare/finalize 顺序与改参、不回归。 |
| `docs/功能对标/对标清单.json` | 修改 | 条目 8 加深证据：补 test_工具深.light、加深目标描述、反跑判据、语言缺陷 L-013/L-014。 |
| `docs/功能对标/语言缺陷账.md` | 修改 | 新增 L-013（单行 for 循环坑）、L-014（语句级下标调用坑）。 |
| `src/工具.light` | 修改（追加对齐） | 补齐原版强制子集缺口：`oneOf`（精确匹配一个）、`additionalProperties:false`（拒绝未声明键）、`type:null` + `enum`/`const` 支持 null；`enum`/`const` 改为 type-gated（仅 type 匹配时校验，对齐原版短路语义）。 |
| `examples/test_工具深.light` | 修改（追加） | 新增 §4.6 覆盖 oneOf / additionalProperties:false / type:null 对齐点。 |

## 2. 定向测试结果（输出落盘 `_taskT10_05_*`）

| 测试 | 命令 | 结果 |
|---|---|---|
| 基础注册表 | `python 运行.py examples/test_工具.light` | ✅ 通过（EXIT=0，输出「工具注册表测试通过」）→ `_taskT10_05_test_工具.txt` |
| 深对齐验收 | `python 运行.py examples/test_工具深.light` | ✅ 通过（EXIT=0，输出「test_工具深 通过」）→ `_taskT10_05_test_工具深.txt` |
| 并行不回归 | `python 运行.py examples/test_并行.light` | ✅ 通过（EXIT=0）→ `_taskT10_05_test_并行.txt` |

校验器实测覆盖：嵌套 object + 数组 item 合法通过；`["参数","秒"]` 列表路径 + `missing`/`type`/`enum`/`pattern`/`minimum`/`maximum` 原因均正确定位。

## 3. 反跑判据验证

| 判据（任务书 §4） | 翻转方式 | 结果 |
|---|---|---|
| §4.2 校验失败→isError | `结果2["isError"]` 断言 `真` 改 `假` | ❌ 立红（EXIT=1） |
| §4.4 prepare 计数 | `计数["准备"]` 断言 `1` 改 `0` | ❌ 立红（EXIT=1） |
| §4.3 原因 type/enum/pattern | 改为非对应原因值 | ❌ 立红（代码内已含静态断言，逻辑可逆） |

→ 反跑判据全部成立，校验逻辑非「假绿」。

| 判据（任务书 §4.6 追加） | 翻转方式 | 结果 |
|---|---|---|
| §4.6 oneOf 精确匹配 | `长(oneOf错2)` 断言 `1` 改 `0` | ❌ 立红（EXIT=1） |
| §4.6 additionalProperties | `长(闭错)` 断言 `1` 改 `0` | ❌ 立红（EXIT=1） |

## 4. JSON Schema 对齐边界澄清（重要更正）

### 4.1 原版真实范围：强制子集仅 8 关键字
原版 `packages/core/tools/src/json-schema.ts` 的 `assertSupportedJsonSchema` 只接受如下**强制子集**（CONSTRAINT_KEYWORDS）：`type` / `oneOf` / `properties` / `required` / `additionalProperties`(仅布尔) / `items` / `enum` / `const`；外加 `type:null`（`JsonSchemaScalar` 含 null）。其余如 `allOf`/`anyOf`/`not`/`$ref`/`pattern`/`minimum`/`maximum`/`format`/`multipleOf`/`uniqueItems` 等**原版会主动拒绝**（判为 violation），并非「未实现」。

### 4.2 本轮已对齐（原版子集缺口已补）
- ✅ `oneOf`：精确匹配一个分支（命中数 ≠ 1 即报错；含「命中两分支」精确匹配判据）。
- ✅ `additionalProperties: false`：拒绝未声明键，错误路径 `["参数", <键>]`、原因 `additionalProperties`。
- ✅ `type: null`：值须为 null（光明 `空`）。
- ✅ `enum`/`const` 支持 null 值（对齐 `JsonSchemaScalar`）。
- ✅ `enum`/`const` 改为 **type-gated**：仅当 `type` 匹配时才校验（对齐原版 `checkScalarValue` 短路语义，避免 type+enum 同时不匹配时叠加双错误）。

### 4.3 宽松超集扩展（原版不支持，但保留，因工具参数校验有用且不破坏既有测试）
`pattern` / `minimum` / `maximum` / `minLength` / `maxLength` / `minItems` / `maxItems`。原版 `assertSupportedJsonSchema` 会拒绝这些关键字；光明版作为超集**宽松接受并校验**。如需严格对齐原版（拒绝这些关键字），需在 `校验参数` 入口加 schema 合法性检查——本任务未做（避免破坏既有测试），列为后续可选。

### 4.4 仍未对齐（属「完整 JSON Schema」，原版亦不支持，故非对齐目标）
`allOf`/`anyOf`/`not`/`$ref`/`definitions`/`patternProperties`/`minProperties`/`maxProperties`/`uniqueItems`/`contains`/`format`/`multipleOf`/`dependentRequired` 等。任务书 §6 原「未覆盖边界」清单按「完整 JSON Schema」列出，属**偏离原版的误导向清单**；对齐原版无需实现它们。

## 5. 红线保持

- `执行` 返回结构严格保持 `{content, isError, concludesTurn, additionalContexts, error}` 五字段；仅在**校验失败**时于 `error` 内补 `字段错误` 列表（`[{"路径":[...], "原因":"...", "细节":"..."}]`），不改任何其他字段。
- 只读文件 `代理.light` / `消息.light` / `流.light` 未改动；并行/分组执行策略不受影响（test_并行 仍绿）。

## 6. 本轮新发现的光明语言缺陷（已登记缺陷账）

- **L-013（最高优先级，编译器级）**：**绝不要写单行 `遍历 X 之 Y: 语句`**。SRC 后端（导入钩子用的 `code_generator.py`）不闭合单行 for 循环，会把后续所有语句乃至下一个顶层类全部吸进循环体，导致类错位嵌套、下游 `从 工具 导入 X` 报 `cannot import name`。**绕法：for/while/if 的体一律换行缩进**。
- **L-014**：不要把 `字典["键"](参数)` 当语句（或表达式）直接调用——统一后端代码生成器不识别 `FunctionCallExpr` 节点，报「未知语句类型」。**绕法：先 `设 函数 为 字典["键"]` 取出，再 `函数(参数)`**（Name 调用两端后端均支持）。
- 注：`属性 X 等于 空` 类成员声明、默认参数、`type(值)==dict` 类型判断、`re.search`、列表路径 `["参数","秒"]` 均验证可用。

## 7. 复刻 Harness 驱动 light 升级提示

T10-05 暴露的两个缺陷（L-013 单行循环、L-014 下标调用）均为「光明写得出但编译/生成错位」的硬坑，建议在 light 语言侧优先修复：
1. 解析器对单行控制结构正确闭合（对齐 Python `for x in y: stmt`）；
2. 代码生成器补齐 `FunctionCallExpr`（下标结果再调用）的语句/表达式处理。
修复后，段言/Harness 复刻中大量「拆行」「先取变量」的绕法可整体回收，可读性显著提升。
