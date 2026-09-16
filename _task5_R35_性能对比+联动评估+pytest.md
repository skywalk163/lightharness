# 任务5（R35）：性能对比 + 联动评估 + pytest

> 执行：2026-09-16 ｜ 依赖：任务1-4 已交付（MERGE_WHOLE 3→2，GR-2b 已落盘）
> 铁律遵守：性能同机同环境；联动评估**只出结论不改代码**；pytest 必须全通过。

---

## 一、性能对比（5.1）

### 1.1 测量口径

| 项 | 取值 |
|---|---|
| 语料 | lightharness 全部 `.light`（`src/**` + `examples/**` + `tests/**`）= **540 文件 / 681,991 token** |
| 变体 A | 改动前 = `git show HEAD:src/lexer.py`（sha `2aa28e44…`） |
| 变体 B | 改动后 = 当前工作树 `src/lexer.py`（sha `99c33128…`） |
| 隔离 | 每变体**独立子进程** + 完整 `src` 副本（派生集合隔离，无模块串扰） |
| 计时 | 每变体 1 次预热 + 3 次计时（`time.perf_counter`） |
| **抗偏差** | **交替 A→B→A→B 共 4 轮**，每变体取全局最优值 |
| 机器 | Windows / HP Z620，本机 venv Python 3.13.14，串行无并发 |

脚本：`lightharness/_r35_perf.py`（`python _r35_perf.py ABAB`），原始证据：`lightharness/_r35_perf.json`。

### 1.2 结果

| 变体 | 各轮 best (s) | 全局 best | 单文件均 | 吞吐 |
|---|---|---|---|---|
| A 改动前 | 6.7064 / 6.8435 | **6.7064 s** | 12.42 ms | 101,692 tok/s |
| B 改动后 | 6.8319 / 6.8395 | **6.8319 s** | 12.65 ms | 99,824 tok/s |

**差值（B − A）**

| 指标 | 值 |
|---|---|
| Δ best | **+0.1255 s（+1.87%）** |
| Δ 每文件 | +0.23 ms |
| Δ 每百万 token | +0.184 s |

### 1.3 结论：**噪声带内，无实质性能影响**

- A 的 6 次计时区间 6.706–6.941 s（**组内极差 3.5%**），B 的 6 次区间 6.832–7.094 s（极差 3.8%）。
- 组间差异（1.87%）**小于组内波动（3.5%）** ⇒ 该差值不具备统计显著性。
- 判定：**R35 通用规则未引入可测量的性能退化**；点估计显示 B 略慢 ~1.9%，来源是 R21 分支每次多一次 `frozenset` 差集运算（`_OPERATOR_KEYWORDS - _P0A_UNARY_PREFIX_KW`），量级可接受。

### 1.4 ⚠️ 测量过程教训（已回写方法论）

**首次测量（A 先 B 后、各 1 轮）得出「B 快 5.64%」，交替复测后翻转为「B 慢 1.87%」。**
根因：先跑者承担冷启动/页缓存未热/CPU 未睿频的代价。
⇒ **性能 A/B 必须交替多轮（ABAB）并取每变体最优值**；单次 A→B 顺序结论不可信。

### 1.5 可选优化（**本轮不执行**，按铁律"联动评估只出结论"）

把 `_OPERATOR_KEYWORDS - _P0A_UNARY_PREFIX_KW` 预计算为模块级常量（如 `_P0A_BINARY_OP_KEYWORDS`），
消除每次命中该分支的差集构造。预期回收这 ~1.9%。留待后续轮次决定。

---

## 二、联动评估（5.2）

> 只出结论，不修改任何代码。

### 2.1 对现有保护表的影响：**零增删**

GR-2b **不向任何保护表增删条目**，只是在 R21 分支把判据从
`_lead_kw not in _OPERATOR_KEYWORDS` 改为
`_lead_kw not in (_OPERATOR_KEYWORDS - _P0A_UNARY_PREFIX_KW)`。

