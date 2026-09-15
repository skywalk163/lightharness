# 第32轮 OPERATOR_VERBS 比较运算符(任务1) 逐条验证清单（合并）

日期：2026-09-15 ｜ 三重判据：G1 全语料零变化 ∧ G2 编译门 rc=0 ∧ G3 边界形态不变

## 一、结论总览

- 本批条目数：**9**
- 可删：**0**（无）
- 保留（真护栏）：**9**（['不大于', '不小于', '不等于', '大于', '大于等于', '小于', '小于等于', '等于', '包含']）
- `lexer.py` 改动：否（无条目可删，主树不变）

## 二、逐条三重判据表

| 条目 | G1 变化文件 | G2 rc | G3 失败形态 | 结论 |
|---|---|---|---|---|
| 不大于 | 0 | 0 | 2 | **保留** |
| 不小于 | 0 | 0 | 2 | **保留** |
| 不等于 | 0 | 0 | 2 | **保留** |
| 大于 | 2 | 0 | 2 | **保留** |
| 大于等于 | 1 | 0 | 2 | **保留** |
| 小于 | 1 | 0 | 2 | **保留** |
| 小于等于 | 1 | 0 | 2 | **保留** |
| 等于 | 2 | 0 | 2 | **保留** |
| 包含 | 0 | 1 | 0 | **保留** |

## 三、各条保留理由（G1/G3 失败点）

### 「不大于」—— 保留（语料命中 1 文件）

G3 失败边界形态（撤除后 token 流变化 = 真护栏）：
- `甲不大于乙`：@0 ('IDENTIFIER', '甲') -> ('IDENTIFIER', '甲不大于乙')
- `不大于号`：@0 ('KEYWORD', '不大于') -> ('IDENTIFIER', '不大于号')

### 「不小于」—— 保留（语料命中 2 文件）

G3 失败边界形态（撤除后 token 流变化 = 真护栏）：
- `甲不小于乙`：@0 ('IDENTIFIER', '甲') -> ('IDENTIFIER', '甲不小于乙')
- `不小于号`：@0 ('KEYWORD', '不小于') -> ('IDENTIFIER', '不小于号')

### 「不等于」—— 保留（语料命中 67 文件）

G3 失败边界形态（撤除后 token 流变化 = 真护栏）：
- `甲不等于乙`：@0 ('IDENTIFIER', '甲') -> ('IDENTIFIER', '甲不等于乙')
- `不等于号`：@0 ('KEYWORD', '不等于') -> ('IDENTIFIER', '不等于号')

### 「大于」—— 保留（语料命中 90 文件）

G3 失败边界形态（撤除后 token 流变化 = 真护栏）：
- `甲大于乙`：@0 ('IDENTIFIER', '甲') -> ('IDENTIFIER', '甲大于乙')
- `大于号`：@0 ('KEYWORD', '大于') -> ('IDENTIFIER', '大于号')

G1 变化文件（撤除后 token 流变化，前 10）：
- `light-merge/bootstrap/release/stdlib/断言工具.light`：@328 ('IDENTIFIER', '断言') -> ('IDENTIFIER', '断言大于')
- `light-merge/examples/basic.light`：@35 ('KEYWORD', '大于') -> ('IDENTIFIER', '大于乙')

### 「大于等于」—— 保留（语料命中 47 文件）

G3 失败边界形态（撤除后 token 流变化 = 真护栏）：
- `甲大于等于乙`：@0 ('IDENTIFIER', '甲') -> ('IDENTIFIER', '甲大于等于乙')
- `大于等于号`：@0 ('KEYWORD', '大于等于') -> ('IDENTIFIER', '大于等于号')

G1 变化文件（撤除后 token 流变化，前 10）：
- `light-merge/bootstrap/release/stdlib/断言工具.light`：@377 ('IDENTIFIER', '断言') -> ('IDENTIFIER', '断言大于等于')

### 「小于」—— 保留（语料命中 83 文件）

G3 失败边界形态（撤除后 token 流变化 = 真护栏）：
- `甲小于乙`：@0 ('IDENTIFIER', '甲') -> ('IDENTIFIER', '甲小于乙')
- `小于号`：@0 ('KEYWORD', '小于') -> ('IDENTIFIER', '小于号')

G1 变化文件（撤除后 token 流变化，前 10）：
- `light-merge/bootstrap/release/stdlib/断言工具.light`：@426 ('IDENTIFIER', '断言') -> ('IDENTIFIER', '断言小于')

### 「小于等于」—— 保留（语料命中 35 文件）

G3 失败边界形态（撤除后 token 流变化 = 真护栏）：
- `甲小于等于乙`：@0 ('IDENTIFIER', '甲') -> ('IDENTIFIER', '甲小于等于乙')
- `小于等于号`：@0 ('KEYWORD', '小于等于') -> ('IDENTIFIER', '小于等于号')

G1 变化文件（撤除后 token 流变化，前 10）：
- `light-merge/bootstrap/release/stdlib/断言工具.light`：@475 ('IDENTIFIER', '断言') -> ('IDENTIFIER', '断言小于等于')

### 「等于」—— 保留（语料命中 316 文件）

G3 失败边界形态（撤除后 token 流变化 = 真护栏）：
- `甲等于乙`：@0 ('IDENTIFIER', '甲') -> ('IDENTIFIER', '甲等于乙')
- `等于号`：@0 ('KEYWORD', '等于') -> ('IDENTIFIER', '等于号')

G1 变化文件（撤除后 token 流变化，前 10）：
- `light-merge/tests/final_test.light`：@56 ('CHINESE_NUM', 5) -> ('IDENTIFIER', '五等于')
- `lightharness/examples/test_R23_IDENTIFIER_SAFE后缀位置.light`：@163 ('KEYWORD', '等于') -> ('IDENTIFIER', '等于甲')

### 「包含」—— 保留（语料命中 332 文件）

G1∧G3 全通过（撤除后 token 零变化），仅 G2 编译门未过 —— 保守保留（详见铁律自检）。

> 说明：`包含` 为**边界情形**。撤除后全语料 857 文件 token 零变化、边界形态不变，说明其 OPERATOR_VERBS 成员资格对分词**冗余**（表达式中 `甲 包含 乙` 恒被吸收为标识符而非运算符）。G2 编译门失败仅因基态 `甲 包含 乙` 即不可编译（语言未将其实现为可编译的中缀运算符）。若后续放宽 G2 口径为「仅验证 token 安全」，包含可删；按本轮回严格门 G1∧G2∧G3 保留。

## 四、铁律自检

| 铁律 | 自检 |
|---|---|
| 只改本批条目，不碰其他批 | ✅ monkeypatch 仅撤除本批条目 |
| 逐条隔离验证 | ✅ 进程内 monkeypatch，不改主树 |
| G1∧G2∧G3 全通过才可删 | ⛔ 本批 9 条均未全通过，全部保留 |
| 删除后全量反跑零回归 | 主树未改，全语料 token 流不变（vacuous） |
| 新增一律 .light | ✅ G2 探针为临时 .light（验证后清理） |