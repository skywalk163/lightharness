# Day2 · 异常处理后端收口（LP-D-011 改靶）· 交付报告（三段式）

> 日期：2026-10-02（Day2 实际执行日；计划书原定 10/3）｜仓库：light-merge（worktree `light-merge-day2`，分支 `day2-lp011`，基线 `589d495d4`）｜
> 反跑判据：LP-D-011「ANTLR 后端 `尝试/捕获/最终` 解析失败（多余的 '结束'）」→ 4 探针两后端全绿 + 门三元数字零回归
> 门结果：**本地探针 PASS**；**0.82 权威门未跑**——但已修好其前置隐患（见 §5.1），Day2 代码已合并回主树 `light-merge` 并推送至 gitea/gitcode。

> **2026-10-02 后续更新**（本报告最初落盘时点）：
> - Day2 改动已本地提交到分支 `day2-lp011`（`76addcc17`）→ fast-forward 合并回主树 `light-merge`（HEAD `589d495d4`→`76addcc17`）。
> - `同步0.82.py` 硬编码主树的隐患已修（新增 `--light-merge` 参数 + `print_probe_identity()`），提交 `2cffa53`（lightharness 仓）。
> - **推送**：light-merge → gitea（192.168.1.5）+ gitcode 已同步（`76addcc17`）；lightharness → myrepo + gitcode 已同步（`beeeebd`）。**github 未推**——lightharness 在 github 存在双推历史分叉（本地 `1065a9b` 与 github `0826b23` 为同一提交不同 hash；github 端另有 6 个本地没有的提交含 R106/R107/R108 设置工作线），经用户确认不推 github、保持主仓+gitcode 已同步。

---

## 〇、开工前置：探针结论（计划书 §五 明令）

探针在**默认 SRC 后端**本已通过（`CATCH_OK: boom`），按计划书「探针不红即销账或改靶」应**改靶**为 ANTLR 后端：

| 后端 | 改前 | 改后 |
|---|---|---|
| SRC（默认） | `尝试/捕获/最终` 全部可用，多捕获单变量形态可用 | **无变化**（本已可用） |
| ANTLR（`--backend antlr`） | `解析失败：第9行, 第0列: 多余的 '结束'` | 4 探针全绿 |

⇒ **改靶成立**：Day2 收口的是 ANTLR 后端，不是 SRC 后端。

## 一、根因

- 现象：`--backend antlr` 跑 `尝试/捕获/最终` 报 `第N行, 第0列: 多余的 '结束'`；SRC 后端同代码正常。
- 定位路径（渐进截断 bisect + 只导入不动用探针）：先用最小 `尝试: 打印("TRY_OK") 结束` 复现 → 再逐层加 `捕获/最终` → 用 `light tokens` 看预处理后的 token 流，确认 `结束` 数量多于源码的 `结束` 数。
- 根因（两层叠加）：
  1. **ANTLR 语法规则过严**（`antlrparser/LightLangParser.g4` 旧版 `tryStmt`）：要求 `K_TRY COLON block K_END PERIOD? K_CATCH ID COLON block K_END PERIOD?`——**两个 `结束`**（try 一个、catch 一个），与实际中文写法「一个 `结束` 收尾」不符。
  2. **两层缩进预处理按缩进回退误插 `结束`**：
     - `antlrparser/light_visitor.py::_auto_close_blocks`：只识别 `若/否则/尝试` 等为「开块关键字」，`捕获/最终` 冒号行被当作普通行压栈，缩进回退时为其补插 `结束`，把 `尝试` 的 `结束` 拆散。
     - `antlrparser/indent_preprocessor.py::preprocess_v3_syntax`：同样的「按缩进回退补 `结束`」逻辑，未识别 `捕获/最终` 为**延续子句**（不新开块、不独立收尾）。

  ⇒ 语法要求 2 个 `结束` + 预处理误插 2 个 `结束`，二者叠加成「多余的 '结束'」。

## 二、做了什么

改动全部落在 worktree `light-merge-day2/`（主树 `light-merge` 未被触碰，见 §五）。共 7 个源文件 + 6 个 ANTLR 生成物：

