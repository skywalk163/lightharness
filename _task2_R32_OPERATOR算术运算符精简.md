# 第32轮 OPERATOR_VERBS 算术运算符(任务2) 逐条验证清单（合并）

日期：2026-09-15 ｜ 三重判据：G1 全语料零变化 ∧ G2 编译门 rc=0 ∧ G3 边界形态不变

## 一、结论总览

- 本批条目数：**10**
- 可删：**0**（无）
- 保留（真护栏）：**10**（['乘', '乘以', '减', '减去', '加', '加上', '除', '除以', '幂', '模']）
- `lexer.py` 改动：否（无条目可删，主树不变）

## 二、逐条三重判据表

| 条目 | G1 变化文件 | G2 rc | G3 失败形态 | 结论 |
|---|---|---|---|---|
| 乘 | 2 | 0 | 1 | **保留** |
| 乘以 | 0 | 0 | 2 | **保留** |
| 减 | 4 | 0 | 1 | **保留** |
| 减去 | 0 | 0 | 2 | **保留** |
| 加 | 4 | 0 | 1 | **保留** |
| 加上 | 0 | 0 | 2 | **保留** |
| 除 | 5 | 0 | 1 | **保留** |
| 除以 | 0 | 0 | 2 | **保留** |
| 幂 | 0 | 0 | 1 | **保留** |
| 模 | 6 | 0 | 1 | **保留** |

## 三、各条保留理由（G1/G3 失败点）

### 「乘」—— 保留（语料命中 85 文件）

G3 失败边界形态（撤除后 token 流变化 = 真护栏）：
- `甲乘乙`：@0 ('IDENTIFIER', '甲') -> ('IDENTIFIER', '甲乘乙')

G1 变化文件（撤除后 token 流变化，前 10）：
- `light-merge/tests/final_test.light`：@54 ('IDENTIFIER', '阶') -> ('IDENTIFIER', '阶乘五')
- `lightharness/examples/test_R24_运算符单字守卫.light`：@72 ('KEYWORD', '乘') -> ('IDENTIFIER', '乘乙')

### 「乘以」—— 保留（语料命中 20 文件）

G3 失败边界形态（撤除后 token 流变化 = 真护栏）：
- `甲乘以乙`：@0 ('IDENTIFIER', '甲') -> ('IDENTIFIER', '甲乘以乙')
- `乘以法`：@0 ('KEYWORD', '乘以') -> ('IDENTIFIER', '乘以法')

### 「减」—— 保留（语料命中 94 文件）

G3 失败边界形态（撤除后 token 流变化 = 真护栏）：
- `甲减乙`：@0 ('IDENTIFIER', '甲') -> ('IDENTIFIER', '甲减乙')

G1 变化文件（撤除后 token 流变化，前 10）：
- `light-merge/examples/advanced.light`：@36 ('KEYWORD', '减') -> ('IDENTIFIER', '减一')
- `light-merge/examples/basic.light`：@91 ('IDENTIFIER', '数') -> ('IDENTIFIER', '数减1')
- `lightharness/examples/test_R24_运算符单字守卫.light`：@61 ('KEYWORD', '减') -> ('IDENTIFIER', '减乙')
- `lightharness/examples/test_R25_词尾并入边界反向.light`：@260 ('KEYWORD', '减') -> ('IDENTIFIER', '减右')

### 「减去」—— 保留（语料命中 33 文件）

G3 失败边界形态（撤除后 token 流变化 = 真护栏）：
- `甲减去乙`：@0 ('IDENTIFIER', '甲') -> ('IDENTIFIER', '甲减去乙')
- `减去法`：@0 ('KEYWORD', '减去') -> ('IDENTIFIER', '减去法')

### 「加」—— 保留（语料命中 521 文件）

G3 失败边界形态（撤除后 token 流变化 = 真护栏）：
- `甲加乙`：@0 ('IDENTIFIER', '甲') -> ('IDENTIFIER', '甲加乙')

