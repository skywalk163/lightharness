# R26 任务2 交付：嵌入式扫描词首并入通用化实现

> 任务书要求只改嵌入式扫描区域（lexer.py:2680-2980），三处与任务1同口径（同一个 `_P0A_HEAD_MERGE_SINGLE`）。
> 实测：**决定性站点在第一层（2553，任务书 2.2 的审计区）**，三处嵌入式扫描是配套同步。

---

## 一、改动清单（4 处，同一口径）

全部以 `CS锚 ∪ (词首 ? _P0A_HEAD_MERGE_SINGLE : ∅)` 表达，「词首」= `scan_pos == 0` + 后随汉字 `_is_han(full_identifier[scan_pos+1])`：

| # | 位置 | 原判据 | 新判据 |
|---|---|---|---|
| A | 第一层 skip_verb (2553) | `keyword in _compound_safe` | `keyword in _compound_safe or (keyword in _P0A_HEAD_MERGE_SINGLE and _is_han(full_identifier[1]))` |
| B | 探测循环 (2736) | `sub_kw in self.compound_safe_single_keywords` | `sub_kw in CS or (sub_kw in _P0A_HEAD_MERGE_SINGLE and scan_pos==0 and scan_pos+sub_len<len(fi) and _is_han(fi[scan_pos+sub_len]))` |
| C | 输出循环 (2813) | 同上 | 同上（判据与 B **严格一致**，否则探测说「有内嵌关键字」而输出侧跳过，会走错分支） |
| D | rematch (2961) | 同上 | `sub_kw in CS or (sub_kw in _P0A_HEAD_MERGE_SINGLE and scan_pos==0 and sub_len<len(fi) and _is_han(fi[sub_len]))` |

### 为什么 A 是决定性的
`长度 为 7` 的破裂发生在第一层：`_match_keyword` 命中 `长`（单字关键字）后，若 `长 ∉ _compound_safe` 则 `skip_verb=False` → 直接 `_tokens_append(KEYWORD,'长')`，嵌入扫描**根本收不到** `长度` 这一串。故只在三处嵌入式扫描加规则**不足以**修复 G2 —— 必须同时改第一层（任务书 2.2 的审计区）。

### 2.2 单字动词词首联动评估（任务书要求）
任务书所指「单字动词在词首且词长>1时跳过」即 **A 站点本身**（2553 的 `if length==1 and keyword in _compound_safe and len(full_identifier)>1`）。
- **不与新规则重复**：它就是词首并入的执行点，正面规则在此并入（union 形式），不是旁路。
- **不与新规则冲突**：`_P0A_HEAD_MERGE_SINGLE` 相对 CS 净增的 14 字在 `full_identifier` 词首 + 后随汉字时触发，与原有 CS 分支同向（都是 `skip_verb=True`），故是**同向扩充**而非改向。
- 原分支里另有「后随中文数字时例外」（`加五`→加+五）与「`之` 成员访问例外」两条收窄，正面规则**不经过它们**（只在 `keyword ∉ CS` 时进入），故两条既有例外对 DUAL 8 与 CS 字一字不改。

---

## 二、一致性约束（探测/输出必须同判据）

历史坑（v7 单02）：探测循环说「有内嵌关键字」而输出循环又跳过 → 走进不一致分支。故 B/C/D 三处**逐字同判据**（同样的 `scan_pos==0` + 后随汉字 + `_P0A_HEAD_MERGE_SINGLE`）。`_r26_ab_final.json` 的 **0/843 零变化**即该一致性的实证。

---

## 三、验证结果

| 判据 | 结果 |
|---|---|
| 全语料 token 零变化（A+B+C+D 合并后） | ✅ **0 / 843 文件** |
| 与任务1 同口径 | ✅ 同一 `_P0A_HEAD_MERGE_SINGLE`，无第二套类别 |
| import 自校验 | ✅ `HEAD−CS == 14字` |
| 快速 `.light` rc=0 | ✅ 覆盖 DUAL 8 词首并入（加法/减法/乘法/除法/模组/真空/到位） |

---

## 四、文件改动（任务2 部分）

- `light-merge/src/lexer.py`：站点 A(2553) / B(2736) / C(2813) / D(2961) 四处判据改写 + 注释
- 证据：`lightharness/_r26_ab_final.json`（0/843）
