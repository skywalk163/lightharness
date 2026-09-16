# 第35轮收口说明（终稿）

> 轮次：第35轮 ｜ 主题：`_P0A_MERGE_WHOLE` 剩余 3 条通用化精简
> 日期：2026-09-16 ｜ 收口：路M ｜ 状态：**已收口 · 分路提交（未 push，用户手工推）**

---

## 一、本轮结论（一句话）

`_P0A_MERGE_WHOLE` **3 → 2**：`非空块` 由**一元前缀运算符通用规则（GR-2b）**接住后移除；
`整理模型消息` 与 `记录类型` 经两次通用化尝试**实证不可通用化**，保留为真护栏。

| 条目 | G1 | G2 | G3 | 处置 | 保留/移除理由 |
|---|---|---|---|---|---|
| 整理模型消息 | 撤单条 0 变化 | rc=0 | **F5 FAIL** | **保留** | `模` 是真取模运算符（`甲模乙` 实证）；GR-1 打红 6 文件、GR-1c 打红 1 文件 |
| 非空块 | **0 变化**（867 文件） | rc=0 | **全通过** | **已移除** | GR-2b 通用规则接住；变异反跑 F2/F5 必红 |
| 记录类型 | 撤单条打红 **2 文件** | rc=0 | **F2/F5 FAIL** | **保留** | 与 `期望类型`/`参数类型` 结构不可分；GR-3 打红 4 个 stdlib，GR-3c 仅调用语境 G1=0 但 G3-F5 仍 FAIL |

---

## 二、代码改动（light-merge）

**唯一改动文件：`light-merge/src/lexer.py`**（34 增 / 6 删，其中**代码改动仅 4 处**，余为注释/文档）

1. 新增类别 `Lexer._P0A_UNARY_PREFIX_KW = frozenset({'非'})`（一元前缀运算符）。
2. R21 词首闸门3 判据改为 `_lead_kw not in (_OPERATOR_KEYWORDS - self._P0A_UNARY_PREFIX_KW)`。
3. 增加收窄：余部是**已声明名字**时 `非X` 仍是 `not X` 表达式，不并入复合名。
4. `_P0A_MERGE_WHOLE` 移除 `'非空块'`（3→2）。

**不变量**：CS=0、CCW=0、NEVER_SPLIT=0、EMBED=3、OPERATOR_VERBS=19、DUAL=8、HM=25、F=46、HARD_STMT=9。
注：R33 的 NEVER_SPLIT 4→0、HM22→25、F43→46、词首切分集 42→39、union 30→32 已随 R33 提交（`ae68deb7`），本轮不改这些。

---

## 三、验收标准核对（路M 复测）

| 项 | 状态 | 证据 |
|---|---|---|
| 3 条通用规则尝试完成（1 成功 / 2 保留） | ✅ | `_task1/2/3_R35_*.md` |
| `_P0A_MERGE_WHOLE` 状态明确（**2 条**） | ✅ | `tests/test_R35_…token.py` |
| 各任务边界用例全部通过 | ✅ | 3 个 `.light` 均 rc=0 |
| 全量反跑零回归 | ✅ | G1：867 可比文件 0 变化 0 新错（`_r35_g1_engine.py`） |
| G3 边界门终验通过 | ✅ | 3 条五形态全通过（`_r35_g3_边界门.py`） |
| 性能对比数据 | ✅ | `_r35_perf.json`（ABAB 交替，Δ=+1.87% 噪声带内） |
| 联动评估结论 | ✅ | `_task5_R35_…md` §2（只出结论，未改代码） |
| pytest 全量 | ✅ | **1197 passed / 1 skipped**（路M 复测，见 §四） |
| R26 基线快照过期红 | ✅ 已解决 | 最小修订 + 审计（§四·决策1） |
| R29/R30 死文件红 | ✅ 已解决 | 登记 EXPECT_RED（§四·决策4） |
| 全量 CI（门禁机 192.168.0.88） | ⬜ 待用户 | 不在本机执行 |
| docs 三件回填 + 反跑判据 §6 | ✅ | 对标清单 #156、行为差异 R35-D1/D2/D3、缺陷账 L-154、反跑判据 §6 |
| git 分路提交 | ✅ 已提交（未 push） | 见 §五 |

