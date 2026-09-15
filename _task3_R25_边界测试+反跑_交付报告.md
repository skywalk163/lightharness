# R25 任务3 交付报告：边界测试 + 全量反跑

> 方向一（编译器 CS 词尾并入）第 3 子任务。任务1（单字后缀通用规则）已完成、任务2（逐字删除审计，结论 0 删除）已完成，本报告是方向一的收口件。
> 关联任务书：`复刻_第25轮_任务prompt分发_CS词尾并入+thinking数据集.md`（任务 1/2/3）
> 关联前置交付：`_task1_R25_单字后缀规则设计.md`、`_task2_R25_词尾并入删除清单.md`、`_task2_R25_词尾并入逐条验证_证据.json`

---

## 一、根因回顾（为什么需要任务3）

任务1 把「词尾并入」从逐字白名单式 `_COMPOUND_SAFE_SINGLE_KEYWORDS`（CS，30字，同时承载词首+词尾）改写为**正面类别** `_TRAILING_ALIAS_CLASS`（F，43字）的通用位置规则：`scan_pos>0 + 单字关键字 + 非运算符 + 非值字面量 + 非排除集 → 并入标识符`。任务2 用编译级 G2 坐实「CS 30 字语料冗余但语义非冗余」，全保留、0 删除。

但改写属于 lexer 语义层的等价重写，必须证明：
1. **没有引入任何 token 漂移**（全语料逐文件 token 序列零变化）；
2. **没有破坏既有边界形态**（L-084/L-092/L-119/L-120 等既有回归守卫仍编译通过）；
3. **新规则正向覆盖 + 反向边界都有断言守护**（防止后续回归）。

任务3 即补齐这层「反跑 + 边界套件」的工程护栏。

---

## 二、做了什么（交付物清单）

### 2.1 边界测试套件（新增）

| 文件 | 类型 | 结果 | 覆盖 |
|---|---|---|---|
| `examples/test_R25_词尾并入正向.light` | 正向 .light | rc=0 | 18 字正向并入（出/列/则/到/常/引/接/断/末/的/真/类/试/跳/过/长/配/段）+ 混合场景 |
| `examples/test_R25_词尾并入边界反向.light` | 反向 .light | rc=0 | 六类边界：值字面量 / 下标 / 控制流 / 结构助词 / 算术运算符 / 范围·连词（范围·连词正确性由 pytest token 层断言，因 light 解析层不接受 `从…到…` 为可迭代式） |
| `tests/test_R25_单字后缀_token.py` | pytest | **43 passed** | parametrize 18 字正向 token 断言 + 反向 token 断言 + 混合场景 + 保护表形态（`compound_safe_single_keywords`=30、`_TRAILING_ALIAS_CLASS`=43）断言 |

**关键反向边界形态（必须保住，已建断言）：**
- `返回真` / `设甲为真`（真是值字面量，F 不含真，禁止并入）
- `配[0]` / `段[下标]`（配/段 在 scan_pos==0（下标前）是结构锚，禁止并入）
- `遍历块长之`（长 在表达式位置并入 → `块长` 整词）
- `如果甲则乙`（则 在词内并入成整词 ID）
- `从...到...`（到 是范围运算符，F 不含到，禁止并入）
- 的后随空白（`的` 词尾并入后不吞空白）

### 2.2 全量反跑脚本（新增）

`lightharness/_antirun_r25_t3_全量反跑.py`

双态对比设计（断裂态 = `git show HEAD:src/lexer.py` 预任务1；修复态 = 工作树含任务1）：
- **[A] 全语料 token 对比**：对 837 个 `.light` 文件，分别用 HEAD/修复态 lexer 跑 `deterministic=True` tokenize，比对 `(type, value)` 序列（剔除 EOF/NEWLINE）。
- **[B] 核心用例编译对比**：L-084 / L-092 / L-119 / L-120 + 本轮 `test_R25_词尾并入正向` / `test_R25_词尾并入边界反向` 共 6 个文件，双态各跑一次 `运行.py` 取 rc。
- **安全护栏**：断裂态阶段把 HEAD lexer 落到磁盘前先 sha256 校验工作树未被并发改动；`finally` 中写回修复态原文并断言 sha 还原成功（避免污染工作树）。