G1 变化文件（撤除后 token 流变化，前 10）：
- `light-merge/examples/basic.light`：@53 ('IDENTIFIER', '加法') -> ('IDENTIFIER', '加法接收甲')
- `lightharness/examples/test_R20_关键字前缀标识符.light`：@628 ('KEYWORD', '加') -> ('IDENTIFIER', '加乙')
- `lightharness/examples/test_R24_运算符单字守卫.light`：@51 ('KEYWORD', '加') -> ('IDENTIFIER', '加乙')
- `lightharness/examples/test_R25_词尾并入边界反向.light`：@246 ('KEYWORD', '加') -> ('IDENTIFIER', '加右')

### 「加上」—— 保留（语料命中 166 文件）

G3 失败边界形态（撤除后 token 流变化 = 真护栏）：
- `甲加上乙`：@0 ('IDENTIFIER', '甲') -> ('IDENTIFIER', '甲加上乙')
- `加上法`：@0 ('KEYWORD', '加上') -> ('IDENTIFIER', '加上法')

### 「除」—— 保留（语料命中 322 文件）

G3 失败边界形态（撤除后 token 流变化 = 真护栏）：
- `甲除乙`：@0 ('IDENTIFIER', '甲') -> ('IDENTIFIER', '甲除乙')

G1 变化文件（撤除后 token 流变化，前 10）：
- `light-merge/bootstrap/release/stdlib/字符串常量.light`：@168 ('IDENTIFIER', '去') -> ('IDENTIFIER', '去除两端空白')
- `light-merge/bootstrap/release/stdlib/日志系统增强.light`：@404 ('IDENTIFIER', '排') -> ('IDENTIFIER', '排除关键词')
- `light-merge/bootstrap/release/stdlib/系统接口.light`：@46 ('IDENTIFIER', '删') -> ('IDENTIFIER', '删除环境变量')
- `lightharness/examples/test_R24_运算符单字守卫.light`：@82 ('KEYWORD', '除') -> ('IDENTIFIER', '除乙')
- `lightharness/src/重复提醒.light`：@576 ('IDENTIFIER', '排') -> ('IDENTIFIER', '排除名单')

### 「除以」—— 保留（语料命中 13 文件）

G3 失败边界形态（撤除后 token 流变化 = 真护栏）：
- `甲除以乙`：@0 ('IDENTIFIER', '甲') -> ('IDENTIFIER', '甲除以乙')
- `除以法`：@0 ('KEYWORD', '除以') -> ('IDENTIFIER', '除以法')

### 「幂」—— 保留（语料命中 50 文件）

G3 失败边界形态（撤除后 token 流变化 = 真护栏）：
- `甲幂乙`：@0 ('IDENTIFIER', '甲') -> ('IDENTIFIER', '甲幂乙')

### 「模」—— 保留（语料命中 502 文件）

G3 失败边界形态（撤除后 token 流变化 = 真护栏）：
- `甲模乙`：@0 ('IDENTIFIER', '甲') -> ('IDENTIFIER', '甲模乙')

G1 变化文件（撤除后 token 流变化，前 10）：
- `light-merge/bootstrap/release/stdlib/临时文件.light`：@18 ('IDENTIFIER', '文本') -> ('IDENTIFIER', '文本模式')
- `light-merge/bootstrap/release/stdlib/文件匹配.light`：@9 ('IDENTIFIER', '提供文件路径') -> ('IDENTIFIER', '提供文件路径模式匹配功能')
- `lightharness/examples/test_R24_运算符单字守卫.light`：@92 ('KEYWORD', '模') -> ('IDENTIFIER', '模乙')
- `lightharness/src/e2b客户端.light`：@27 ('IDENTIFIER', '本地') -> ('IDENTIFIER', '本地模拟')
- `lightharness/src/子智能体.light`：@80 ('IDENTIFIER', '目录') -> ('IDENTIFIER', '目录模式')
- `lightharness/src/权限.light`：@211 ('IDENTIFIER', '危险') -> ('IDENTIFIER', '危险模式')

## 四、铁律自检

| 铁律 | 自检 |
|---|---|
| 只改本批条目，不碰其他批 | ✅ monkeypatch 仅撤除本批条目 |
| 逐条隔离验证 | ✅ 进程内 monkeypatch，不改主树 |
| G1∧G2∧G3 全通过才可删 | ⛔ 本批 10 条均未全通过，全部保留 |
| 删除后全量反跑零回归 | 主树未改，全语料 token 流不变（vacuous） |
| 新增一律 .light | ✅ G2 探针为临时 .light（验证后清理） |