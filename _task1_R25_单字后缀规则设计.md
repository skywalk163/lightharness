# R25 任务1交付：单字后缀位置上下文规则

> 日期：2026-09-15 ｜ 仓库：light-merge（`src/lexer.py`）｜ 证据在同目录 `_task1_*.json` / `_r25_p5_verify.py`
> 一句话结论：**把「单字词尾并入」从「保护表补集」改成「正面规则」，全语料 834 文件 token 零变化、18 项边界形态零变化、词法单测失败集零新增。**

---

## 一、改动前：为什么必须改

第 23 轮任务 2 实现了**多字**后缀位置规则（`_P0A_SUFFIX_SPLIT_KW`）：

```
scan_pos > 0（词中/词尾） + 多字关键字 + 非运算符 + 非排除集  ⇒  并入标识符
```

其**单字**对称版当时被写成 `_TRAILING_ALIAS_CLASS = F − _COMPOUND_SAFE_SINGLE_KEYWORDS`（21 字），
即**对保护表（CS）取补集**。这个写法带来一个结构性后果：

| 位置 | CS 成员 | 非 CS 成员 |
|---|---|---|
| 词首 | **并入**（`_tokenize_chinese_sequence` 首层 `_compound_safe` 分支） | 切出 KEYWORD |
| 词中 | 并入（探测循环无条件 skip） | 并入（P0-A 词中规则） |
| 词尾 | 并入（同上，借 CS 分支） | 并入（仅当 ∈ TAM） |

**CS 一词同时承载「词首并入」与「词尾并入」两种能力**，因此撤掉任何一条都会同时失去两种能力
（`长度` → `长`+`度`、`标准输出` → `标准输出失`+`真` 的风险来自词尾那一半）。第 24 轮任务 3 的
清表审计把 13 条判为「语料冗余但语义非冗余」，根因即在此。

本轮把词尾那一半**改成正面规则**，使 CS 退化为纯粹的「词首并入锚」，两种能力解耦。

## 二、改动内容（`src/lexer.py`）

### 2.1 新增单字排除集 `_P0A_SUFFIX_SPLIT_SINGLE`（类体，`_P0A_SUFFIX_SPLIT_KW` 之后）

```python
_P0A_SUFFIX_SPLIT_SINGLE = frozenset(
    _k for _k in (_P0A_OP | _OPERATOR_KEYWORDS | _P0A_NEVER_SPLIT
                  | _AWAIT_KEYWORDS | _VALUE_LITERAL_KEYWORDS)
    if len(_k) == 1)
```

**按语义类别整体排除，不逐字补白名单**（与多字规则同口径，避免重蹈「打地鼠」）。五类共 21 字：

| 类别 | 单字成员 | 缺了它会怎样（反例） |
|---|---|---|
| `_P0A_OP`（算术运算符 + 成员/关系分隔符） | 加 减 乘 除 余 幂 之 在 于 为 与 | `甲加乙`、`自之姓名`、`如果为真` 会被并成单标识符 |
| `_OPERATOR_KEYWORDS`（逻辑/比较） | 且 或 非（及其与上表的交集） | `甲或"x"`、`甲且乙`、`甲非乙` 失真 |
| `_P0A_NEVER_SPLIT`（范围/步长/永不切分） | 到 至 步 模 | `从1到10`、`甲步2`、`甲至10`、`模块名称` 断裂 |
| `_AWAIT_KEYWORDS` | 等 | `甲等(乙)` 吞掉 await |
| `_VALUE_LITERAL_KEYWORDS` | 真 假 空 | `返回 真`、`设 甲 为 空` 失真 |

### 2.2 词尾并入类别改为正面推导

```python
# 旧：_ALL_KEYWORDS_WITH_VERBS − _P0A_OP − _OPERATOR_KEYWORDS − _P0A_NEVER_SPLIT
#     − _AWAIT_KEYWORDS − _COMPOUND_SAFE_SINGLE_KEYWORDS − 值字面量      → 21 字
# 新：_ALL_KEYWORDS_WITH_VERBS − _P0A_SUFFIX_SPLIT_SINGLE                → 43 字（≡ F）
_TRAILING_ALIAS_CLASS = frozenset(_k for _k in (_ALL_KEYWORDS_WITH_VERBS
                                 - _P0A_SUFFIX_SPLIT_SINGLE) if len(_k) == 1)
```

