# 任务3 R58 —— 代码生成断言 21 条 + 类/成员访问 14 条归因（纯只读）

> 日期：2026-09-18 ｜ 轮次：R58 ｜ 性质：**纯只读归因，未修未改任何仓库文件**
> 数据源：`reports/_task4_R57_存量红明细_072454.json` baseline_reds 中 `语义债-代码生成断言`（21）+ `语义债-类/成员访问`（14）
> 结构化明细：`_task3_R58_代码生成语义债归因明细.json` + `.csv`（35 条，字段：id/category/红因/根因/根因类别/修复建议/改动面/与L-175相关性）
> 归因手法：junitxml message + 测试源码断言 + codegen 发射逻辑源码 + **本机只读编译冒烟**（复现产物形态，未跑任何 pytest，未跑全量；0.82 复现配额未动用）

---

## 一、总览（R59 决策底表）

| 根因类别 | 条数 | 改动面 | R59 处置 |
|---|---|---|---|
| 测试期望过时（L-096 `_light_attr_get/_set` 发射形态） | 21 | 小 | 改测试断言/期望，一次 PR 可全清 |
| codegen 缺陷（粘连 `己X` 读取位不展开 → NameError） | 14 | 中 | **一条 codegen 修复可全清**（两后端 `_resolve_*` 同加分支） |
| 需语义评审 | 0 | — | — |
| 疑似已变化待全量确认 | 0 | — | — |
| **合计** | **35** | — | R59 可修 35（21 小 + 14 中） |

**与 R57 L-175 相关性**：35 条已用 R57 终跑 junitxml（`_082_lm_results_2026-09-18-100010.xml`）与 072454 基线逐条交叉核对——31 条 message 全同、4 条仅空白差异，**无一条变化**；且 L-175 只改 `_resolve_exception_type` 类基类映射（10 行，:2349/:2374/:2671-2677），与成员访问/属性赋值发射链路无交集。归因结论：**全部无关**。

---

## 二、根因一：测试期望过时（21 条，改动面小）

### 2.1 统一根因：L-096 属性访问/赋值统一走 helper

`src/code_generator.py:1333/1339` 定义 `_light_attr_get(_o,_k)` / `_light_attr_set(_o,_k,_v)`，定义处注释（:1329-1344）明确这是 L-096 的**有意设计**：dict 目标 → 键访问（与 字典获取/字典设置 一致），类实例/模块 → 原生 getattr/setattr（行为不变）。发射点：

- 属性赋值语句：`code_generator.py:1684-1693`（注释明言「绝不能把 _light_attr_get(...) 放在赋值左侧」）；
- 属性访问表达式：`code_generator.py:3819-3822`；
- 交叉证据：方法**调用**路径 `code_generator.py:3806` 仍直发 `{obj}.{member}(...)`——发射逻辑只对「纯属性读/写」换了形态，类实例运行期语义等价。

21 条测试的断言停留在 helper 引入前的直发文本（`self.x = 1`、`p.x`、`await 甲.乙.丙()` 等），与产物形态脱钩。

### 2.2 分组对照（21 条）

