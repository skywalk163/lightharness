# 任务4（R35）：3 条合并验证 + 全量反跑 + G3 边界门终验

> 日期：2026-09-16 ｜ 前置：任务1-3 交付后，基于合并后的 `light-merge/src/lexer.py` 执行
> 结论：**全量反跑零回归，G3 边界门全通过，1 条通用化成功、2 条保留**

---

## 一、合并结果总览

| 条目 | 通用规则 | G1 | G3 | 处置 | `_P0A_MERGE_WHOLE` |
|---|---|---|---|---|---|
| 整理模型消息 | GR-1 / GR-1c 均失败 | 撤单条 0 变化 | **F5 FAIL** | **保留** | ✅ 在 |
| 非空块 | **GR-2b 成功** | **0 变化** | **全通过** | **移除** | ❌ 已删 |
| 记录类型 | GR-3 / GR-3c 均失败 | 撤单条 **打红 2 文件** | **F2/F5 FAIL** | **保留** | ✅ 在 |

**`_P0A_MERGE_WHOLE`：3 条 → 2 条**（`整理模型消息`、`记录类型`）。

### 规则冲突检查

- GR-2b 只作用于 **R21 上下文敏感分支** 的闸门3（词首关键字类别判定），
  引入新类别 `_P0A_UNARY_PREFIX_KW`；
- 任务1（GR-1/GR-1c）与任务3（GR-3/GR-3c）**均未落盘**（验证失败即放弃），
  主树不存在它们的补丁；
- ⇒ **合并态实际只有 GR-2b 一条新规则**，无组合冲突；
- GR-2b 与既有规则的正交性已验证：不影响 `_P0A_OP` / `_P0A_SEP` /
  `_P0A_HARD_STMT` / `_P0A_SUFFIX_SPLIT_KW` / `_TRAILING_ALIAS_CLASS` / `HM` / `DUAL`
  （反向形态 12 条零变化 + 全语料零变化）。

---

## 二、全量反跑（G1 硬门槛）

### 2.1 口径

- 语料：8 组 glob（lightharness 三目录 + light-merge 五目录），**869 文件**
  （含本轮新增 3 个边界用例），可比 **867**（2 个「基线即失败」文件排除）。
- 比对：逐文件 tokenize → `[(type.name, value)]`（去 EOF/NEWLINE）→ `sha256`。
- 方法：临时副本 + 子进程（不碰主树；`LIGHT_MERGE` 环境变量法实测静默失效，未采用）。

### 2.2 结果（`_antirun_r35_final.py` A 段）

```
=== A. G1 语料门：当前 vs HEAD ===
  可比文件=867 变化=0 新错=0 ✅ 零回归
```

「当前」= 已改 lexer（`_P0A_MERGE_WHOLE` 2 条 + GR-2b）；
「HEAD」= 改动前（3 条，无 GR-2b），经 `git show HEAD:src/lexer.py` 取原文。

### 2.3 各变体 G1 明细（`_r35_g1_engine.py`）

| 变体 | 说明 | 变化文件数 |
|---|---|---|
| `mw_empty` | 三条全撤，无通用规则 | 2 |
| `mw_no1` | 撤 整理模型消息 | **0** |
| `mw_no2` | 撤 非空块 | **0** |
| `mw_no3` | 撤 记录类型 | **2** |
| `gr1_only` | 运算符分支收窄到 `_P0A_OP` | **6** |
| `gr1c_only` | 同上 + 两侧均 ≥2 字 | **1** |
| `gr2_only` | 一元前缀例外（未收窄） | **0**（但反向形态 2 变） |
| `gr3_only` | 词尾硬语句关键字并入 | **4** |
| `gr3c_only` | 同上，仅调用语境 | **0**（但 G3-F5 FAIL） |
| `gr2b_only` | **GR-2b** | **0** |
| **`gr2b_mw_no2`** | **最终态** | **0** ✅ |

---

## 三、G3 边界门终验

### 3.1 形态定义

```
F1 设名      设 X 为 1
F2 函数名     返回 X(1)
F3 成员访问   设 r 为 结果.X
F4 段落名     段落 X:
F5 传参位     断言相等(X, 1, "t")
```

### 3.2 终验结果（`_antirun_r35_final.py` B 段，当前 vs HEAD）

```
整理模型消息   G3通过
非空块      G3通过
记录类型     G3通过
```