---

## 四、路M 收口决策（原 §四 三项 + 新增一项，全部已落地）

### 决策 1：R26 全语料基线快照过期 → **最小可审计修订（非整体重生）**

2 条 `test_fingerprint_unchanged` 报「1 文件变化：`test_审批.light`」。

**实证（决定性）**：用**当前（R35 改动后）lexer** 对**快照时点**内容（`git show e26ed3d^:examples/test_审批.light`）tokenize，
指纹与快照记录**逐位一致**（`3440261634d1…`），token 数 1309→1309 不变；对新（工作树）内容不同。
时间线：快照 2026-09-15 **13:31** < 文件入库 `e26ed3d`（2026-09-15 **20:02**，第31轮 T4 flaky 修复 `time.time→time.monotonic`）**晚 6.5 小时**。
⇒ **零词法回归**，纯源文件漂移。

**处置**：不整体重生快照（避免把其它文件真实回归一并洗白，即守"合并前不刷 baseline"红线）。
只修订该条 `per_file[...].sha`，并追加 `_amendments` 审计条目（时间/提交号/新旧 token 指纹/新旧源文件内容 sha256/token 数/理由），
`corpus_aggregate_fingerprint` 保持原值。工具 `_taskM_amend_r26_快照.py`（dry-run 默认，加 `--apply` 落盘；内置取证，旧内容不符快照会自动 ABORT）。
指纹测试已转绿（R27/R28 由红转绿）。

### 决策 2：缺陷账 L-154（CCW 清零后合成名整词能力丧失）

`异步读取文件` / `并发等待` / `常量时间比较` 不再整词。全语料零命中故影响低，风险在于**静默**。
本轮已用"钉住现状"断言（`test_ccw_names_split_after_ccw_cleared`）使其可感知，未修（超出范围，修它等于重引白名单）。
**状态：待立项**，由用户后续决定。

### 决策 3：2 条方法论写入 `docs/功能对标/反跑判据.md` §6

- **§6.1** 收口必须跑全量 `pytest tests/`（不能只跑 `.light` 套件）—— 本轮即因之前只跑 `.light` 套件，
  漏掉 R33 遗留 16 条过期断言潜伏一整轮。
- **§6.2** 性能 A/B 必须交替多轮（ABAB）—— 首测 +5.6% 被复测翻转为 −1.9%。
- **§6.3** 语料指纹快照漂移：先取证证明零回归，再最小修订（本条即本次处置的标准化）。

### 决策 4（新增）：R29/R30 两个 `.light` 边界测试是**死文件** → 登记 EXPECT_RED

收口复测暴露 2 条 `test_回归.py::test_example_exit_code` 红：`test_R29_CCW精简边界.light` / `test_R30_CCW通用化边界.light`。

**根因（决定性实证）**：用 lexer 直接 tokenize 这些名字，CCW 清零（R30 自己干的，184→0）后它们已被切分——
`位与`→`位`+`与`、`位非`→`位`+`非`、`幂次`→`幂`+`次`、`除非`→`除`+`非`、`应当`→`应`+`当`。
原文件设计前提（"CCW 清零后这些复合名仍整词成 IDENTIFIER 并可作函数调用"）已被**现实推翻**；
且两文件各含**孤立 `捕获` 块缺 `尝试:`**、`调用未定义函数名（位与/幂次/记录类型…）`。
**自入库起从未 rc=0**（解析期即失败，整份用例从未真正执行，是假死边界测试）。

**A/B 验证**：用 `git show HEAD:src/lexer.py`（R35 改动前）跑这两文件 → **同样红、错误信息逐字一致** ⇒ 与 R35 无关。
另 light-merge `tests/test_lexer.py` 的 3 条红（`设甲为三加五` 期望切出关键字）经同法 A/B 验证亦与 R35 无关，属 light-merge 历史基线债，本轮不处理。

**处置**：不删文件（保留历史意图可追溯），在 `tests/test_回归.py` 的 `EXPECT_RED` 登记这 2 条（原因写明），
使其可被门禁感知（将来若修复文件使之 rc=0，本条会反红逼你移除登记），而非悄悄绿着。
**已验证**：`-k "R29_CCW or R30_CCW"` → `2 passed`。

