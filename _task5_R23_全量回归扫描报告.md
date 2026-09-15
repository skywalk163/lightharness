# 第23轮 任务5 交付报告 —— 全量回归扫描与反跑

> 日期：2026-09-14 ｜ 轮次：第23轮 任务5（P1）
> 脚本：`lightharness/_antirun_r23_t5_全量回归扫描.py` → **ALL OK**
> 　　　`lightharness/_r23_subset_ab.py`（全量失败子集 A/B）→ **ALL OK**
> 证据：`lightharness/_task5_R23_全量回归证据.json`
> 　　　`lightharness/_task5_R23_失败子集AB_证据.json`
> 修改编译器源码：**无**（本任务只新增脚本与报告）
>
> **交付提交**：`light-merge` 分支 `main` 上的 **`ca5741a8`**
> 「第23轮保护表通用化替代: 阶段A _TRAILING_ALIAS_MERGE清表(1→0…); 阶段B …; 阶段C CCW 184→37…」
> —— 该提交含 `src/lexer.py` + `tests/unit/test_lexer_p0a_deterministic.py`（230+/240−），
> 提交后 `git diff HEAD -- src/lexer.py` **为空**，即本报告验证的工作树状态 **≡ 已提交状态**
> （`sha256` 前缀 `342bc6c4…` 两侧一致），A/B 基准 `e99bdb80` 即该提交的父提交。

---

## 零、结论速览

| 项 | 结果 |
|---|---|
| 语料规模 | **829** 个 `.light`（真实源 776 + 生成产物树 53） |
| 断裂态基准 | 自动上溯到 **e99bdb80**（首个不含 R23 标记 `_TRAILING_ALIAS_CLASS` 的祖先提交） |
| 真实源 token 变化 | **0 / 776 文件** |
| 生成产物树漂移 | **6 文件**（全部 `light-merge/bootstrap/release/stdlib/`，非测试断言路径） |
| 编译结果由绿变红 | **0** |
| 性能 | 基准中位 11.66s → 修复态中位 **9.63s**，**×1.210（更快 21%）** |
| 核心用例（9 个） | 两侧 rc / stdout **逐字节一致**，全部 rc=0 |
| codegen 产物（2 探针） | 两侧 sha256 **完全一致** |
| light-merge 全量套件（本机 Windows 串行） | 8322 collected / **203 红**；失败子集基线 A/B → **新增回归 0**（§5.3） |
| 判定 | **ALL OK** |

---

## 一、验收标准对照（任务书 §任务5「验证标准」）

| # | 验收标准 | 实测 | 判据 |
|---|---|---|---|
| 1 | 全量 examples 无新增红用例（绿→红 = 0） | ✅ 0 | [E] 9 核心用例两侧一致；[B] 蕴含全量 |
| 2 | token 序列零变化 | ✅ 真实源 0/776 | [B] |
| 3 | codegen 输出不变（任务3 迁移内建名） | ✅ 2 探针 sha256 一致 | [F] |
| 4 | 性能提升或持平 | ✅ **×1.210**（提升 21%） | [C] |
| 5 | 反跑 ALL OK | ✅ A~F 全 PASS | — |

---

## 二、扫描口径

### 2.1 基准自动上溯（不用裸 HEAD）

```
断裂态 = 最近一个「不含 R23 通用规则标记」的祖先提交的 src/lexer.py
         （标记：`_TRAILING_ALIAS_CLASS`；R23 若已提交，HEAD 会自带该标记，
           此时判据 A 恒假 ⇒ 自动退到 HEAD^ / HEAD^^ … 直到命中）
修复态 = 当前工作区 src/lexer.py
```

本轮命中基准 **e99bdb80**（第22轮保护表深度精简），两侧状态：

| 项 | 断裂态（e99bdb80） | 修复态（工作区） |
|---|---|---|
| `_TRAILING_ALIAS_MERGE` | 1 条 `['己']` | 已删除 |
| `_TRAILING_ALIAS_CLASS` | — | **21 字** |
| `COMMON_COMPOUND_WORDS` | 184 条 | **37 条** |

### 2.2 真实源 vs 生成产物树

| 类别 | 文件数 | 是否门控 |
|---|---|---|
| 真实源（lightharness/examples+src+tests、light-merge/examples+stdlib+src+tests） | 776 | **门控** |
| 生成产物树（`light-merge/bootstrap/**`，由 `build_bootstrap_release.py` 生成） | 53 | 只记录（不在任何测试断言路径） |

口径与第22轮一致。

