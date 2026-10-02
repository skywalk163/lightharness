# T2 契约 · LP-D-013 ANTLR 补缺口（已声明变量可作成员访问基名）

> 夜场派单表：`Day2夜场_派单表.md` **v1.2**｜行：**A（编译器门线）／5 路并行中的串行尾**
> **资源型**：CPU 中 + **改编译器 + 重新生成 parser**｜**需门**：**是**｜**预计**：约 1.5–2 小时
> **前置**：**T1 收口即可开，不必等修复** —— ① **T1 合流**，**或** ② **T1 探针判定「已可用 → 销账」**（此时 T2 立即可开；参照 LP-D-011/013 两次先例）。
> 　└ **只有 T1 与 T2 争 `src/`+`antlrparser/`**；T3/T4/T5/T6 与 T2 无共享资源，可同时跑。
> ⚠️ **最小改动约束（用户决策）**：冻结已正式解除，但**只允许 §十一 所述的最小改动**。
> **出口 tag**：`subtask-T2-done`

---

## 一、目标

修掉 LP-D-013 的 **ANTLR 后端**缺口：让「已由 `设`/`遍历` 声明为变量的中文关键字/词根名」可作**成员访问基名**（如 `出.追加(1)`、`跳过.追加(块)`），使 `test_Day4_LP013_探针回归.py` 里那 **2 条 xfail 转为 passed**。

## 二、前置事实（已核实，省去你摸索）

| 项 | 值 |
|---|---|
| 账内定性 | **立账**（不是销账）——`Day9_附件_Day3账面差与LP-D-013立账.md` §一/§1.2 |
| **SRC 后端** | 两例已销账（rc=0，`出.追加(1)` → `[1]`）——**这部分不要动** |
| **ANTLR 后端** | 两例 xfail（`@pytest.mark.xfail(reason=..., strict=False)`），实证缺口 |
| 回归测试 | **`lightharness/tests/unit/test_Day4_LP013_探针回归.py`**（改前/改后跑：2 passed + 2 xfailed，见 `logs/day2/S4_pytest_lp013_{before,after}.log`） |
| 探针 | `docs/国庆7天/probes/lp013_probe.light`（`出`）、`lp013_probe2.light`（`跳过`） |
| ANTLR 报错原文 | `解析失败: 第9行, 第0列: 多余的 '结束'，此处应为 <EOF>、K_IF、设 等` |
| 要改的文件 | `antlrparser/LightLangLexer.g4` / `LightLangParser.g4`、`antlrparser/indent_preprocessor.py`、生成的 `light_parser/*` |

## 三、🔴 硬规程：ANTLR 重新生成必须按「权威姿势」（白天首版就栽在这里）

白天第一版重生成 **丢了中文字面量** → 新增红 7 + 5 条静默转 skipped → **砍线回退**（留下 `_archive/` 里那份 **566 KB** 的 `_day2_antlr尝试_待重做.patch`）。重做成功靠的是下面这套姿势，**原文见 `Day2_异常处理后端收口.md`**：

| 项 | 要求 | 出处 |
|---|---|---|
| **首版失败原因** | 「**未指定 `-encoding UTF-8` 且未按「lexer 先行 → parser `-lib`」两步生成**」 | `Day2_异常处理后端收口.md:185` |
| **工具链** | **Temurin JRE 17.0.20.1** + **antlr-4.13.2-complete.jar**（与 `antlr4-python3-runtime` 4.13.2 同版本）；脚本自动下载缓存到 `%TEMP%` | `:193` |
| **生成姿势（两步）** | `[1/2] LightLangLexer.g4`（`-encoding UTF-8`）→ `[2/2] LightLangParser.g4`（`-encoding UTF-8` + **`-lib light_parser`**） | `:194` |
| **对拍产物** | Lexer `LightLangLexer.py/.interp/.tokens` + `LightLangParser.tokens` vs git HEAD → **逐字节一致** | `:201` |
| 注意 | 本机 `java` 当时不可用（`:164`）→ 先确认工具链可用（或用 `:193` 的自动下载脚本），**别在没有 JRE 的机器上硬生成** | `:164` / `:193` |

**现成脚本（先审计再复用，不要从零写）**：
`light-merge/antlrparser/scripts/generate.ps1`、`light-merge/scripts/generate_antlr_parser.py`、`light-merge/scripts/generate_parser.py`、`light-merge/scripts/fix_parser_syntax.py`
→ 逐个看哪个实现了上面的两步姿势 + `-encoding UTF-8`；把**实际使用的命令**落盘进报告。

## 四、文件白名单 / 黑名单

| | 路径 |
|---|---|
| **可写** | `light-merge/antlrparser/*.g4`（仅改必要规则）、`light-merge/antlrparser/indent_preprocessor.py`、`light-merge/antlrparser/light_parser/*`（**只能由生成器产出**）、`light-merge/src/`（**仅在确有必要时**）、`lightharness/tests/unit/test_Day4_LP013_探针回归.py`（把 xfail 改回普通断言）、`docs/国庆7天/Day2夜_T2_LPD013_ANTLR补缺口.md`、`logs/day2-night/T2_*` |
| **禁止** | `lightplugin/`、`lightharness/` 其它文件、`_push_github_*.py`、**其它 g4 语义**（只动与「基名解析」相关的部分） |

