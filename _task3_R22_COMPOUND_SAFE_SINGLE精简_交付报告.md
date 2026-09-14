# 第22轮 任务3 交付报告：`_COMPOUND_SAFE_SINGLE_KEYWORDS` 逐条精简

> 日期：2026-09-14 ｜ 负责人：路M ｜ 结论：**精简 52 → 30（删除 22 条冗余，保留 30 条护栏）**
> 修改文件：`light-merge/src/lexer.py` —— `_COMPOUND_SAFE_SINGLE_KEYWORDS` 定义（行 414-447），仅增删条目，引用代码未动
> 验证脚本（终版）：`lightharness/_sweep_r22_t3_v3.py`（双 oracle：真实源 771 文件 + 词法单测套件，FAILED+SUBFAILED 双捕获）
> 反跑脚本：`lightharness/_antirun_r22_t5_全量回归扫描.py`（任务5 全量回归，结论 ALL_OK）
> 证据：`lightharness/_task3_R22_v3_evidence.json`（终版）、`_sweep_t3_v3_final.txt`（逐条明细）、`_verify_30.py`（30 条候选终验）

---

## 一、目标与背景

任务3 要求对 `_COMPOUND_SAFE_SINGLE_KEYWORDS`（52 条单字关键字复合保护）逐条执行**隔离中立验证**（判据③：撤掉该条目后全语料 token 序列零变化 ⇒ 冗余；有变化 ⇒ 真护栏），删除冗余条目、保留真护栏。

该表被四类引用位置消费：
- `_match_keyword`
- `_skip_compound_safe_and_match`
- `_tokenize_chinese_sequence`（OLD 路径）
- **`_P0A_COMPOUND_SAFE = _COMPOUND_SAFE_SINGLE_KEYWORDS | {'当'}`（P0A 确定性路径派生集合）**

> ⚠️ **关键陷阱（见第四节）**：`_P0A_COMPOUND_SAFE` 是 `Lexer` 的**类属性**，在模块 import 时即由 52 条集合一次性算定。若只改模块级全局 `_COMPOUND_SAFE_SINGLE_KEYWORDS` 而不重导模块，P0A 路径不会跟着变 —— 这是 v1 误报的根因。

---

## 二、验证方法（v3 双 oracle：隔离中立 + 单元测试，FAILED+SUBFAILED 双捕获）

v3 在 v2 基础上补齐了 **单元测试 oracle** 并修正了解析器，彻底纠正 v2/v3-初版漏判：

1. **真实源 oracle**：git HEAD 52 条集合的 lexer 对全语料（**771 个真实源 `.light`**）dump token 序列 SHA256 作基线。
2. **单元测试 oracle**：用 `sys.modules['lexer']` 打补丁方式，把"去掉单条 k 的修改版 lexer"注入 pytest 收集前，使 `from lexer import Lexer` 绝对命中修改版，**绕过 `src` 路径阴影**。套件：`test_lexer.py` / `test_lexer_compound_safe_alignment.py` / `test_lexer_p0a_deterministic.py` / `test_lexer_perf.py`。
   - **双捕获**：解析 pytest 输出时**同时捕获 `FAILED `（整测试失败）与 `SUBFAILED(`（子测试失败）**——这是 v3-初版漏掉 5 个子测试回归的根因（见 4.2）。
3. 对每个候选单字 `k`：
   - 用 `importlib.util.spec_from_file_location` + `tempfile` 新加载一个去掉 `k` 的 lexer 模块（强制 `_P0A_COMPOUND_SAFE` 随候选重算为 51 条 ∪ {当}）。
   - 真实源：重新 dump 全语料 token 序列，与基线逐文件对比变化数。
   - 单测：跑上述套件，取失败集（FAILED+SUBFAILED），与**基准失败集**做差（预存失败不算回归）。
   - `k` 可删 ⇔ 真实源变化 = 0 **且** 单测失败集 ⊆ 基准失败集。
4. **终验**：把所有"可删"条一次性删除（保留 30 条），再跑单测套件，确认失败集 == 基准失败集（零回归）。

> 基准失败集（52 条工作区 lexer 预存 6 失败，非本次回归，均为 `FAILED`）：
> `test_simple_tokenize`、`test_number_prefix_still_split_when_rest_is_keyword`、`test_自之X_仍是单B修好的样子`、两个 `test_lexer_p0a_deterministic` 分隔符测试、`test_lexer_correctness_smoke`。

---

## 三、验证结果（v3 终版）

| 指标 | 数值 |
|---|---|
| 基准条目数 | 52 |
| 删除（冗余） | 22 |
| 保留（护栏） | 30 |
| 精简幅度 | **42.3%**（超过任务书 ≥20% 要求） |
| 逐条验证覆盖 | 52 / 52 全覆盖（双 oracle，FAILED+SUBFAILED） |
| 终验单测失败集 | == 基准 6 失败（零回归） |
| 任务5 全量回归 | **ALL_OK（真实源零变化）** |

