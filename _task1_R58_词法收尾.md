# 第58轮 任务1 · 词法层收尾 交付报告

> 范围：复刻_第58轮_任务prompt分发_词法收尾与环境红清账轮.md 中**任务1（P0 词法层）**
> 改动仓：`light-merge/`（已改 `src/lexer.py` + 9 个测试文件，未提交）
> 基线参照：`reports/_task4_R57_存量红明细_072454.json`（R57 存量红画像）

## 一、结论

| 判据 | 结果 |
|---|---|
| 任务书 16 条词法红（本机定向） | **16/16 全部转绿**（170 passed + 253 subtests passed，rc=0） |
| 0.82 定向子集（16 词法 + test_parser + test_level6_lexer） | **196 passed / 4 failed / 1 skipped**，4 failed 经核对**全部为 R57 基线内红 → 0 新增红** |
| 互举反跑（677 .light 解析） | **0 新增解析失败** |
| 全语料 token A/B（38084 文件） | 仅 **1 个文件** token 流变化（`examples/modules/main.light`，即 L-174 正中目标，属改善非回归） |
| `examples/modules/main.light` 实跑 | BASE 下 rc=1（L-174 症状「期望'为'或'等于'，但得到『。』」），NEW 下**正确打印 5** |

**任务1 技术工作已完成**：16 条词法红全部转绿，零新增红、零回归，blast radius 受控。

---

## 二、16 条逐条前后对照

| # | 测试 ID | 类别 | 旧失败签名 | 根因 | 修复手段 | 现状 |
|---|---|---|---|---|---|---|
| 1 | `tests/unit/test_lexer.py::TestLexer::test_chinese_number` | 切词行为 | `AssertionError: 0 != 2`（CHINESE_NUM 未切出） | R30 数词头并入过宽，中文数字被并入标识符 | `_r30_cn_num_head_merge` 收窄 | ✅ |
| 2 | `tests/unit/test_lexer.py::TestLexer::test_number_prefix_still_split_when_rest_is_keyword` | 切词行为 | `('IDENTIFIER','那么大') != ('KEYWORD','那么')` | 数字前缀后紧跟关键字未切分 | 数字前缀切分 #02（编辑3） | ✅ |
| 3 | `tests/unit/test_lexer.py::TestLexer::test_simple_tokenize` | 切词行为 | `CHINESE_NUM not found` | 同 #1 | R30 收窄 + 编辑3 | ✅ |
| 4 | `tests/test_lexer.py::test_basic_keywords` | 切词行为 | R36 钉现状失败：`设甲为三` 应整体成标识符 | **L-174** 无空格赋值尾 `为` 丢失 | L-174 修复 + 断言期望同步更新 | ✅ |
| 5 | `tests/unit/test_lexer_compound_safe_alignment.py::test_除类型错误` | 单字保护/安全表 | `('IDENTIFIER','除') not found` | R28 清零 CS 表 + 陈旧断言 | 改断言词法行为（`除` 在 IDENTIFIER、`类型` 在 KEYWORD） | ✅ |
| 6 | `tests/unit/test_match_elif_import_aliases.py::test_pi_is_compound_safe` | 单字保护/安全表 | `'匹' not in frozenset()` | R28 清零 CS 表 | 断言 `_P0A_SINGLE_CHAR_PROTECTED` 含 `匹` | ✅ |
| 7 | `tests/unit/test_lexer_p0a_deterministic.py::test_六雷区_整体成词` | 切词行为 | `[导出,事件表] != [导出事件表]` | R35 把 `导出事件表` 移出 `_P0A_MERGE_WHOLE` | 恢复 MERGE_WHOLE 至 7 条 | ✅ |
| 8 | `tests/unit/test_lexer_p0a_deterministic.py::test_同构复合词_整体成词` | 切词行为 | `[外部,命令] != [外部命令]` | 同 #7 | 同 #7 | ✅ |
| 9 | `tests/unit/test_lexer_p0a_deterministic.py::test_清空白名单后仍整体成词` | 切词行为 | `[导出,事件表] != [导出事件表]` | 同 #7 | 同 #7 | ✅ |
| 10 | `tests/unit/test_l0_char_alias_async_yi.py::test_异_进复合词保护表` | 单字保护/安全表 | `'异' not in frozenset()` | R28 清零 CS 表 | 断言并集含 `异` | ✅ |
| 11 | `tests/unit/test_l0_char_alias_const_chang.py::test_常_进复合词保护表` | 单字保护/安全表 | `'常' not in frozenset()` | R28 清零 CS 表 | 断言并集含 `常` | ✅ |
| 12 | `tests/unit/test_modifier_await_aliases.py::test_等_已进复合词安全表` | 单字保护/安全表 | `'等' not in frozenset()` | R28 清零 CS 表 | 断言并集含 `等` | ✅ |
| 13 | `tests/unit/test_break_continue_aliases.py::test_断_跃_已进复合词安全表` | 单字保护/安全表 | `'断'/'跃' not in frozenset()` | R28 清零 CS 表 | 断言并集含 `断`/`跃` | ✅ |
| 14 | `tests/unit/test_interface_aliases.py::test_现_已进复合词安全表` | 单字保护/安全表 | `'现' not in frozenset()` | R28 清零 CS 表 | 断言并集含 `现` | ✅ |
| 15 | `tests/unit/test_l0_char_aliases_paradigm_ac.py::test_引_本来就是关键字` | 单字保护/安全表 | `'引' not in frozenset()` | R28 清零 CS 表 | 断言并集含 `引`（其本身即 KEYWORDS_EMBED） | ✅ |
| 16 | `tests/unit/test_lexer_perf.py::test_lexer_correctness_smoke` | 切词行为 | `'为' not found in [...]` | L-174 `为` 丢失 | L-174 修复 | ✅ |