---

## 三、判据结果

### [A] 基线自检 —— PASS

同一模块两次 dump 一致（确定性）。**语料内容在脚本启动时一次性快照**，
使 [A] 只检验词法器确定性，免受多 agent 并行写入干扰。

### [B] 真实源 token 零变化 —— PASS（零回归）

```
真实源 token 变化 0 文件（生成产物树漂移 6）
```

**token 流逐文件逐字节一致** ⇒ 解析树 / 代码生成 / 执行结果在逻辑上不可能不同，
故「全量 examples 无新增红用例」由 [B] **蕴含**；[E]/[F] 再对代表用例做具体实测交叉印证。

### [C] 性能 —— PASS（提升 21%）

| 项 | 基准（184 条 CCW + 1 条白名单） | 修复态（37 条 + 21 字通用类别） |
|---|---|---|
| 中位耗时（全语料一轮） | 11.66 s | **9.63 s** |
| 三次采样 | 15.64 / 11.66 / 8.24 | 13.44 / 9.63 / 6.77 |
| 倍率 | — | **×1.210** |

保护表从 184+1 条降到 37 条（+1 个推导式类别），**集合 membership 的热路径开销显著下降**；
上下文判定未引入回退（任务书阈值：>10% 判回归）。

### [D] OLD 路径（`deterministic=False`，遗留模式）—— 只留痕，不门控

真实源变化 **0**；生成树 6（与 [B] 同源）。遗留模式非生产路径。

### [E] 核心用例（9 个）编译运行 rc / stdout 两侧逐字节一致 —— PASS

| 用例 | rc | 输出 |
|---|---|---|
| `test_L084.light` | 0 | `test` |
| `test_L092.light` | 0 | `1` |
| `test_L119.light` | 0 | `1` / `test_L119 PASS` |
| `test_L120.light` | 0 | `测试错误` / `test_L120 PASS` |
| `test_L137.light` | 0 | `1` |
| `test_R21_L152家族嵌套形参.light` | 0 | `test_R21_L152家族嵌套形参 PASS` |
| `test_R21_L152嵌套段落形参.light` | 0 | `test_R21_L152嵌套段落形参 PASS` |
| `probe_己词尾并入.light`（compile） | 0 | gen sha `9d53dc53…`, len 13454 |
| `probe_内建名迁移.light`（compile） | 0 | gen sha `17df02f1…`, len 13543 |

> 实现要点：`compile` 成功时 stdout 含**输出文件路径**（两侧临时文件名不同），
> 故该字段不进比对；仅比对 `rc` + 生成物 `gen_sha`/`gen_len`，失败时才记录输出尾部。

### [F] codegen 产物对比 —— PASS

| 探针 | 覆盖点 | 断裂态 sha256 | 修复态 sha256 |
|---|---|---|---|
| `probe_己词尾并入.light` | 任务1：`自己/爱己/知己/错误己` 词尾并入 | `9d53dc53…` | `9d53dc53…` ✅ |
| `probe_内建名迁移.light` | 任务3：`平方根/四舍五入/随机整数/十六进制/追加` 内建名 | `17df02f1…` | `17df02f1…` ✅ |

（任务3 验证标准③「codegen 输出不变」的直接证据。）

### 还原校验 —— OK

`src/lexer.py` sha256 = `342bc6c4…`，两侧原地替换后**已完整还原**。
脚本在替换前加了**外部写入检测**：若 sha 与起始快照不符则放弃替换，
避免多 agent 并行时覆盖他人改动。

---

## 四、生成产物树漂移（6 文件）

```
light-merge/bootstrap/release/stdlib/外部命令.light
light-merge/bootstrap/release/stdlib/字符串工具.light
light-merge/bootstrap/release/stdlib/字符串常量.light
light-merge/bootstrap/release/stdlib/文件匹配.light
light-merge/bootstrap/release/stdlib/系统接口.light
light-merge/bootstrap/release/stdlib/编码解码.light
```

- 全部位于 `bootstrap/release/`（`build_bootstrap_release.py` 的**构建输出**）；
- 漂移集中在**模块头部文档文本**中的多字/单字语句别名（如 `是否Windows` 由
  `是`+`否`+`Windows` 并为单颗 IDENTIFIER，属正确性改进）；
- 对编译结果**零影响**（同一文件两侧编译 rc 一致）；
- 不参加任何测试断言。

**建议**：后续在 `build_bootstrap_release.py` 产出后做一次全量重生成，使产物与当前
词法口径对齐（本轮不动，避免越界）。

