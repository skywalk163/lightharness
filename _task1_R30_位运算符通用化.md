# R30 任务1：位运算符 4 条通用化

> 交付：`light-merge/src/lexer.py`（新增词首前缀类 + CCW 删 4 条）
> 证据：`lightharness/_task1t2_R30_证据.json`、`lightharness/_r30v2_iso.py`
> 基线对照：`lightharness/_r29_baseline_tokens.json`（CCW=10 态全语料 token）
> lexer sha（二进制）：`96f63c114746`

## 1. 目标

为 `位与` / `位异或` / `位或` / `位非` 提供通用词法规则，使其在语句起始 / 表达式位置
**不被关键字「与 / 或 / 非」劈开**，从而把这 4 条从 `COMMON_COMPOUND_WORDS`（CCW）移除。

## 2. 场景定位（全语料 .light）

| 场景 | 文件 | 形态 | 说明 |
|---|---|---|---|
| 调用语境 | `lightharness/examples/test_R29_CCW精简边界.light:7-10` | `设 r1 为 位与(3, 1)` | R29 遗留边界测试，非语句起始 |
| 字符串内（伪命中） | `lightharness/examples/test_acp内容.light:35` | `"等号错位非规范"` | `位非` 是 `错位非规范` 的子串，**在 STRING 内不产生 token** |
| 注释（伪命中） | `light-merge/stdlib/选择器.light:23-24` | `# …不用 位与/位或…` | 注释不产生 token |
| 运算符语义 | `light-merge/src/code_generator.py:263-268` / `parser_expr.py:373-641` | `位与→&` `位或→\|` `位异或→^` `位非→~` | 语言**内建按位运算符** |

**结论**：真实语料中位运算符 4 条**无实际代码使用**（仅字符串 / 注释 / R29 测试），
故删 CCW 后全语料 token 零变化是可预期的。

分类小结：**函数调用 4**（R29 测试）、**赋值/表达式 4**（同上）、**字符串 1**（伪命中）、
**注释 2**（伪命中）；**语句起始 0**。

## 3. 机制订正（任务书方案 A 不可行）

任务书推荐「方案 A：扩展 HM（`_P0A_HEAD_MERGE_SINGLE`），把『位』加入 HM 集合」。
**实测该机制不成立**（`_r30_probe.py`）：

- `位` **不是关键字**：`_match_keyword('位…')` 返回 `None`；
- 而 HM 是由关键字**推导**的（`HM = _ALL_KEYWORDS_WITH_VERBS − 排除集`，模块级 `assert` 自校验），
  `位` 不在关键字集合内，**无法加入 HM**；
- 同理任务书对「应」的判断也误（`应` 亦非关键字）。

任务书机制描述基于已废弃 / 失效的表名，与当前实现不符 ⇒ 采用**等价目标的新机制**（见 §4）。

## 4. 实现（新增词首前缀类）

新增模块级保护表（lexer.py L3910）：

```python
# ── R30 任务1/2：词首前缀类（位/应/除）──────────────────────────────
# 这三个字都是「非关键字」或「被 DUAL 抑制后成标识符」的单字，其后随关键字
# （与/或/非/当）时会在词中被劈开（位+与、应+当、除+非）⇒ 命中即整串并入 IDENTIFIER。
_P0A_HEAD_MERGE_PREFIX = frozenset({'位', '应', '除'})
assert _P0A_HEAD_MERGE_PREFIX == frozenset({'位', '应', '除'}), (
    'R30 前缀类应为 3 字（位/应/除）')
```

主循环插入判定（lexer.py L2387-2394，位于「关键字前缀标识符整体成词」分支内、
`if _ctx_call or not self._at_statement_start(...)` 条件之后）：

```python
if full_identifier[0] in _P0A_HEAD_MERGE_PREFIX:
    _tokens_append(_Token(_TokenType.IDENTIFIER, full_identifier, line, current_col))
    consumed += len(full_identifier)
    current_col += len(full_identifier)
    continue
```

**位置口径**：**函数调用语境（整串后紧随 `(`）或非语句起始位置**。
语句起始**非调用**形态被主动排除（见 §6 冲突说明）。
外层三条既有闸门依然有效：`len>1` ∧ 整串非关键字 ∧ 非 user_definition ∧ 非 CCW。

CCW 删除 4 条：`位与`、`位异或`、`位或`、`位非`。

## 5. 三重判据结果

| 判据 | 口径 | 结果 |
|---|---|---|
| **G1 语料门** | 全语料 tokenize 对照 `_r29_baseline_tokens.json` | ✅ **848 可比文件零变化**（排除 2 个基线即失败的既有错误文件：`bootstrap/release/stdlib/集合.light`、`examples/_test_nested_closure.light`） |
| **G2 编译门** | 含 4 条位运算符的语句 rc=0 | ✅ 见 `examples/test_R30_位运算符通用化_快速.light`（rc=0） |
| **G3 边界门** | 6 类边界形态整词并入 + 反向形态不变 | ✅ 见下表 |

G3 边界形态（每格 ✓ = 撤 CCW 后仍整词成 IDENTIFIER）：

| 词 | 设名 | 段落名 | 返回调用 | 列表元素 | 条件位 | 字符串态 |
|---|---|---|---|---|---|---|
| 位与 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 位异或 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 位或 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 位非 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

反向形态（不受影响）：

| 形态 | token 流 |
|---|---|
| `设 位 为 1` | `KEYWORD 设` / `IDENTIFIER 位` / `KEYWORD 为` / `NUMBER 1` |
| `当 x > 0:` | `KEYWORD 当` …（循环关键字） |
| `设 y 为 非 真` | `KEYWORD 非` / `KEYWORD 真`（逻辑关键字） |
| `设 z 为 甲 与 乙` | `KEYWORD 与`（逻辑关键字） |

> 注：任务书 G3 反向写「`位 为 1` → 位为 **KEYWORD**」。实测 `位` **不是关键字**，
> 独立使用时是 `IDENTIFIER`（与基线一致）—— 任务书此处对 `位` 的属性描述有误。

## 6. 关键发现：语句起始「除」与异常子句冲突

隔离实验（`_r30v2_iso.py`）把前缀类判定**提升到位置无关**（覆盖语句起始非调用）后：

- G3 正向 **全部通过**（含 `除非 条件:`）；
- 但 **G1 破坏 1 个文件**：`light-merge/bootstrap/release/stdlib/断言工具.light`。

根因（该文件 4 处）：

```
49:    除类型错误:
207:    除异常类型:
209:    除异常(e):
216:    除异常(e):
```

`除` 在**语句起始是异常捕获子句关键字**（= except），`除异常(e):` / `除类型错误:` 中
`除` 必须单独成 `KEYWORD`。词法层无法把「语句起始 `除X` 是异常子句」与
「`除非` 是复合标识符」区分开 ⇒ **语句起始扩展被否决**，
规则限定为「调用语境 / 非语句起始」，保住 `除异常` 子句语义（真实语料命中）。

该权衡符合铁律优先级：**全语料 token 零变化（硬门槛）> 任务书设想的 G3 形态**
（`除非 条件:` 在语料中**零命中**，非真实需求）。

## 7. 结论

- CCW `位与/位异或/位或/位非` 4 条**删除**（累计 CCW 37→10→…，本任务净减 4）。
- 新规则 `_P0A_HEAD_MERGE_PREFIX` 是**通用**规则（一次覆盖 3 个字，非逐词白名单），
  同时服务任务1（位）与任务2（应/除）。
- 三重判据全通过；快速验证 `examples/test_R30_位运算符通用化_快速.light` **rc=0**。