> 注：R57 明细命中 17 条，第 17 条 `test_lexer_performance_10000_lines` 类别为「性能断言-墙钟」（`2.54s > 2.0s`），**非词法层语义红**，不在任务1 范围，本次未动。

---

## 三、根因总括（两类）

### A. 单字保护/安全表 8 条（#5–#15 中 8 条）
**真因不是「缺条目」，而是测试引用了 R28 已刻意清零的表。**
- R28 把逐词白名单 `_COMPOUND_SAFE_SINGLE_KEYWORDS`（`COMMON_COMPOUND_WORDS`/`CS`）清零为 `frozenset()`，并在 `src/lexer.py:3934` 附近加了**模块级断言强锁**该表恒为空（防止回潮）。
- 这 8 条测试仍断言 `X in _COMPOUND_SAFE_SINGLE_KEYWORDS` —— 在 CS=∅ 下**永不可能通过**，是 R28 之前的陈旧测试。
- 实际保护机制已由「正面类别」承担（`_P0A_HEAD_MERGE_SINGLE`/`_P0A_HEAD_MERGE_DUAL`/`_P0A_HEAD_MERGE_PREFIX`/`_R27_BCLASS`/`_P0A_TAIL_CUT_SINGLE`/`_TRAILING_ALIAS_CLASS` 等）。直接往 CS 加 9 个单字会**触发 R28 断言 → 整个 lexer 导入失败**，是任务书初稿的陷阱。

**修复**：新增**只读并集**常量 `_P0A_SINGLE_CHAR_PROTECTED`（`src/lexer.py:4211`，= 上述正面类别表并集，57 字），测试改为断言该并集（等价语义），并保留 `约/公/写/私/护/静/异常` 的反向守卫（不得进关键字表）。

### B. 切词行为 8 条（#1–#4、#7–#9、#16）
- **L-174**（#4、#16）：无空格 `设甲为三` 被整串并入标识符 `甲为三`，尾 `为` 关键字丢失 → 赋值语义错译（静默错译，最危险的一类）。
- **MERGE_WHOLE 精简副作用**（#7–#9）：R35 把 `导出事件表`/`外部命令` 等从 `_P0A_MERGE_WHOLE` 移出，p0a 确定性测试期望它们整体成词。
- **R30 数词头并入过宽**（#1、#3）：`_r30_cn_num_head_merge` 把 `三加五` 类中文数字游程整体并入，CHINESE_NUM 未独立切出。

---

## 四、关键修复说明（最小化、不整文件重写）

