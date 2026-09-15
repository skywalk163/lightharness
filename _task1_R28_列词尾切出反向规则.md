# 任务1（R28）交付报告 —— 列 的词尾切出反向规则设计与实现

> 日期：2026-09-15 ｜ 轮次：第28轮 ｜ 范围：`light-merge/src/lexer.py`（词尾切出反向规则）
> 对应任务书：`复刻_第28轮_任务prompt分发_CS表2字逐字通用化.md` 任务1

---

## 1. 目标与结论

**目标**：为 `列` 实现「词尾切出 KEYWORD」反向规则，使其在 `对于元素在序列:` 等场景
词尾切出为 KEYWORD（与 R25 词尾并入方向相反），从而可从 CS 表移除，且全语料 token 零变化。

**结论**：✅ 达成。`列` 已从 CS 表移除（CS 2→0），全语料 **845 文件 token 零变化**。
实现方式：新增正面类别 `_P0A_TAIL_CUT_SINGLE = frozenset({'列'})`，在
`_tokenize_chinese_sequence` 的**嵌入输出循环**单字锚分支加入「词尾切出」判据。

---

## 2. 列的语料场景全量定位

`lightharness` + `light-merge` 全语料中 `列` 的场景仅 3 类（实测 `_dbg_r28_ground.py`）：

| 场景 | 样例 | 基线（CS=2） | 撤 CS 后 | 说明 |
|---|---|---|---|---|
| **词尾切出** | `对于元素在序列:` | `IDENTIFIER(序)+KEYWORD(列)+COLON` | `IDENTIFIER(序列)+COLON` | **本任务的目标** |
| 词首并入 | `列数 为 3` / `列表 为 []` / `列名 为 "id"` | `IDENTIFIER(列数)` | 同 | 不受影响（HM 词首规则） |
| 词尾并入（非切出语境） | `序列 为 [1,2,3]` / `序列:` / `甲序列:` | `IDENTIFIER(序列)` | 同 | 不受影响（`embedded_found=False` 整词出口） |

> 语料触发点唯一：`light-merge/bootstrap/release/stdlib/断言工具.light`
> L226 `对于元素在序列:`（bootstrap release 的 Python 风格 stdlib，
> 语义为 `for 元素 in 序列:`，`序列` 是参数名）。

---

## 3. 机制定位（实测，非推测）

### 3.1 切出只发生在「嵌入输出循环」

`_tokenize_chinese_sequence` 对一段连续汉字段的处理分两步：

1. **探测循环**：逐位找内嵌关键字。若某关键字「需要跳过」（含 CS 锚、HM 词首并入、
   词尾并入类别 `_TRAILING_ALIAS_CLASS=F` 等）则不标记；只要有一个**真关键字**
   （如 `在`/`之`）未被跳过 → `embedded_found = True`。
2. **输出循环**（仅 `embedded_found=True` 时进入）：逐段输出标识符与 KEYWORD。

**关键分支**（`lexer.py` 输出循环，CS 锚分支 `else` 子句）：

```python
elif (sub_len == 1 and (sub_kw in self.compound_safe_single_keywords or ...)):
    ...
    else:
        # 只跳过不在词尾的关键字；在词尾时作为关键字输出
        if scan_pos + sub_len < len(full_identifier):
            scan_pos += sub_len
            continue
```

即 **CS 单字锚在词中并入、在词尾落出 KEYWORD**。`列` 正是靠这条在
`元素在序列` 的输出循环中于词尾（`scan_pos+1==len`）落出 KEYWORD。

> 撤 CS 后，`列 ∈ HM` 但 HM 分支要求 `scan_pos==0`；词尾 `列` 落到
> `elif sub_len==1 and deterministic and sub_kw not in _P0A_OP` 分支，
> 因 `_seg_after_sep`（前一段刚输出过成员/关系分隔符 `在`）为真 → **被并入** →
> 与基线不符（`序列` 整词）。这就是 G1 打红的根因。