### 3.3 逐条撤除态的 G3（未加通用规则时）

```
整理模型消息   G3失败 ['F5 传参位']         → 整理 + 模 + 型消息
非空块      G3失败 ['F2 函数名','F5 传参位'] → 非 + 空块        （GR-2b 后转通过）
记录类型     G3失败 ['F2 函数名','F5 传参位'] → 记录 + 类型
```

---

## 四、变异反跑（证明规则是活的，非假绿）

`_antirun_r35_final.py` C 段：把 GR-2b 的一元前缀例外撤掉
（闸门3 恢复为 `_OPERATOR_KEYWORDS` 全禁），而 `非空块` 仍不在 `_P0A_MERGE_WHOLE`：

```
非空块 变异后 G3 失败形态：['F2 函数名', 'F5 传参位']
  [F2] HEAD  : KEYWORD·返回 IDENTIFIER·非空块 LPAREN·(
       变异态: KEYWORD·返回 KEYWORD·非 IDENTIFIER·空块 LPAREN·(
  [F5] HEAD  : ( IDENTIFIER·非空块 ,
       变异态: ( KEYWORD·非 IDENTIFIER·空块 ,
判定：✅ 规则敏感（变异必红）
```

⇒ `非空块` 的整词语义确由 GR-2b 承载。

---

## 五、反向形态（不误伤关键字正常语义）

`_r35_probe_反向形态.py` 12 条探针，当前 vs HEAD **变化数 = 0**：
`非 甲`（带空格）、`如果 非 甲:`、`非甲`（甲已声明）、`非甲乙`、
`甲模乙`（取模守卫）、`甲 模 乙`、`类型 甲 = 记录`、`返回 类型`、
`模型`、`非空`、`段落 记录类型:`、`结果.期望类型`。

---

## 六、G2 编译门（合并态，改动后）

| 用例 | rc |
|---|---|
| `examples/test_R35_整理模型消息边界.light` | 0 |
| `examples/test_R35_非空块边界.light` | 0 |
| `examples/test_R35_记录类型边界.light` | 0 |
| `examples/test_R32_MERGE_WHOLE精简边界.light`（回归） | 0 |
| `examples/test_L030.light`（非空块 8 处真实用法，回归） | 0 |

三个新用例在**改动前**亦各跑一次 rc=0（G2 两态各跑一次）。

### 全量 pytest 回归

```
pytest tests/test_回归.py -q   →  381 passed, 2 failed (795s)
  FAILED test_R29_CCW精简边界.light
  FAILED test_R30_CCW通用化边界.light
```

**2 红为既有红（PREEXISTING）**：`git status` 显示两个文件均为 **tracked 且未改动**，
单独复跑 rc=1，与 R34 基线（377 passed / 2 failed）红名单一致，**非本轮引入**。
本轮净增 4 条通过（含 3 个新 R35 边界用例）。

---

## 七、风险与遗留

1. **`_P0A_MERGE_WHOLE` 未能清零**：剩余 2 条均有实证反例（`甲模乙` 取模守卫；
   `期望类型`/`参数类型` 结构不可分），属真护栏。
2. **GR-3c 是「可用但未采」的规则**：G1=0 且能修好 `记录类型` 的 2 个 G1 打红文件，
   但 G3-F5 不过，按铁律未采。若后续接受 `X类型` 在传参位并入（会改动 3 个 stdlib 文件），
   可连同 GR-3 一并重新立项。
3. 本轮改动**未提交 git**（用户红线：手工推）。

---

## 八、交付物

- `lightharness/_antirun_r35_final.py` —— 标准化反跑脚本（G1 + G3 + 变异三段）
- `lightharness/_antirun_r35_final.json` —— 终验结果
- `lightharness/_r35_g1_engine.py` / `_r35_variants.py` —— 全语料引擎 + 变体定义
- `lightharness/_r35_g3_边界门.py` —— G3 五形态门
- `lightharness/_r35_probe_反向形态.py` —— 反向形态 12 探针
- `lightharness/_r35_probe_根因.py` / `_r35_probe_上下文矩阵.py` /
  `_r35_probe_记录类型diff.py` / `_r35_probe_变体diff.py` —— 根因与差异定位
- 缓存：`_r35_g1_cache/*.json`（各变体全语料 token sha）
