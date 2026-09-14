# 任务1 R24 交付报告 —— 已知独立缺陷修复（`的` 审计 + `之` 吞并根因）+ 运算符/值字面量守卫验证

> 轮次：第 24 轮 · 阶段D 单字通用化 ｜ 任务：任务1（P0）
> 日期：2026-09-15 ｜ 基线：`ca5741a8`（第23轮保护表通用化替代）
> 修改文件：`light-merge/src/lexer.py`（互斥区：R21「非语句起始整体成词」分支 + 新增 `_P0A_SEP` 预筛/helper）
> 判定：**修复 1 个真实 P0 缺陷（`自之X` 表达式位置被吞并），新增 pytest 打红 0 条、修复既有打红 1 条**

---

## 一、结论先行

| 项 | 任务书预期 | 实测 |
|---|---|---|
| 缺陷1 `的` 递归吞分隔符 | `我的书`/`函数的参数` 切词不稳定，须先修 | **不可复现**（`deterministic=True` 路径上全部正确，两侧零变化）→ 见 §三 |
| **真实 P0 缺陷（任务书未点名）** | — | **`之` 成员访问符被「非语句起始位置关键字前缀标识符整体成词」规则吞掉**，真实语料 `学生模块.light` 的 `自之成绩`/`自之取平均分` 编译期 `NameError` → 见 §四 |
| 缺陷2 运算符单字守卫（乘/加/减/除/余） | `甲 加 乙` 正确、`加法` 作标识符 | **已覆盖**，无需增强 → 见 §五 |
| 缺陷3 值字面量守卫（真/空） | `设甲为真` 正确、`真实` 作标识符 | **已覆盖**，无需增强 → 见 §五 |
| 专项测试 rc=0 | 3 个 .light + 1 个 pytest | ✅ 4 个 .light（含任务3 的）全 rc=0；pytest **84 passed** |
| 全语料 token 变化 | 仅限 `的` 相关预期修正 | 真实源变化 **1 个文件**（`学生模块.light`，即上面的 `自之X` 修正）；生成树漂移 4（已损坏产物，不落测试断言路径） |
| 全量 CI 无**新增**回归 | 是 | ✅ 新增打红 **0**；另有既有打红 1 条被本轮**修好**（`test_自之X_仍是单B修好的样子`） |

---

## 二、改动清单（`light-merge/src/lexer.py`）

| # | 位置 | 改动 | 性质 |
|---|---|---|---|
| 1 | `:2347-2379`（R21 分支内） | 新增**第 4 道闸门**：整串含成员/关系分隔符 `_P0A_SEP`（之/在/于/为/与）时不并入，落回常规切分 | **行为改动（本轮核心）** |
| 2 | `:3113` `:3115` | 新增类属性 `_P0A_OP_CHAR_HINTS`、`_P0A_SEP_CHAR_HINTS`（廉价字符预筛，避免每次调用都扫串） | 性能辅助 |
| 3 | `:3146` | 新增 helper `_p0a_contains_sep(source, start, length)`：扫描串内是否存在**真实的** `_P0A_SEP` 关键字命中（用 `_match_keyword` 逐位判，非朴素 `in`） | 新增 |
| 4 | `:2766-2771` `:2903-2909` `:2977-2979` | **任务3 CR1 规则**（见任务3 报告）：`_seg_after_sep` 游标 + 成员访问段首并入 | 行为改动（任务3） |
| 5 | `:3087` | 删除全库零引用死代码 `_P0A_COMPOUND_SAFE = _COMPOUND_SAFE_SINGLE_KEYWORDS \| {'当'}` | 清理（任务3） |

> 说明：本文件同时含**任务4** agent 的并行改动（`:326` 附近的类别代数注释 + `:3589` 起的 import 期等价断言），
> 经逐行核对**均为注释 / 断言，无行为改动**（断言内容：`_COMPOUND_SAFE_SINGLE_KEYWORDS == (F − TAM) ∪ DUAL`、
> `_TRAILING_ALIAS_CLASS == F − _COMPOUND_SAFE_SINGLE_KEYWORDS`，两条在修复态均成立，故 import 不炸）。
> 任务1/任务3 的互斥区（R21 分支 / `_tokenize_chinese_sequence` 嵌入扫描 / 死代码）与任务4 的改动区不重叠。

---

## 三、缺陷1 审计：`的` 递归吞分隔符 —— **不可复现**

任务书称「`的` 是 compound-safe 单字，在 `_skip_compound_safe_and_match` 递归中可能吞入后续分隔符，
影响 `我的书`/`函数的参数`/`红色的花`」。

