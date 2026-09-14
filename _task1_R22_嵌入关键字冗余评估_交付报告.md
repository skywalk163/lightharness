# 第22轮 任务1 交付报告：`_EMBED_MAX_MATCH_KEYWORDS` 冗余评估与移除

> 日期：2026-09-14 ｜ 负责人：路M ｜ 结论：**保留（非冗余）**
> 修改文件：`light-merge/src/lexer.py` —— **本轮未改动**（判定为非冗余，保留定义与引用代码块）
> 反跑脚本：`lightharness/_antirun_r22_t1_嵌入关键字移除.py`
> 验证样例：`lightharness/examples/test_R22_嵌入关键字冗余验证.light`

---

## 一、目标与背景

任务1 要求验证 `_EMBED_MAX_MATCH_KEYWORDS`（`为`/`返回`/`尝试`，定义行539 + 引用块行2320-2399）是否已被第21轮上下文敏感切词覆盖；若冗余则移除定义与引用代码，收敛词法维护面。

任务书给出的线索（第21轮收口观察）：撤掉该集合后 **L-084 仍绿**，推断其可能冗余。
本任务以「全语料隔离中立验证（判据③）」为准，对全量语料重新评估，结论与第21轮的窄观察**相反**。

---

## 二、验证方法（判据③：隔离中立）

沿用第21轮任务3 的决定性判据：撤掉该条目后，全语料 token 序列零变化 ⇒ 冗余；有变化 ⇒ 真护栏。

本任务采用**等价置空法**（与 `_antirun_r21_t3_保护表精简.py` 同口径，原地改模块全局、finally 还原，不碰磁盘文件）：
1. 基线 A：当前 lexer（`_EMBED_MAX_MATCH_KEYWORDS = {'为','返回','尝试'}`）对全语料 dump token 序列 SHA256。
2. 禁用 B：置空该集合（等价于移除定义 + 引用代码块，引用块 `any(_ek in full_identifier ...)` 恒假 → 整块不触发）后重新 dump。
3. 对比 A/B 的逐文件 token 哈希。

语料：`lightharness/examples` + `lightharness/src` + `light-merge/examples` + `light-merge/stdlib` + `light-merge/src` + `light-merge/tests`，共 **770** 个 `.light`（不含 `_taskD_review_base` 巨型审查树）。

---

## 三、验证结果

| 检查 | 结果 |
|---|---|
| [A] 基线自检（两次 dump 一致） | PASS |
| [B] 置空集合 → 语料 token 变化 | **17 文件**（FAIL，即非中立） |
| [C] 边界用例 token 序列不变 | **10 条变化**（FAIL） |
| 判定 | **KEEP（非冗余）** |

### 3.1 变化的 17 个语料文件
```
light-merge/examples/L1_baihua/05_遍循环.light
light-merge/examples/L1_baihua/07_字典.light
light-merge/examples/L1_baihua/08_函数.light
light-merge/examples/L1_baihua/09_异常.light
light-merge/examples/L3_domain/all_in_one_L3_demo.light
light-merge/examples/L3_domain/demo1_sql.light
light-merge/examples/L4_python/all_in_one_demo.light
light-merge/examples/L4_python/demo2_pandas_csv.light
light-merge/examples/advanced.light
light-merge/examples/basic.light
light-merge/examples/hello.light
light-merge/examples/modules/main.light
light-merge/examples/modules/math_utils.light
light-merge/examples/modules/simple_export.light
light-merge/examples/modules/string_utils.light
light-merge/examples/test_L070.light
lightharness/src/代理.light
```

### 3.2 变化的 10 条边界用例（token 序列对比）
| 输入串 | 有集合（正确） | 无集合（切碎，错误） |
|---|---|---|
| `行为` | IDENTIFIER(行为) | ID(行) + KEYWORD(为) |
| `末位行为` | IDENTIFIER(末位行为) | ID(末位行) + KEYWORD(为) |
| `作为` | IDENTIFIER(作为) | ID(作) + KEYWORD(为) |
| `成为` | IDENTIFIER(成为) | ID(成) + KEYWORD(为) |
| `认为` | IDENTIFIER(认为) | ID(认) + KEYWORD(为) |
| `为了` | IDENTIFIER(为了) | KEYWORD(为) + ID(了) |
| `返回表` | IDENTIFIER(返回表) | KEYWORD(返回) + ID(表) |
| `返回结果` | IDENTIFIER(返回结果) | KEYWORD(返回) + ID(结果) |
| `尝试记录` | IDENTIFIER(尝试记录) | KEYWORD(尝试) + ID(记录) |
| `尝试捕获` | IDENTIFIER(尝试捕获) | KEYWORD(尝试) + ID(捕获) |

