# R26 任务1 交付：词首并入正面规则设计 + 实现

> 方向：阶段E —— _COMPOUND_SAFE_SINGLE 词首并入通用化（CS 表完整通用化最后一步）
> 任务书：`复刻_第26轮_任务prompt分发_CS词首并入通用化.md`
> 铁律要求只改 `_match_keyword` 及相关规则定义。**勘察后发现真实站点与任务书不符，见 §一。**

---

## 一、勘察结论（与任务书假设的三点偏差）

任务书「词首并入机制现状」列了 3 处（`_match_keyword` / `_skip_compound_safe_and_match` / 嵌入式扫描三处）。实测勘察发现**真实承载词首并入的是 5 处**，且 `_match_keyword` 并非决定性站点：

| # | 站点（行号） | 作用 | 位置相关性 | R26 是否介入 |
|---|---|---|---|---|
| 1 | `_match_keyword` (1238) + 孪生 `_skip_compound_safe_and_match` (1318) | 「CS 字后随**关键字**→不成词」 | **位置无关**（无 scan_pos 上下文） | 仅随 CS 精简而收缩 |
| 2 | `_tokenize_chinese_sequence` 第一层 skip_verb (2553) | **词首**单字关键字 → 整体成标识符 | 词首（`pos==i+consumed`） | ✅ 加正面类别 |
| 3 | 嵌入扫描·探测循环 (2736) | scan_pos 任意位置跳过 CS 字 | 任意 | ✅ 加 scan_pos==0 正面类别 |
| 4 | 嵌入扫描·输出循环 (2813) | 同上（输出侧，判据须与探测一致） | 任意 | ✅ 加 scan_pos==0 正面类别 |
| 5 | 嵌入扫描·rematch (2961) | 关键字输出后余段词首 | 词首（scan_pos 已置 0） | ✅ 加正面类别 |

**决定性站点是 #2（第一层 skip_verb）**：`长度 为 7` 被切成 `长`+`度` 的根因就在此处 —— `keyword in _compound_safe` 不成立时 `skip_verb=False`，`长` 直接发成 KEYWORD。
`_match_keyword`（#1）是**位置无关**的：它拿不到 scan_pos，无法表达「词首」条件。任务书给出的替换式
`if candidate in _P0A_HEAD_MERGE_SINGLE and pos+1<text_len and _is_han(text[pos+1]): return None,0`
会把「后随**任意**汉字」都判为成词（原语义是「后随**关键字**」），并且会打掉 R24 L-153 的 `自之姓名` 修复（`之`∈_P0A_OP，但判据看的是 `自` 的后随字）。**故 #1 不套用词首正面规则，只随 CS 精简收缩**，本项作为设计偏差在 §四 记录。

---

## 二、正面类别定义（派生，不逐词登记）

```
_P0A_HEAD_MERGE_SINGLE = F − _P0A_HEAD_SPLIT_SINGLE        # 22 字
  其中 F = _TRAILING_ALIAS_CLASS（R25 词尾并入类别，43 字）
       _P0A_HEAD_SPLIT_SINGLE = _P0A_SUFFIX_SPLIT_SINGLE   # R25 词尾排除集（运算符/分隔符/值字面量/范围/await）
                              ∪ _R26_STMT_HEAD_SINGLE      # 单字语句关键字（21 字）
_R26_STMT_HEAD_SINGLE = {设 己 父 从 导 返 若 并 终 现 当 异 宏 匹 否 承 抛 捕 掷 跃 遍}
```

推导结果 `F ∩ CS_原30` = **22 字**：`余 例 出 列 则 对 常 引 接 断 是 末 段 的 类 自 试 跳 过 配 长 首`。

### 关键发现：任务书排除集**不完整**
任务书排除集只列了 `设/己/为 + 运算符 + 值字面量 + 范围`。实测把 `F` 直接当词首类别（`CSplusF` 变体）后，全语料 **19 个文件 token 变化**，真因是 `F−CS` 的 21 字**都是单字语句关键字**：

