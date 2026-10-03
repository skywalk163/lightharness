# Day3 清晨 T3 · LP-D-018 收口报告（SRC 后端「返回 关键字词变量名」）

> 派单表：`Day3清晨_派单表.md` v1.1｜行：**B（编译器）· T3**｜需门：**是（与 T4 合一条门线）**
> 出口 tag：`subtask-T3-done`｜被测树：light-merge 工作区（基于 `e53073d3c`，未提交）

---

## 一、结论（先看这里）

1. **LP-D-018 已修复并复验绿**：`返回 跳过`（`跳过` 为已声明关键字词变量）在 SRC 后端
   现与 ANTLR 后端一致输出 `[7]`。
2. **修复分两步**：并行会话先落了首版补丁（+11 行）；T3 核查 A/B 实证首版
   **把跨行 continue 语句误降级**（`TypeError: 'int' object is not callable`），
   随即收窄为「**同行**回溯」终版（+18 行）。
3. **门**：`082全量 all --mode full`（2026-10-03 09:32:46，remote 0.82）
   = **8355 passed + 2 xpassed / 0 failed / 121 skipped**，对锚点 `234800`（8357/0/121）
   **三元持平 → 门 PASS**。
4. **新增防回归用例**：`lightharness/tests/unit/test_Day3_T3T4_LP018_LP019回归.py`，9 passed。

---

## 二、根因（三层）

以 `probes/lp018_返回关键字词变量.light` 为例：`段落 乙(值): 设 跳过 为 [] / 跳过.追加(值) / 返回 跳过`。

| 层 | 事实 | 证据 |
|---|---|---|
| 词法 | `跳过` ∈ `KEYWORDS_LOOP`，token 流里是 `KEYWORD('跳过')` | `light.py tokens`：L9 = `KEYWORD '返回'` + `KEYWORD '跳过'` |
| 词法（缺口位） | `src/lexer.py:_lpd013_010_reclassify_declared_keywords`（LP-D-013 机制）只把「后随 `.`/`[`/`(`」的已声明关键字词降级为 IDENTIFIER；`返回 跳过` 后随 NEWLINE，**无后缀 → 不降级** | `lexer.py:1356-1373`（改前） |
| 解析 | `parser_stmt.py:_parse_return_stmt` 的语句关键字闸门（集合含 `'跳过'`）把它当语句关键字 → **`value = None`** | `parser_stmt.py:3403-3407` |
| 产物 | SRC 生成裸 `return`（函数内），调用方拿到 `None`；ANTLR 走 `returnStmt: K_RETURN expr?` 且 `identifier_like` 含 `K_CONTINUE` → 正常返回 `[7]` | 编译产物 `return`（无值） |

> 同一函数内 `打印(转字符串(跳过))` 一直正常 —— 缺口精准落在「`返回` 语句位」，
> 与 LP-D-013（成员访问基名位）同族不同位，故单独立账。

---

## 三、修复（`light-merge/src/lexer.py`，最终 +18 行）

在 LP-D-013 重分类的 `declared` 分支里补一条：已声明的 `出`/`跳过`，
**前随「`返回`/`返` 且同一行」时降级为 IDENTIFIER**。

```diff
                 if _j < n and tokens[_j].type in _ident_follow:
                     _tok.type = TokenType.IDENTIFIER
+                    continue
+                # LP-D-018：返回 已声明关键字词变量名（`返回 跳过`）——
+                # ⚠️ 只认**同一行**：向前回溯不许跨 NEWLINE。
+                _k = _idx - 1
+                while _k >= 0 and tokens[_k].type in (TokenType.INDENT, TokenType.DEDENT):
+                    _k -= 1
+                if _k >= 0 and tokens[_k].type == TokenType.KEYWORD \
+                        and tokens[_k].value in ('返回', '返'):
+                    _tok.type = TokenType.IDENTIFIER
                 continue
```

**为什么必须「同行」**：`返回 X` 的取值位必然与 `返回` 在同一行（token 相邻）。
首版补丁用 `_skip`（含 NEWLINE）回溯，向前跨过 NEWLINE/DEDENT 就落进了**另一条语句**：

- `返回\n…\n跳过`（跨 DEDENT 出块）→ `跳过` 是外层的 continue 语句；
- `返回\n跳过`（相邻行同缩进）→ 同上。

误降级后产物由 `continue` 变成 `跳过()`（对同名 int 变量求值调用）→
`TypeError: 'int' object is not callable`，且循环不再短路——**正是派单表点名的「静默错值」类**。