### 3.2 反向对照（证明切出与「同段真关键字」强相关）

| 输入 | 基线 | 说明 |
|---|---|---|
| `甲在序列:` | `甲`(ID)`在`(KW)`序`(ID)`列`(KW) | 段内有真关键字 `在` → 输出循环 → 词尾切出 |
| `甲之序列:` | `甲`(ID)`之`(KW)`序`(ID)`列`(KW) | 同上（`之` 为分隔符） |
| `x在序列:` | `x`(ID)`在`(KW)`序列`(ID) | ASCII `x` 截断使 `在序列` 成**独立段**，`在` 被第一层直接输出 → `序列` 成独立段（无内嵌）→ 整词 |
| `序列:` / `甲序列:` | `序列`(ID) / `甲序列`(ID) | 段内无真关键字 → `embedded_found=False` → 整词 |

---

## 4. 规则设计与实现

### 4.1 类别定义（`lexer.py` 文末 R28 类别区）

```python
_P0A_TAIL_CUT_SINGLE = frozenset({'列'})
assert _P0A_TAIL_CUT_SINGLE == frozenset({'列'}), (
    'R28 词尾切出类别漂移：应恒为 1 字（列）')
```

### 4.2 判据接入（输出循环单字锚分支）

在既有 `CS ∪ (HM∩词首) ∪ (DUAL∩词首)` 条件下，追加：

```python
or (sub_kw in _P0A_TAIL_CUT_SINGLE
    and scan_pos > 0
    and scan_pos + sub_len == len(full_identifier)
    and _is_han(full_identifier[scan_pos - 1]))
```

命中后落入 `else` 分支的「词尾不跳过」路径 → 落出 KEYWORD，与 CS 行为等价。

### 4.3 关键约束（均已验证）

- 词首并入 `列数` 不受影响：词首位置走第一层 skip_verb / HM 分支，**不进**本判据（`scan_pos>0` 门槛）。
- 裸 `序列` / `甲序列` 不受影响：段内无真关键字 → 不进输出循环。
- 词尾并入（非切出语境）不受影响：`embedded_found=False` 整词出口。
- **探测循环不改**：`列` 在探测循环仍按 `_TRAILING_ALIAS_CLASS` 跳过（保证裸 `序列` 整词）；
  二者「不一致」不影响结果——输出循环只在**另有真关键字**触发，列的词尾行为此时必须切出。

> ⚠️ 本类别是**逐字反向规则**（R28 残部专用）。之所以无法由既有类别推导：`列` 的切出与
> 并入由**位置**区分（词尾切出 / 词首并入 / 无关键字整词），非单一方向；且 `列 ∈ F`，
> 不得加入词尾排除集 `_P0A_SUFFIX_SPLIT_SINGLE`（否则 HM 词首 `列数` 打红）。语料仅此一例。

---

## 5. 验证结果

| 判据 | 口径 | 结果 |
|---|---|---|
| **G1** 语料判据 | 撤 `列` 后全语料 token 序列零变化 | **0/845 文件变化 ✅** |
| **G2** 词首编译门 | `列数 为 7` / `列表 为 7` 整词成单 token | ✅（与基线一致） |
| **G3** 边界形态门 | `对于元素在序列:` / `甲之序列:` / `序列:` / `序列 为 [1,2,3]` | ✅ 全 PASS |
| 快速 `.light` | `examples/test_R28_列词尾切出_快速.light` | **rc=0 ✅** |

验证脚本：`lightharness/_antirun_r28_t3_CS表清零验证.py`（A/B：改造前快照 CS=2 vs 现文件 CS=0）。

---

## 6. 交付物

- `light-merge/src/lexer.py`：`_P0A_TAIL_CUT_SINGLE` 类别 + 输出循环判据
- `lightharness/examples/test_R28_列词尾切出_快速.light`（rc=0）
- 本报告