---

## 五、提交清单（分路提交，未 push）

### light-merge（1 个已跟踪文件）
```
git add src/lexer.py
git commit -m "第35轮：_P0A_MERGE_WHOLE 3→2（非空块 由一元前缀运算符通用规则接住）"
```

### lightharness（已跟踪 14 + 新增 12）

已跟踪（M）：
```
docs/功能对标/对标清单.json          # 追加 #156
docs/功能对标/行为差异清单.md         # 追加 R35-D1/D2/D3（+D3 路M裁定）
docs/功能对标/语言缺陷账.md           # 追加 L-154
docs/功能对标/反跑判据.md             # 追加 §6（收口方法论）
tests/test_回归.py                    # 登记 2 条 EXPECT_RED（R29/R30 死文件）
tests/test_R23_词法边界_token.py     # CCW 清零后 3 例改钉现状
tests/test_R25_单字后缀_token.py     # 旧属性名 + F=46 + 到∈F
tests/test_R26_词首并入_token.py     # HM=25 / SPLIT=39 / union=32 / F=46
tests/test_R27_CS表16字词首并入_token.py  # DUAL/净增量/A类交集
tests/test_R28_CS表2字词尾上下文_token.py # 净增量 / HM=25
tests/test_R29_CCW表分批精简_token.py     # HM=25
tests/test_R30_CCW保留10条通用化_token.py # F=46
tests/test_R32_OPERATOR+MERGE_WHOLE精简_token.py  # MERGE_WHOLE 3→2
tests/test_R33_NEVER_SPLIT精简_token.py   # MERGE_WHOLE 3→2 + HM=25
```

新增（`??`，建议提交）：
```
tests/test_R35_MERGE_WHOLE通用化_token.py   # 新增 31 用例（全绿）
examples/test_R35_整理模型消息边界.light
examples/test_R35_非空块边界.light
examples/test_R35_记录类型边界.light
_task1_R35_整理模型消息通用化.md
_task2_R35_非空块通用化.md
_task3_R35_记录类型通用化.md
_task4_R35_合并验证+全量反跑+G3终验.md
_task5_R35_性能对比+联动评估+pytest.md
_task6_R35_质量审查报告.md
_taskM_第35轮收口说明.md
_taskM_amend_r26_快照.py                # 收口工具（被反跑判据.md §6.3 引用）
```

不提交（收口/临时探针，按惯例）：`_antirun_r35_*`、`_r35_*.py`、`_r35_*.json`、
`_r35_lexer_AFTER.bak`、以及历史各轮 `_*` 探针与日志。

> 注意：`_antirun_r26_基线快照.json` 是**已跟踪数据文件**（非临时探针），其本次最小修订
> （§四·决策1：只改 1 条 `per_file` 指纹 + 追加 `_amendments` 审计）**随收口一并提交**，
> 否则工作树会脏、且别人 clone 后指纹测试会复红。

---

## 六、后续轮次建议（路M 参考）

1. `_P0A_MERGE_WHOLE` 剩 2 条均为真护栏，**不再尝试精简**，定期（每 5 轮）复验即可。
2. 一元前缀类别 `_P0A_UNARY_PREFIX_KW` 目前仅 `非`；若 `负`/`反` 等出现"无空格恒为复合名"证据，直接加类别（同口径收窄）。
3. 词首并入 / 词尾切分不对称（R35-D2）如需对称化，须同时改 L3343，属独立变更，单独立项。
4. 性能可选优化：`_OPERATOR_KEYWORDS - _P0A_UNARY_PREFIX_KW` 预计算为模块常量（预期回收 ~1.9%）。
5. **建议下一轮清理**：R29/R30 两个死文件要么真正重写为钉住"CCW 清零后被切分"现状的合法 `.light`，
   要么从 `examples/` 移入 `docs/` 作为"历史意图存档"并移出 `test_回归.py` 收集范围；
   当前 EXPECT_RED 登记仅是门禁止血，不是终态。
6. light-merge `tests/test_lexer.py` 的 3 条基线红（错误假设确定性词法应切出关键字）应单独立项修正或移除。