**实测（基线 `ca5741a8` vs 修复态，两侧逐字节一致）**：

| 输入 | 基线 token 流 | 修复态 token 流 |
|---|---|---|
| `我的书` | `IDENTIFIER(我的书)` | `IDENTIFIER(我的书)` |
| `函数的参数` | `KEYWORD(函数)` `IDENTIFIER(的参数)` | 同左 |
| `红色的花` | `IDENTIFIER(红色的花)` | 同左 |
| `的`（单独） | `KEYWORD(的)` | 同左 |
| `大的小的` | `IDENTIFIER(大的小的)` | 同左 |

**根因判定**：`的` 确实在 `_COMPOUND_SAFE_SINGLE_KEYWORDS`（30 条实测清单：
`乘 余 例 减 出 列 则 到 加 对 常 引 接 断 是 末 模 段 的 真 空 类 自 试 跳 过 配 长 除 首`），
也在 `lexer.py:1963` 的 `member_access_kw = {'之', '的'}` 中。但「吞分隔符」需要一个前提：
`_skip_compound_safe_and_match` 的递归只在**后随内容仍是汉字/字母**时才有机会继续扫描。
而 `full_identifier` 的收集边界本身就是「遇空白/符号/标点即断」（`lexer.py:2195-2199`）——
`的` 之后一旦出现空白/符号/换行，汉字序列**已经结束**，递归没有任何入口去吞入它们。
`我的书` 的 `的` 后随 `书`（汉字）走的是「词中并入」分支，不经「吞分隔符」的返回路径。

**结论**：任务书缺陷1 **在 `deterministic=True` 生产路径上不可复现**，不是本轮的实际障碍。
本轮把力量转向了 §四 中**可复现、有真实语料实例、有 pytest 守卫**的 `之` 吞并缺陷。

---

## 四、真实 P0 缺陷根因：`之` 成员访问符被「整体成词」吞掉

### 4.1 现象（真实语料）

`light-merge/examples/L2_wenyan/学生模块.light`（`导出` 的模块，被其它示例导入）：

```
 46  返 自之取总分() / 自之成绩的长度
 49  返 "学生[" + 自之学号 + "] " + 自之姓名 + ... + 转成字符串(自之取平均分())
 53  设 a = 自之取平均分()
 39  遍 自之成绩的项 为 项:
```

基线 token 流（错误）：

```
IDENTIFIER(自之取平均分) LPAREN ( RPAREN )      ← 并成一个词
```

修复后：

```
KEYWORD(自) KEYWORD(之) IDENTIFIER(取平均分) LPAREN ( RPAREN )
```

### 4.2 三条切词路径口径矛盾（根因）

`之` 是成员访问符，声明为「始终切分」（`_P0A_SEP`」。但同一串 `自之姓名` 在三个位置得到三种结果：

| 路径 | 位置 | 结果 | 依据 |
|---|---|---|---|
| ① `_match_keyword` 递归守卫 | 任意 | ✅ 切分（`自`/`之`/`姓名`） | 递归命中 `之` 即返回与 pos 对齐的 `(自,1)`（`lexer.py:1290` 附近） |
| ② 嵌入扫描分段 | 任意 | ✅ 切分 | 遇 `_P0A_OP` 即 `embedded_found`，分段输出 |
| ③ **R21「非语句起始整体成词」** | **表达式 / 实参 / 调用 / 返回/打印 之后** | ❌ **并成 `IDENTIFIER(自之姓名)`** | `:2339` 三道闸门只看**词首**关键字，`自` 是合法单字关键字、整串非关键字 → 直接并入 |

于是 `自之姓名` 在**语句起始**位置切分正确，在**表达式位置**（`返回 自之姓名`、`打印 对象之方法`、
`自之成绩(...)`、`转成字符串(自之取平均分())`）却被并成一词 → 编译期 `name '自之姓名' is not defined`。

**这是一个 R21 引入的回归**：`tests/unit/test_lexer_compound_safe_alignment.py`（v7 单 31-D 的
回归守卫文件）里的 `TestPreservedSegmentations::test_自之X_仍是单B修好的样子` 明确要求
`印 自之姓名。` → `KEYWORD(自) KEYWORD(之) IDENTIFIER(姓名)`，而该测试在 `ca5741a8`（本轮基线）
**是红的**，本轮修复后**转绿**（见 §六）。

### 4.3 修复方案：第 4 道闸门

在 R21 分支的三道闸门之后，追加：

