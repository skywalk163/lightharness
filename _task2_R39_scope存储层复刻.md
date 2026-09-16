# 第 39 轮 任务 2 交付报告 —— scope 存储层复刻（NamedEntries / AnonymousEntries / ScopedLayers）

> 日期：2026-09-16 ｜ 方向：上游复刻 —— `@deepseek-ai/dsh-scope` 存储层
> 上游基线：deepseek-harness 0.1.5-rc.2
> 上游源码：`G:\github\deepseek-harness\packages\core\scope\src\store.ts`（267 行，全文精读）
> 上游用例：`packages/core/scope/tests/store.spec.ts`（8 用例）
> 交付物：`src/作用域.light`（**§6–§7 为本任务**，与任务1 合并同一文件）、
>         `examples/test_R39_作用域存储.light`（单元测试，**rc=0**）

> 分工边界（任务书 §通用约束 11）：任务1 写 §1–§5（作用域键/父链/循环检测/上下文/载体/准入），
> 任务2 写 §6–§7（三个存储层类）。本次由同一执行者顺序落盘，**不存在两路并行改同一文件的冲突**。
> 文件级 sha256：`6275f7bbc7d8aecc6db27df041ce334f5c694b21fe54b301c5f5993770bb66dc`（745 行）。

---

## 一、上游源码精读（store.ts 267 行）

### 1.1 `class NamedEntries<V>`（L30–105）

| 上游 | 语义要点 |
|---|---|
| `private data = new Map<string, V>()` | **插入有序**（Map 迭代序 = 插入序） |
| `constructor(private readonly duplicateError: (name) => Error)` | **重复诊断由调用方拥有**，本类只负责触发 |
| `insert(name, value)` | 重复名 → `throw this.duplicateError(name)`；成功 → 返回**只删这一次插入**的幂等 undo |
| undo 体 | `if (!active) return; active = false; data.delete(name); if (data.size === 0 && this.data === data) this.data = new Map()` |
| 空表优化 | 排空时**换新 Map** ⇒ 之前抓到的迭代器与后续插入**脱钩**（`drain detaches iterators`） |
| `get` / `has` / `keys` / `entries` / `values` / `isEmpty` | 直通 Map |

### 1.2 `class AnonymousEntries<V>`（L114–150）

- 内部 `Map<symbol, V>`：**等值条目的注册身份彼此独立**（同值 append 两次 = 两条）。
- `append(value)` 返回同构的幂等 undo；同样有**排空换新 Map** 的代数语义。
- 只有 `values()` / `isEmpty()`（上游**无** `has`）。

### 1.3 `class ScopedLayers<L extends ScopeLayer>`（L159–267）

| 成员 | 语义要点 |
|---|---|
| `readonly global: L` | **构造时立即创建**全局层 |
| `constructor(createLayer, onChange)` | 建层器 + 变更通知器（均由调用方注入） |
| `peek(scope)` | **读不建层**；`undefined` scope ⇒ `undefined`。刻意「chain-blind」：只给精确作用域自己的贡献 |
| `chainLayers(scope)` | 沿 `scopeChainOf(scope).reverse()`：**最远祖先在前、精确作用域在最后**（调用方按序叠加 ⇒ 最近作用域最终拍板） |
| `merge(scope, pick)` | 先全局、再链上遮蔽：`new Map(global.entries())` 后逐层 `set` ⇒ **同名最近覆盖，且保留首次插入位置** |
| `effect(ctx, action, options)` | 用 `ctx.effect(generator, label)`：scope 由 `scopeOf(ctx)` 决定；**工厂抛错则不留层**；动作抛错时「新建且为空」才回收；yield 的注销器 = `undo(); 若作用域层空则回收; 通知`；**通知抛错由 cordis 回滚**（先通知 → 抛 → 触发注销器 `undo` → 通知） |
| 回收条件 | **只回收「完全空」的聚合层**（`layer.isEmpty()`） |

---

## 二、光明适配设计（§6–§7）

### 2.1 类型对照

