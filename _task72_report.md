# _task72_report.md —— B 线交付小结：agent-presets 纯逻辑复刻（对标 #72）

- 交付人角色：lightharness 复刻开发工程师（B 线）
- 复刻对象：`G:\github\deepseek-harness\packages\preset\agent-presets\src\`
  （`specifier.ts` / `preset.ts` / `metadata.ts` / `session.ts` / `discovery.ts` / `mount.ts` / `authoring.ts`；
  `index.ts` 装配层 / `invariant.ts` Cordis 宿主绑定 不在本批白名单，未复刻）
- 新增白名单文件：
  - `src/预设.light`（核心纯逻辑，37 个导出段落）
  - `examples/test_预设.light`（反跑测试，19 个正例用例 + 8 组 反跑_ 断言）
  - `_task72_entry.json`（对标清单条目）
  - `_task72_report.md`（本文件）
  - `_task72_antirun.py`（定向反跑脚本，零 /tmp 依赖）
- 未触碰任何其它文件；未 commit / 未 merge / 未 push。

---

## 1. 原版文件 → 光明段落 对照表（函数级）

### specifier.ts

| 原版函数 | 光明段落 | 说明 |
|---|---|---|
| `classifyRowSpecifier(s)` | `分类行标识符(标识符)` | cordis:/./../ / /X:/file:/@ 五类映射 |
| `isAbsolute(p)` | `是绝对(路径)` | / 开头或 X: 盘符 |
| `startsWith(p, pre)` | `前缀是(路径, 前缀)` | deleteComposition 检查 |

### preset.ts

| 原版函数 | 光明段落 | 说明 |
|---|---|---|
| `validatePresetId(id)` | `标识合法(标识)` | `^[a-z0-9-]+$`，首字符非 `-` 闸 |
| `validatePresetId` 别名 | `校验预设标识(标识)` | 复用 标识合法 |
| `availableText(list)` | `可用文本(列表)` | 空→`"none"`，否则首元素 |
| `PresetNotFoundError` | `造未知道错误(标识, 可用)` | 拼 available 串 |
| `PresetLockedError` | `造锁错误(会话标识, 预设标识)` | |
| invalid-preset reason 分支 | `造挂载错误(预设标识, 理由)` | |
| read-only preset | `造只读错误(预设标识, 来源)` | |
| bad-request / internal | `造坏请求错误()` / `造内部错误()` | |

### metadata.ts

| 原版函数 | 光明段落 | 说明 |
|---|---|---|
| `displayMetadata` 的 trim 折叠 | `文本(值)` | 非串→空；去空白后空白→空 |
| `extractDisplayMetadata` | `提取显示元数据(元)` | name/description 非空串、order 整数；三道闸 |
| `extractDisplayMetadata` 空则空 | `造显示元数据记录(元)` | 键数 0 → 空，否则返回记录 |

### session.ts

| 原版函数 | 光明段落 | 说明 |
|---|---|---|
| `presetProjection` 初值 | `预设投影初值(状态)` | 含 agentPreset 键则取其值，否则 空 |
| `presetProjection` reduce | `预设投影应用(当前, 动作)` | type==selected 取 data.agentPreset，否则保持当前 |

### discovery.ts

| 原版函数 | 光明段落 | 说明 |
|---|---|---|
| `row` 的 disabled 取反 | `行启用(行)` | |
| `compositionShapeProblem`（递归 group） | `条目列表问题(列表, 根)` | 非列表 / 非字典行 / 空名 三闸；group 递归 |
| `unresolvableRows`（跳过 disabled / group 递归 / 行解析判定） | `不可解析行(行列表, 预设基, 宿主基, 解析能力, 前缀)` | |
| 行「是否可解析」（固定判定） | `预设行解析(分类, 预设基, 宿主基)` | 无包注册表，package 一律不可解，对齐原版默认语义 |
| `compositionProblem(path, base)` | `合成问题(路径, 宿主基, 读文件能力, 解析能力)` | 拆 读→解析→形状→不可解析；宿主能力注入 |
| `scanRoot` 稳定排序比较 | `应前(a, b)` | 先 order 后 id；缺省 order=+∞ |
| 交换元素（返回新列表） | `交换元素(列表, i, j)` | |
| `scanRoot` 的 order→id 稳定排序 | `扫描根排序(列表)` | 插入排序 |
| `discoverPresets` 跨根去重保留首现 | `发现预设(根表)` | |

### mount.ts

| 原版函数 | 光明段落 | 说明 |
|---|---|---|
| `withinFiber` | `在纤维内(纤维表, 纤维, 根)` | 沿父链上行命中根即真 |
| `leakedServices` | `泄出服务(服务, 纤维表, 根)` | 根隔离 且 fiber 隶属根，按名排序（复用 排序名） |
| 服务名 sort | `排序名(列表)` | 插入排序 + 交换元素 |
| `inactiveRows` | `未激活行(条目)` | disabled 跳过；无 fiber→never started；缺注入→waiting for |
| name list 逗号拼接 | `名文本(列表)` | 审计消息 |
| `detailBranches` | `明细分支(错误)` | 存在 原因→以原因为单元素分支递归渲染（注：比原版 lossy 行为更完整，与 明细_嵌套 验收一致） |
| `mountDetail` | `挂载明细(错误)` | 递归扁平化，首行 + 缩进分支 |

### authoring.ts

| 原版函数 | 光明段落 | 说明 |
|---|---|---|
| `writableRoot` | `可写根(根列表)` | 首个 user 根；无则抛 |
| `deleteComposition` 两条闸 | `可删判定(预设, 可写根目录)` | user + 绝对且位于可写根下 |
| `copyMetadata` | `可复制元数据(源, 名)` | name 覆盖 + 保留 description |

---

## 2. 根因修正（重要：纠正前序误判）

`提取显示元数据` / `造显示元数据记录` 一度返回 `None`，前序一度误判为「**if 块内修改字典 + 返回该字典 → None**」的语言陷阱。本轮用隔离探针**实测证伪**该误判：

| 探针 | 变量名 | 结构 | 结果 |
|---|---|---|---|
| P0 / R0 | `出` | 顶层 `设 出["name"] 为 X` + `返回 出` | **None** |
| S0 | `结果` | 顶层 `设 结果["name"] 为 X` + `返回 结果` | `{'name':'X'}` ✓ |
| S1 / S2 / S3 | `结果` | if 块（含函数调用条件 / 嵌套）内改字典 + 返回 | 均正常 ✓ |

**结论：真因是单字 `出` 为保留字（L-046）**，`设 出 为 {}` 静默生成坏绑定，`返回 出` → `None`；与 if 块结构**无关**——任何结构下用 `出` 作变量名都会 None。前序「if 块陷阱」是 `出` 变量名造成的假象。

**修复**：将 `预设.light` 内全部 5 处 `出` 局部变量（提取显示元数据 / 造显示元数据记录 / 排序名 / 未激活行 / 可复制元数据）改名为 `结果`；`泄出服务`（函数名含 `出`）不受影响、保持原样。改名后测试复绿。

> 旁证：`预设.light` 文件头注释已固化「函数一律块形式」「字面量单行」「字典/列表下标用 builtin」三条规避约定，正是 L-013 / L-051 / L-036 / L-058 的对应绕法。

---

## 3. 反跑验证（`_task72_antirun.py`）

测试文件自带反跑层（8 组 `反跑_*` 断言）。另以脚本做**定向单点破坏**：从绿色原文出发，逐一轮换 5 个独立破坏，每个对应一个 `反跑_*` 断言，确认全部立红（rc=1，首个失败断言命中对应标签），每轮后立即从内存原文还原，末尾跑一次复绿确认。

| # | 破坏点 | 变异 | 立红断言 | 结果 |
|---|---|---|---|---|
| ① | 标识合法 首字符闸 | `标识[0]=="-" → =="X"` | `标识_连字符开头` | 红 ✓ |
| ② | 条目列表问题 空名闸 | `名=="" → =="BREAK"` | `形状_空名` | 红 ✓ |
| ③ | 扫描根排序 比较方向 | `应前(b,a) → 应前(a,b)` | `排序_a` | 红 ✓ |
| ④ | 在纤维内 未命中闸 | `未命中→返回 假` 改 `返回 真` | `隶属_无此纤维` | 红 ✓ |
| ⑤ | 预设投影应用 selected | `=="agent-preset/selected" → ==".../BREAK"` | `应用_选中` | 红 ✓ |

- **还原后复绿**：`python 运行.py examples/test_预设.light` → `--- 测试预设 通过 ---`，rc=0。
- **脚本纪律**：绿色原文全程驻留内存，零 `/tmp` 依赖（规避此前 windows python `/tmp` 不存在导致源文件被覆盖清空的坑）；还原后独立再跑一次绿色基线确认无残留破坏。
- 门禁达成：`python 运行.py examples/test_预设.light` 退出码=0 且断言全过。

---

## 4. 语言缺陷（本批复刻触及 / 规避）

| L 号 | 与本项目关系 |
|---|---|
| **L-046** | **真因**：单字 `出` 不能作变量名，`设 出 为 {}` 静默坏绑定使 `返回 出`→None。已将 5 处 `出` 局部变量改名 `结果`。 |
| L-013 | 单行控制结构（for/if 尾随语句）会吞噬后续缩进。`预设.light` 全部函数/分支用块形式。 |
| L-051 | 多行字典/列表字面量破坏后续块缩进。全部字面量单行书写。 |
| L-036 | 缺失键 `[]` 直接访问抛 键错误（JS 取缺失属性得 undefined）。所有可选字段访问用 `字典包含键` 守卫。 |
| L-058 | `如果 (cond): X 为 Y` 内联赋值静默不执行（X 撞动词名时降级为比较）。if + 赋值一律块形式。 |

> 另两类开发期踩坑已用规范规避、未单独记 L 号：① `段落 X 接收 p: 返回/抛出`（单行函数）触发生成器缩进累积，使 `主程()` 被嵌进永不调用的 wrapper（rc=0 无输出）——全部函数改块形式；② 内联 `如果 (cond): STMT` 后接 `否则` 块报「否则是保留关键字」——`否则` 一律另起块形式。③ 跨函数局部变量不可被另一函数读取（预期作用域语义），抛错桩函数所需数据提到模块级全局。

---

## 5. 遗留 / 后续

- `index.ts` 装配层、`invariant.ts` Cordis 宿主绑定不在本批白名单，未复刻（与任务书边界一致）。
- `明细分支` 选择「以原因为单元素分支整体渲染」，比原版对 AggregateError 的 lossy 处理更完整；若需严格对齐原版丢 `cause.message` 行为，后续可调。
- 待合流任务（#4）将本 entry 并入 `docs/功能对标/对标清单.json`（70→73 条），并汇总 A/B/C 三线语言缺陷账。