---

## 四、A/B 实证（HEAD = `e53073d3c` 原版 lexer；SRC 后端真实编译+执行）

| 探针 | HEAD（改前） | 首版补丁 | **T3 终版** | ANTLR（基准） |
|---|---|---|---|---|
| `lp018_返回关键字词变量`（主症） | rc=0 `[7]` / `空` ❌ | rc=0 `[7]` / `[7]` ✅ | **rc=0 `[7]` / `[7]` ✅** | rc=0 `[7]` / `[7]` ✅ |
| `lp018_对照_普通名` | `[7]` / `[7]` ✅ | ✅ | ✅ | ✅ |
| `lp018_反例_返回后跟跳过`（同缩进） | `3` ✅ | `3` ✅ | **`3` ✅** | `3` ✅ |
| `lp018_反例_返回后隔DEDENT跳过`（跨块） | `3` ✅ | **rc=1 TypeError ❌** | **`3` ✅** | `3` ✅ |
| `lp018_边界矩阵`（5 形态：返回出 / 带句号 / 真 continue / 空行后 continue / 成员后缀） | — | — | **`[7]`,`[7]`,`3`,`9`,`[7, 0]` 全对** | 末段因行 19 新发现差异 rc=1（见矩阵 #19，与本修复无关） |

> 反例 1（同缩进）在首版补丁下侥幸不炸（`跳过` 成了无副作用表达式、后无落穿语句），
> 属「静默改写控制流」；反例 2（跨块）必炸。两个都收进防回归用例。

---

## 五、验证与门

| 项 | 结果 |
|---|---|
| 探针两后端一致（主症） | ✅ `[7]`/`[7]` |
| 防回归用例 | `test_Day3_T3T4_LP018_LP019回归.py` **9 passed**（17.7s，含两反例、主症、判型族） |
| 082 门 | `all --mode full`，2026-10-03 09:32:46，remote 0.82，elapsed 431s |
| 门三元（对锚点 `234800` = 8357/0/121） | failed **+0** / skipped **+0** / passed **8357 = 8357 持平** → **PASS** |
| SRC diff | `src/lexer.py` 单文件 +18 行（首版 11 行的收窄版），无其他 src 改动 |

> 口径说明：pytest 实跑汇总行为 `8355 passed, 2 xpassed`；基线 JSON 把 XPASS 计入 passed
> ⇒ `passed=8357`。08:53 那份并行基线显示 `passed 8359 / xfailed 9`，差额同样是
> `test_验证IP地址`/`test_验证JSON` 两个 `xfail(strict=False)` 用例 XPASS 的归类口径问题，
> **与 T3/T4 改动无因果**（原生腿 stdlib 行为），已如实记录。

---

## 六、改动清单（T3 名下）

| 文件 | 改动 |
|---|---|
| `light-merge/src/lexer.py` | LP-D-018 降级分支 +18 行（并行首版 +11 → 核查收窄为同行版） |
| `lightharness/docs/国庆7天/probes/lp018_反例_返回后跟跳过.light` | 新增（同缩进反例） |
| `lightharness/docs/国庆7天/probes/lp018_反例_返回后隔DEDENT跳过.light` | 新增（跨块反例，**本回归的最小复现**） |
| `lightharness/docs/国庆7天/probes/lp018_边界矩阵.light` | 新增（5 形态边界） |
| `lightharness/docs/国庆7天/probes/lp018_位点变体矩阵.light` | 新增（7 位点取值矩阵，行 20 差异来源） |
| `lightharness/tests/unit/test_Day3_T3T4_LP018_LP019回归.py` | 新增（9 用例） |
| `lightharness/docs/功能对标/语言缺陷账.md` | LP-D-018 行状态 → 已修复 + 回归修正记 |
| `lightharness/docs/功能对标/ANTLR_SRC_对拍矩阵.md` | 行 1 补证据/回归修正小节；追加行 19、20 新发现 |

## 七、遗留

1. 探针 `lp018_位点变体矩阵.light` 在 ANTLR 下 rc=1 —— 非 T3 缺口，是矩阵行 20（`列.获取` 未注册）
   与行 19（`自我` 组合）两个**新发现**，已入矩阵活账，待后续批次立账修复。
2. 未提交、未打 tag（`subtask-T3-done` 由会话收口统一处置）；未 push（等用户示意）。