---

## 五、全量 CI（本机）

### 5.1 lightharness 测试套件

```
python -m pytest tests/ -p no:cacheprovider -q --tb=line
→ 552 passed in 1073.15s (0:17:53)
```

**552 passed / 0 failed**（含 `test_R23_词法边界_token.py`、`test_R23_词法边界_反向.py`、
`test_回归.py` 等 552 项）。

### 5.2 light-merge 词法专项单测（含基线对照）

同一批用例分别对「工作区」与「基线 `e99bdb80`」执行：

```
python -m pytest tests/unit -p no:cacheprovider -q --tb=line -k "lexer or 词法"
```

| 侧 | 结果 |
|---|---|
| 工作区（R23 合并态） | **6 failed, 60 passed, 4081 deselected, 140 subtests passed** |
| 基线 `e99bdb80`（`sys.modules` 注入，不改文件） | **6 failed, 60 passed, 4081 deselected, 140 subtests passed** |

失败集合**逐一相同**（`test_number_prefix_still_split_when_rest_is_keyword`、
`test_simple_tokenize`、`test_自之X_仍是单B修好的样子`、`test_成员与关系分隔符`、
`test_语句关键字词首切分`、`test_lexer_correctness_smoke`）
⇒ **0 新增失败**，6 项为**已知基线失败**（与第22轮记录一致），非本轮引入。

> 注入法说明（第22轮沉淀）：基线对比只能靠 `sys.modules['lexer']` 打补丁——在
> `pytest_configure` 中先装载基线模块，早于测试收集；subprocess + `PYTHONPATH`
> 会被测试文件内 `sys.path.insert(0, src)` 阴影，永远测到基线（假阳）。
> 插件：`C:\Users\skywalk\AppData\Local\Temp\r23_inject\_inject_baseline_lexer.py`。

### 5.3 light-merge 全量套件（本机 Windows · 串行）

```
python -X utf8 -m pytest tests/ -p no:cacheprovider -q --tb=no -rf --junitxml=<xml>
→ collected=8322  failures=194  errors=9  skipped=116     （串行，约 60 min）
```

本机**未装 pytest-xdist**，无法 `-n`，故耗时远高于门禁机。失败 203 条（194 failed + 9 errors）
分布：`tests/e2e` 44、根目录 `tests/test_*` 23、`test_context_manager` 17、`test_stdlib_phase9` 16、
`test_process_tree_light` 14、`test_agent_tools_light` 11、`tests/unit` 9 …

**⚠️ 本机全量的红不是判绿 oracle**（原因见 §5.4）。判绿改用 **失败子集 A/B**：

| 侧 | 重跑失败子集（203 条 nodeid，全部可重建） |
|---|---|
| C1 工作区 lexer | 190 failed + 9 errors = **199 红** |
| B1 基线 lexer `e99bdb80`（`sys.modules` 注入，不改文件） | 190 failed + 9 errors = **199 红** |

**候选新增回归 = 0 ⇒ ALL OK。**

> **判据的逻辑完备性**：回归的定义是「**改动前能过、改动后变红**」的用例——这类用例
> **必然落在当前失败集 F_cur（203 条）之内**。把 F_cur 全部拿去基线 lexer 下重跑：
> 无一例出现「工作区红、基线绿」，即 F_cur ⊆ 基线失败集 ⇒ **零新增回归**。

**4 条抖动**（原全量红、子集两侧皆绿，两侧表现完全一致）：
`tests.unit.test_原生腿_R11B_中文工具::{test_中文分词_O0对拍, test_手机号校验_O0对拍, test_拼音转换_O0对拍, test_身份证校验_O0对拍}`
—— 均为 O0 原生腿对拍（`SystemExit: 1`），单独跑即过、全量跑时因原生编译资源/临时目录竞争而红，
与词法改动无关、两侧无差异。

### 5.4 CI 的真实判绿口径（重要 —— 本机不能照抄）

`gitea CI`（`.gitea/workflows/ci.yml`）最后一步**不是**「全量全绿」，而是：

```
python tools/ci/check_regression.py \
  --junit .ci/non-e2e.xml --junit .ci/e2e.xml --junit .ci/light_soft.xml \
  --baseline tests/ci_baseline_failures.txt \
  --soft-classname 'tests.test_*' --soft-classname 'tests._test_*'
```

语义：**只拦「基线之外的新增打红」**；基线里已有、这次没红只提示（修好应刷新基线）。
该仓库有 v7 收尾期存量欠账（`docs/v7_失败用例根因聚类工单.md`），故不要求全绿。