> 注：依赖该集合的标识符（17 文件）远不止上表 10 例，上表为代表性边界串。`设 甲 为 空` / `断言为真(条件)` / `段落 断言为真 接收:` 等**带值/调用语境**的串在两种状态下 token 一致（由嵌入块 (a)(c) 守卫与 R21 上下文敏感共同保证），故不依赖该集合的"纯嵌入"判定。

---

## 四、根因分析

`为` / `返回` / `尝试` 同时出现在 `_OPERATOR_KEYWORDS`（`lexer.py:37-41`，含 `'为'`）中——它们是赋值 / 返回 / 尝试语句的**运算符/关系关键字**，在表达式语境（`甲 为 乙`）必须切出。

第21轮任务2 的上下文敏感切词（`_tokenize_chinese_sequence` 行2401-2435）对「关键字前缀标识符」整体成词，**但显式排除 `_OPERATOR_KEYWORDS`**（行2431：`_lead_kw not in _OPERATOR_KEYWORDS`）。原因：若把 `为` 也纳入「前缀合并」，会破坏 `甲 为 乙` 的中缀切分。

于是出现覆盖盲区：
- `行为` 的**词首** `行` 不是关键字 → R21 上下文敏感块的「词首命中更短关键字」闸门（行2429-2431）**不触发**；
- `为` 嵌在词**内部**，R21 块只查词首关键字，看不到内部 `为`；
- 唯一能识别「`为` 嵌在长汉字串内部、应整体成词」的逻辑，就是本集合的嵌入块（行2320-2399）。

因此：本集合是 `为`/`返回`/`尝试` 嵌入式标识符的**唯一兜底护栏**，不可被 R21 上下文敏感切词替代。

### 与第21轮收口结论的矛盾说明
第21轮据「撤掉集合后 L-084 仍绿」推断冗余，但其验证只覆盖 L-084 单点。L-084 的 `设 末位行为 为 "test"` 中，L-084 真正依赖的是**词尾 `为` 的 (b) 值上下文守卫**——该守卫在 R21 上下文敏感落地后（对 `断言为真` 这类「非语句起始 + 关键字前缀」已能合并）部分被覆盖，故 L-084 单点变绿；但 `行为`/`返回表`/`尝试记录` 等**纯嵌入**（词首非关键字、整串非关键字）场景从未被 R21 块覆盖，撤掉即切碎。属「窄点验证通过、全量验证失败」的典型误判，本次已用全量证据纠正。

---

## 五、增强方案建议（未来轮次，非本轮实现）

若希望最终收敛该集合，可扩展 R21 上下文敏感切词，新增「**嵌入运算符关键字合并**」分支：
- 当连续汉字串 `full_identifier` 不以关键字开头、但**内部含** `_OPERATOR_KEYWORDS` 成员 `为/返回/尝试`；
- 且该成员**不处于值/关键字起始语境**（复用嵌入块的 (a)(b)(c) 守卫：紧邻 `空/真/假`、或词尾后跟 `{ [ " 数字` 则切分；函数调用语境 `( ` 则合并）；
- 则整串作为 IDENTIFIER。

该方案把「白名单 `为/返回/尝试`」升级为「基于语境规则的通用合并」，可消除本集合，且不影响 `甲 为 乙` 中缀切分。风险：需在全量语料上重新 A/B 验证（尤其 `设 X为 <值>` 形态不能误并）。建议列入第23轮「保护表通用化替代轮」候选，本轮**不实现**。

---

## 六、结论与交付

- **结论**：`_EMBED_MAX_MATCH_KEYWORDS` **非冗余**，必须保留。本轮**不修改** `light-merge/src/lexer.py`。
- **反跑 ALL OK 口径**：断裂态（有集合，基线）vs 修复态（无集合）对比，证明移除会引入 17 文件 / 10 边界串回归 → 保有意义成立。
- **交付物**：
  1. 反跑脚本 `lightharness/_antirun_r22_t1_嵌入关键字移除.py`（A/B/C 三层判据，证据落 `_task1_R22_嵌入关键字冗余_evidence.json`）
  2. 验证样例 `lightharness/examples/test_R22_嵌入关键字冗余验证.light`（锁定 行为/末位行为/返回表/尝试记录/作为/成为/认为/为了 整体成词，rc=0）
  3. 本报告
- **后续**：若第23轮实施第五节增强方案，可回过头来重新评估本集合的可移除性。