| 上游 | 光明 |
|---|---|
| `Map<string, V> data` | 类成员 `数据` = `{}`（Python dict，保留插入序） |
| `Map<symbol, V>` | 类成员 `数据` = `{ "匿名N": V }`（自增符号ID 作键） |
| `entry.values()` 活迭代器 | 成员 `代数`（generation）+ `游标()` 返回 `{"数据": <字典引用>, "位置": 0}` + 段落 `推进游标(游标)` |
| `() => void` undo | 句柄字典 `{"活跃": 真, …}` + 段落 `注销命名条目` / `注销匿名条目` |
| `ScopeLayer.isEmpty()` | 类 `简单作用域层` 的方法 `为空()`；判定契约：**必须实现 `为空()`** |
| `createLayer` / `onChange` | 构造参数 `建层器实参` / `变更器实参`（段落值）；缺省由 `造作用域层组()` 注入 `建标准层` / `空变更` |

### 2.2 导出清单（§6–§7，任务2 部分共 13 项）

| 分组 | 导出 | 上游对应 |
|---|---|---|
| §6 条目表 | `命名条目表` `注销命名条目` | `NamedEntries` / `insert` 的 undo |
| §6 条目表 | `匿名条目表` `注销匿名条目` | `AnonymousEntries` / `append` 的 undo |
| §6 工具 | `默认重复报错` `推进游标` | 缺省 `duplicateError` / 迭代器 `next()` |
| §7 层 | `简单作用域层` `建标准层` `取名字表` | `ScopeLayer` 实现 / 缺省 `createLayer` / `merge` 的 `pick` |
| §7 层组 | `作用域层组` `造作用域层组` `空变更` `注销附着` | `ScopedLayers` / 缺省依赖注入 / 缺省 `onChange` / `effect` 返回的 disposer |

### 2.3 `作用域层组` 方法 ↔ 上游成员

| 光明方法 | 上游 |
|---|---|
| `全局层()` / 属性 `全局` | `global` |
| `取层(作用域键)` | `peek` |
| `链上层(作用域键)` | `chainLayers` |
| `层链(作用域键)` | 上游无（= `[global, ...chainLayers]`，供 `收集` 用） |
| `合并命名(作用域键, 取表=空)` | `merge` |
| `收集(作用域键, 取表=空)` | 上游无（**逐层原样罗列** `{"命名条目": […], "匿名条目": […]}`，不去重；去重视图用 `合并命名`） |
| `为空(作用域键)` | `peek(...)?.isEmpty() ?? true` |
| `附着(上下文, 动作, 标签=空, 通知=真)` | `effect(ctx, action, {label, notify})` |
| `撤销附着(句柄)` | `effect` 返回的 disposer |
| `确保层(作用域键)` / `层数()` | 上游无（诊断/构造辅助） |

### 2.4 迭代器代数（最关键的语义复刻）

上游 `store.spec.ts` 有 2 条用例专门验证「**排空换代后旧迭代器脱钩**」：

```js
const undo = entries.insert('first', 1)
const values = entries.values()
expect(values.next()).toEqual({ value: 1, done: false })
undo()
entries.insert('replacement', 2)
expect(values.next().done).toBe(true)        // 旧迭代器已脱钩
expect([...entries.values()]).toEqual([2])   // 新代可见
```

光明实现（`己.回收空代()`）：

```
如果 己.为空() == 真:
  设 己.数据 为 {}            # ← 换新字典对象（旧字典仍被游标持有）
  设 己.代数 为 己.代数 + 1
```

- **同一代内**：`数据` 对象未换 ⇒ 游标按 `位置` 继续读到后插入的条目（活迭代器语义）✔
- **排空后**：`数据` 换成新字典 ⇒ 旧游标仍在遍历**旧的、已排空的**字典 ⇒ 立刻返回 `完成=真` ✔
- 该机制之所以在光明成立：**光明的字典/列表是引用对象**（本轮探针实证：`设 句柄 为 甲["数据"]` 后 `甲["数据"] 为 {}`，句柄仍指向旧对象且旧对象保留原条目）。

### 2.5 §3.3 已知行为差异（必须记入 `行为差异清单.md`）