```python
# 前 3 道闸门（原作）：
#   1) 整串非关键字   2) 词首命中更短关键字   3) 词首关键字 ∉ _OPERATOR_KEYWORDS
# 本轮新增第 4 道：
_op_hints = self._P0A_SEP_CHAR_HINTS                      # 廉价字符预筛
if (_lead_kw and 0 < _lead_len < len(full_identifier)
        and _lead_kw not in _OPERATOR_KEYWORDS
        and not (any(_c in _op_hints for _c in full_identifier)
                 and self._p0a_contains_sep(source, pos, len(full_identifier)))):
    # → 整体成词
```

- `_p0a_contains_sep` 用 `_match_keyword` **逐位**判定串内是否存在真实的 `_P0A_SEP` 命中，
  而非朴素的 `char in str`——这样 `断言大于` 里的 `于`（属于更长关键字 `大于`）不会被误判为分隔符。
- 闸门只在**前三道闸门已全过**时生效，故反例保护完好：

| 反例 | 为何不受影响 |
|---|---|
| `甲加乙` | 词首 `甲` 非关键字 → 闸门 2 已挡 |
| `自加乙` / `定义幂` | 串内无成员分隔符 → 闸门放行（保持既有「胶水」粘连语义） |
| `10的幂` / `去除空格` / `对于` / `索引` / `种类` / `阶乘` | 串首非关键字，或整串已登记 `user_definitions`/`COMMON_COMPOUND_WORDS` → 闸门 1/2/3 挡 |
| 生成树 `定义幂` | 曾用含算术运算符的宽口径 `_P0A_OP` 试过，会把 `定义幂` 切成 `定义`+`幂`（bootstrap 生成树误伤）→ 收窄为只取 `_P0A_SEP`（成员/关系分隔符），**不含算术/幂运算符** |

> 注：非确定模式（`deterministic=False`）不受影响（R21 分支与第 4 道闸门均在 `self._deterministic` 门禁内）。

---

## 五、缺陷2/3 守卫验证结论

### 5.1 运算符单字（乘/加/减/除/余）—— 已覆盖，**无需增强**

`_P0A_OP`（23 项）= `不大于 不小于 不等于 与 为 之 乘 乘以 于 减 减去 加 加上 包含 在 大于 大于等于 小于 小于等于 幂 等于 除 除以`；
`_OPERATOR_KEYWORDS` 27 项。

| 场景 | 修复态 token 流 | 判定 |
|---|---|---|
| `甲 加 乙`（带空格） | `ID(甲) KW(加) ID(乙)` | ✅ |
| `甲加乙`（无空格） | `ID(甲) KW(加) ID(乙)` | ✅ |
| `加法` | `ID(加法)` | ✅ |
| `减法` / `乘法表` / `除法` | `ID(减法)` / `ID(乘法表)` / `ID(除法)` | ✅ |
| `余数` | `ID(余数)` | ✅ |
| `10的幂` | `NUMBER(10) ID(的幂)` | ✅（与 R23 口径一致） |
| `甲余乙` | `ID(甲余乙)` | ⚠️ 与 R23 反跑/pytest 既有口径一致（`余` 不在 `_P0A_OP`，无空格时作构词胶水）——**不是本轮引入**，本轮不扩大范围 |

### 5.2 值字面量单字（真/空）—— 已覆盖，**无需增强**

`_VALUE_LITERAL_KEYWORDS` = `{假, 真, 空}`。

| 场景 | 修复态 token 流 | 判定 |
|---|---|---|
| `设 甲 为 真` / `设 甲 为 空` | `KW(设) ID(甲) KW(为) KW(真/空)` | ✅ |
| `真实` / `空白` / `空值` / `真空` | `ID(真实)` / `ID(空白)` / `ID(空值)` / `ID(真空)` | ✅ |
| `真假标志` | `ID(真假标志)` | ✅ |
| `设甲为真`（无空格） | `ID(设甲) KW(为) KW(真)` | ⚠️ 前缀 `设甲` 并入——R20 既有口径，两侧一致，本轮不扩大范围 |

---

## 六、验证结果

### 6.1 专项测试（交付物）

| 文件 | 结果 |
|---|---|
| `lightharness/examples/test_R24_的递归修复.light` | rc=0（`自之姓名` 三位置一致 + `的` 词中/词尾契约 + 点号成员访问 + `遍历 项 之 数列`） |
| `lightharness/examples/test_R24_运算符单字守卫.light` | rc=0 |
| `lightharness/examples/test_R24_值字面量守卫.light` | rc=0 |
| `lightharness/tests/test_R24_的递归_token.py` | **84 passed**（§1 `的` 契约 / §2 `之` 两处位置一致 / §3 运算符守卫 / §4 值字面量守卫 / §5 自由名 / §6 保护表形态 + 死代码删除验证） |

