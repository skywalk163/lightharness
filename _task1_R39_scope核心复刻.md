# 第 39 轮 任务 1 交付报告 —— scope 核心模块复刻（作用域键 / 父链 / 循环检测 / 上下文 / 载体 / 准入）

> 日期：2026-09-16 ｜ 方向：上游复刻 —— `@deepseek-ai/dsh-scope` 核心部分
> 上游基线：deepseek-harness 0.1.5-rc.2
> 上游源码：`G:\github\deepseek-harness\packages\core\scope\src\index.ts`（204 行，全文精读）
> 上游用例：`packages/core/scope/tests/scope.spec.ts`（10 用例）
> 交付物：`src/作用域.light`（新增模块，§1–§5 为任务1，§6–§7 为任务2）、
>         `examples/test_R39_作用域.light`（单元测试，**rc=0**）

---

## 一、并行写入事故与留档（必读）

本轮开工时发现 **另一路 agent 已于 12:49:29 写入同一文件 `src/作用域.light`**（sha256 `3a3af723…`，392 行，17 导出）。

实测该版本**不可解析**（15 处语法错误），且存在两处结构性缺陷：

| 缺陷 | 位置 | 后果 |
|---|---|---|
| `循环:` 不是光明 while 语法 | 第 111/161/179 行 | 解析错误「无法识别的语法元素：':'」 |
| **模块级标量在段落内自增**（`设 作用域计数器 为 作用域计数器 + 1`） | 第 43/63、188/192 行 | 段落体内 `设` 只建局部名 ⇒ 每次调用都得 `ID=1`，**所有作用域键互相串号** |
| 使用了 `current` / `currentID` 英文名混排 | 第 165/168 行 | `name 'current' is not defined` |
| 未导入却调用 `字典值列表` / `字典项列表` | 第 243/246 行 | `NameError` |

处置（按多 agent 纪律「不覆盖他人」执行前置冻结检测）：

1. 采样 sha256 ×6（跨 ~50 s）确认**已停止写入**（`3a3af723…` 恒定）；
2. **留档**被取代版本 → `_superseded_作用域_并行版_12h49m29s.light`（sha256 同 `3a3af723…`，可回溯）；
3. 确认**全仓库无任何文件引用该模块**（`grep -rn "从 作用域 导入"` 仅命中其自身）；
4. 落我的完整实现，并在交付前再次采样 sha256 确认无人回写。

> ⚠️ 若 12:49 那一路 agent 仍在活动并回写本文件，请以本报告 sha 为准：**本轮交付版 sha256 = `6275f7bbc7d8aecc6db27df041ce334f5c694b21fe54b301c5f5993770bb66dc`**（745 行，CRLF，无 BOM）。

---

## 二、上游源码精读（index.ts 204 行）

| 上游要素 | 实现 | 语义要点 |
|---|---|---|
| `type ScopeKey = object` | `export type ScopeKey = object` | **不透明、标识比较**（不是字符串） |
| `const kScope = Symbol('dsh.scope')` | `const kScope = Symbol('dsh.scope')` | 由 `createScope` 写进上下文的标签 |
| `const carrierKeys = new WeakMap<object, ScopeKey\|undefined>()` | L30 | **存在性**区分「未指键载体」与「非载体」 |
| `const scopeParents = new WeakMap<ScopeKey, ScopeKey>()` | L39 | 一条关系支撑两个方向：注册视图**向下继承**、事件准入**向上扩展** |
| `linkScopeParent(key, parent)` | L54–59 | 从 `parent` 沿父链上行，`cursor === key` ⇒ `throw '…would form a cycle'` |
| `bindScopeParent(key, parent)` | L72–82 | `scopeParents.has(key)` ⇒ 抛「already bound」；返回唯一 `{rebind}` |
| `scopeParentOf(key)` | L89–91 | 根的父为 `undefined` |
| `scopeChainOf(key)` | L98–102 | `[key, parent, …, root]`；`undefined` ⇒ `[]` |
| `createScope(ctx, key, options)` | L137–147 | 可带 `parent`；返回 `{ctx, rawDispose, dispose}`；`dispose` **共享静默**（`disposing ??=`） |
| `scopeOf(ctx)` | L154–156 | 读最近继承到的标签 |
| `scopeTarget(base, key)` | L170–185 | 保留 `base` 上已有的 Cordis filter（并保留其接收者 `baseFilter.call(base, ctx)`）；`key` 为 `undefined` 的载体**全局准入** |
| `isScopeCarrier` / `carrierKeyOf` | L192–204 | 判型 / 取键 |