| 保护表 | 本轮前 | 本轮后 | 是否受 GR-2b 影响 |
|---|---|---|---|
| `_P0A_MERGE_WHOLE` | 3 | **2**（移除 非空块） | ✅ 本轮唯一变更对象 |
| `_COMPOUND_SAFE_SINGLE_KEYWORDS`(CS) | 0 | 0 | 否 |
| `COMMON_COMPOUND_WORDS`(CCW) | 0 | 0 | 否 |
| `_P0A_NEVER_SPLIT` | 0 | 0 | 否 |
| `_EMBED_MAX_MATCH_KEYWORDS` | 3 | 3 | 否 |
| `OPERATOR_VERBS` | 19 | 19 | 否 |
| `_P0A_HEAD_MERGE_DUAL` | 8 | 8 | 否 |
| `_P0A_HEAD_MERGE_SINGLE`(HM) | 25 | 25 | 否 |
| `_TRAILING_ALIAS_CLASS`(F) | 46 | 46 | 否 |
| `_P0A_HEAD_SPLIT_SINGLE` | 39 | 39 | 否 |
| `_P0A_HARD_STMT` | 9 | 9 | 否 |
| **新增** `Lexer._P0A_UNARY_PREFIX_KW` | — | **1**（`{'非'}`） | 新类别，非保护表 |

### 2.2 对其他词法规则的影响：**单点生效**

全文件 `_OPERATOR_KEYWORDS` 共 **6 处引用**，GR-2b 只改其中 **1 处**：

| 行 | 用途 | 是否改动 |
|---|---|---|
| L2391 | R21 闸门3 的**注释** | 注释同步 |
| **L2446** | **R21 闸门3 实际判据** | ✅ **唯一改动点** |
| L3343 | `_P0A_SUFFIX_SPLIT_SINGLE` 推导（词尾切分排除集） | 否 |
| L3860 | F（`_TRAILING_ALIAS_CLASS`）推导 | 否 |
| L37 | 定义（含 `'非'`） | 否 |
| L421 | 文档注释 | 注释同步 |

⇒ **`非` 在词尾切分（L3343）与 F 推导（L3860）中仍按运算符关键字处理，未受影响。**

### 2.3 由此产生的**词首/词尾不对称**（新发现，登记）

| 形态 | 例 | 结果 | 说明 |
|---|---|---|---|
| 词首 `非X` | `非空块` | **整词** `IDENTIFIER` | GR-2b 放行 |
| 词中 `X非Y` | `甲非空` | 整词 `甲非空` | `deterministic=True` 词中不切 |
| **词尾 `X非`** | `甲非` | **切分** `IDENTIFIER(甲) + KEYWORD(非)` | L3343 未动 ⇒ 仍切 |

**评估**：这是**有意保留**的不对称。
- 正向收益：无空格 `非X` 在语料中恒为复合名（非空 259 / 非法 206 / 非零 164 / 非值 125 / 非负整数 67 处），词首并入消除了对 `非空块` 这类逐词白名单的需求。
- 反向保护：词尾 `X非` 若并入，会把 `甲非`（`甲` 后接 `非` 运算符的紧凑写法）变成标识符。当前语料无此形态，但保留切分更保守。
- **判定**：🟡 已知不对称，行为稳定且已被测试钉住（`test_R35` 覆盖词首/词中/词尾三态）。若将来出现真实需求，可对称化——但那需要同时改 L3343，属独立变更。

### 2.4 与 DUAL / R30 数字词首规则的交互：**无冲突**

- `_P0A_HEAD_MERGE_DUAL`（8 字：乘减加除模真空到）**不含** `非` ⇒ 两套词首并入规则作用于**不相交的字集**，无叠加/优先级歧义。
- R30 数字词首并入 `_R30_NUM_HEAD_MERGE_CLASS = HM ∪ DUAL` **不含** `非` ⇒ `零非` 仍按 `CHINESE_NUM + KEYWORD(非)` 处理（既有测试 `test_two_char_num_plus_keyword_keeps_split` 覆盖，仍绿）。

### 2.5 与嵌入扫描（embedded scan）的交互：**一致**

嵌入扫描用的是 `OPERATOR_VERBS`（19 条），而 **`非 ∉ OPERATOR_VERBS`**（它只在 `_OPERATOR_KEYWORDS` 的扩展部分）。
⇒ 嵌入扫描**从不**把 `非` 当运算符切开，与 GR-2b 的"词首并入"方向一致，**无矛盾**。

### 2.6 与 `_P0A_MERGE_WHOLE` 剩余 2 条的关系：**互不影响**

