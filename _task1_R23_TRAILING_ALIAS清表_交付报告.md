# 第23轮 任务1 交付报告 —— 阶段A：`己` 并入通用规则，删除 `_TRAILING_ALIAS_MERGE`

> 日期：2026-09-14 ｜ 轮次：第23轮 任务1（P0） ｜ 方向：保护表通用化替代
> 修改文件：`light-merge/src/lexer.py`（唯一）
> 反跑脚本：`lightharness/_antirun_r23_t1_TRAILING_ALIAS清表.py` → **ALL OK**
> 复现用例：`lightharness/examples/test_R23_己词尾并入.light` → rc=0
>
> ⚠️ **用例文件归属说明**：该路径在文件互斥表中同时属任务1 交付物与任务4 的
> `lightharness/examples/test_R23_*.light` 范围；执行期间**任务4 已用「任务1/任务4 共用版」覆盖**
> （覆盖后 rc=0，覆盖面更广：`自己` / `错误己` / `本己录`（词中）/ `记己`+`记己结果`（段名+词中））。
> 本报告 §三.4/§四 的 [F] 判据以**反跑脚本内的内存态断言**为准，不依赖该文件的具体写法定稿。

---

## 零、结论速览

| 项 | 结果 |
|---|---|
| `_TRAILING_ALIAS_MERGE` 定义 | **已删除**（原 1 条：`己`） |
| 两处引用分支 | **已改写**为通用类别 `self._TRAILING_ALIAS_CLASS` |
| 通用类别规模 | **21 字**（由关键字表推导，非逐词登记） |
| 真实源语料 token 变化 | **0 / 773 文件** |
| 生成产物树漂移 | 1 文件（纯并入，编译结果不变，见 §五） |
| `test_L120.light` | rc=0 |
| `test_R23_己词尾并入.light` | rc=0 |
| 反跑 A~H2 | 全 PASS，判定 **ALL OK** |

---

## 一、验收标准对照（任务书 §任务1「验证标准」）

| # | 验收标准 | 实测 | 证据 |
|---|---|---|---|
| 1 | `_TRAILING_ALIAS_MERGE` 整表删除（定义 + 引用代码全部移除） | ✅ 定义删除；2 处引用改为通用类别；全文件无该名字 | 反跑 [H1]；`grep` 无代码引用 |
| 2 | `test_L120.light` rc=0 | ✅ rc=0（stdout `测试错误 / test_L120 PASS`） | 反跑 [G] |
| 3 | 全语料 token 零变化 | ✅ 真实源 **0/773**；生成树 1 文件为纯并入改进 | 反跑 [B]/[B2] |
| 4 | 全量 CI 无回归 | ✅ lightharness 552 passed；词法专项单测基线 A/B 零新增失败；**全量 203 红经失败子集 A/B 判定零新增回归** | `_task5_R23_全量回归扫描报告.md` §5.1–5.5 |
| 5 | 反跑 ALL OK | ✅ 断裂态（`{'己'}`）vs 修复态（21 字）A~H2 全 PASS | 反跑输出 |

---

## 二、现状验证：`己` 的词尾并入场景是否已被通用规则覆盖

**结论：已覆盖**，无需新增上下文规则主分支改动（任务书 §「如果未覆盖」分支未触发）。

验证路径（三支探针，`lightharness/_r23_t1_probe*.py`）：

1. **枚举 L0 单字别名全集**：以 `_ALL_KEYWORDS_WITH_VERBS` 为基础，逐层扣除运算符
   （`_P0A_OP` / `_OPERATOR_KEYWORDS`）、范围与步长字（`_P0A_NEVER_SPLIT`）、await 动词
   （`_AWAIT_KEYWORDS`）、单字复合安全字（`_COMPOUND_SAFE_SINGLE_KEYWORDS`）、值字面量
   （`_VALUE_LITERAL_KEYWORDS`），得 **27 条候选**（含 `己`）。
2. **逐条加入验证**：对 27 条中的每一条，单独制造「词尾出现」样本，确认通用规则确实
   会把它并入标识符（而非依赖白名单）。27/27 命中。
3. **全语料零变化**：把「旧白名单 `{'己'}`」与「27 字通用类别」分别 tokenize 全语料，
   逐文件 sha256 一致；再对 27 字逐字收缩验证，全部零变化 ⇒ 旧白名单对全语料**无独占贡献**。

随后按语义收紧为 **21 字**（排除 6 个「语义不止于词首」的单字，理由见 §三.4）。

---

## 三、修改内容（`light-merge/src/lexer.py`）

### 3.1 删除