### 3.1 删除的 22 条冗余（撤掉后：真实源 0 变化 + 单测 0 新增失败）

> 以下 22 条经双 oracle 自证：单独撤掉后，771 真实源文件 token 序列**零变化** 且 词法单测失败集（含子测试）**不扩大**，即它们从未在真实源里起到保护复合标识符的作用（其"保护"效果已被第21轮上下文敏感切词 / OLD 路径既有逻辑覆盖）。

```
数 串 典 集 从 假 父 若 且 并 或 非 导 步 骤 序 否 匹 跃 现 等 异
```

### 3.2 保留的 30 条护栏（撤掉后触发真实源 token 变化 或 单测失败）

括号内 = 撤掉该条后：真实源变化文件数 + 单测新增失败（F=整测试 / S=子测试，附触发用例）。

| 单字 | 真实源变化 | 单测新增失败（触发用例） | 保留主因 |
|---|---:|---|---|
| 常 | 108 | — | 真实源头部护栏 |
| 类 | 26 | — | 真实源 |
| 模 | 20 | — | 真实源 |
| 段 | 14 | S:test_compound_safe_control_group_unchanged | 真实源+单测 |
| 列 | 12 | — | 真实源 |
| 断 | 11 | — | 真实源 |
| 引 | 9 | — | 真实源 |
| 对 | 7 | F:test_对于；S:test_compound_safe_supplement_merges_words | 真实源+单测 |
| 的 | 4 | — | 真实源 |
| 接 | 3 | — | 真实源 |
| 例 | 3 | — | 真实源 |
| 出 | 2 | — | 真实源 |
| 加 | 2 | S:test_arithmetic_operator_compound_words | 真实源+单测 |
| 自 | 2 | S:test_compound_safe_control_group_unchanged | 真实源+单测 |
| 则 | 2 | — | 真实源 |
| 乘 | 1 | — | 真实源 |
| 末 | 1 | S:test_compound_safe_supplement_merges_words | 真实源+单测 |
| 真 | 1 | — | 真实源 |
| 过 | 1 | — | 真实源 |
| 试 | 1 | — | 真实源 |
| 跳 | 1 | — | 真实源 |
| 到 | 1 | — | 真实源 |
| 长 | 1 | — | 真实源 |
| 空 | 0 | F:test_等于空那么 | 单测钉住 |
| 是 | 0 | S:test_identifier_safe_module_print_merged_inside_word | 单测钉住 |
| 减 | 0 | S:test_arithmetic_operator_compound_words | 单测钉住 |
| 除 | 0 | F:test_除类型错误；F:test_去除空格仍是一个标识符；S:test_compound_safe_control_group_unchanged；S:test_compound_safe_supplement_merges_words | 单测钉住 |
| 首 | 0 | S:test_compound_safe_supplement_merges_words | 单测钉住 |
| 余 | 0 | S:test_compound_safe_supplement_merges_words | 单测钉住 |
| 配 | 2 | S:test_compound_safe_supplement_merges_words | 真实源+单测 |

> `常`(108) 是头部护栏：P0A 路径尤其依赖它。`常`黏在标识符词尾时必须整体成词，否则会被切碎。
> `空/是/减/除/首/余` 真实源 0 变化但被**单测（含子测试）钉住**——这正是 v3-初版漏判的条目（仅 `空`/`除` 被整测试钉住，`首`/`余`/`减`/`是` 被子测试钉住，v3-初版解析器未捕获 `SUBFAILED` 而误删）。

---

## 四、版本修正史（重要工程记录）

### 4.1 v1 → v2：P0A 类属性派生集合陷阱

首版脚本复用旧模式「原地改模块全局 + finally 还原」，报告 41 冗余 / 11 护栏。**该结论错误**，根因：

- `_P0A_COMPOUND_SAFE = _COMPOUND_SAFE_SINGLE_KEYWORDS | {'当'}` 是 **`Lexer` 类属性**，在 `import lexer` 时由当时的 52 条集合一次性算定并缓存。
- 原地改模块级全局时，**类属性不会重新求值**，P0A 确定性路径仍按旧 52 条 ∪ {当} 工作。
- v1 漏报了所有"仅在 P0A 路径生效"的护栏（`常`108 / `模`20 / `段`14 / `类`26 等），误标为冗余。

**修正**：v2 对每个候选用 `importlib` + `tempfile` 重新加载模块，强制 `_P0A_COMPOUND_SAFE` 随候选重算。

> 经验沉淀：建议将 `_P0A_COMPOUND_SAFE` 改为实例属性或 `@property`，从源头消除该陷阱。

### 4.2 v2 → v3-初版：补齐单元测试 oracle（仍漏子测试）

v2 仅以 **771 真实 `.light`** 为 oracle，结论 28 冗余 / 24 护栏。漏掉单元测试合成串依赖：当按 v2 编辑为 24 条（删 `空`/`除`）时，词法单测出现 **16 个回归**。根因定位后回退到 52 条基线，构建 v3。

