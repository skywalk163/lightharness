# `_l172probe/` —— R53 L-172 诊断取证脚本

> 配套报告：`../_task1_R53_L172诊断.md`、`../_task2_R53_L172修复.md`
> 用法：`cd light-merge && ./.venv/Scripts/python.exe _l172probe/<脚本>.py`
> 全部为**只读诊断/取证**脚本（除 `mut_r52.py`/`pre_fix.py` 会临时写文件，见下）。可整目录删除。

| 脚本 | 作用 |
|---|---|
| `dump.py` | 单文件诊断：打印顶层语句结构 / 入口检测（entry/arity/module_invokes_entry/_entry_call）/ 产物末尾 |
| `matrix.py` | 7 种「非主段落体按名调用被导入函数」形态矩阵（stdlib 导入 / 本地 .light 导入 / 参数 / 顺序 / 返回值） |
| `fuzz.py` `fuzz2.py` | 1620 组形态组合模糊搜索，判定「有 `主` 但无 `MAIN-OK` 输出」= 静默 |
| `pre_fix.py` | 把真实 `test_R52_ssh协议.light` 机械还原成 pre-fix「包裹段落」形态（⚠️ 写到 `lightharness/examples/`，跑完请删生成文件） |
| `mut_r52.py` | 在真实 R52 用例上做 3 种反向突变（⚠️ 同样写到 `lightharness/examples/`） |
| `w_lightharness.py` | lightharness 布局（examples 主文件 + src 真模块 + `_light_import_hook`）+ 包裹段落 + 自动入口 |
| `var_sweep.py` | 空格/连写/全角标点变体扫描（复现 L-155 词法类副作用） |
| `scan_missing_entry.py` | 全语料 730 个 `.light`：源含 `段落 主` 但产物缺入口调用块的伪抑制扫描 |
| `measure_arity.py` | 全语料入口段落 arity 分布（度量「带形参入口」影响面） |
| `gate3.py` | 顶层**裸引用**入口名 → 静默抑制入口块的最小复现 + 「收紧闸门」影响面度量 |
| `cand.py` | 入口判定三闸门的候选静默形态逐个实测（含 arity>0 / 条件内定义入口等） |
| `probe_entry.py` | 真实 R52 用例去尾 `主()` 后的入口检测归因（逐条顶层语句命中情况） |
| `probe_drop.py` | parser 静默丢语句路径探测（`_parse_statement` 返回假值只 `pos += 1`） |
| `h1.py` | R52 报告 §4.3 pre-fix 形态的最小自包含还原 |
| `verify_fix.py` | **红前/绿后双向取证**：monkeypatch 还原旧闸门口径 vs 当前源码 vs arity 告警 |

## 结论速览

- 「非 `主` 段落其函数体按名调用被导入函数」**不复现**（`matrix.py`/`fuzz2.py`/`pre_fix.py`/`w_lightharness.py`/`var_sweep.py`/`scan_missing_entry.py`）。
- **真复现**：顶层裸引用入口名（`gate3.py`、`cand.py` 的 F 变体）→ 入口自动调用被静默抑制。
- **次静默点**：带形参入口（`cand.py` A/E 变体）→ 静默不调用，现已改为编译期告警。