官方 `scope.spec.ts` 10 用例可归为 4 组：`createScope`（4）、`scopeTarget`（4）、父链（2）。

---

## 三、光明适配设计

**模块名**：`src/作用域.light`（命名预检查：全 `src/*.light` 段落/类名集合交集为空，零冲突）。

### 3.1 四处等价替代

| # | 上游机制 | 光明实现 | 等价性论证 |
|---|---|---|---|
| A1 | `WeakMap` 对象键 | 模块级字典，键为**唯一ID 字符串** | 「标识比较」语义由唯一ID 承载；`作用域相等` 比 ID，两对象必不等 |
| A2 | JS 闭包 undo（`() => void`） | **句柄字典** `{"活跃": 真, …}` + 具名段落 `注销命名条目(句柄)` | 幂等由 `活跃` 标记保证，重复调用安全 |
| A3 | JS `Map` 活迭代器 | **游标** `{"数据": <字典引用>, "位置": n}` + `推进游标` | 本仓库字典是引用对象：同一代内可见后续插入；排空时 `己.数据` 换新字典 ⇒ 旧游标命中已空旧字典 ⇒ 自动失效（= `drain detaches iterators`） |
| A4 | cordis `ctx.effect` 惰性注册 | `附着` **立即执行动作并同步通知**，返回句柄充当 disposer | 见任务2报告 §3.3「已知行为差异」 |

### 3.2 关键数据结构

```
作用域序盘 = {"值": 0}                 # 唯一ID 发生器（模块级标量在段落内自增会失效，必须落在字典上）
载体序盘   = {"值": 0}
作用域父表 = { <键ID>: <父键> }         # 键存在 ⇔ 已绑定（= scopeParents.has(key)），无需独立绑定标记表
载体键表   = { <载体ID>: <键|空> }      # 值可为空 = 未指键载体
链卫兵上限 = 10000                     # 上游靠 JS 引擎兜底环，光明显式设遍历上界
作用域键   = { "__作用域键__": "skN", "标签": … }    # 不透明对象
载体       = { "__作用域载体__": "载体N", "基础": <过滤器|空> }
上下文     = { "作用域键": <键|空>, "父": <上下文|空>, "标签": … }   # 替代 ctx.extend
域体       = { "键", "上下文", "注销器表", "已注销" }                # 替代 Scope{ctx,rawDispose,dispose}
```

### 3.3 导出清单（§1–§5，任务1 部分共 28 项）

| 分组 | 导出的光明名 | 上游对应 |
|---|---|---|
| §2 作用域键（5） | `建作用域键` `是作用域键` `作用域键ID` `作用域键标签` `作用域相等` | `ScopeKey` / 类型判据 / 标识比较 |
| §3 父链（7） | `作用域循环检测` `写父作用域` `绑定父作用域` `重绑父作用域` `取父作用域` `取作用域链` `取作用域链向上` | `linkScopeParent` / `bindScopeParent` / `rebind` / `scopeParentOf` / `scopeChainOf` |
| §4 上下文与生命周期（11） | `建上下文` `扩展作用域上下文` `派生上下文` `取上下文作用域` `建作用域` `取作用域键` `取作用域上下文` `登记作用域注销` `原始注销作用域` `注销作用域` `作用域已注销` | `ctx.extend` / `scopeOf` / `createScope` / `rawDispose` / `dispose` |
| §5 载体与准入（5） | `建作用域目标` `是作用域载体` `取载体作用域` `取目标作用域` `作用域准入` | `scopeTarget` / `isScopeCarrier` / `carrierKeyOf` / `filter` |

