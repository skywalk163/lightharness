# 任务2（R28）交付报告 —— 类的类声明上下文词尾并入设计与实现

> 日期：2026-09-15 ｜ 轮次：第28轮 ｜ 范围：`light-merge/src/lexer.py`（user_definitions 前缀匹配判据扩展）
> 对应任务书：`复刻_第28轮_任务prompt分发_CS表2字逐字通用化.md` 任务2

---

## 1. 目标与结论

**目标**：为 `类` 实现「类声明上下文中词尾类并入标识符」规则，使 `类 独立类:` 整词成
IDENTIFIER，从而可从 CS 表移除，且全语料 token 零变化。

**结论**：✅ 达成。`类` 已从 CS 表移除（CS 2→0），全语料 **845 文件 token 零变化**。
实现方式：扩展 `_tokenize_chinese_sequence` 的 **user_definitions 前缀匹配判据**
（`remaining in _compound_safe` → `remaining ∈ CS ∪ HM ∪ DUAL`）。

---

## 2. 类的语料场景全量定位

| 场景 | 样例 | 基线（CS=2） | 撤 CS 后 | 说明 |
|---|---|---|---|---|
| **类声明（词尾并入）** | `类 独立类:` / `类 测试类:` / `类 有界队列类:` | `KEYWORD(类) IDENTIFIER(独立类) COLON` | `独立`+`类`(KW) | **本任务的目标** |
| 独立关键字 | `类 名称:` | `KEYWORD(类) IDENTIFIER(名称) COLON` | 同 | 不受影响（类在语句起始） |
| 词首并入 | `类别` / `类型` / `类似` | `IDENTIFIER(类别)` 等 | 同 | 不受影响（HM 词首规则） |
| 类声明继承 | `类 子类 继承 基类:` | 子类/基类整词 | 同 | 不受影响 |

> 语料触发点：`lightharness/examples/test_L013.light` L10 `类 独立类:`。
> 关键上下文：同文件 L21 有 `设 独立 为 新建 独立类()` → **`独立` 被预扫描进
> `user_definitions`**，使 L10 的 `独立类` 走「用户定义前缀匹配」路径。

---

## 3. 机制定位（实测，非推测）

### 3.1 隔离 vs 整文件差异

| 输入 | 基线 | CS=0 | 差异 |
|---|---|---|---|
| `类 独立类:`（隔离，user_definitions 为空） | `独立类` 整词 | `独立类` 整词 | **无** |
| `设 独立 为 1\n类 独立类:`（`独立` ∈ user_definitions） | `独立类` 整词 | `独立`+`类`(KW) | **有** |

→ 差异由 **`user_definitions` 前缀匹配路径**触发，与语句/缩进上下文无关。

### 3.2 关键分支（`lexer.py` 第一层「用户定义前缀匹配」）

```python
if prefix_matched:
    remaining = full_identifier[len(prefix_matched):]
    if len(remaining) == 1 and remaining in _compound_safe:   # ← 旧判据
        prefix_matched = None                                  # 不拆分，整词输出
    elif remaining and remaining[0] in OPERATOR_VERBS:
        prefix_matched = None
    elif remaining and not _match_kw(remaining, 0)[0]:
        prefix_matched = None
    else:
        # 输出前缀，余部交后续循环 → 类 被切出为 KEYWORD
```

- **基线（`类 ∈ CS`）**：`独立类` 前缀匹配 `独立`，余部 `类` 单字且 ∈ CS → `prefix_matched=None`
  → 不拆分 → `独立类` 整词。
- **撤 CS 后**：余部判据不成立 → 走 `else` → 输出 `独立`，`类` 下一轮成 KEYWORD
  → G1 打红。

---

## 4. 规则设计与实现

### 4.1 判据扩展（`lexer.py` ~L2530）

```python
remaining = full_identifier[len(prefix_matched):]
if len(remaining) == 1 and (remaining in _compound_safe
                            or remaining in _P0A_HEAD_MERGE_SINGLE
                            or remaining in _P0A_HEAD_MERGE_DUAL):
    prefix_matched = None
```

### 4.2 为何这是「通用化」而非白名单

旧判据 `remaining in _compound_safe` 的语义是「余部单字是**可构词的别名/双位字** →
并入前缀，不拆」。该语义在 R25/R26 后已由正面类别精确表达：

- `_P0A_HEAD_MERGE_SINGLE`（HM，22 字）= 「词首+后随汉字可并入的单字关键字」；
- `_P0A_HEAD_MERGE_DUAL`（DUAL，8 字）= 「运算符/值字面量/范围符中的可构词字」。

`类` 与 `列` 均 ∈ HM，故扩展为「CS ∪ HM ∪ DUAL」**语义一致、无逐字登记**。CS 清零后
`_compound_safe = ∅`，判据由 HM ∪ DUAL 提供同一行为 → 全语料零变化。

### 4.3 关键约束（均已验证）

- 类独立关键字 `类 名称:` 不受影响：`类` 在语句起始、走第一层最长匹配，不进本判据。
- 词首并入 `类别` 不受影响：`类别` 整串不是「user_definitions 前缀 + 单字余部」形状。
- 非类声明上下文的词尾类（如 `人类`）不受影响：仅当前缀 ∈ user_definitions 时才触发。

---

## 5. 验证结果

| 判据 | 口径 | 结果 |
|---|---|---|
| **G1** 语料判据 | 撤 `类` 后全语料 token 序列零变化 | **0/845 文件变化 ✅** |
| **G2** 词首编译门 | `类别 为 7` / `类型 为 7` 整词成单 token | ✅（与基线一致） |
| **G3** 边界形态门 | `类 独立类:` / `类 名称:` / `类 子类 继承 基类:` | ✅ 全 PASS |
| 快速 `.light` | `examples/test_R28_类声明词尾并入_快速.light` | **rc=0 ✅** |

验证脚本：`lightharness/_antirun_r28_t3_CS表清零验证.py`。

---

## 6. 交付物

- `light-merge/src/lexer.py`：user_definitions 前缀匹配判据扩展
- `lightharness/examples/test_R28_类声明词尾并入_快速.light`（rc=0）
- 本报告