| 文件 | 用例 | 期望 → 实测 | 备注 |
|---|---|---|---|
| tests/unit/test_v35_chained_call.py | TestDotPeriodSplit 5 条（dot_member_access / mixed_period_and_dot / no_period_no_dot_ambiguity / period_in_class_body / dot_access_after_new_keyword） | `p.x`/`p.x = 3`/`self.x`/`a.x` → `_light_attr_get(p,'x')` / `_light_attr_set(…)` | 组 A |
| tests/unit/test_v35_chained_call.py | TestChainedAttributeAssignment 4 条（two_level / self_chain / three_level / attr_assign_with_expr） | `b.a.x = 42`/`self.inner.val`/`a.b.c.val = 99`/`a.x = ` → 嵌套 `_light_attr_set(_light_attr_get(b,'a'),'x',42)` 等 | 组 A |
| tests/unit/test_v34_syntax_sugar.py | TestAttributeAssignment 4 条（self_attr_eq / self_attr_等于 / obj_attr_eq / dot_access_still_works） | `self.x = 1`/`p.x = 10` → `_light_attr_set(…)` | 组 A |
| tests/test_context_manager.py | TestL2OOPCodegen::test_自_param_and_body_both_self | `self.姓名 = 姓名` → `_light_attr_set(self,'姓名',姓名)`（本机复现） | 手工 AST 直驱 codegen |
| tests/test_context_manager.py | TestJueyiOOP成员赋值目标 4 条 | `self.姓名=姓名`/`self.成绩[科目]=分数`/`obj.字段=1` → `_light_attr_set` / `_light_attr_get(self,'成绩')[科目]=分数` | 组 B |
| tests/test_context_manager.py | TestAwaitMemberAccess::test_await_chained_member | `await 甲.乙.丙()` → `await _light_attr_get(甲,'乙').丙()`（本机复现） | await 语义等价 |
| tests/test_context_manager.py | TestJueyiE遍历为连接词::test_为搭配函数调用 | `'==' not in 产物` 失败——**for i in range(1, 10): 发射正确**；`==` 来自产物头部运行时预置内置表（如『是负零』lambda `v == 0.0`） | 特殊：断言面过宽被预置误伤，非「为→==」回归 |
| tests/test_async_class_method.py | TestAsyncClassMethod::test_03_async_method读写己属性 | `self.值 = (self.值 + 1)` → `_light_attr_set(self,'值',(self.值+1))`；读取侧 `return self.值` 已直发（本机复现） | 组 C 第 11 条 |

> ⚠️ 组 A 附带观察（不计入 35 条，建议 R59 立工作项）：test_period_in_class_body 产物出现 `def get(self, self)`——`self` 被重复收集为普通形参（_is_self_param 判据与手工 AST 形参表对不上时才会发生），与本条失败无因果，但属潜在静默错编形状。

### 2.2 R59 修复路径（21 条，小）

- 改断言接受 helper 形态；更稳妥的是把「产物形状断言」升级为「行为断言」（exec 产物后断言属性读写正确），一劳永逸免疫发射形态再演化；
- test_为搭配函数调用 单独处理：把 `'==' not in 全产物` 收窄为对循环行的断言（预置中的合法 `==` 恒在，且会继续增长）。

---

## 三、根因二：粘连 `己X` 读取位不展开（14 条，改动面中）

### 3.1 现象

14 条运行期红全部是 `NameError: name '己XXX' is not defined`（或 `[run] 退出码 1: name '己项' …`）：

- tests/test_context_manager.py：test_继承链可用、TestChaoSuper 3 条（共 4 条，Category=类/成员访问）；
- tests/test_frontend_blockers_run.py：test_a24_泛型类真跑、test_a24_多参数泛型类、test_a25_两个嵌套类且外层成员不被吞（3 条）；
- tests/integration/test_class_system.py：5 条（constructor_with_inheritance / class_with_attributes / method_override / self_method_call / multiple_classes_in_one_file）；
- tests/test_level6_types.py::test_class_instantiation（1 条）；
- tests/test_edge_cases.py::test_class_with_multiple_methods（1 条，message 内附完整生成代码）。

### 3.2 根因链（本机只读冒烟逐层坐实，读写两侧不对称）

| 层 | 赋值位（语句头 `己X 为 …`） | 读取/实参位（`打印 己姓名`、`列表追加(己项, 值)`、`返 己名称`） |
|---|---|---|
| 词法 | `己名称` 整词一个 IDENTIFIER（`己` 是 KEYWORD 但 lexer 对汉字连写不切） | 同左（实测 `tokenize('列表追加(己项, 值)')` → IDENTIFIER '己项'） |
| 解析 | `parser_stmt.py:959 _parse_self_assignment` 专门吃这个形状 → SelfAssignment / 折叠 target | **无任何折叠**（parser 只在「粘连方法调用 己方法()」处折叠成 `己.方法`，见 code_generator.py:3517 注释；裸属性引用不在其列） |
| codegen src 后端 | `code_generator.py:2531-2535` SelfAssignment → `self.X = …` ✅ | `_resolve_identifier_name`（:4342-4359）：`_map_self_prefix`（:4318）只匹配裸 `己`/`自` 与 `己.`/`自.` 前缀；类属性分支（:4356）按**整名** `raw_name in _class_attr_names` 匹配——`己名称` 不在（表里是 `名称`）→ 落空，发射裸名 |
| codegen unified 后端 | 赋值 target 已被 parser 折叠成 `Identifier('self.项')`（本机 AST 实测）→ 发射正确 | `_resolve_name`（code_generator_unified.py:586-611）同样只匹配裸/带点前缀，**且该后端根本没有类属性回退分支**（源码中无 class_attr_names）→ 发射裸名 |

