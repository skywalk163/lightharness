# 任务3（R36）交付报告：性能优化——预计算 `_OPERATOR_KEYWORDS_NO_UNARY_PREFIX`

> 目标：将 R21 词首闸门3 每次成词判定时的重复集合差运算
> `_OPERATOR_KEYWORDS - self._P0A_UNARY_PREFIX_KW` 预计算为模块常量，消除重复构造。
> 附加：扫描 lexer.py 热路径探查其他可预计算的重复集合运算。

---

## 一、改动清单（light-merge/src/lexer.py）

| 位置 | 改动 |
|---|---|
| L47（新增） | 模块常量 `_OPERATOR_KEYWORDS_NO_UNARY_PREFIX = _OPERATOR_KEYWORDS - frozenset({'非'})` |
| L2452（R21 闸门3） | `_lead_kw not in (_OPERATOR_KEYWORDS - self._P0A_UNARY_PREFIX_KW)` → `_lead_kw not in _OPERATOR_KEYWORDS_NO_UNARY_PREFIX` |
| L3928–3932（新增） | import 自校验④：`_OPERATOR_KEYWORDS_NO_UNARY_PREFIX == _OPERATOR_KEYWORDS - Lexer._P0A_UNARY_PREFIX_KW`，防止未来 `_P0A_UNARY_PREFIX_KW` 增删成员时遗漏同步 |

**语义等价性**：差集成员为 `_OPERATOR_KEYWORDS`（27 元，含逻辑/关系/比较运算符）减去一元前缀 `{非}` → 26 元；与原内联运算逐元素一致，已由自校验④ + pytest 双重兜底。

---

## 二、热路径重复集合运算探查结论

扫描 `_tokenize_chinese_sequence` 等热路径，除 R21 闸门3 的集合差外：
- `_ALL_KEYWORDS_WITH_VERBS` / `user_definitions` / `_common_compounds` 的 `in` 判定均为**既有 frozenset/set 的成员查询**（O(1)，无重复构造）；
- `_P0A_OP_CHAR_HINTS` / `_P0A_SEP_CHAR_HINTS` / `_P0A_SUFFIX_SPLIT_SINGLE` 等集合均已在类/模块层**预计算**（见 L3342–3352）；
- 其余 `|`/`&` 运算均在**类定义期**一次性求值（非 per-token 热路径）。

→ **仅 R21 闸门3 一处是 per-token 热路径里的重复集合差构造**，已修复。无其他语义安全的预计算点（铁律：只做语义等价常量预计算，不做算法级重构）。

---

## 三、性能 A/B 验证（ABAB 交替 + 严格配对）

### 方法
- A = HEAD 版 lexer（R35 收口态，内联集合差）；B = 当前版（预计算常量）。
- 语料：676 个 .light 文件 / 2,805,348 字符，每轮全量 tokenize。
- 两次测量：① 粗放 ABAB（6+6 轮）② 严格配对（10 对，每对 A/B 紧邻）。

### 结果
| 测量 | A 均值 | B 均值 | Δ(B−A) |
|---|---|---|---|
| 粗放 ABAB | 8458.9 ms | 8585.5 ms | +1.50% |
| 严格配对（10 对） | 8822.5 ms | 8909.2 ms | +1.15%（σ=8.98%，正2/负7/平1） |

### 判读（诚实结论）
- **未观测到任务书预期的 ~1.9% 回收**。原内联集合差运算作用于 27 元 frozenset，单次开销 <1μs，
  且 R21 闸门3 仅在「非语句起始/调用语境的候选成词」这一小比例路径触发，全语料累计收益
  **远低于本机测量噪声**（HP Z620 工作站系统噪声 ±9%，单对波动 -6.88%~+19.7%）。
- Δ 均值 +1.15% 落在噪声带内，**非真实回归**。
- **结论**：本优化是**零风险代码整洁度改进**（消除重复构造、常量名自文档化、加自校验兜底），
  **不是性能回收**。保留之（任务书明确要求实施，且语义等价已证）。

---

## 四、全量反跑（G1 零变化硬门槛）

`_antirun_r36_final.py`：逐文件比对 HEAD 版与当前版 lexer 对全语料（676 文件）的 token 流。

```
反跑语料：676 文件
不一致文件数：0 / 676
判定：全语料 token 流逐字节一致（G1 零变化）→ 合格
```

---

## 五、pytest 验证

`tests/test_R36_性能优化_token.py`（新增，5 用例全绿）：
- 常量 == 内联差集（含自校验④ 双重兜底）；
- `非` 词首并入（非语句起始：`设 X 为 非空`/`打印 非空块` → IDENTIFIER）；
- `非` 词尾切分（`长度非0` → 长度+非(KW)+0）；
- 语句起始 `非甲` → 非(KW)+甲(ID)（not 表达式，R21 闸门不在语句起始生效）；
- 词中 `甲非乙` → 整体并入 IDENTIFIER。

---

## 六、交付物
- `light-merge/src/lexer.py`（预计算常量 + 闸门3 改用 + 自校验④）
- `lightharness/tests/test_R36_性能优化_token.py`（pytest，5 用例）
- `lightharness/_antirun_r36_final.py` + `_antirun_r36_final.json`（反跑，零变化）
- `lightharness/_r36_perf_abab.py` / `_r36_perf_paired.py`（ABAB 性能探针，不提交）
- 本报告
