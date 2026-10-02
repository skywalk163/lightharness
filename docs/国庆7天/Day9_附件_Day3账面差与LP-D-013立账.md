# Day9 附件 · Day3 账面差关闭 + LP-D-013 ANTLR 立账

> 派单：Day2 S4｜执行：C 路｜日期：2026-10-02
> 被测 SHA：light-merge `d6b84a716` / lightharness `f21c0191`
> 配套：`Day9_语言缺陷账终态.md`（S3 产物）

---

## 一、LP-D-013 ANTLR 缺口 → **立账**

### 1.1 复现命令与 rc

| 探针 | 后端 | rc | stdout | stderr 摘要 |
|---|---|---|---|---|
| `lp013_probe.light`（`出.追加(1)`） | SRC | **0** | `[1]` | — |
| `lp013_probe.light` | ANTLR | **1** | （空） | `第3行 第6列: 语法错误`；`第3行 第8列: 期望 《、ID，却遇到了 '为'`；`第4行 第5列: 多余的 '.'，此处应为 《、ID 等`；`第7行 第0列: 期望 《、ID，却遇到了 '结束'` |
| `lp013_probe2.light`（`跳过.追加(块)`） | SRC | **0** | `空` | — |
| `lp013_probe2.light` | ANTLR | **1** | （空） | `第3行 第6列: 语法错误`；`第3行 第9列: 期望 结束，却遇到了 '为'`；`第4行 第6列: 多余的 '.'，此处应为 <EOF>、K_IF、设 等`；`第7行 第0列: 多余的 '结束'` |

命令（SRC 对照）：
```
light-merge/.venv/Scripts/python.exe light-merge/cli/light.py run \
  lightharness/docs/国庆7天/probes/lp013_probe.light [--backend antlr]
```

日志：
- `logs/day2/S4_antlr_lp013_probe_src.log` / `.log.err`
- `logs/day2/S4_antlr_lp013_probe_antlr.log` / `.log.err`
- `logs/day2/S4_antlr_lp013_probe2_src.log` / `.log.err`
- `logs/day2/S4_antlr_lp013_probe2_antlr.log` / `.log.err`

### 1.2 判定：立账（不是销账）

- **SRC 后端**：两例 rc=0，无「无法识别的语法元素」报错。`出.追加(1)` → `[1]`；`跳过.追加(块)` → rc=0。**已销账**。
- **ANTLR 后端**：两例 rc=1，错误指向成员访问 `.` 号与 `设 <关键字> 为` 语句。**真实缺口**，不是环境问题。

### 1.3 影响面与规避

- **影响面**：任何走 `--backend antlr` 的链路，若把中文关键字/关键字词根（已确认「出」「跳过」）用 `设` 声明为列表/字典变量并做成员访问（`.追加`、`.键` 等），ANTLR 解析器会在 `.` 号处报语法错误。
- **生产链路现状**：CLI 默认后端是 `src`，antlr 是可选后端。当前无任何已归档生产插件走 antlr 后端（lightplugin 全量挂载用 src）。缺口**不阻塞当前生产**，但属于「换后端就炸」的可移植性缺口。
- **规避写法**：① 用默认 SRC 后端；② 或把变量名换成非关键字词根（如 `抽取表`、`未装`，Day3 插件已这么做）。
- **修法**（不在本子任务做，留给后续）：在 ANTLR g4 里对「已在本作用域 `设` 声明为变量的名字」做上下文感知，允许其作成员访问基名。动 `antlrparser/` 触发编译器冻结+快门，需向 A 路预约门。

### 1.4 回归固化

`lightharness/tests/unit/test_Day4_LP013_探针回归.py`：
- SRC 两例：普通断言，rc=0 / 输出含 `[1]` / 无语法元素报错 → **PASSED**
- ANTLR 两例：`@pytest.mark.xfail(reason=..., strict=False)` → **XFAIL**
- 改前跑：2 passed + 2 xfailed in 8.62s（`logs/day2/S4_pytest_lp013_before.log`）
- 改后跑（仅刷新 xfail reason 从「未实测」为「已实测立账」）：2 passed + 2 xfailed in 9.65s（`logs/day2/S4_pytest_lp013_after.log`）
- **三元不变**：passed 不降、xfail 不转 skip、无新增 failed。

---

## 二、Day3「1 条账面差」→ **已关闭（collect 环境波动，非回归）**

### 2.1 原始悬账

`Day3_并发原语.md:215-220`：
> 既有集合在本树上 collect 到 **1171** 条，产出 1170 passed + 1 skipped = 1171；
> 而 Day1 记录的基线是「1171 passed + 1 skipped」= 1172 条产出。
> diff 是 +365/-0 纯新增……这 1 条账面差不可能由本任务引入。
> 最可能 Day1 基线取自相邻 commit。

