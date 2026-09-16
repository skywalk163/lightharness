# 任务2（R35）：非空块 通用化替代 —— 结论：通用化成功，条目已移除

> 日期：2026-09-16 ｜ 范围：light-merge/src/lexer.py（通用规则）+ lightharness（验证）
> 判据：G1 全语料 token 零变化 ∧ G2 边界 .light rc=0 ∧ G3 五种边界形态 token 一致

---

## 一、结论

| 项 | 结果 |
|---|---|
| 通用化是否成功 | **是** |
| `_P0A_MERGE_WHOLE` 该条目 | **已移除**（3 → 2 条） |
| 替代它的通用规则 | **GR-2b：一元前缀运算符类别 + R21 闸门3 例外 + 已声明名字收窄** |
| G1 | **0 变化 / 0 新错**（867 可比文件） |
| G2 | 边界 .light **rc=0**（改动前后各跑一次） |
| G3 | 五种边界形态 **全部一致** |
| 反向形态 | **0 变化**（`非 甲` / `非甲` 仍是取反） |
| 变异反跑 | 关掉 GR-2b ⇒ 非空块 **F2/F5 必红**（规则敏感，非假绿） |

---

## 二、根因分析

### 2.1 劈开机制

撤除条目后，`非空块` 在**词首**被 `非` 劈开：

```
基线（含条目）: IDENTIFIER·非空块
撤除后        : KEYWORD·非  IDENTIFIER·空块
```

`非` 是逻辑运算符关键字，位于 `_OPERATOR_KEYWORDS`
（`= OPERATOR_VERBS ∪ {与,或,且,非,在,为,之,于}`）。

### 2.2 为什么 R21 上下文敏感分支接不住

R21 分支（lexer.py `_tokenize_chinese_sequence`）的四道闸门中，**闸门3**明确排除运算符关键字：

```python
if (_lead_kw and 0 < _lead_len < len(full_identifier)
        and _lead_kw not in _OPERATOR_KEYWORDS      # ← 非空块 被这道门挡住
        and not (... 含 _P0A_SEP ...)):
```

闸门3 的立论是：**二元中缀运算符**（加/减/乘/除/等于/大于/小于/包含/与/或/且）
在表达式中必须两侧切出操作数，故带运算符前缀的串不能并入标识符（`甲加乙` → 甲/加/乙）。
这道门对**二元**运算符完全正确，但 `非` 是**一元前缀**运算符，语义不同。

### 2.3 语料实态：无空格 `非X` 恒为复合名

全语料 `非` 后紧跟汉字的形态统计（前 15）：

```
非空 259   非法 206   非零 164   非值 125   非负整数 67
非负 66    非正 62    非范围 58  非负数 56   非空元素 56
非零值 53  非正数 53  非字符串 44  非对象 43  非阻塞 39
```

逐一核对真实代码（`e2b配套.light`、`代理团队.light`、`JSONRPC传输.light`）：
`设 非法 为 假` / `如果 非法 == 假:` / `段落 非有限 接收 值:` —— **全部是标识符名**，
**零处**是无空格的 `not X` 表达式。语料中 `非` 作取反时恒带空格（`非 甲`）。

⇒ 立论成立：**无空格 `非X` 恒为复合名，不是 `not X`。**

---

## 三、通用规则 GR-2b 设计

### 3.1 规则本体（三要素）

**（1）新建语义类别**（lexer.py `Lexer` 类属性）：

```python
# R35 任务2：一元前缀运算符（目前仅 `非`）
_P0A_UNARY_PREFIX_KW = frozenset({'非'})
```

**（2）R21 闸门3 对一元前缀类开例外**：

```python
and _lead_kw not in (_OPERATOR_KEYWORDS - self._P0A_UNARY_PREFIX_KW)
```

**（3）收窄（反例保护）——余部若是已声明名字则仍是操作数**：

```python
and (_lead_kw not in self._P0A_UNARY_PREFIX_KW
     or full_identifier[_lead_len:] not in user_definitions)
```

即 `非甲`（`甲` 已声明）仍切分为 `非` + `甲` = `not 甲`；
`非空块`（`空块` 未声明）整体并入标识符。
该收窄与既有 `_tail_is_alpha_operand`（「运算符左边那段必须是本文件已声明的名字」）
同口径，非新造判据。

### 3.2 为什么这是「通用规则」而非逐词白名单

- 判据落在**语义类别**（一元前缀 vs 二元中缀）与**位置/上下文**（R21 已有的
  非语句起始 ∨ 调用语境、不含 `_P0A_SEP`）上；