**签名差异（1 处，已记入行为差异）**：上游 `scopeTarget(base, key)` 是 `(基础, 键)`；光明实现为
`建作用域目标(键, 基础=空)`，以满足任务书「`建作用域目标(键)`」的调用形态，同时保留基础过滤器能力。

---

## 四、单元测试覆盖（`examples/test_R39_作用域.light`，rc=0，14 组）

| 组 | 覆盖点 | 上游对应用例 |
|---|---|---|
| #00 | 判据自检（断言助手必须真能报错；抛错助手必须真能报错） | —（防空判 PASS 铁律） |
| #01–02d | 建键 / 判型（字典·空·字符串·非键）/ 每键唯一 ID / 标签 / 同键相等 / 异键不等 / 空与非键不参与相等 / 键为不透明对象 | 「opaque branded carrier with a separately tracked key」前半 |
| #03–03h | 绑定父 / 取父（根为空、空键为空）/ 取链（就近优先、单元素、空键空链）/ 取链向上 / **间接环检出** | 「links at mint, walks to the root, and rejects cycles」 |
| #04 | **一次性绑定**：二次绑定抛 `ALREADY_BOUND` | 「re-links only through the binding held by the original binder」前半 |
| #05–06b | **自环**抛 `SCOPE_CYCLE`；`写父作用域` 直接调用同样拦环；非作用域键入参抛 `NOT_SCOPE_KEY` | 「rejects cycles」 |
| #07–07d | 重绑生效 / 重绑后新链闭合 / **重绑仍做环检测** / 非法句柄抛 `INVALID_BINDING` | 同上后半（`binding.rebind(presetB)` + `rebind(child)` 抛环） |
| #08–08g | 根上下文无标签 / 作用域上下文带标签 / 派生继承最近标签 / **内层标签胜出** / 空键扩展不引入标签 | 「tags contexts and derived contexts, with the nearest tag winning」 |
| #09–09m | 取作用域键 / 未注销 / 注销幂等 / 原始注销（空表安全）/ 拒绝空撤销器 / 空域体全路径返回约定 / 建作用域入参校验 | 「shares quiescence across repeat and raw-disposer-first calls」的可用子集 |
| #10–10i | 载体判型（字典/空/非载体）/ 取键 / 别名 / **未指键载体仍是载体** / 载体互为不同对象 | 「uses an opaque branded carrier with a separately tracked key」 |
| #11–11h | **准入语义四象限**：无标签全局准入 / 祖先标签准入 / 自身标签准入 / **旁支拒绝** / **子标签拒绝（事件不下行）** / 未指键载体：无标签放行·有标签拒绝 / 非载体一律拒绝 | 「routes scoped listeners by key while untagged listeners remain global」+「admits an ancestor-tagged listener for a descendant dispatch, never the reverse」 |
| #12–12d | **基础过滤器先否决则否决**（无标签/有标签两态）；放行后退回作用域语义 | 「preserves a base Cordis filter and its receiver」 |
| #13–13c | 同键不同载体互不影响、各自记录键、准入语义一致 | 载体身份独立性 |

**未覆盖并显式记录（非缺陷）**：
- cordis fiber 生命周期（`quiesceFiber` / `inertia` / 复合 effect 有序拆除）——光明无异步 fiber，由 `注销器表` + `原始注销作用域` 承载可用子集。
- `{ global: true }` 监听器语义——依赖 cordis 监听器注册表，属任务5「scope + system-prompt 联动」的作用域过滤层，本轮 `作用域准入` 已提供判定原语。

---

## 五、反跑证据（判据有效性）

脚本：`_antirun_r39_t12_scope反跑.py`（变异写在**根目录**临时文件，跑完即删；与正常用例严格串行）