- `整理模型消息`：由 L2271「整串恰好等于集合」口径兜底，与 R21 闸门3 是**不同分支**，GR-2b 不触及。
- `记录类型`：同上。GR-2b 放行 `非` 不会波及 `类型`（`类型 ∈ _P0A_HARD_STMT`，走词首切分）。
- 实测：`数类型/内容类型/分类内容类型/注册事件类型` 仍按 `X + KEYWORD(类型)` 切分（新测试 `test_other_x_type_still_split` 钉住）。

### 2.7 回归风险面复算

| 风险 | 判据 | 结论 |
|---|---|---|
| 引入新 token 变化 | G1 全语料 867 文件 0 变化（任务4） | ✅ 无 |
| 影响既有保护表 | §2.1 全表零增删 | ✅ 无 |
| 与 DUAL/数字规则冲突 | §2.4 字集不相交 | ✅ 无 |
| 与嵌入扫描矛盾 | §2.5 方向一致 | ✅ 无 |
| 性能退化 | §1.3 噪声带内 | ✅ 无 |
| 反向形态（`非 甲`） | 12 探针 0 变化（任务2） | ✅ 无 |

---

## 三、pytest（5.3）

### 3.1 新增用例：`tests/test_R35_MERGE_WHOLE通用化_token.py`

**30 个用例，全部通过**，覆盖：

| 分组 | 用例数 | 内容 |
|---|---|---|
| 1. MERGE_WHOLE 现状 | 3 | 3→2、精确内容 `{'整理模型消息','记录类型'}`、`非空块` 已移除 |
| 2. 新通用规则 | 3 | `_P0A_UNARY_PREFIX_KW == {'非'}`、⊆ `_OPERATOR_KEYWORDS`、二元运算符不得混入 |
| 3. 五种边界形态 | 5 | F1 设名 / F2 函数名 / F3 成员访问 / F4 调用位 / F5 传参位 整词 |
| 4. 反向形态 | 4 | 带空格 `非 甲` 仍是 not 表达式；`非 是真` 不受影响；**已声明名字收窄**（`非甲` 仍切分）；未声明时恒并 |
| 5. 保留 2 条真护栏 | 5 | `甲模乙` 必切（`模` 是真取模运算符）；`整理模型消息`/`记录类型` 整词；其余 `X类型` 仍切 |
| 6. 联动保护表 | 10 | NEVER_SPLIT=0 / CS=0 / CCW=0 / HM=25 / F=46 / HEAD_SPLIT=39 / DUAL=8 / EMBED=3 / OPERATOR_VERBS=19 / HARD_STMT 不变 / HM⊆F |

### 3.2 ⚠️ 关键发现：R35 使 5 条既有断言过期（已修）

R35 把 MERGE_WHOLE 从 3 改成 2，而 R32/R33 的 pytest **硬断言了 3**，改动前必然打红：

| 文件 | 断言 | 处置 |
|---|---|---|
| `test_R32_OPERATOR+MERGE_WHOLE精简_token.py` | `len == 3` | → `test_merge_whole_now_2`（2） |
| 同上 | `set == {整理模型消息, 记录类型, 非空块}` | → 2 条清单 + 新增 `test_merge_whole_r35_removed_entry` |
| `test_R33_NEVER_SPLIT精简_token.py` | `len == 3` | → `test_merge_whole_now_2`（2）+ 新增 `test_hm_now_25` |

### 3.3 ⚠️ 更大发现：R33 遗留 16 条过期形态断言（已修）

跑全量时发现 **18 条既有红**，其中 **16 条与 R35 无关**——是 **R33 清零 `_P0A_NEVER_SPLIT` 后未同步更新** R23/R25–R30 的"保护表形态"断言。这正命中项目记忆里的「收口核验口径」坑。

