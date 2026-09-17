# 第52轮 任务1 交付报告 —— workflow-ptc meta(validateMeta) + realm(materializeFromRealm) 纯逻辑

> 日期：2026-09-17 ｜ 优先级：P1 ｜ 跨项目：lightharness
> 上游基线：deepseek-harness 0.1.6-alpha.1（gitea fork master `c47b24803e`）
> 验收：`examples/test_R52_workflow_ptc.light` 本机 `rc=0`

## 1. 范围与上游依据

对齐 `packages/workflow/workflow-ptc` 的纯逻辑面：

| 上游文件 | 对齐内容 | 落点 |
|---|---|---|
| `meta.ts` | `validateMeta(value): WorkflowMeta` | `src/工作流错误.light :: validateMeta` + `校验元形状` |
| `realm.ts` | `materializeFromRealm` / `MaterializeError` / `renderThrown` | `src/工作流错误.light :: 物化自域 / 建立物化错误 / 渲染抛出` |

只读复刻，纯函数化；**未改动** #41 已做的 `建立工作流错误` / `判定致命工作流错误` / `已知工作流错误码` / `渲染监听错误`。

## 2. 改动文件

### 2.1 `src/工作流错误.light`（修改，增量追加 R52 任务1 段）
新增段落：
- `是数`：等价 `isNumber`（排除 bool）——`是整数(值) 或 是浮点(值)`。
- `建立物化错误(路径, 原因)`：以 `{"名":"MaterializeError","路径","原因"}` 标记建模 host 不可伪造语义。
- `渲染抛出(错误)`：`renderThrown` 等价——优先 `消息(字典)` → `字符串(标量)` → `转字符串(对象)`，全程 `尝试/捕获` 绝不向上抛（total）。
- `校验元形状(元)`：`validateMetaShape` 等价——逐字段校验 `name`(非空串)/`description`(非空串)/`whenToUse?`(串)/`phases?`(数组，每项 `title`(非空串)+可选 `detail`/`provider`/`model` 串)；未知字段、类型错逐条命名累加；全部通过则构建归一化 `元`（不别名调用方）。
- `validateMeta(值)`：无 `元` 则抛 `建立工作流错误("invalid meta: " + 连接文本(违规,"; "), "META_INVALID", 真)`；否则返回归一化副本。
- `连接文本(表, 分隔)`：`Array.join` 等价（避开未知内置）。
- `物化自域(值, 根)`：根 `空`(null) 原样返回；其余走 `物化`，`MaterializeError` 原样重抛，其余异常包成 `建立物化错误(根, "reading the value threw: " + 渲染抛出(...))`。
- `物化(值, 路径, 已见)`：按类型分流 bool/string/数(非有限→拒)/字典/列表/空；函数及其他非 JSON 值统一抛 `functions are not plain JSON data`。
- `物化数组` / `物化对象`：深拷贝，用 `id(值)` 做循环引用检测（等价上游 `seen` Set）；含 `已见` 进出栈（弹出尾部）。

### 2.2 `examples/test_R52_workflow_ptc.light`（新增）
§1 `validateMeta` 合法（完整/最小/空phases/仅标题phase）
§2 `validateMeta` 非法形状逐条命名（2a–2l：非对象/数组非对象/未知字段/空name/缺description/when类型错/phases非数组/phase非对象/phase未知字段/phase空title/phase detail类型错/phase model类型错）
§3 `materializeFromRealm` 深拷贝独立性（标量/嵌套字典/嵌套列表/深结构）
§4 根 null 原样返回
§5 非有限数拒绝 → `MaterializeError`
§6 函数拒绝 → `MaterializeError`
§7 循环引用拒绝（含嵌套循环）→ `MaterializeError`
§8 `renderThrown` total（字典消息/字符串/异常对象）
§9 归一化副本不别名调用方

**反跑判据**：把任一 `断言相等` 期望改反即红；把归一化字段改错即红。

## 3. 关键实现决策（语言层等价建模）

| 上游 JS 概念 | 本复刻建模 |
|---|---|
| `host instanceof WorkflowError` 不可伪造 | `名` 标记 + `致命` 标志（字典） |
| `MaterializeError` 子类 | `{"名":"MaterializeError",...}` 标记 |
| `renderThrown` 优先 stack→message→String | 消息(字典)→字符串→转字符串，try/catch 兜底 `[unrenderable thrown value]` |
| 原型链 / 符号键 / 稀疏数组 / bigint / undefined | 光明无对应概念 → plain 判定恒真、空(null)即合法 JSON、不可物化值统一按「函数非纯 JSON」拒绝 |
| `seen` Set 循环检测 | `id(值)` 表（光明对象 `id` 稳定） |
| 归一化返回不别名调用方 | 深拷贝构建新字典/列表 |

## 4. 修复记录（调试期）

1. **缺键访问崩溃**：`校验元形状` 原直接 `记录["description"]` / `阶段项["title"]`，对缺 `description` 或 `title` 的非法输入会触发缺键 `KeyError` 而非抛出 `META_INVALID`，进而被 `校验抛META` 捕成字符串使 `错误体["名"]` 断言崩溃。改为 `字典包含键` 先判再访问（与文件头「顺序 如果 规避 且/或 链」一致）。
2. **列表字面量误用**：测试 §2b 曾误写 `["x","y"]` 当对象、§2h 误写 `["t"]` 当对象，导致 `validateMeta` 不抛；已改为合法列表 `["x","y"]` / `["t"]`。
3. **`列表设置` 不存在**：测试 §3 深拷贝独立性用 `列表设置` 改列表元素，但 harness stdlib 无该内置；改用 `列表弹出`+`列表插入` 做原地变异以验证深拷贝独立。
4. **`新建 错误` 不存在**：断言辅助与异常构造改用直接字符串 `抛出`，§8c 改由 `尝试/捕获` 取得真实异常对象传给 `渲染抛出`。

## 5. 运行

```bash
cd lightharness
../light-merge/.venv/Scripts/python.exe 运行.py examples/test_R52_workflow_ptc.light
# 期望输出：--- R52 任务1 workflow-ptc meta+realm 纯逻辑测试通过 ---
```

## 6. 上游增量登记

- 对标清单条目：**#188 workflow-ptc**（纯逻辑 meta+realm 已覆盖；上游 `meta.ts` 尚有 `validateMetaShape` 之外的 `MetaIssue`/`renderMeta` 展示面，属 harness UI 层，本仓未覆盖，登记待补）。