| 判据 | 变异 | 结果 |
|---|---|---|
| T1-值反 | `作用域相等(键甲, 键乙)` 期望 `假` → `真` | rc=1，报 `断言失败` ✅ |
| T1-抛反 | §04 二次绑定换成新键（不再抛） | rc=1，报 `应抛错未抛` ✅ |
| T2-值反 | §05d 旧游标 `完成` 期望 `真` → `假` | rc=1，报 `断言错误` ✅ |
| T2-抛反 | §15 动作失败改为正常动作（不再抛） | rc=1，报 `应抛错未抛` ✅ |
| 还原复跑 | — | 两个用例均 rc=0 ✅ |

`R39 任务1+2 反跑判据：ALL PASS`

---

## 六、语言缺陷/边界发现（供路M回填 `docs/功能对标/语言缺陷账.md`）

> 任务书铁律「docs 归路M统一写」，此处只交初稿，不改 docs。

### L-NEW-A（**高危**）：`作用域` 是保留关键字，不可作标识符

- **证据**：`light-merge/src/keywords.py:179` 关键字列表含 `'作用域'`（与 `'异步'`、`'等待'` 同组）。
- **症状**：以裸 `作用域` 作为**语句首 token** 的语句一律解析失败：
  `「作用域」是保留关键字，不能直接作为语句开头。`（本轮实测 7 处，见 `src/作用域.light` §4 首版）
- **反例/边界**：`作用域键`、`作用域父表`、`作用域层组` 等**以关键字开头的复合标识符**不受影响（不可被关键字序列完全切分）；
  `段落 建作用域键`、`类 作用域层组` 也正常。**只有「该 token 恰好整体等于关键字」时才炸**。
- **修法**：作用域实例变量/形参一律改名（本轮用 `域体`）；避免任何**恰好等于**保留字的标识符。
- **文档影响**：L-119 单字别名清单之外，需补一条「**多字关键字同样不可裸用**」的通用规则。

### L-NEW-B（**高危**）：标识符中含关键字 `函数` 会导致解析失败

- **症状**：类体 `属性 建层函数 等于 空` 报
  `类体内不支持的成员声明：'等于'`（类体成员关键字表含 `函数`，导致 `属性` 名被截断、后随 `函数` 被当成新成员声明）。
- **连带**：解析失步会把后续若干行也报成语法错误（本轮首版报 4 处，实际只有 1 处真错），**定位时必须从第 1 个错开始修**。
- **修法**：标识符（段落名/属性名/变量名）一律避开 `函数` 二字 → 本轮改用 `建层器` / `变更器` / `重复报错`。

---

## 七、验证记录（本机口径）

| 项 | 结果 |
|---|---|
| 单跑 | `cd lightharness && <venv-py> 运行.py examples/test_R39_作用域.light` → **rc=0**，打印 `作用域 判据通过：14 组` |
| 反跑 | `_antirun_r39_t12_scope反跑.py` → **ALL PASS** |
| 影响面 | `git status --short -- src examples` 中**无任何已跟踪文件被修改**（只有新增 untracked） |
| 导入路径 | `grep -rn "从 作用域 导入"` → 仅 `examples/test_R39_作用域.light` / `examples/test_R39_作用域存储.light`（新增），零既有引用 |
| 回归抽样 | `test_R38_工具展示` `test_R37_代理默认模型` `test_R38_集成测试` `test_R37_集成测试` `test_代理循环` `test_工具` `test_会话存储` 全 GREEN |
| 行尾 | 三个新增文件 CRLF，LF-only=0，无 BOM |
| 命名冲突 | 全 `src/*.light` 段落/类名交集 = 0 |
| 全量反跑 | 本轮**纯新增**（新增 1 模块 + 2 用例，0 既有文件改动）⇒ 结构性零回归；正式全量反跑按任务书归属任务5 / 路M 统一执行 |

---

## 八、已知限制与移交

1. **`作用域准入` 是判定原语，不是监听器注册表**：事件派发接线属任务5「scope + system-prompt 联动」，本轮不越界。
2. **`附着` 非惰性**（光明无 cordis 延迟效应）：见任务2报告 §3.3，已作为行为差异记录。
3. **父链遍历卫兵 10000**：正常构造下不可达；仅防御异常状态。
4. 被取代的并行版本留档于 `_superseded_作用域_并行版_12h49m29s.light`，**不提交**。