```python
# 删除前（第22轮精简后仅剩 1 条）
_TRAILING_ALIAS_MERGE = frozenset({
    '己',   # L-120（E批次）
})

# 删除后：整块替换为通用化替代的说明性注释（记录旧实现/新实现/判据/证据）
```

### 3.2 新增（通用类别，位于类体中 `_P0A_CN_SINGLE` 之后）

```python
_TRAILING_ALIAS_CLASS = frozenset(
    _k for _k in (_ALL_KEYWORDS_WITH_VERBS - _P0A_OP - _OPERATOR_KEYWORDS
                  - _P0A_NEVER_SPLIT - _AWAIT_KEYWORDS
                  - _COMPOUND_SAFE_SINGLE_KEYWORDS - _VALUE_LITERAL_KEYWORDS)
    if len(_k) == 1)
```

推导结果 **21 字**：

```
从 匹 否 宏 导 己 并 异 当 承 抛 捕 掷 父 现 终 若 设 跃 返 遍
```

配套新增两个具名集合（供推导使用，语义自解释）：

| 集合 | 内容 | 用途 |
|---|---|---|
| `_VALUE_LITERAL_KEYWORDS` | `真` `假` `空` | 值字面量：词尾（`返回真`）是合法无空格写法，不并入 |
| `_AWAIT_KEYWORDS` | `等` `等待` | await 动词（L-056），动词前缀语义，不并入 |

### 3.3 两处引用点改写

| 位置 | 改前 | 改后 |
|---|---|---|
| `_tokenize_chinese_sequence` 方法头（局部缓存） | （无） | `_trailing_alias = self._TRAILING_ALIAS_CLASS` |
| 探测循环（原 line ~2742） | `sub_kw in _TRAILING_ALIAS_MERGE` | `sub_kw in _trailing_alias` |
| 输出循环（原 line ~2893） | `sub_kw in _TRAILING_ALIAS_MERGE` | `sub_kw in _trailing_alias` |

> **未触碰**：`_at_statement_start`、上下文敏感切词主分支、`_EMBED_MAX_MATCH_KEYWORDS`、
> `_COMPOUND_SAFE_SINGLE_KEYWORDS`（任务书通用约束 2/10/11）。
> 已逐行核对：新旧实现**除「集合来源」外代码结构完全一致**（旧 2742/2893 ↔ 新 2691/2841）。

### 3.4 为什么是 21 字而不是 27 字 —— 类别排除与边界反证

初版推导得 27 字（含 `且 或 步 等 至 非`）。逐字边界探针
（`lightharness/_r23_t1_hazard.py`）实测以下**合法写法会被误并**：

| 输入 | 27 字版本的错误结果 | 正确结果 |
|---|---|---|
| `甲至10` | `IDENTIFIER(甲至)` + `10` | `甲` / `至` / `10`（步长范围） |
| `甲步2` | `IDENTIFIER(甲步)` + `2` | `甲` / `步` / `2` |
| `甲或"x"` | `IDENTIFIER(甲或)` + 字符串 | `甲` / `或` / 字符串（逻辑或） |
| `甲且/x/` | 同上（`且`） | `甲` / `且` / … |
| `甲非…` | 同上（`非`） | `甲` / `非` / … |
| `甲等(乙)` | `IDENTIFIER(甲等)` + 调用 | `甲` / `等` / 调用（await） |
| `平台信息等。` | `IDENTIFIER(平台信息等)` | `平台信息` / `等` / `。` |

这 6 类单字的语义**不止于词首**（中缀运算符 / 关系连接词 / 步长范围符 / await 动词），
不属于「语句别名」，故按**语义类别整体排除**（`_P0A_OP` / `_OPERATOR_KEYWORDS` /
`_P0A_NEVER_SPLIT` / `_AWAIT_KEYWORDS`），而不是把这 6 个字逐个补回白名单——后者正是本轮要
消除的「打地鼠」形态。

> 收紧后 `_TRAILING_ALIAS_CLASS` 仍**包含 `己`**（[E] 判据逐字核对），故 L-120 语义完全保留。

---

## 四、反跑结果（`_antirun_r23_t1_TRAILING_ALIAS清表.py`）

**隔离口径（本脚本核心）**：任务1/2/3 都改 `lexer.py`，工作区是**三改动合并态**。
若拿祖先提交（HEAD=e99bdb80，同时含旧 IDENTIFIER_SAFE 5 + TRAILING_ALIAS 1 + CCW 184）
当「断裂态」，对比会并入任务2/3 的改动，**无法隔离任务1**。故采用**内存态精确隔离**：