```
基线            变体(F 词首并入)
己 名称 为 名称 → 己名称             ← self 语义丢失
父 进程ID      → 父进程ID           ← super 语义丢失
当 真:         → 当真               ← when 语句断裂
def 异常       → def异常
除异常         → 除异+常
```

故 `_P0A_HEAD_SPLIT_SINGLE` 必须补上这 21 字。补全后正面类别的**净增量**（相对 CS 16 字）恰为 14 字，由模块末尾断言②硬钉：
```python
assert _P0A_HEAD_MERGE_SINGLE - _COMPOUND_SAFE_SINGLE_KEYWORDS == _R26_CS_REMOVED   # 14 字
```

---

## 三、验证结果

| 判据 | 结果 |
|---|---|
| **全语料 token 零变化** | ✅ **0 / 843 文件**（`_r26_ab_final.json`，基线 = R25 工作树 lexer） |
| 快速验证 `.light` rc=0 | ✅ `examples/test_R26_词首并入_快速.light`（22 正面字 + DUAL 8 + 反向硬语句） |
| G2 词首编译门（语句起始裸名 `{名} 为 7`） | ✅ 16/16 整词成 IDENTIFIER（长度/出错/列数/规则/则例/常规/引导/接续/断裂/月末/试探/首项/余数/举例/是否/接口*） |
| 反向：硬语句关键字词首切分 | ✅ `己 名称`/`父 进程ID`/`当 真:`/`从 甲 导入 乙`/`设 X 为 5`/`返回 真`/`甲 加 乙`/`返回 空`/`类 动物:` 全部切分 |
| 既有单测零新增打红 | ✅ 6 条失败全部与基线（R25 态）**逐条相同**（见 §四） |
| import 期自校验 | ✅ 断言①`CS==(F∩CS)∪DUAL`、②`HEAD−CS==14字`、③`HEAD⊆F` 全过 |

\* `接口`/`跳过` 是**多字关键字**，最长匹配优先，本就不走词首并入。

---

## 四、设计偏差与已知问题（如实记录）

1. **`_match_keyword` 未套用词首正面规则**（§一）。理由：位置无关 + 会破坏 R24 L-153 `自之姓名` 修复。它随 CS 精简收缩为 16 字，实测全语料零变化。**待任务5 评估是否可进一步简化/删除其递归。**
2. **既有 6 条 lexer 单测红**，基线（R25）即红，R26 **未新增**：
   `test_lexer.py::test_simple_tokenize`、`test_number_prefix_still_split_when_rest_is_keyword`、
   `test_lexer_p0a_deterministic.py::test_成员与关系分隔符`、`test_语句关键字词首切分`、
   `test_lexer_perf.py::test_lexer_correctness_smoke`、`test_l0_char_alias_async_yi.py::test_异_进复合词保护表`。
3. **`_P0A_HEAD_SPLIT_SINGLE` 用了 21 字显式清单**。原因：这 21 字在 keywords.py 的语句类别里与「可构词别名字」**同类混排**（如 `例`与`匹`同属 KEYWORDS_MATCH、`出`与`从/导`同属 KEYWORDS_DEFINE），无法用类别 union 分离（已穷举验证）。清单语义单一且稳定（「单字语句关键字」），优于原 CS 的混合语义。

---

## 五、文件改动

- `light-merge/src/lexer.py`
  - CS 表：30 → 16（本项属任务3 删除动作，见任务3 交付）
  - 新增模块级：`_R26_STMT_HEAD_SINGLE` / `_P0A_HEAD_SPLIT_SINGLE` / `_P0A_HEAD_MERGE_SINGLE` / `_R26_CS_REMOVED` + 3 条 import 自校验断言
  - 第一层 skip_verb（2553）：加 `or (keyword in _P0A_HEAD_MERGE_SINGLE and _is_han(full_identifier[1]))`
- `lightharness/examples/test_R26_词首并入_快速.light`（rc=0）
- `lightharness/_r26_ab_final.py` + `_r26_ab_final.json`（零变化证据）
- `lightharness/_r26_probe_g1.py` / `_r26_probe_g2.py`（勘察探针）
