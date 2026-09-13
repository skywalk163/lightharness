# 第19轮 任务1 交付报告 —— 词法分析器核心（L-084 / L-092 / L-137）

> 日期：2026-09-13 ｜ 编译器项目：`light-merge`（branch main）
> 验证项目：`lightharness`（branch main）
> 路：任务1（词法分析器核心，标识符最大匹配策略）
> 铁律：跨项目操作；每缺陷最小复现；不破坏现有回归；反跑 A/B/C 三项。

---

## 一、根因

中文关键字/保留字出现在标识符中时被"关键字优先"策略在关键字边界切碎。本轮聚焦的 3 个缺陷根因都是同一类——**嵌入关键字子串被误判为关键字边界**：

- **L-084**：`为` 黏在标识符尾部（`末位行为` → `末位行` + `为`），`为` 被误当赋值关键字，导致 `设 末位行为 为 "test"` 解析失败。
- **L-092**：标识符含 `返回`（`返回表` → `返回` + `表`）。
- **L-137**：变量名以 `尝试` 开头（`尝试记录` → `尝试` 被当 `尝试...捕获` 语句开头）。

`为`/`返回`/`尝试` 这三个字在光明语法中**恒带空格使用**（`设 X 为 Y` / `返回 值` / `尝试...捕获`），一旦黏在更长汉字串中，必是标识符的一部分，整串应作为标识符输出，仅当整串精确等于关键字时才作关键字。

---

## 二、改动点（light-merge 仅改 `src/lexer.py`，符合文件互斥）

### 2.1 新增模块级常量（line 530~537）
```python
# 任务1（L-084/L-092/L-137）：嵌入关键字最大匹配集合。
# `为`/`返回`/`尝试` 是恒带空格使用的关键字，一旦黏在更长汉字串中必是标识符的一部分，
# 整串作为标识符输出，绝不按关键字边界切碎；仅当整串精确等于关键字时才作关键字。
_EMBED_MAX_MATCH_KEYWORDS = frozenset({'为', '返回', '尝试'})
```

### 2.2 在 `_tokenize_chinese_sequence` 的 `_P0A_MERGE_WHOLE` 检查之后新增最大匹配分支（line 2285~2302）
```python
# 任务1（L-084/L-092/L-137）：嵌入关键字最大匹配。
# `为`/`返回`/`尝试` 恒带空格使用，黏在更长汉字串中必为标识符的一部分，整串作标识符输出
# （如 行为/末位行为→ID(末位行为)、返回表→ID(返回表)、尝试记录→ID(尝试记录)）。
# 仅当整串精确等于关键字时才作关键字（设 X 为 Y / 返回 值 / 尝试...捕获 中关键字恒独立成 token，不受影响）。
if (full_identifier not in _ALL_KEYWORDS_WITH_VERBS
        and len(full_identifier) > 1):
    _emb_hit = False
    for _ek in _EMBED_MAX_MATCH_KEYWORDS:
        if _ek in full_identifier:
            _emb_hit = True
            break
    if _emb_hit:
        _tokens_append(_Token(_TokenType.IDENTIFIER, full_identifier, line, current_col))
        consumed += len(full_identifier)
        current_col += len(full_identifier)
        continue
```

### 2.3 设计要点（防回归）
- 分支**前置条件** `full_identifier not in _ALL_KEYWORDS_WITH_VERBS and len(full_identifier) > 1`：
  - 整串精确等于关键字（如独立 `为`/`返回`/`尝试`）时 `len==1` 不满足 `>1`，仍走原关键字路径 → 赋值/返回/尝试语句语法不变。
  - 整串是其它合法关键字（如 `如果`/`否则`）不受影响。
- 仅对**含嵌入关键字子串且长度>1**的候选做整体标识符化，口径与既有 `_COMPOUND_SAFE_SINGLE_KEYWORDS` / `_P0A_MERGE_WHOLE` / 嵌入关键字扫描保持一致，避免重复切碎。

---

## 三、验证结果

### 3.1 最小复现用例（lightharness/examples/）
| 用例 | 缺陷 | 修复前 | 修复后 | 说明 |
|---|---|---|---|---|
| `test_L084.light` | L-084（`末位行为` 被切） | 立红（解析失败） | **绿 rc=0**，打印 `test` | 本轮**真正修复** |
| `test_L092.light` | L-092（`返回值` 参数） | 已绿（既有硬化） | **绿 rc=0**，打印 `1` | 回归保护用例，前序已覆盖 |
| `test_L137.light` | L-137（`尝试记录` 被切） | 已绿（既有硬化） | **绿 rc=0**，打印 `1` | 回归保护用例，前序已覆盖 |

> **诚实声明**：经 Lexer.tokenize 直测与变异实验确认，L-092/L-137 的嵌入 `返回`/`尝试` 场景在**本轮修改前即已绿**——由既有的复合词硬化（`_COMPOUND_SAFE_SINGLE_KEYWORDS` + 嵌入关键字扫描）独立覆盖。本轮新增的嵌入最大匹配分支把 `为`/`返回`/`尝试` 纳入**统一口径**，主要价值是修复 L-084（`为` 词尾）并防止该家族回归；**不为 L-092/L-137 伪造"修复前立红"**。L-092/L-137 作为回归保护用例保留，验收标准"修复后 rc=0"满足。

### 3.2 反跑脚本 `_antirun_t1_词法核心.py`（A/B/C 三项全过）
- **A 判据**：干净运行 3 用例全绿 → `ANTIRUN T1 ALL OK`
- **B 判据**：边界用例 PASS —— 独立 `为`（`设 甲 为 10`）/ 独立 `返回`（`段落 取 接收 值: 返回 值`）仍作关键字；`为了`/`行为`/`作为`/`成为`/`认为` 作整体标识符（分别打印 1/2/3/4/5）。
- **C 判据**：撤掉本轮分支（锚点 `_EMBED_MAX_MATCH_KEYWORDS` 置空）→ **L-084 立红**（证明修复必要）；L-092/L-137 仍绿（证明由既有硬化独立保护）。恢复后 sha256 一致、3 用例复绿。

### 3.3 词法家族回归（铁律5）
`test_L004` / `test_L010` / `test_L011` / `test_L012` / `test_L015` 全部 **rc=0**，无回归。

---

## 四、全量 CI 期望

- 运行：`$env:LIGHT_MERGE="G:\dswork\duan-light-merge\light-merge"; python 运行.py examples/test_L084.light`（rc=0）
- 反跑：`python _antirun_t1_词法核心.py` → `ANTIRUN T1 ALL OK`
- lightharness 全量 CI（路M 收口执行）：期望 pytest 311+ passed + smoke 5/5。本轮仅改词法器一处（新增恒带空格关键字的整体标识符化分支），已有 Lexer.tokenize 直测 + 词法家族回归用例保证不回潮；无已知破坏现有回归的风险。

---

## 五、交付物清单
- light-merge 修复代码：`src/lexer.py`（新增 `_EMBED_MAX_MATCH_KEYWORDS` + 嵌入最大匹配分支）
- lightharness 复现用例：`examples/test_L084.light` / `test_L092.light` / `test_L137.light`
- lightharness 反跑：`_antirun_t1_词法核心.py`
- lightharness 报告：本文件

---

## 六、遗留/后续
- L-092/L-137 实为前序硬化已修复，建议缺陷账状态更新为「已修复（既有硬化；R19 统一口径纳入）」，不必占用本轮编译器修复额度。
- 后续若扩展嵌入关键字集合（如新增恒带空格关键字），只需在 `_EMBED_MAX_MATCH_KEYWORDS` 加字，无需改分支逻辑。