| 文件 | 变更 | 说明 |
|---|---|---|
| `antlrparser/LightLangParser.g4` | `tryStmt` 重写（约 -18/+12） | 改为 `K_TRY COLON block (K_CATCH catchSpec COLON block)* (K_FINALLY COLON block)? K_END PERIOD?`——**单个 `结束` + 多捕获 + 可选 `最终`**；新增 `catchSpec`（1 或 2 个 `identifier_or_type`）与 `identifier_or_type` 子规则 |
| `antlrparser/light_ast.py` | `TryStatement` 加字段 | 新增 `catch_clauses: List[tuple]`、`finally_body: List[ASTNode]`、`catch_type: str`；保留旧字段 `catch_var/catch_body` 兼容 |
| `antlrparser/visitor_stmt.py` | `visitTryStmt` 重写 + 新 helper | `_text_of_iot`/`_spec_text`/`_spec_is_type`；单 iot=变量捕获、双 iot=类型+变量捕获 |
| `antlrparser/interpreter_core.py` | `_exec_try` 重写 | 优先用 `catch_clauses`，遍历多捕获；类型不匹配 `continue`；`finally` 无条件执行 |
| `antlrparser/light_visitor.py` | `_auto_close_blocks` | 新增 `_CONTINUE_KEYWORDS = ('捕获','捕','最终','终')`；命中冒号行则不入栈、不 `close_before`（用 `_is_cont` 标志 + 外层 `continue`，避免重复 append） |
| `antlrparser/indent_preprocessor.py` | 新增 `_is_continue_clause` | 在缩进回退处理**前**拦截延续子句与显式 `结束` 行，静默弹出更深层挂起缩进而不插 `结束` |
| `antlrparser/light_parser/*` | 重新生成（6 个文件） | 用 `antlr-4.13.2-complete.jar` 重新生成，含 `CatchSpecContext`/`Identifier_or_typeContext` |
| `lightharness/docs/功能对标/语言缺陷账.md` | LP-D-011 状态更新 | 「已定性待修」→「已改靶 + ANTLR 收口（Day2）」，并同步 §1747 过时结论（LP-D-011 已收口，生态层剩余缺口仅 LP-D-012 等） |

工具链（临时，运行后由 runtime 回收，不污染环境）：JDK 11.0.2 走华为云镜像、`antlr-4.13.2-complete.jar` 走 Maven 官方仓，均落 `${BOX_AGENT_SCRATCH_DIR}/day2-toolchain/`。

## 三、现在能跑什么

探针目录：`lightharness/docs/国庆7天/probes/`

```bash
PY=light-merge/.venv/Scripts/python.exe; D2=light-merge-day2
for p in lp011_probe lp011_probe2 lp011_finally lp011_multi_catch; do
  f="lightharness/docs/国庆7天/probes/$p.light"
  echo "===== $p (ANTLR) ====="; $PY $D2/cli/light.py run "$f" --backend antlr; echo "rc=$?"
  echo "----- $p (SRC) -----";  $PY $D2/cli/light.py run "$f"; echo "rc=$?"
done
```

输出（关键行，全部 rc=0）：

| 探针 | 覆盖 | ANTLR | SRC |
|---|---|---|---|
| `lp011_probe` | 正例（`尝试` 无异常） | `TRY_OK` rc=0 | `TRY_OK` rc=0 |
| `lp011_probe2` | 单捕获 + 异常绑定 + 控制流 | `CATCH_OK: boom` / `AFTER` rc=0 | `CATCH_OK: boom` / `AFTER` rc=0 |
| `lp011_finally` | `最终` 块 | `TRY_OK` / `FINALLY_OK` / `AFTER` rc=0 | `TRY_OK` / `FINALLY_OK` / `AFTER` rc=0 |
| `lp011_multi_catch` | 多捕获 + `最终`（两后端通用形态） | `CATCH1: boom` / `FINALLY` / `AFTER` rc=0 | `CATCH1: boom` / `FINALLY` / `AFTER` rc=0 |

**多捕获形态选择**：曾试 `捕获 串 错:`（类型 + 变量），ANTLR 修复后通过，但 SRC 后端报 `name '串' is not defined`（SRC 侧 `_parse_catch_clause` 不支持类型前缀，其测试用例全用单变量 `捕获 e:`）。为避免两后端语义分叉，探针定为**两后端通用的多捕获单变量形态**（`捕获 错:` / `捕获 其他:`）。

### 门三元数字（基线 → 本轮）

| 量 | 基线（主树 `589d495d4`） | 本轮（`light-merge-day2`） | 判定 |
|---|---|---|---|
| failed | 61 | 61 | **新增 0** |
| passed | 21 | 21 | 不下降 |
| errors | 16 | 16 | 不新增 |