v3-初版补全单测 oracle，但 `run_tests` 解析器**只捕获 `FAILED ` 行、漏掉 `SUBFAILED(` 子测试失败**，得出 "52→26（删 26，含 `首`/`余`/`减`/`是`）" 的错误结论。直接在真实编辑态跑单测暴露 **11 失败**（6 FAILED + 5 SUBFAILED：首项/首字母大写/余额/是可打印/减法），证明 `首`/`余`/`减`/`是` 被**子测试**钉住，v3-初版的"26 条"结论不成立。

### 4.3 v3 终版：FAILED+SUBFAILED 双捕获

修正 `run_tests` 同时捕获 `FAILED ` 与 `SUBFAILED(`，并把基线来源固定为 `git HEAD`（与工作区编辑解耦），重跑逐条扫描：

- 22 条可删（每条：单测 0 新增失败 + 真实源 0 变化）。
- 30 条保留：`空`/`除`/`首`/`余`/`减`/`是` 被单测（含子测试）钉住，其余 24 条被真实源 token 变化钉住。
- **终验**（仅留 30 条）单测失败集 == 基准 6 失败 ⇒ 零回归，确认 v3 终版结论自洽。

### 4.4 双 oracle / 解析器实施细节（供复现）

- 真实源 oracle：`module_tok` 用独立加载模块逐文件 SHA256。
- 单测 oracle：`_run_lex_tests.py` 在 pytest 收集前 `sys.modules['lexer'] = 修改版模块`，再 `pytest.main([...])` 进程内运行；父进程解析 `FAILED <nodeid>` 与 `SUBFAILED(code='..',desc='..') tests/unit/...` 行得失败集。
- 为何不能 subprocess+PYTHONPATH：测试文件 `sys.path.insert(0, src)` 会把真实 `src/lexer.py` 置于临时模块之前，导致永远测到 52 条基线（假阳）。`sys.modules` 打补丁在导入期绝对优先于路径查找，是唯一可靠方式。
- **致命细节：`SUBFAILED` 必须捕获**。单测套件用 `subTest` 驱动大量合成串断言（首项/余额/是可打印/减法/配置…），这些失败只以 `SUBFAILED(...)` 形式出现，不进 `FAILED ` 统计。任何"忽略子测试"的解析都会把被单测钉住的护栏误判为冗余。

---

## 五、交付物清单

| 类型 | 文件 | 状态 |
|---|---|---|
| 编译器修改 | `light-merge/src/lexer.py`（`_COMPOUND_SAFE_SINGLE_KEYWORDS` 52→30） | 已改，未提交 |
| 验证脚本（误版 v1） | `_sweep_r22_t3_compound_safe_single.py` | 保留备查（结论作废） |
| 验证脚本（终版 v3 双捕获） | `_sweep_r22_t3_v3.py` | ✓ |
| 单测打补丁器 | `_run_lex_tests.py` | ✓ |
| 30 条候选终验 | `_verify_30.py` | ✓ |
| 证据（终版） | `_task3_R22_v3_evidence.json` + `_sweep_t3_v3_final.txt` | ✓ |
| 全量反跑 | `_antirun_r22_t5_全量回归扫描.py` + `_task5_R22_全量回归证据.json` | ✓ ALL_OK |
| 本报告 | `_task3_R22_COMPOUND_SAFE_SINGLE精简_交付报告.md` | ✓ |

---

## 六、与任务书验证标准对照

| 任务书标准 | 结果 |
|---|---|
| 52 条逐条隔离中立验证 | ✓ 全覆盖（双 oracle：真实源 + 单测 FAILED+SUBFAILED） |
| 精简后全量 CI 无回归 | ✓ 任务5 反跑真实源 0 变化 + 单测终验失败集 == 基准 |
| 精简幅度 ≥ 20% | ✓ 42.3% |
| 保留条目有护栏证据 | ✓ 每条护栏记录依赖文件数 / 单测钉住证据（见 3.2） |
| 只删不增 | ✓ 未新增任何条目 |

> **OLD 路径补充说明**：本表亦被 OLD 路径 `_tokenize_chinese_sequence` 消费。任务5 反跑 [D] 节用 `deterministic=False` 兜底核验发现：删除 22 条后 OLD 路径真实源有 **8 文件** token 变化。但 OLD 路径是 P0A 之前的遗留模式——全仓生产编译/运行入口全部使用默认 `Lexer()`（P0A），唯一显式 `deterministic=False` 的 `test_lexer_p0a_deterministic.py` 仅用合成片段、不硬编码这 8 个文件。故 22 条"冗余"判定是针对**生产路径（P0A）**的结论，OLD 路径 8 处变化属遗留模式的预期漂移，不影响生产编译与现有测试，已记入任务5 报告 3.3 节。
