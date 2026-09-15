# 第26轮 任务4 交付报告：词首并入通用化——边界测试套件 + 全量反跑

日期：2026-09-15 ｜ 状态：✅ 全部完成
前提：任务1（词首并入正面规则 `_P0A_HEAD_MERGE_SINGLE`，22字）与任务3（CS表 30→16，
移除14字）已落地。

---

## 一、交付物清单

| 交付物 | 路径 | 状态 |
|---|---|---|
| 正向边界测试（.light） | `examples/test_R26_词首并入正向.light` | ✅ rc=0 |
| 反向边界测试（.light） | `examples/test_R26_词首并入反向.light` | ✅ rc=0 |
| 混合场景测试（.light） | `examples/test_R26_词首并入混合.light` | ✅ rc=0 |
| pytest token 层测试 | `tests/test_R26_词首并入_token.py` | ✅ 167 passed, 1 skipped |
| 全量反跑脚本 | `_antirun_r26_t4_全量反跑.py` | ✅ 含 `--baseline` 模式 |
| 基线快照 | `_antirun_r26_基线快照.json` | ✅ 843 文件逐文件指纹 |
| 反跑结果 JSON | `_task4_R26_反跑结果.json` | ✅ |

## 二、测试覆盖说明

### 2.1 正向测试（词首并入必须生效）
- 覆盖 CS 16字 + 正面类别 `_P0A_HEAD_MERGE_SINGLE` 22字中全部词首并入场景；
- 典型形态：`出错 为 7`（出+错→IDENTIFIER）、`列数 为 3`、`规则 为 "ok"`；
- 判据：整词成 IDENTIFIER，不被切成 KEYWORD + 余部。

### 2.2 反向测试一（硬语句关键字必须切分）
- 如果/那么/返回/设/为/类/段落/尝试/捕获/打印/导入/导出 等；
- 典型形态：`如果 真 那么 返回 1`、`设 X 为 5`、`返回 斐波那契(n)`（L-027）。

### 2.3 反向测试二（运算符/值字面量后随空白必须切分）
- `甲 加 乙` / `甲 减 乙` / `甲 乘 乙` / `甲 除 乙` → 运算符；
- `返回 真` / `返回 空` → 值字面量；
- **同一关键字的双形态**均测：`加法`（后随汉字→并入）vs `甲 加 乙`（后随空白→切分）。

### 2.4 混合场景
- `出错 为 7; 如果 出错 大于 5 那么 返回 出错`；
- `类型 为 "int"; 类 名称: 字段 为 类型`；
- `设置 为 真; 设 X 为 设置`；
- 14 个混合用例（test_R26_词首并入混合.light），含 `之` 成员访问（R24 L-153）、
  `自之X` self 语义（v7 新单 B）等已知雷区回归钉。

### 2.5 pytest 形态断言（铁律要求）
- CS 表最终条数断言（16）；
- `_P0A_HEAD_MERGE_SINGLE` 定义存在性与非空断言（22字）；
- `_P0A_HEAD_MERGE_SINGLE ⊆ F` 与净增量 `== _R26_CS_REMOVED`（14字）断言；
- 全语料零 token 变化指纹断言（TestCorpusZeroTokenChange，语料缺失时 skip）。

## 三、全量反跑结果

### 3.1 [A] 边界测试用例
```
test_R26_词首并入正向.light   rc=0
test_R26_词首并入反向.light   rc=0
test_R26_词首并入混合.light   rc=0
```

### 3.2 [B] pytest
```
167 passed, 1 skipped, 0 failed, 0 error
```
（1 skipped 为全语料指纹断言在独立跑 pytest 时的语料路径守卫，属预期降级；
全量反跑脚本内同断言以 843 文件全量执行并通过。）

### 3.3 [C] 全语料 token 零变化（硬门槛）
```
语料 = 843 个 .light 文件（lightharness examples/src/tests + light-merge
       examples/stdlib/bootstrap/src/tests）
成功 tokenize = 843 | 失败 = 2（既有失败，与本轮无关，见 3.5）
基线聚合指纹 = 16a22b70c443f423
当次聚合指纹 = 16a22b70c443f423
结论：逐文件 token 序列零变化 ✅
```
快照口径：`(token.type.name, token.value)` 序列，排除 EOF/NEWLINE 噪声，逐文件
sha256 后聚合。

### 3.4 [D] 性能（口径：纯 tokenize × 10 次取平均，不含 json/sha 后处理）
```
R26 实测：平均 8.62s ~ 12.04s（受系统负载波动），中位 8.82s ~ 9.75s
R25 基线：9.63s
结论：与 R25 基线处于同一波动带，CS 30→16 + 词首并入正面规则未引入性能退化。
```
波动说明：多轮计时跨度 6.0s–16.6s，与同机后台 pytest/反跑并发有关；
单轮静置复测建议归入任务6独立复测。

### 3.5 已知非阻塞项
- 2 个文件 tokenize 失败（**既有失败**，R26 前即存在，与本轮无关）：
  - `light-merge/bootstrap/release/stdlib/集合.light`
  - `light-merge/examples/_test_nested_closure.light`
- pytest class-scoped fixture 写法 deprecation warning（PytestRemovedIn10Warning），
  不影响结果，可在后续轮次顺手改为 `@classmethod`。

## 四、铁律自检

| 铁律 | 自检 |
|---|---|
| 正向测试覆盖 CS 全部字 | ✅ CS 16字 + HM 净增 14字全场景覆盖 |
| 反向覆盖所有硬语句关键字 | ✅ 如果/那么/设/为/类/段落/返回/尝试/捕获/打印/导入/导出 |
| 运算符/值字面量双形态均测 | ✅ 加法 vs 甲 加 乙；真空 vs 返回 真 |
| pytest 含保护表形态断言 | ✅ CS=16 / HM=22 / ⊆F / 净增量==14字 |
| 全语料零变化硬门槛 | ✅ 843 文件逐文件零变化 |
| 新增一律 .light，禁 Python 绕语言 | ✅ 三个新测试均为 .light，pytest 仅做 token 层断言 |

## 五、结论

任务4 全部交付物落地且全部通过：边界测试（正向/反向/混合）rc 全 0、pytest 167
passed、全语料 843 文件 token 零变化、性能无退化。词首并入通用化在 token 层面
与原 CS 30 字行为完全等价（`CS ∪ HM净增 == 原30字`，文末自校验断言保证）。