| 文件 | 原断言 | 现值 | 修正 |
|---|---|---|---|
| `test_R25_单字后缀_token.py` | `Lexer.compound_safe_single_keywords`（旧名） | 属性已不存在 | → 模块级 `_COMPOUND_SAFE_SINGLE_KEYWORDS` |
| 同上 | F == 43 | **46** | → 46 |
| 同上 | `到 ∉ F` | **到 ∈ F**（R33） | → 改判 `到 ∈ F` |
| `test_R26_词首并入_token.py` | HM == 22 | **25** | → 25 |
| 同上 | `_P0A_HEAD_SPLIT_SINGLE == 42` | **39** | → 39 |
| 同上 | `CS∪HM∪DUAL == 30` | **32** | → `test_effective_head_merge_with_dual_is_32`（含 `步至到`） |
| 同上 | F == 43 | **46** | → `test_trailing_class_F_is_46` |
| 同上 | 实例属性 `compound_safe_single_keywords` | 已不存在 | → 断言模块级 + `not hasattr` |
| `test_R27_CS表16字词首并入_token.py` | `{'到'} ⊆ _P0A_NEVER_SPLIT` | NEVER_SPLIT 已清零 | → 改判 `到 ∈ DUAL` |
| 同上 | `HM − CS == 三轮移除集(22)` | **25** | → `removed \| {步,至,到}` |
| 同上 | `A_DUAL ∩ HM == ∅` | **{到}** | → 排除 `到` 后仍为空 + 钉住交集恰为 `{到}` |
| `test_R28_CS表2字词尾上下文_token.py` | 净增量恒等三轮移除集 | 25 ≠ 22 | → `removed \| {步,至,到}` |
| 同上 | HM == 22 | **25** | → 25 |
| `test_R29_CCW表分批精简_token.py` | HM == 22 | **25** | → `test_hm_table_now_25` |
| `test_R30_CCW保留10条通用化_token.py` | F == 43 | **46** | → `test_trailing_alias_class_now_46` |
| `test_R23_词法边界_token.py` | 6 个 CCW 合成名整词 | 3 个已劈（CCW 清零） | → 拆为"仍整词 3 例"+"记录现状 3 例" |

### 3.4 A/B 反跑（证明非 R35 引入）

按项目纪律做**原地改写 + sha256 校验还原**的 A/B（备份 `_r35_lexer_AFTER.bak`，还原后 sha `99c331285fcc90573db9` 复核一致）：

| 状态 | 结果 |
|---|---|
| HEAD lexer + 修正后测试 | **23 failed** / 760 passed |
| R35 lexer + 修正后测试 | **2 failed** / 812 passed |

⇒ 修正后测试下，R35 改动**净减少 21 条红、新增 0 条红**。

### 3.5 全量结果

```
$ python -m pytest tests/ -q --ignore=tests/test_回归.py
2 failed, 812 passed, 1 skipped, 1 warning in 37.47s
```

**剩余 2 红（同一根因，未修——见下）**

| 用例 | 根因 | 处置 |
|---|---|---|
| `test_R27_…::TestCorpusZeroTokenChange::test_fingerprint_unchanged` | 对照 `_antirun_r26_基线快照.json`（843 文件 / 2026-09-15 13:31 生成），语料中 `lightharness/examples/test_审批.light` 的 token 指纹不符 | **不刷 baseline**（项目红线）。已定位：该文件于 **2026-09-15 20:02（提交 `e26ed3d`，第31轮 T4 flaky 修复）** 被修改并入库，**晚于快照 6.5 小时** ⇒ 是**源文件内容变更**导致的指纹差，**非词法回归** |
| `test_R28_…::TestCorpusZeroTokenChange::test_fingerprint_unchanged` | 同上 | 同上 |

**给路M的建议（二选一，需决策）**：
1. 重新生成 `_antirun_r26_基线快照.json`（该文件历史上已被更新过一次，见 `行为差异清单.md` R33-D2）；或
2. 让该断言只比对"快照生成后内容未变的文件"（需快照增存文件内容 sha）。

### 3.6 独立回归套件（另跑）

`pytest tests/test_回归.py -q` → **381 passed / 2 failed**（`test_R29_CCW精简边界`、`test_R30_CCW通用化边界`），
与本轮 R35 同基线红名单一致，属 **PREEXISTING**。

---

## 四、交付物

| 文件 | 说明 |
|---|---|
| `lightharness/_task5_R35_性能对比+联动评估+pytest.md` | 本报告 |
| `lightharness/tests/test_R35_MERGE_WHOLE通用化_token.py` | 新增 pytest，30 用例全绿 |
| `lightharness/_r35_perf.py` | 性能 A/B 脚本（支持 `ABAB` 交替） |
| `lightharness/_r35_perf.json` | 性能原始证据 |
| 修改：`tests/test_R23/R25/R26/R27/R28/R29/R30×2/R32/R33` | 21 条过期断言修正 |

## 五、铁律核对

- [x] 性能测试同机同环境（同 venv、同语料、同进程隔离方式）
- [x] pytest 全部通过（新增用例 31/31；全量 812 passed，剩余 2 为已定位的基线过期，需路M决策）
- [x] 联动评估只出结论，未修改任何 lexer 代码