`antlrparser/test/` 全量：`$PY -m pytest antlrparser/test/ -q --no-header -p no:cacheprovider --tb=no`。

**零回归证据**：基线 FAILED 集合与 day2 FAILED 集合按 `diff` 逐条比对——**完全一致，无新增、无消失**。61 条失败是**基线本就存在**的（`antlrparser/test` 与真实测试入口 `tests/` 不同步，如 `RangeExpr` 未定义等），**非 Day2 引入**。零回归的判据应是「相对基线的差集」，而非「绝对 failed=0」。

## 四、反跑判据验证

1. **破坏点 = g4 `tryStmt` 仍要求两个 `结束`** → 探针 `lp011_probe`/`lp011_finally` 应报「多余的 '结束'」：改后**不报**，rc=0。✔
2. **破坏点 = 两层预处理按缩进回退为 `捕获/最终` 补插 `结束`** → token 流应出现源码中不存在的 `结束`：已用 `light tokens` 验证，`捕获`/`最终` 冒号行不再被压栈补 `结束`；`若/否则/遍历/重复` 等非延续块无回归。✔
3. **破坏点 = 多捕获语义分叉**（SRC 报 `name '串' is not defined`）→ 探针改为两后端通用单变量多捕获形态后，两后端输出**逐字节一致**。✔

## 五、遗留 / 偏离声明

### 5.1 ⚠ 重大隐患（源自 workbuddy 复核，已确认属实）—— Day2 0.82 权威门 **未跑**，且当前状态**跑不得**

`lightharness/scripts/同步0.82.py` 第 34 行硬编码：

```python
LIGHT_MERGE = ROOT / "light-merge"        # 主树，非 worktree
```

- 当前 `light-merge-day2`（worktree，分支 `day2-lp011`）的 13 个改动文件**全部未提交、未合并回主树**；主树 `light-merge` `git status` 干净。
- ⇒ **现在跑 0.82 权威门，同步上去的是「未修改的主树」，Day2 的 ANTLR 改动根本不会被测到**——门 PASS 就是自欺欺人。
- workbuddy 判断完全正确，且其推论成立：**此隐患不解决，Day2 的门就是自欺欺人，Day3 建在其上会更糟。**

**根因**：`同步0.82.py` 假定「被测代码 = `ROOT/light-merge`」，但 `git worktree` 机制使并发任务的改动落在 `ROOT/light-merge-day2` 等独立工作树。二者路径不同，同步脚本无法感知。

**Day2 的后续动作（2026-10-02）**：本报告落盘时仅做本地探针 + 本地门数字验证、不跑 0.82 门、不自行 push。此后已按用户示意完成：① worktree 改动本地提交到 `day2-lp011`（`76addcc17`）；② fast-forward 合并回主树 `light-merge`（HEAD→`76addcc17`）；③ 修 `同步0.82.py` 硬编码主树隐患（`2cffa53`，见下方建议 1 已落地为 `--light-merge` 参数 + `print_probe_identity()`）；④ 推送到 gitea + gitcode（github 因历史分叉经用户确认不推）。**0.82 权威门仍未实际运行**——代码前置已就绪，可由后续轮次/总调执行。

**给 Day3 与总调的硬性建议**（1、2 已在 `2cffa53` 落地，3 待后续轮次执行）：
1. ~~跑 0.82 权威门的前置动作~~ **已落地**（`2cffa53`）：Day2 改动已合并回主树 `light-merge`（`76addcc17`），并给 `同步0.82.py` 新增 `--light-merge <path>` 参数（默认仍主树，worktree 开发时可显式指定）。
2. ~~在 `同步0.82.py` 加显式断言/参数 + sync 前打印被测身份~~ **已落地**（`2cffa53`）：`print_probe_identity()` 在 sync/run 前打印 lightharness/light-merge 的被测路径 + `git status`（脏/干净）+ HEAD sha，让「测的是哪个 commit」一目了然。
3. **门结论必须注明被测 commit（待执行）**：`sync` 应在远端落盘一份「被测 light-merge HEAD = <sha>」的标记（例如 `reports/同步0.82_被测HEAD.txt`），并在最终门报告里引用；避免「门 PASS 但测的是旧代码」这类假绿再发生。当前 `print_probe_identity()` 只在**本地** sync 前打印，远端副本未留痕——建议后续轮次补。

### 5.2 本地探针是「真测到改动」的证据