冒烟复现（本机，只读编译）：`列表追加(己项, 值)` → `_light_builtin.列表追加(己项, 值)`；`返 己名称` → `return 己名称`；同源码里 `己项 为 列表创建()` → `self.项 = …` 正确。**两个后端同病**。

### 3.3 为什么说这是缺陷而不是期望过时

- 光明语规范里 `己X`/`自X` 是 self 引用的粘连写法（赋值位被专门支持并正确工作，大量既有测试/examples 在用）；同一写法在读取位 NameError，属读写不对称的实现缺口，不是测试钉错。
- 修复判据明确：类方法内、name 以 `己`/`自` 开头且**剩余部分 ∈ 当前类属性名集合** → `self.剩余`。放 `_resolve_identifier_name`（src 后端）与 `_resolve_name`（unified）两处，同口径。
- 误伤护栏：`己方`/`自己`/`己方情报` 这类普通标识符不得被拆——白名单判据（剩余 ∈ _class_attr_names）天然规避；改后必须互举反跑（677 .light 零新增解析失败）+ 0.82 定向验证。

### 3.4 R59 修复路径（14 条，中）

一条 codegen 修复（两后端 `_resolve_*` 各加一个分支）预计 14 条同时转绿；建议归 R59 第一优先（改动集中、判据明确），验证配对：本批 14 条 + `tests/test_context_manager.py` 定向子集 + 互举反跑。

---

## 四、归类输出（任务书 §六.5 要求）

| 类别 | 条数 | 明细 |
|---|---|---|
| **R59 可修（codegen 一处修复）** | 14 | 粘连 `己X` 读取位不展开（B 4 + C 10），src+unified 两后端 `_resolve_*` 同加类属性白名单分支 |
| **R59 可修（测试期望更新）** | 21 | L-096 helper 形态 20 条 + `'=='` 预置误伤 1 条（test_为搭配函数调用） |
| 需语义评审 | 0 | — |
| 测试期望更新以外的「改 codegen」 | 0 | 21 条期望过时不需要动 codegen |
| 疑似已变化待全量确认 | 0 | 100010 交叉核对全部一致 |
| **合计** | **35** | 21（测试期望）+ 14（codegen 缺陷） |

重点文件分布（与任务书 §六.3 对账）：

| 文件 | 条数 |
|---|---|
| tests/test_context_manager.py | 11（7 代码生成断言 + 4 类/成员访问） |
| tests/unit/test_v35_chained_call.py | 9（5+4） |
| tests/unit/test_v34_syntax_sugar.py | 4 |
| tests/integration/test_class_system.py | 5 |
| tests/test_frontend_blockers_run.py | 3 |
| tests/test_async_class_method.py / test_level6_types.py / test_edge_cases.py | 各 1 |

---

## 五、附：本任务产出的证据可复核点

- 本机冒烟均为只读编译（LightParser/LightCompiler + 两个 codegen），未 exec 任何 NameError 场景、未跑 pytest；
- 词法证据：`Lexer().tokenize('列表追加(己项, 值)。')` → IDENTIFIER '己项'；
- AST 证据：构造器 `Assignment.target = Identifier(name='self.项')`（parser 已折叠赋值位）vs `FunctionCall.arguments[0] = Identifier(name='己项')`；
- junitxml 交叉核对：`reports/_082_lm_results_2026-09-18-100010.xml`，35 条 key=(classname,name) 全部命中 failure/error，message 与 072454 一致（4 条仅空白差异：a24×2、a25、edge_cases）。