## 五、步骤

1. **复现**：跑 `test_Day4_LP013_探针回归.py`（ANTLR 侧）→ 落盘 2 xfailed + 报错。
2. **改 g4**：在 parser 规则里让「已声明为变量的名字」可作**成员访问基名**（上下文感知；参照账内说的 L-021 对 `属性`、L-025 对 `包含` 的既有范式，以及 LP-D-013 账内期望的「按标识符解析」）。必要时配合 `indent_preprocessor.py`（「多余的 `结束`」很可能是**解析失败后的连带症状**，不是缩进本身的问题）。
3. **重生成**（§三 硬规程）：两步 + `-encoding UTF-8` → **对拍产物**（Lexer 三件 + Parser tokens vs HEAD）：若**除你刻意修改的规则外**出现差异 → **停下来查**，不许带差异继续。
4. **回归**：
   - `test_Day4_LP013_探针回归.py`：**2 passed + 0 xfailed**（xfail 去掉，**不许改成 skip**）；
   - `antlrparser/test` 门三元不劣化；
   - `light-merge/tests/test_module_system.py` 不劣化（它走 ANTLR 后端，是这套改动的**高危邻居**）。
5. **跑 0.82 门**（A 线独占；锚点见 §七）。
6. **账内收尾**：LP-D-013 的 ANTLR 部分由「立账」改为**已修复**（写明 commit + 证据文件名）。

## 六、交付物

| 路径 | 内容 |
|---|---|
| `docs/国庆7天/Day2夜_T2_LPD013_ANTLR补缺口.md` | 三段式；**必须含**：改前/改后 g4 diff、**实际使用的重生成命令全文**、产物对拍结论（逐字节/差异清单） |
| `light-merge/antlrparser/light_parser/*` | 重生成产物（**逐字节校验通过**才算交付） |
| `lightharness/tests/unit/test_Day4_LP013_探针回归.py` | xfail → 普通断言 |
| `lightharness/docs/功能对标/语言缺陷账.md` | LP-D-013 ANTLR 段状态刷新（**与 T5 串行**） |
| `logs/day2-night/T2_*.log` | 复现/生成/对拍/回归/门 的原始输出 |

## 七、验收标准（可量化）

1. `test_Day4_LP013_探针回归.py`：**2 passed / 0 xfailed / 0 skipped**；第二例不得再报「无法识别的语法元素 '.'」或「多余的 '结束'」。
2. **产物一致性**：Lexer 三件 + Parser tokens 与「改前 + 你的规则改动」等价（**逐字节给出结论**）。
3. **antlrparser 门**三元不劣化（failed / skipped / passed）。
4. **0.82 门三元**：failed 新增 0 **且** skipped 不增 **且** passed 不降
   - **对拍锚点**：`reports/082_lightmerge基线_2026-10-02-171604.json` = **8356 / 0 / 122**
5. 四件套齐全 + **被测 SHA 必写**。

## 八、反跑判据

1. 破坏「已声明变量可作成员访问基名」的 g4 规则 → 探针**复红**（复现原 ANTLR 报错）。
2. 破坏 `-encoding UTF-8`（或改用一步生成）→ **产物对拍应出现差异**（这条既是反跑，也是给你的警戒线：证明这套规程不是形式主义）。

## 九、砍线与降级

- **150min 上限**。
- **重生成再次出偏差 → 立即回退到 git HEAD 的 `light_parser/*` 产物**（照白天那次砍线的做法），出口降级为「探针 + g4 设计 diff + 失败原因分析 + 复现命令」，**绝不带着坏产物跑门、绝不进 T7 之前留下红基底**。
- 门红 → 回退，**不阻塞其它子任务**。

## 十、必须带回的证据（四件套）

命令 + 退出码 + 日志路径（`logs/day2-night/`）+ 被测 SHA（`light-merge` HEAD；如工具链有版本也一并写）。

## 十一、禁止事项

> ⚠️ **最小改动约束（派单表 v1.2 用户决策：冻结已正式解除，但只限 T1/T2 的最小改动）**：g4 只改与「基名解析」**直接相关**的规则；**禁止**顺带重构、整文件格式化、改无关语法分支、扩大 blast radius。**改动清单必须逐文件逐行列出**（文件 + 行号 + 改了什么 + 为什么）。

除夜场派单表附录 B 的 10 条外：
1. **不许手改 `light_parser/*` 生成产物**——只能由生成器产出（手改下次重生成即丢）。
2. **不许把 xfail 改成 `skip`/删除**来「收口」（三元判据明确「passed 变 skipped 即劣化」）。
3. 不许动与「基名解析」无关的 g4 语义（会把 blast radius 扩大到整套 parser）。
4. 不许在未做产物对拍的情况下提交重生成结果。