**但基线是平台相关的**：当前 `tests/ci_baseline_failures.txt` 只有 **12 条、全部是
`tests.e2e.test_e2e_chain`**，由 **FreeBSD runner** 生成（快照 `collected=1203`）。
把本机 Windows 的 junit 拿它比：

```
[CI] 基线 12 条；新增打红 84 条；相比基线已转绿 8 条      → 退出码 1（假红）
```

84 条「新增」与 8 条「转绿」全部来自平台差异（原生编译 / HTTP / 沙箱 / 进程树等
Windows 行为不同），**不是回归**。

> 故本机自查**必须**用 §5.3 的**基线 lexer A/B**；**推 gitea 前仍以门禁机
> 192.168.0.88（FreeBSD / `-n 8`，约 9 min）跑官方闸门为准**。

### 5.5 词法相关失败的性质（说明项，非回归）

失败集中 10 条与词法相关，A/B 已证明它们在基线 lexer 下**同样打红**：

| 用例 | 失败信息 | 性质 |
|---|---|---|
| `tests.test_lexer::test_basic_keywords` | `Token(IDENTIFIER,'设甲为三')` 期望 `KEYWORD` | **P0-A 确定性切词的旧断言**（`deterministic=True` 自 R21 起已默认），根目录 `tests.test_*` 在 CI 属 `--soft-classname` **软豁免** |
| `tests.test_lexer::test_multiple_keywords` | `assert '映射' in ['遍历']` | 同上 |
| `tests.test_lexer::test_complex_expression` | `assert '设' in []` | 同上 |
| `tests.unit.test_lexer*` 6 条 | 见 §5.2 | 第22轮已记录的**已知基线失败** |
| `tests.unit.test_原生腿_R11B_中文工具::test_中文分词_O0对拍` | `SystemExit: 1` | 原生腿编译环境（见 §5.3 抖动） |

**结论**：R23 未使任何用例由绿转红。

---

## 六、验证标准自查

| 项 | 状态 | 证据 |
|---|---|---|
| 无新增红用例 | ✅ | 全量 203 红 → 基线 lexer A/B **0 新增**（§5.3） |
| token 序列零变化（真实源） | ✅ 0/776 | [B] |
| codegen 输出不变 | ✅ | [F] |
| 性能提升或持平 | ✅ ×1.210 | [C] |
| 反跑 ALL OK | ✅ | `_antirun_r23_t5_全量回归扫描.py` |
| 未修改编译器源码 | ✅ | 本任务只新增脚本与报告 |
| 反跑 finally 恢复 + sha256 校验 + 外部写入检测 | ✅ | — |
| lightharness 全套件 | ✅ 552 passed | §5.1 |
| light-merge 词法专项单测（基线 A/B） | ✅ 0 新增失败 | §5.2 |
| light-merge 全量（本机） | ✅ 203 红全为既存（A/B 证明） | §5.3 / `_task5_R23_失败子集AB_证据.json` |

---

## 七、遗留与后续

1. **生成树重生成**（§四）。
2. **并行写入影响**：本轮执行期间 `light-merge/src/lexer.py` 与语料目录存在**并发写入**
   （同一工作树上有其他 agent 在改任务2 等）。本脚本已用「语料一次性快照 + 外部写入检测」
   消除该影响；语料数从 825 → 826 → 829 的动态增长属并行新增用例，非回归。
3. **建议后轮追加删除 3 条条件中立 CCW 条目**（`低级关闭` / `正则匹配` / `环境枚举`），
   详见 `_task3_R23_CCW内建名迁移_交付报告.md` §4.2。
4. **全量判绿的平台差异（§5.4）**：本机 Windows 全量与 FreeBSD 基线不可直接比较。
   推 gitea 前请在 **192.168.0.88** 跑官方闸门 `tools/ci/check_regression.py`（`-n 8`，约 9 min）。
5. **`tests.test_lexer::{test_basic_keywords, test_multiple_keywords, test_complex_expression}`
   三条旧断言**（§5.5）：仍是 P0-A 之前的词法口径，属 `tests.test_*` 软豁免。建议后轮
   按确定性切词口径改写，或明确标注为「历史口径存档」。
6. **本机全量复跑工具已沉淀**：`_r23_subset_ab.py`（XML 采集 → 失败子集 → 基线 lexer A/B），
   后续任何「改词法后要证零回归」的场景可直接复用（`--xml <全量 junit>`）。