| # | 差异 | 上游 | 光明 | 影响 |
|---|---|---|---|---|
| R39-D1 | `effect` **非惰性** | `ctx.effect(gen)` 只登记、**不调用** action（用例 `expect(action).not.toHaveBeenCalled()`） | `附着` **立即执行** action 并同步通知 | 上游该用例无法逐字映射；光明改为断言「句柄承载标签/通知标记 + 动作已执行」。语义等价性保留在「返回句柄即 disposer」 |
| R39-D2 | 缺 `ctx.fiber.getEffects()` 的标签内省 | 可枚举 effect 标签 | 无 | 光明显式提供 `句柄["标签"]` 作诊断替代 |
| R39-D3 | 通知抛错回滚载体不同 | cordis 捕获并在回滚时调用已登记注销器 | `附着` 内 `尝试/捕获` 手工回滚：`撤销()` → 空层回收 → 再通知 → 上抛 | **事件序列逐位一致**：`['action','notify','undo','notify']`（用例 §16b 实证） |
| R39-D4 | `quiescence` 异步共享 | `disposing ??= quiesceFiber(fiber)` 多次 `dispose()` await 同一 Promise | 无异步：`已注销` 标记做同步幂等 | 可观测行为等价（只执行一次） |

---

## 三、单元测试覆盖（`examples/test_R39_作用域存储.light`，rc=0，19 组）

| 组 | 覆盖点 | 上游 `store.spec.ts` 用例 |
|---|---|---|
| #00 | 判据自检（断言助手真能报错） | —（防空判 PASS） |
| #01–01k | 初始为空 / 取 / 缺失取空 / 有无 / **名字·值·项三列表插入有序** / 条目数 / 非空 | 「owns duplicate diagnostics, lookup, insertion order, live iteration, and exact idempotent undo」前半 |
| #02–02d | 缺省重复报错抛 `DUPLICATE_NAME` / **调用方拥有诊断**（自定义抛 `CALLER_DUP`）/ 重复插入不污染原值 / 默认报错可抛 | 同上（`duplicateError` 被调用并传入名字） |
| #03–03d | undo 生效 / **只删自身** / 重插成功 / 幂等后仍只余重插项 | 同上后半（`undoA(); insert('a',3); undoA(); get('a')===3`） |
| #04–04d | **同一代内游标可见后续插入**（`values.next()` 在 `insert` 后仍前进） | 「starts a fresh iterator generation after the table drains」的**同代**半边 |
| #05–05g | 未换代 / **排空换代**（`代数` 0→1）/ **旧游标失效** / 新代可见新插入 / 新游标从头 / 走完 | 同上「**排空换代**」半边 |
| #06–06k | 等值独立注册（同值两次 = 2 条）/ 插入序 / `有无` / undo 幂等只删自身 / 匿名游标 / 排空换代 / 非法句柄返回假 | 「owns equal values independently with live insertion-ordered iteration and idempotent undo」 |
| #07–07g | 无键标准层 / 空判定（命名空 + 匿名空）/ **缺省取名字表** / 自定义取表 / 层记录作用域键 | `ScopeLayer` 契约 + `merge(..., pick)` 的 `pick` 参数 |
| #08–08i | 父链就近优先 / **读前无层** / **取层不创建** / **读后仍无层** / 全局属性直读 / 空键取层为空 / 空键层为空 / 无层时只见全局 / 无层时链上层为空 | 「constructs global state eagerly while reads stay non-creating and merge named shadows in order」 |
| #09–09m | 两个作用域层 / 预设层遮蔽全局 / **最近作用域最终拍板** / 链上层祖先在前·自身在后 / 单层时链上层仅自身 / 层链含全局且全局最前 / 为空判定 / 未建层视为空 / 确保层幂等 | 同上 + 「uses the same scoped context for lazy visibility and ownership」前半 |
| #10–10h | **收集逐层原样罗列**（4 条：全局 a、全局共享、预设共享、代理共享）/ 匿名收集 / 无作用域层只收全局 | `merge` 与逐层可见性的对照 |
| #11–11i | 注销返回真 / **重复注销返回假** / **空聚合层被回收** / **仍有条目则保留层** / 回收后遮蔽退回全局 / 层级为空 / 层数回落 / 归零 | 「reclaims only an empty aggregate」 |
| #12–12f | **动作先于通知** / 标签随句柄保留 / 通知标记 / **撤销顺序 + 幂等**（`['action','notify','undo','notify']`）/ 撤销后层回收 / 全局层无残条 | 「runs action, notification, undo, and disposal notification in order with Cordis idempotence and labels」 |
| #13–13e | `notify=false` 不通知（落层与撤销两态皆不通知）/ 标记为假 / 条目已落层 / 撤销后回收 | 同用例的 `notify: false` 分支 |
| #14–14c | **工厂失败不留层**（层数归零） | 「cleans up failed factories and empty failed actions without discarding an existing layer」前半 |
| #15–15d | 动作失败上抛 / **新建空层回收** / **既有层不被丢弃**（保留条目仍在） | 同用例后半 |
| #16–16d | **通知抛错回滚**：`['action','notify','undo','notify']` / 回收空聚合 / 层数归零 | 「rolls back a scoped insertion when notification throws」 |
| #17–17c | 无作用域标签 ⇒ 写入全局层 / 不建作用域层 / 撤销后全局层为空 | `effect` 的 `scope===undefined` 分支 |
| #18–18d | 缺省建层器（`建标准层`）/ 层携带作用域键 / 确保层登记 / 缺省变更器（`空变更`） | 缺省依赖注入 |