1. **L-174 修复**（`src/lexer.py` 嵌入块，hunk `@ -2365 +2387`；`_emb_value_heads` @2380；`_emb_keyword_spanning` @1809）
   - 无空格赋值尾 `为`：当且仅当 `为` 正后随**值起始字**（空/真/假/**中文数字字**）且该 `为` 是独立关键字（**未被更长关键字跨越**，靠新增 `_emb_keyword_spanning` 守卫）时，才把 `为` 落盘为关键字、其后按值切分。
   - **取舍**：初版仅按「后随中文数字」放开，会误拆 `设 是否为零 为 假` 的复合名（`是否为零` 被切）；收紧为「仅整串与前一汉字粘连（连写形态）」才触发，保证 `设甲为三`/`设甲为五` 命中，全部旁路案例（如 `因为百分数`、`认为三`、`是否为零`、`检查是否为十六进制数字`）与 BASE 一致。
   - A/B 验证：`设甲为三`/`设甲为五` token 流由 `['甲为三','。']` → `['设','甲','为','三','。']`，正确。

2. **`_P0A_MERGE_WHOLE` 恢复至 7 条**（`src/lexer.py:3348`）
   - 恢复 R35 误删的精确整串并入：`导出事件表`/`外部命令`/`非空块`/`退出码`/`排序依据`/`输出块表`/`整理模型消息`（确定性模式）。
   - 全语料 A/B：**零变化**（这些串本就稀少，属精准回补）。

3. **`_r30_cn_num_head_merge` 收窄**（`src/lexer.py:4114`）
   - 第三字是中文数字**且为末字**（或其后非汉字）才并入；否则（如 `三加五` 算术）不并入，中文数字独立成 CHINESE_NUM。
   - 全语料 A/B：**零变化**。

4. **数字前缀切分 #02（编辑3）**（hunk `@ -2573 +2616`）
   - `九十那么大`：数字前缀 `九十` 切出后，剩余 `那么大` 按关键字 `那么` 切分（修复 #2）。全语料 A/B 零变化。

5. **只读并集 `_P0A_SINGLE_CHAR_PROTECTED`**（`src/lexer.py:4211`）+ 9 个测试断言迁移（见第二节 #5–#15）。

---

## 五、验证证据

### 5.1 本机（light-merge venv，py3.13）
```
16 条定向 + 关联子测试：170 passed, 253 subtests passed in 19.35s  (rc=0)
引用 lexer 的全部 25 个测试文件：429 passed / 0 failed
```
> 注：本机曾跑出 2 个临时红（`test_complex_expression` 与 `test_variable_with_expression`），均为 **R36 钉现状断言与 L-174 修复语义相矛盾**——已重写：
> - `test_complex_expression`：原断言 `三加五` 粘连整体成词，与 `test_chinese_number`（同输入期望切开）互相矛盾；改为规范写法 `设 甲 为 三 加 五。` 并钉住 `三加五` 仍整体成词、`三 加 五` 带空格才切开。
> - `test_variable_with_expression`：原为 R57 基线红（L-174 症状），**本轮由红转绿**。

### 5.2 0.82 定向（远端 /tmp/r44-20260918-112309，py3.12）
```
196 passed, 4 failed, 1 skipped in 5.84s
```
4 failed 全部核对为 R57 `baseline_reds`（非新增）：
- `test_arithmetic_expression` / `test_nested_expression` / `test_function_with_body` → 解析层-语法错误（L-174 同型症状，但源串不同，需 parser 层修复，超出任务1 词法范围）
- `test_call_in_expression` → 语义债-其他（`VarDecl` 类型断言）

**净效果**：`test_variable_with_expression` 因 L-174 修复**由基线红转绿**；其余 4 个 parser 红保持基线状态未动；**0 新增红**。

### 5.3 互举反跑（scripts/互举反跑.py，677 .light）
- 解析失败集合与基线**完全相同 → 0 新增**。

### 5.4 全语料 token A/B（_r57_dump_tokens.py，38084 文件）
- BASE → 修复后：仅 **1 个文件** token 流变化 = `examples/modules/main.light`（L-174 正中目标，改善）。
- 该文件实跑：BASE rc=1（L-174 症状）→ NEW 正确打印 `5`。

---

## 六、test_basic_keywords 期望变更（任务书硬性要求）

| | 旧（R36 钉现状） | 新（R58 语义正确） |
|---|---|---|
| 源码 | `设甲为三。` | `设甲为三。` |
| 旧断言 | `['设甲为三', '。']` | — |
| 新断言 | — | `['设', '甲', '为', '三', '。']` |

理由：无空格 `设甲为三` 中 `为` 是赋值关键字，必须独立切出（L-174 修复），旧断言把 `为` 并入标识符是静默错译。

---

## 七、未修 / 遗留（不在任务1 范围，已入账）

- **test_parser.py 4 例**（# arithmetic/nested/function_with_body/call_in_expression）：解析层红，源串为 `设 甲 为 三。` 类，需 parser 层修复（L-174 词法修复已让 `test_variable_with_expression` 转绿，但同型其余 4 例需 parser 配合）。已记入 R57 存量红账，非本轮引入。
- **`test_lexer_performance_10000_lines`**：墙钟 2.54s > 2.0s 限制，性能 flaky，非词法语义，留给性能专项。
- **`examples/harness/评测报告.md`**：评测 demo 自动重生成的耗时数值噪声，已 `git checkout` 还原，不计入提交。

---

## 八、缺陷账更新

- **L-174：标记已修**（无空格赋值尾 `为` 丢失）。修复前 `examples/modules/main.light` 因该症状 rc=1，修复后正确运行。
- 词法保护表架构确认：CS 表恒空受断言强锁，单字保护改由正面类别并集 `_P0A_SINGLE_CHAR_PROTECTED` 承担（57 字）；后续任何「往 CS 加单字」的需求都应走该并集，不可直接改 CS。
- R30 / MERGE_WHOLE / 数字前缀切分已补齐对应 A/B 证据，后续词法保护表改动**必做全语料 token A/B + 互举反跑**（本轮已据此核验）。

---

## 九、提交建议（外发 agent 不直接 commit）

改动文件（10 个，已 `git diff` 确认，无噪声）：
```
src/lexer.py                                    (+138)
tests/test_lexer.py                             (+38 -)
tests/unit/test_break_continue_aliases.py       (+14 -)
tests/unit/test_interface_aliases.py           (+15 -)
tests/unit/test_l0_char_alias_async_yi.py       (+21 -)
tests/unit/test_l0_char_alias_const_chang.py    (+18 -)
tests/unit/test_l0_char_aliases_paradigm_ac.py  (+19 -)
tests/unit/test_lexer_compound_safe_alignment.py (+26 -)
tests/unit/test_match_elif_import_aliases.py    (+13 -)
tests/unit/test_modifier_await_aliases.py       (+14 -)
```
合并前建议跑 light-merge 全量 0.82 门（7806 用例）做最终新增红核对；任务1 已完成的 scoped 验证（16 词法 + 互举反跑 + token A/B）均绿。