- 覆盖整类 `非 + 名词` 复合名（非法/非零/非值/非负整数/非空元素/非阻塞…），
  不只是 `非空块` 一个词；
- 不含任何整词字符串，不随语料生长。

### 3.3 被否决的过宽版本（GR-2，未采用）

只做要素（1）（2）、不做收窄（3）时，G1 仍是 0 变化，但**反向形态打红 2 条**：

```
非 单字变量名（无空格）: 基线 KEYWORD·非 IDENTIFIER·甲 → 变体 IDENTIFIER·非甲
非 双字变量名（无空格）: 基线 KEYWORD·非 IDENTIFIER·甲乙 → 变体 IDENTIFIER·非甲乙
```

这会**静默收窄语言语义**（无空格 `非X` 不再是取反）。加收窄（3）后反向形态归零。

---

## 四、三重判据验证

### G1 语料门

| 变体 | 结果 |
|---|---|
| `mw_no2`（仅撤条目，无通用规则） | 0 变化 |
| `gr2_only`（仅通用规则，未收窄） | 0 变化 |
| `gr2b_only`（通用规则 + 收窄） | **0 变化** |
| `gr2b_mw_no2`（**最终态**） | **0 变化 / 0 新错**（867 可比文件） |

终验 `_antirun_r35_final.py`：**当前 lexer vs 改动前 HEAD ⇒ 867 可比文件 0 变化 0 新错**。

### G2 编译门

| 用例 | 改动前 | 改动后 |
|---|---|---|
| `examples/test_R35_非空块边界.light` | rc=0 | **rc=0** |
| `examples/test_R32_MERGE_WHOLE精简边界.light` | rc=0 | **rc=0** |
| `examples/test_L030.light`（非空块 8 处真实用法） | rc=0 | **rc=0** |

### G3 边界门（当前 vs HEAD）

```
整理模型消息   G3通过
非空块      G3通过   ← 本任务目标
记录类型     G3通过
```

### 反向形态（12 条探针）

```
非 一元取反（带空格）      一致   KEYWORD·非 IDENTIFIER·甲
非 一元取反（条件位）      一致   KEYWORD·如果 KEYWORD·非 IDENTIFIER·甲
非 单字变量名（无空格）     一致   KEYWORD·非 IDENTIFIER·甲      ← 收窄(3) 生效
非 双字变量名（无空格）     一致   KEYWORD·非 IDENTIFIER·甲乙    ← 收窄(3) 生效
取模 甲模乙（守卫）        一致   KEYWORD·模
取模 带空格              一致   KEYWORD·模
类型 声明语句 / 裸关键字    一致
模型 / 非空 / 记录类型段落名 / 成员访问 X类型   一致
变化数 = 0
```

### 变异反跑（证明规则是活的）

把 GR-2b 的一元前缀例外撤掉（闸门3 恢复为 `_OPERATOR_KEYWORDS` 全禁），
而 `非空块` 仍不在 `_P0A_MERGE_WHOLE`：

```
非空块 变异后 G3 失败形态：['F2 函数名', 'F5 传参位']
  [F2] HEAD: 返回 IDENTIFIER·非空块 (     变异态: 返回 KEYWORD·非 IDENTIFIER·空块 (
  [F5] HEAD: ( IDENTIFIER·非空块 ,        变异态: ( KEYWORD·非 IDENTIFIER·空块 ,
判定：✅ 规则敏感（变异必红）
```

⇒ 非空块的整词语义**确由 GR-2b 承载**，不是被其他规则或预扫描偶然掩盖。

---

## 五、lexer.py 实际改动

1. 新增 `Lexer._P0A_UNARY_PREFIX_KW = frozenset({'非'})`（附完整立论注释）；
2. R21 分支条件改为
   `_lead_kw not in (_OPERATOR_KEYWORDS - self._P0A_UNARY_PREFIX_KW)`
   并追加「余部是已声明名字则仍是操作数」收窄；
3. `_P0A_MERGE_WHOLE` 移除 `'非空块'`（3 → 2）；
4. 注释更新：记录 R35 精简结论与另 2 条保留的逐条证据。

`py_compile` + `import` 自检通过；`_P0A_MERGE_WHOLE = ['整理模型消息', '记录类型']`。

---

## 六、交付物

- `light-merge/src/lexer.py`（通用规则 + 条目移除）
- `lightharness/examples/test_R35_非空块边界.light`（边界测试，rc=0）
- `lightharness/_antirun_r35_final.py` + `_antirun_r35_final.json`（终验）
- 证据脚本：`_r35_g1_engine.py`、`_r35_g3_边界门.py`、`_r35_probe_反向形态.py`、`_r35_probe_上下文矩阵.py`、`_r35_variants.py`