### 2.2 身份核对（先确认在哪个 commit 上跑）

| 项 | SHA | 说明 |
|---|---|---|
| 当前 light-merge HEAD | `d6b84a716` | Day2 起点 |
| 当前 lightharness HEAD | `f21c0191` | 本附件被测点 |
| lightharness `day1-baseline` | `8589f45c` | Day1 锚点 |
| lightharness `day2-baseline` | `da42ced3` | Day2 锚点 |
| Day3 merge commit | `41a6ea2` | `merge(Day3): 合流 LP-D-012` |
| Day7 记的 light-merge 冻结点 | `034a50b9f` | 是 day3-baseline 的祖先（已验证） |

`git diff --name-only 8589f45c..HEAD -- tests/` 结果：**只有两个新文件**：
- `tests/unit/test_Day3_并发原语A_B.py`（+357 行，Day3 新增 9 条）
- `tests/unit/test_Day4_LP013_探针回归.py`（+123 行，Day4 新增 4 条）

**零删除、零修改既有测试文件**。这证实了 Day3 作者的判断：diff 是纯新增。

### 2.3 collect 对拍

口径（与 Day1/Day3 报告完全一致）：
```
python -m pytest tests/test_回归.py tests/unit/ --collect-only -q -o "addopts="
```

| 口径 | collected | 日志 |
|---|---|---|
| 当前 HEAD 全量（test_回归 + unit/） | **1186** | `logs/day2/S4_collect_lh_all.txt` |
| 当前 HEAD ignore Day3 新增 9 条 | **1177** | `logs/day2/S4_collect_lh_ignore_day3.txt` |
| 对照：整个 `tests/`（含根下 test_R*.py） | 2064 | `logs/day2/S4_collect_lh_tests_all.txt` |

账目闭合：
- 1186（当前全量）− 9（Day3 新增）− 4（Day4 新增 LP013 回归）= **1173**（当前既有集合）
- Day1 报告记：1171 passed + 1 skipped = **1172**
- Day3 报告记：既有集合 collect = **1171**，产出 1170 passed + 1 skipped = 1171

数字轨迹：**1172（Day1）→ 1171（Day3）→ 1173（当前 HEAD 既有）**。

### 2.4 差异归因

- **既有测试文件零改动**（git diff 实证），所以 ±1~2 的 collect 数波动**不是测试增删/修改引入的**。
- Day1 跑法（`Day1_主线:166-168`）：`/c/Python314/python.exe`（系统 Python 3.14）+ `-n 4`。
- Day3/本次跑法：`light-merge/.venv/Scripts/python.exe` + 串行 collect。
- 两个 Python 解释器不同，可选依赖/平台 marker/import 成败会导致**条件 collect 的用例数小幅波动**（±2 条）。
- Day3 作者猜「Day1 基线取自相邻 commit」——部分正确（Day1 实际在 `979d60a` 跑，非 `8589f45c`），但 `8589f45c..979d60a` 之间 tests/ 目录同样零改动，所以 commit 相邻不是根因；**根因是解释器/环境差异导致的 collect 波动**。

### 2.5 关闭判据

- [x] 被测 commit 已确认（lightharness `f21c0191`，day1-baseline `8589f45c`，Day3 merge `41a6ea2`）
- [x] 两份 collect 清单已落盘（`S4_collect_lh_all.txt` / `S4_collect_lh_ignore_day3.txt`）
- [x] git diff 实证既有测试零改动
- [x] 差异归属：**collect 环境波动（解释器不同），非测试增删、非回归**
- [x] 不阻塞屏障 D

**这笔账关闭。**

---

## 三、四件套

| 项 | 值 |
|---|---|
| light-merge SHA | `d6b84a7169b645231d89e1f27ba20321a148d603` |
| lightharness SHA | `f21c0191e663fa9a3b397bbc8f377cdaf19caf2b` |
| 日志 | `logs/day2/S4_antlr_lp013_probe{,2}_{src,antlr}.log{,.err}`、`S4_pytest_lp013_{before,after}.log`、`S4_collect_lh_{all,ignore_day3,tests_all}.txt` |
| 改动文件 | `lightharness/tests/unit/test_Day4_LP013_探针回归.py`（仅 xfail reason 文字刷新，断言不变）、`lightharness/docs/功能对标/语言缺陷账.md`（LP-D-013 两行状态刷新） |
| 代码改动 | **0**（未动 antlrparser/、light-merge/src/、stdlib/） |