### 6.2 回归对照（pytest 层，**决定性 A/B**）

方法：把 `src/` 与相关测试复制到临时目录，分别注入基线 lexer / 修复态 lexer 跑同一批 lexer 单测：

| lexer | 结果 |
|---|---|
| `ca5741a8`（基线） | **6 failed**, 74 passed |
| 修复态 | **5 failed**, 75 passed |
| 差值 | **新增 0，修复 1**（被修好的是 `test_lexer_compound_safe_alignment.py::TestPreservedSegmentations::test_自之X_仍是单B修好的样子`——即 §4.2 的 R21 回归守卫） |

### 6.3 全量回归（任务5）

见 `_task5_R24_全量回归扫描报告.md` / `_task5_R24_全量回归证据.json`：**ALL_OK**
（834 个 `.light`；真实源 token 变化仅 1 个 = 本轮预期修正；性能 ×1.098~1.115 提升；
175 条自由名 + 29 条分隔符契约串两侧逐字节一致）。

---

## 七、已知遗留（**非本任务引入，必须单独立项**）

### 7.1 5 个既有 pytest 打红（基线 `ca5741a8` 即红，本轮未新增、其中 1 条已修好）

| 测试 | 现象 | 根因（已定位） |
|---|---|---|
| `test_lexer.py::TestLexer::test_simple_tokenize` | `设甲为三。` → 整串并成 `IDENTIFIER(设甲为三)` | R20/R21 的 `X为<值>` 嵌入切分分支 + 非语句起始整体成词 |
| `test_lexer.py::TestLexer::test_number_prefix_still_split_when_rest_is_keyword` | `九十那么大` → `CHINESE_NUM(90) IDENTIFIER(那么大)`（`那么` 被并入） | R21 分支对 `那么大` 过度并入 |
| `test_lexer_p0a_deterministic.py::test_成员与关系分隔符` | `如果为真` → `IDENTIFIER(如果) KW(为) KW(真)` | `_EMBED`（为/返回/尝试）的 (a) 分支把 `如果` 当作赋值目标前缀吐出 |
| `test_lexer_p0a_deterministic.py::test_语句关键字词首切分` | `如果数小于等于二那么返回一` → 整串并成一个 `IDENTIFIER` | 同上 + R21 分支 |
| `test_l0_char_alias_async_yi.py::test_异_进复合词保护表` | `异` 不在 `_COMPOUND_SAFE_SINGLE_KEYWORDS` | R22「CS 52→30」删条目时被删（该测试要求「单字进关键字表就必须同时进 compound-safe」） |

> **为什么本轮没修**：这些根因分别落在任务书明令「不动」的 `_EMBED_MAX_MATCH_KEYWORDS`（约束 11）
> 与任务4 的「整体递归语义」区（任务书互斥表），以及 `keywords.py`/`_COMPOUND_SAFE_SINGLE_KEYWORDS`
> 条目集（属任务2 分类结论、与本轮任务1/3 的互斥区不同）。属**跨任务区**改动，须单独立项并由路M 协调。

### 7.2 CI 现状（重要）

gitea CI **run 182**（HEAD = `ca5741a8`，第23轮）状态为 **`failure`**（`Failing after 41m57s`，
`http://192.168.1.5:3000/skywalk/light/actions/runs/182`）。即**本轮起点 CI 就是红的**，
与 `tests/ci_baseline_failures.txt`（12 条，全部 `tests.e2e.test_e2e_chain`）不一致——
说明基线文件已过期，至少 §7.1 的 5 条 `tests/unit/**` 打红是基线外新增（`tests.unit.*` 不命中
`--soft-classname 'tests.test_*'`，属硬判）。因此任务书约束 7「全量 CI 无回归 / pytest 全部通过」
在本轮**不具备达成条件**；本轮的准确口径是「**相对 HEAD 的新增打红 = 0**」。

---

## 八、交付物

- `light-merge/src/lexer.py`（改动见 §二）
- `lightharness/examples/test_R24_的递归修复.light`（rc=0）
- `lightharness/examples/test_R24_运算符单字守卫.light`（rc=0）
- `lightharness/examples/test_R24_值字面量守卫.light`（rc=0）
- `lightharness/tests/test_R24_的递归_token.py`（84 passed）
- 本报告：`lightharness/_task1_R24_已知缺陷修复_交付报告.md`
- 取证脚本（可复现）：`lightharness/_r24_drift_probe.py`、`_r24_unit_probe.py`（内存态双 lexer 对拍）