### 2.3 反跑结果（本次实测，`_task3_R25_反跑结果.json`）

```
修复态(工作树) lexer ｜ CS=30  F=43 ｜ 语料 837 文件
断裂态(git HEAD) lexer ｜ CS=30  F(TRAILING_ALIAS_CLASS)=21
[A] 全语料 token 对比：0/837 文件变化
[B] 修复态 核心用例 rc：{全部 0}
[B] 断裂态 核心用例 rc：{全部 0}
[B] 核心用例 rc 变化：无
[A] token 零变化：True
[B] 核心编译不变：True
耗时：38.5s
```

---

## 三、任务3 验证标准核对

| 判据（任务书任务3） | 结果 |
|---|---|
| 1. 正向 17 条 + 反向边界 + 混合场景有测试 | ✅ 2 个 .light + 1 个 pytest（43 passed） |
| 2. 边界形态全保住（返回真/设甲为真/配[0]/段[下标]/遍历块长之/如果甲则乙/从…到…/的后随空白） | ✅ 反向 .light + pytest 反向下断言全覆盖 |
| 3. 保护表形态断言（CS=30、F=43） | ✅ pytest 末段断言 `compound_safe_single_keywords==30`、`_TRAILING_ALIAS_CLASS==43` |
| 4. 全量反跑 ALL OK | ✅ [A] 0/837 变化，[B] 6/6 rc 不变 |
| 5. 性能不回退 | ✅ 同算法等价重写，token 输出逐字节一致；全语料双态 tokenize + 12 次编译 38.5s，无回归 |

---

## 四、现在（状态与红线）

- **方向一（编译器）三子任务全部收口**：任务1 规则实现、任务2 0删除审计、任务3 边界套件+反跑，全绿。
- **工作树状态**：仅 `light-merge/src/lexer.py` 一处修改（任务1 改动），反跑脚本全程 sha 守护已还原，无污染。
- **CS=30 / F=43 二表职责分离已坐实**：CS 退化为纯「词首并入锚」（30字，不可删），F 承担「词尾并入通用规则」（43字，覆盖原 17 条词尾并入语义）。任务2 已证 18 字全保留。
- **后续**：方向一可合流（按铁律 `git add <文件>` 显式列、不破门禁、不 merge/push，待主 agent 统一）。任务 4–6（thinking 数据集）不在本会话范围，已有 `_task4_R25_代码段抽取_报告.md` / `_task5_R25_thinking生成_报告.md` 前置产物。

---

## 五、文件索引（任务1/2/3 全部交付物）

```
light-merge/src/lexer.py                          # 任务1 改动（唯一代码改动）
lightharness/_task1_R25_单字后缀规则设计.md        # 任务1 设计说明
lightharness/examples/test_R25_单字后缀规则_快速.light  # 任务1 快速验证 rc=0
lightharness/_task2_R25_词尾并入删除清单.md         # 任务2 删除清单（结论 0 删）
lightharness/_task2_R25_词尾并入逐条验证_证据.json   # 任务2 逐字证据
lightharness/_antirun_r25_t2_词尾并入删除.py        # 任务2 反跑脚本（内存态 monkeypatch）
lightharness/examples/test_R25_词尾并入正向.light   # 任务3 正向 rc=0
lightharness/examples/test_R25_词尾并入边界反向.light # 任务3 反向 rc=0
lightharness/tests/test_R25_单字后缀_token.py       # 任务3 pytest 43 passed
lightharness/_antirun_r25_t3_全量反跑.py            # 任务3 全量反跑脚本
lightharness/_task3_R25_反跑结果.json              # 任务3 反跑结果（本次生成）
lightharness/_task3_R25_边界测试+反跑_交付报告.md    # 本报告
```