**不再对 CS 取补集**。使用点（探测循环 `skip_kw` 判据、输出循环词尾分支）保持原样，
行为差异只出现在「既是 CS 成员、又落在词尾」的情形——见 §三实测为零。

### 2.3 连带修改（注释与断言）

* 文末 import 时自校验断言 ②：`TAM == F − CS` → **`TAM == F`**（防止排除集漂移出五类之外）；
  断言 ①（CS 字面量 == (F−TAM)∪DUAL）保持不变，仍保护 R24 的类别代数不漂移。
* 注释同步：`_VALUE_LITERAL_KEYWORDS` 上方 43 字推导说明、两处「21 字/27 字」旧计数。
* **未**改动 `_COMPOUND_SAFE_SINGLE_KEYWORDS` 字面量（属任务 2 区域）、**未**动 CCW 37 条与
  `_EMBED_MAX_MATCH_KEYWORDS`（本轮红线）。

## 三、验证（脚本 `_r25_p5_verify.py` / `_r25_p2_sweep.py`）

| 判据 | 结果 |
|---|---|
| 全语料 834 文件（lightharness+light-merge 的 examples/src/tests/stdlib/bootstrap）token 序列 | **变化 0 个文件** |
| 边界形态 18 项（值字面量/单字下标/控制流/范围/运算符/结构助词） | **不一致 0** |
| 词尾并入正向 33 项（17 类场景全覆盖） | **不一致 0** |
| 词法单测（test_lexer / test_lexer_p0a_deterministic / test_lexer_compound_safe_alignment / test_lexer_perf / test_l0_char_alias_async_yi） | 失败集与 HEAD 断裂态**完全相同**（6 条既有红，零新增） |
| 保护表形态 | CS 仍 30 条（本轮任务 1 不触碰），TAM 21 → 43 |
| 运行期用例 `examples/test_R25_单字后缀规则_快速.light` | **rc=0** |

为什么 token 零变化却仍然是有意义的改动：改前 CS 成员在词尾的并入**只存在于「探测循环
全 skip」这一条窄路**——一旦同一汉字串里还有其它关键字被判定为 embedded，输出循环会走到
`compound_safe_single_keywords` 分支、把词尾的 CS 成员重新吐成 KEYWORD。改后两条路径口径统一，
这类「口径分裂」被消除；只是现有语料恰好没有触发它的字符串，所以 token 流零变化。

## 四、边界形态实测明细（`_r25_p5_verify.py` 第二组，18/18 保持）

```
返回 真 / 设 甲 为 真 / 设 甲 为 空 / 返回 假        → KEYWORD:真|假|空 独立成词（值字面量）
打印 配[0] / 配[0] / 段[1] / 配[键]                 → IDENTIFIER:配|段 + 下标（L-119 单字别名）
如果 甲 则 乙 / 否则 则 丙                          → KEYWORD:如果|则|否则 正常切分
从 1 到 10 / 从 甲 到 乙                            → KEYWORD:从|到 范围运算符（L-038）
甲 加 乙 / 甲 减 乙                                 → KEYWORD:加|减 算术运算符
我的 书                                             → IDENTIFIER:我的 + IDENTIFIER:书（的后随空白）
遍历 块长 之 项                                     → KEYWORD:遍历 IDENTIFIER:块长 KEYWORD:之 …
长度 为 5 / 设 长度 为 5                            → IDENTIFIER:长度 KEYWORD:为 NUMBER:5
```

## 五、对任务 2 的意义（慎读）

规则化之后，**「词尾并入」不再需要 CS 兜底**——CS 的字面量只剩「词首并入」这一个职责。
这是辞退 CS 条目的**必要前提**；但它不是**充分条件**：词首那一半仍然存在真实的
护栏（详见 `_task2_R25_词尾并入删除清单.md` §三，含编译级回归证据）。
任务 2 的逐条验证结论是：**17/18 条在本轮均不得删除**，CS 保持 30 条。