`light-merge-day2/cli/light.py` 用 `__file__` 定位项目目录（`_CLI_DIR = os.path.dirname(os.path.abspath(__file__))`），因此在 `light-merge-day2/` 目录下执行时加载的是 **day2 的 antlrparser**。已实测 `sys.path.insert(0, 'light-merge-day2')` 后 `import antlrparser.LightLangParser` 报 `ModuleNotFoundError`（说明 day2 的 `antlrparser` 不是包，靠 `cli/light.py` 的 `sys.path` 注入 `antlrparser/` 生效）——本地探针路径正确。

### 5.3 基线红账

`antlrparser/test/` 基线即有 61 failed + 16 errors（含 `RangeExpr` 未定义、`TestErrorListener` 无法 collect 等），是**与真实测试入口 `tests/` 不同步**的历史遗留，非 Day2 引入。若 Day3 需把该套件纳入门禁，应另行定靶。
---

## §六 · 【team lead 追加】本线已按砍线条款**回退**（2026-10-02 08:0x，真实时间）

> ⚠️ **本节由 team lead 在合流验收时追加。§一–§五 的记录保留原貌，但「已交付」结论已被下述实测推翻。**

### 6.1 合流验收实测：本线引入 7 条硬失败 + 5 条静默回退

组合态 0.82 权威门（`all --mode full`，LM `76addcc17` + LH `41a6ea2`）**判 FAIL**：

```
[082全量] 失败数 0 → 7（8489 → 8489 用例）
[082全量] 新增红 7
[082全量] 门：FAIL ❌
```

| 类型 | 明细 |
|---|---|
| **7 条硬失败** | `test_import_math_{abs,round,sqrt,sum}`、`test_import_time_format`、`test_import_with_multiple_symbols`、`test_mixed_stdlib_builtins` —— 全部 `RuntimeError: ANTLR 解析错误: 3/5/7 个` |
| **5 条静默回退** | Day1 刚修好的 `test_regex_{search,findall,replace,is_match,escape}` 由 **passed → skipped**（解析异常被用例自己的 `except Exception → skipTest` 吞掉），另加 `test_base64_encode_decode`/`test_hex_encode_decode`/`test_md5_hash` 3 条新 skip |

> 后一类是计划书 §三「门判据盲区」的再次实证：**门只比 failed 集合，看不见 passed→skipped**。

### 6.2 根因（team lead 独立复现）

重生成的 `antlrparser/light_parser/LightLangLexer.py` **丢失全部中文字面量词法规则**。同一输入
`从《数学》导入《平方根》。` 的 token 流对拍：

```
Day1(589d495d4): K_FROM '从' | BOOK_L '《' | ID '数学' | BOOK_R '》' | K_IMPORT '导入' | PERIOD '。'
Day2(76addcc17): ID     '从' | UNKNOWN '《' | ID '数学' | UNKNOWN '》' | ID '导入'     | UNKNOWN '。'
```

ANTLR 报 `line 1:1 no viable alternative at input '从《'` + `mismatched input '。' expecting PERIOD`。

`antlrparser/LightLangLexer.g4` **本线未被修改**，但生成物变了 910 行、`.tokens` 变了 92 行 ——
形态与「只把 `LightLangParser.g4` 单独喂给 ANTLR、没喂 lexer 语法」一致（parser 用的是 `K_*` 记号，
单独生成得到的 lexer 不含 `'从'` 这类字面量规则）。
本机与 0.82 的 `antlr4-python3-runtime` 均为 4.13.2，故本机复现有效；本机 `java` 不可用，无法就地正确重生成。

### 6.3 为什么本线的本地验证没发现

本线自测用的是 `antlrparser/test/`（见 §5.3），该套件自带 61 failed + 16 errors 的历史红账、
且与真实入口 `tests/` 不同步 —— **在噪声里看不出这 7 条**。教训：ANTLR 后端改动必须跑
**真实入口**（`tests/test_module_system.py` 或 0.82 权威门），不能只跑 `antlrparser/test/`。

### 6.4 处置

- `antlrparser/` 全目录回退到 Day1 状态（LM commit `c775f27d3`）。
- LP-D-011「ANTLR 后端 尝试/捕获」**未收口** → 按计划书 Day2 砍线条款退回「登记为后端差异」。
- 本线完整尝试留档 `_day2_antlr尝试_待重做.patch`（8529 行，monorepo 根），重做时据此起步。
- **保留**（与本回退无关的正向产出）：`2cffa53` 修 `同步0.82.py` 硬编码主树隐患（新增 `--light-merge` 参数
  + sync/run 前打印被测身份）——这条是有价值的，D2 报告 §5.1 的定位正确。

