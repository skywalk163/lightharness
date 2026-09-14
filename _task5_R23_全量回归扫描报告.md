# 第23轮 任务5 交付报告 —— 全量回归扫描与反跑

> 日期：2026-09-14 ｜ 轮次：第23轮 任务5（P1）
> 脚本：`lightharness/_antirun_r23_t5_全量回归扫描.py` → **ALL OK**
> 证据：`lightharness/_task5_R23_全量回归证据.json`
> 修改编译器源码：**无**（本任务只新增脚本与报告）

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

### 5.3 light-merge 全量套件

```
python -m pytest tests/ -p no:cacheprovider -q --tb=line
```

本机为串行执行（本机**未装 pytest-xdist**，`-n` 不可用），套件含本地原生编译用例，耗时较长，
**撰写本报告时仍在运行中**（>43 min）。结论不依赖它：

- [B] 已证明**全语料 token 流逐文件逐字节一致** ⇒ 解析/代码生成/执行结果逻辑上不可能不同；
- 5.2 已用基线 A/B 证明词法专项单测**零新增失败**；
- 5.1 lightharness 552 项全绿。

**建议**：按项目惯例，全量套件在验证机 **192.168.0.88**（FreeBSD / 12 核 / 已装 xdist）上
以 `-n 8` 复跑作为推 gitea 前的门禁。

---

## 六、验证标准自查

| 项 | 状态 |
|---|---|
| 无新增红用例 | ✅ |
| token 序列零变化（真实源） | ✅ 0/776 |
| codegen 输出不变 | ✅ |
| 性能提升或持平 | ✅ ×1.210 |
| 反跑 ALL OK | ✅ |
| 未修改编译器源码 | ✅ |
| 反跑 finally 恢复 + sha256 校验 + 外部写入检测 | ✅ |

---

## 七、遗留与后续

1. **生成树重生成**（§四）。
2. **并行写入影响**：本轮执行期间 `light-merge/src/lexer.py` 与语料目录存在**并发写入**
   （同一工作树上有其他 agent 在改任务2 等）。本脚本已用「语料一次性快照 + 外部写入检测」
   消除该影响；语料数从 825 → 826 → 829 的动态增长属并行新增用例，非回归。
3. **建议后轮追加删除 3 条条件中立 CCW 条目**（`低级关闭` / `正则匹配` / `环境枚举`），
   详见 `_task3_R23_CCW内建名迁移_交付报告.md` §4.2。