```
断裂态 = 载入【当前工作区】lexer.py，再把 Lexer._TRAILING_ALIAS_CLASS 覆写为 frozenset({'己'})
修复态 = 载入【当前工作区】lexer.py 原样（21 字）
两侧源码逐字节相同；唯一差异就是那个集合 ⇒ 这才是任务1 的净改动
```

| 判据 | 内容 | 结果 |
|---|---|---|
| [A] | 基线自检：两侧各两次 dump 一致 | **PASS** |
| [B] | 任务1 净改动：真实源 token 变化 0 / 773 文件（生成树漂移 1） | **PASS（零变化）** |
| [B2] | 生成树漂移性质：`是 + 否 + Windows → IDENTIFIER(是否Windows)`（同理 Linux/Mac）——纯并入 | **PASS** |
| [C] | 正向控制①：修复态剔除 `己` → `test_L120.light` token 变化 | **PASS** |
| [D] | 正向控制②：断裂态清空白名单 → `test_L120.light` token 变化 | **PASS** |
| [E] | 通用类别自证：现算 21 字 == 现存 21 字 == 期望 21 字 | **PASS** |
| [F] | 覆盖 + 反向：`自己/爱己/知己/错误己` → 单颗 IDENTIFIER；`己姓名` → KEYWORD(己)+IDENTIFIER；`甲加乙` → 甲/加/乙 | **PASS** |
| [G] | L-120 关联：`test_L120.light` rc=0、`test_R23_己词尾并入.light` rc=0 | **PASS** |
| [H1] | 模块已无 `_TRAILING_ALIAS_MERGE` 名字 | **PASS** |
| [H2] | 旁证：祖先提交 e99bdb80 vs 修复态，全语料变化 6 / 826 文件（全在生成树，见 §五） | 信息项 |
| 还原校验 | `src/lexer.py` sha256 前后一致（本脚本不写该文件） | **OK** |

**判定：ALL OK**

---

## 五、生成产物树漂移说明（唯一 1 文件）

漂移文件：`light-merge/bootstrap/release/stdlib/系统接口.light`
（`bootstrap/release/` 由 `light-merge/bootstrap/build_bootstrap_release.py` 生成，
属**构建输出**，不在任何测试断言路径；口径与第22轮 / 本轮任务5 一致。）

| 项 | 断裂态（`{'己'}`） | 修复态（21 字） |
|---|---|---|
| `是否Windows` | `是` + `KEYWORD(否)` + `Windows`（**切碎**） | `IDENTIFIER(是否Windows)` ✅ |
| `是否Linux` / `是否Mac` | 同上切碎 | 同上并入 ✅ |
| 出现位置 | 模块头部**文档文本**（第 55~57 行 API 说明） | 同 |
| 编译结果 | rc=1（库片段无 `主`，两侧**完全一致**） | rc=1（同） |

⇒ 该漂移是通用规则**覆盖到 `否` 后的正确性改进**（`否` 也是单字语句别名，
词尾应并入），**不是回归**；且对编译结果零影响。
（`_antirun_r23_t1_...` [B2] 用二分归并比对自动判定为「纯并入」。）

[H2] 中祖先提交对比的 6 个文件同属 `bootstrap/release/stdlib/`（外部命令/字符串工具/
字符串常量/文件匹配/系统接口/编码解码），性质相同——由三轮改动合并所致，非任务1 独占。

---

## 六、验证标准自查

| 项 | 状态 |
|---|---|
| 反跑 ALL OK | ✅ |
| 真实源 token 零变化 | ✅ 0/773 |
| `test_L120.light` rc=0 | ✅ |
| 新复现用例 rc=0 | ✅ |
| codegen 无关（本任务不涉内建登记） | — |
| 未改 `_at_statement_start` / 上下文主分支 | ✅ |
| `_EMBED_MAX_MATCH_KEYWORDS` / `_COMPOUND_SAFE_SINGLE_KEYWORDS` 未动 | ✅ |
| 反跑 finally 恢复 + sha256 校验 | ✅（本脚本全程只读 lexer.py） |

---

## 七、遗留与后续

1. **生成树 `bootstrap/release/stdlib/*.light` 的 token 漂移会在每次通用化后累积**。
   它们不参加测试断言，但建议后续轮次在 `build_bootstrap_release.py` 产出后做一次
   全量重生成，使产物与当前词法口径对齐（本轮不动，避免越界）。
2. **`_r23_t1_probe*.out/py`、`_r23_t1_hazard.py`** 为过程探针，保留在 `lightharness/` 供复核。
3. 阶段B（IDENTIFIER_SAFE，任务2）与阶段C（CCW，任务3）与本任务共享同一 `lexer.py`，
   三方合并后的全量口径由任务5 复核。