**显式未覆盖（非缺陷）**：
- `expect(ctx.fiber.getEffects().map(e => e.label)).toContain('store.order')`——cordis fiber 内省，光明无对应（见 R39-D2）。
- `expect(returned).toBe(rawDispose)` + `expect(action).not.toHaveBeenCalled()`——cordis 惰性 effect 身份（见 R39-D1）。
- `expect(layers.peek(key)?.named.get('kept')).toBe(1)` 的空值链写法 → 光明改为直接断言 `取层(键).命名.取("保留")`。

---

## 四、反跑证据

见 `_task1_R39_scope核心复刻.md` §五（同一脚本 `_antirun_r39_t12_scope反跑.py` 覆盖两套用例）：

| 判据 | 变异 | 结果 |
|---|---|---|
| T2-值反 | §05d 旧游标 `完成` 期望 `真` → `假` | rc=1，报 `断言错误` ✅ |
| T2-抛反 | §15 动作失败 → 换成正常动作（不再抛） | rc=1，报 `应抛错未抛` ✅ |

`R39 任务1+2 反跑判据：ALL PASS`

---

## 五、验证记录

| 项 | 结果 |
|---|---|
| 单跑 | `<venv-py> 运行.py examples/test_R39_作用域存储.light` → **rc=0**，打印 `作用域存储 判据通过：19 组` |
| 反跑 | ALL PASS（值反 + 抛反各 1 条） |
| 影响面 | 新增 1 模块 + 2 用例，**0 既有文件改动**（`git status --short -- src examples` 无 `M` 行） |
| 导入路径 | `从 作用域 导入` 仅 2 个新增用例文件 |
| 回归抽样 | 相邻 7 个既有用例全 GREEN（见任务1报告 §七） |
| 行尾 | 新增文件 CRLF / LF-only=0 / 无 BOM |
| 全量反跑 | 纯新增 ⇒ 结构性零回归；正式全量反跑归属任务5 / 路M |

---

## 六、已知限制与移交

1. **`收集` 不去重**（逐层原样罗列）；需要「就近覆盖」的名字视图请用 `合并命名`。
2. **层对象契约**：传入自定义层**必须**实现 `为空()`（等价上限 `isEmpty()`）；`收集` 还要求层暴露 `命名` / `匿名`。
3. **光明无闭包 ⇒ 撤销器须借模块级槽字典**（见测试 §2 的 `槽盘`），这是调用方写 `附着` 动作时的固定范式，建议在任务5 集成测试沿用。
4. `作用域层组` 的 `建层器` 会在**构造期**以 `空` 调用一次（对齐上游 `createLayer(undefined)`），自定义建层器需容忍该空参。
5. `_superseded_作用域_并行版_12h49m29s.light`（被取代的并行版本）与 `_antirun_r39_t12_scope反跑.py` **保留不提交**。