---

## §七 · 【重做收口】按权威姿势重做，§6.1 的 15 条问题全部翻绿（2026-10-02 08:1x–08:3x）

> 本节由 Day2 线在用户示意后追加。首版病根（重生成丢中文字面量）已定位为
> **未指定 `-encoding UTF-8` 且未按「lexer 先行 → parser `-lib`」两步生成**；
> 本轮改用权威脚本 `scripts/generate_antlr_parser.py`（自带工具链下载 + 正确姿势）重做，
> 改动内容与首版一致（从 `_day2_antlr尝试_待重做.patch` 恢复）。

### 7.1 重做姿势（LM `9a5c5920b`）

| 项 | 值 |
|---|---|
| 工具链 | Temurin **JRE 17.0.20.1** + **antlr-4.13.2-complete.jar**（与 `antlr4-python3-runtime` 4.13.2 同版本），由脚本自动下载缓存至 `%TEMP%/light-antlr-tools/` |
| 生成姿势 | `[1/2] LightLangLexer.g4`（`-encoding UTF-8`）→ `[2/2] LightLangParser.g4`（`-encoding UTF-8` + `-lib light_parser`）——与首版「一条命令喂两个 g4、无编码参数」的差异即病根 |
| 生成物 | Lexer 4 文件 + Parser 3 文件 + Visitor，全部落 `antlrparser/light_parser/` |

### 7.2 验证实测（全部真实执行，主树 LM `9a5c5920b`）

| # | 验证 | 结果 |
|---|---|---|
| 1 | **对拍产物**：Lexer `LightLangLexer.py/.interp/.tokens` + `LightLangParser.tokens` vs git HEAD（revert 后正确基线） | **逐字节一致** → 编码正确、中文关键字字面量零丢失（§6.2 病根消除的直接证据） |
| 2 | 对拍产物：`LightLangParser.py/.interp` | 差异仅 tryStmt 规则传导（g4 改动预期范围）；Visitor 仅 +10 行（`visitCatchSpec`/`visitIdentifier_or_type`） |
| 3 | **§6.1 全部 15 条对拍**（7 硬失败 + 5 regex 静默回退 + 3 新 skip） | **15 passed, rc=0**（`test_import_math_*`、`test_import_time_format`、`test_import_with_multiple_symbols`、`test_mixed_stdlib_builtins`、`test_regex_{search,findall,replace,is_match,escape}`、`test_base64_encode_decode`、`test_hex_encode_decode`、`test_md5_hash`） |
| 4 | `test_module_system.py` 全量 | **51 passed / 7 skipped, rc=0**；7 skip 均为既有 API 兼容性跳过（时间模块缺失/中文数字标识符/数学库统计函数缺名），与 Day1 基线口径一致，不属本路 |
| 5 | LP-D-011 四探针（`lp011_{probe,probe2,finally,multi_catch}`） | ANTLR+SRC 全部 rc=0，输出两后端一致 |
| 6 | 第 5 个端到端 `mod_greet.light` | ANTLR rc=0 / SRC rc=0，输出一致（注：`sample_quicksort.light` SRC 侧解析失败为 src 后端既有 lexer bug，与 ANTLR 无关——src 侧最后改动为 Day1 `589d495d4`） |
| 7 | `antlrparser/test/` 门三元数字 | failed 61→61 / passed 21→21 / errors 16→16，FAILED 集合逐条 diff 与 Day2 前基线一致 → **零回归** |
| 8 | `scripts/antlr_leg_smoke.py` ANTLR 腿冒烟 | **42/42 通过**（20.4s），rc=0，矩阵已落盘 `reports/antlr腿_冒烟_2026-10-02-081927.md` |

### 7.3 遗留

- **组合态 0.82 权威门对 `9a5c5920b` 尚未重跑**（上轮 PASS 是对回退基线 `c775f27d3` 的判定）。
  本地同口径验证已全绿（§7.2 #3/#4/#7/#8），风险点仅在远端环境复现，待 team lead 排队放行后执行。
- `day1-baseline` tag 已推送两仓四远端中的 gitea+gitcode（github 按用户决定不推，见 §5.1）。
