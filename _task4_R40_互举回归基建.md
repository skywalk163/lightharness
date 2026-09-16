# 任务4 交付报告：互举回归基建（基线外打红 CI 门 + 互举反跑脚本）

> 轮次：第40轮「互举闭环端到端集成」｜任务4（P1）｜完成日期：2026-09-16
> 交付物：`light-merge/scripts/check_ci_baseline.py`、`lightharness/scripts/互举反跑.py`、
> `lightharness/scripts/互举反跑基线.json`、本报告
> 铁律核对：**只新增脚本文件，未修改 src/ 与 examples/**；仅标准库；`0 新增解析失败 = 绿`

---

## 0. 状态一览

| 子任务 | 交付物 | 状态 | 验证 |
|---|---|---|---|
| 4.1 基线外打红 CI 门 | `light-merge/scripts/check_ci_baseline.py`（20.7 KB / 411 行） | ✅ 完成 | 受控实验：引入新红→报警（rc=1）→还原→绿（rc=0） |
| 4.2 互举反跑脚本 | `lightharness/scripts/互举反跑.py`（15.6 KB / 341 行）+ 基线 JSON | ✅ 完成 | 644 文件扫描，**0 新增解析失败 = 绿** |
| 4.3 使用文档 | 两脚本模块级 docstring（含用法/退出码/判据）+ 本报告 | ✅ 完成 | — |

**本轮额外产出（非计划内，但直接决定门「能不能用」）**：定位并修掉了**三个真实缺陷**——
① 基线文件**身份格式失配**（转义 vs 原始汉字）→ 使 CI 回归闸门**恒红**；
② **SKIP 被误判为「已转绿」** → 会诱导使用者刷新基线、**静默删掉真实欠账**；
③ 交付脚本被 `.gitignore` 的 `check_*.py` 规则**静默吃掉** → 干净克隆里脚本不存在、门禁整条失效。
详见 §2.3 / §2.4 / §2.6。

**改动文件清单**（light-merge 侧）：
`scripts/check_ci_baseline.py`（新增）、`tests/ci_baseline_failures.txt`（**未改**）、
`tools/ci/check_regression.py`（**未改**）、`.gitignore`（**+1 条精确豁免**）。
lightharness 侧：`scripts/互举反跑.py`（新增）、`scripts/互举反跑基线.json`（新增）。

---

## 1. 互举闭环是什么，这两条基建各守哪一段

```
        ┌──────────────────────────┐         ┌──────────────────────────┐
        │  light-merge（编译器）    │         │  lightharness（框架）     │
        │  光明语言本体 + cli       │         │  用光明语言复刻 harness    │
        └───────────┬──────────────┘         └───────────┬──────────────┘
                    │                                     │
      「框架驱动语言」│ 编译 lightharness 全树               │「语言是框架地基」
                    ▼                                     ▼
        ┌──────────────────────────────────────────────────────────────┐
        │  任务4.2 互举反跑：lightharness 644 个 .light 能否 tokenize+parse │
        │  → 0 新增解析失败 = 语言没退化 ⇒ 框架仍可编译                      │
        └──────────────────────────────────────────────────────────────┘
        ┌──────────────────────────────────────────────────────────────┐
        │  任务4.1 基线门：pytest 打红 − 基线 = 新增打红？                  │
        │  → 新增 0 条 = 编译器/运行时没退化 ⇒ 存量欠账 ≠ 新回归             │
        └──────────────────────────────────────────────────────────────┘
```

一句话：**4.2 守「词法/语法层不退化」，4.1 守「端到端行为不退化」**；
两者都以「**只拦新增、放行存量**」为判据，避免既要修旧账又要被旧账挡门的死锁。

---

## 2. 子任务 4.1：基线外打红 CI 门

### 2.1 脚本定位与用法

**位置**：`light-merge/scripts/check_ci_baseline.py`（仓库根 `scripts/` 下）

**与既有 `tools/ci/check_regression.py` 的关系**：后者是 CI 内部用的**极简闸门**（只吃 junit、只打 key）；
本脚本是它的「**开发机友好超集**」，把「基线外新增打红」变成**本地可自查**的能力。
（不动 `tools/ci/check_regression.py` —— 它是 CI 正在跑的脚本，改动属另一 PR 范围。）

```
# ① 自行跑 pytest（默认 tests/ 全量；开发机最省事）
python scripts/check_ci_baseline.py
python scripts/check_ci_baseline.py tests/unit tests/e2e/test_e2e_chain.py
python scripts/check_ci_baseline.py --pytest-args "-k lexer -x"

# ② 复用已有 junit（CI 用；也避开 Windows 控制台中文用例名的双重编码损坏）
python scripts/check_ci_baseline.py --junit .ci/report.xml
python scripts/check_ci_baseline.py --junit '.ci/*.xml'

# ③ 只警告不阻断（观察模式）
python scripts/check_ci_baseline.py --junit .ci/report.xml --warn

# ④ 修好一批后刷新基线
python scripts/check_ci_baseline.py --junit .ci/report.xml --write-baseline

# ⑤ 只跑基线里登记过的测试文件（CI 上省时）
python scripts/check_ci_baseline.py --junit .ci/report.xml --only-baseline

# ⑥ 额外产出 JSON 报告；⑦ 软通配（命中的 classname 只报不拦）
python scripts/check_ci_baseline.py --junit .ci/report.xml --json gate.json
python scripts/check_ci_baseline.py --junit .ci/report.xml --soft-classname 'tests.test_*'
```

**退出码**：`0` 无基线外新增打红（绿）｜`1` 存在基线外新增打红（红/回归）｜`2` 用法或环境错误。

**输出格式**（任务书要求：测试名 + 失败原因摘要 + 是否基线内）：

```
==============================================================================
基线门报告：基线 12 条 ｜ 本次打红 32 条（硬） + 0 条（软）｜ 新增打红 28 条
==============================================================================
状态     测试名                                                          失败原因摘要
------------------------------------------------------------------------------
基线内    tests.test_demo::test_known_red                              AssertionError: 存量欠账
新增     tests.test_demo::test_introduced_red                         AssertionError: 故意引入的新回归
...
基线外新增打红（视为回归）：
   ! tests.e2e.test_e2e_chain::test_duan_run[basic.light]   ← AssertionError: duan run 失败 (basic.light):
判据：新增打红 28 条 ⇒ 阻断（退出码 1）
```

实现细节（都是本仓既有踩坑的固化）：
- **一律走 junit**，绝不解析控制台输出——Windows 控制台对中文用例名**双重编码**，`-rf` 的 nodeid **有损**，
  只能按 `classname + name` 从 junit 重建（与本仓 memory 口径一致）。
- 强制 UTF-8 stdout（`stream.reconfigure`），避免 Windows 默认 GBK 下 `print` 中文把整步堵死。

### 2.2 受控实验：故意引入新红 → 报警 → 还原（任务书要求的证据）

在 `_r40tmp/gate_demo/` 建了一个**最小可复现套件**（不污染主仓），完整五步实录：

| 步骤 | 动作 | 结果 | 退出码 |
|---|---|---|---|
| A | 迷你套件（1 红 `test_known_red` + 1 绿）→ 生成基线 | 写入基线 1 条 | 0 |
| B | 用**同一份 junit** 复跑门 | `新增打红 0 条 ⇒ 通过` | **0** |
| C | **故意追加** `test_introduced_red`（`assert 1 == 2`） | pytest `2 failed, 1 passed` | — |
| D | 门跑新 junit | `新增打红 1 条 ⇒ 阻断（退出码 1）`；精确点名 `test_introduced_red` | **1** |
| E | **还原**（删掉故意引入的红）→ 复跑 | `新增打红 0 条 ⇒ 通过` | **0** |

关键片段（步骤 D，真实输出）：

```
基线门报告：基线 1 条 ｜ 本次打红 2 条（硬） + 0 条（软）｜ 新增打红 1 条
新增     tests.test_demo::test_introduced_red        AssertionError: 故意引入的新回归
基线内    tests.test_demo::test_known_red           AssertionError: 存量欠账

基线外新增打红（视为回归）：
   ! tests.test_demo::test_introduced_red   ← AssertionError: 故意引入的新回归

判据：新增打红 1 条 ⇒ 阻断（退出码 1）
```

**结论**：门的三态都正确——**只拦新增**（步骤 D 只点了新引入的那条，存量红被正确判为「基线内」放行），
**还原即绿**（步骤 E），**基线态恒绿**（步骤 B）。受控套件的临时红**已全部删除**，主仓 `tests/` 未受影响。

### 2.3 【重要发现】本仓基线文件的「身份格式失配」缺陷（已在本脚本内修复）

**现象**：用真实 e2e junit 复验时，`tests/ci_baseline_failures.txt` 里的 12 条记录**一条都匹配不上**。

**根因**：基线文件里部分记录是 **Python 转义形态**，而 junit 写出的是**原始汉字**：

```
基线文件里：  tests.e2e.test_e2e_chain::test_duan_run[E\u9636\u6bb5_L3L4\u539f\u751f\u8bed\u6cd5/E4_...]
junit 里：    tests.e2e.test_e2e_chain::test_duan_run[E阶段_L3L4原生语法/E4_L4_沙箱隔离验证.light]
```

两边做集合差**永不相交** ⇒ 这 12 条会被**永久误报为「新增打红」**，
⇒ **CI 回归闸门恒红**。这与本仓 memory 记录的「*CI run 182 = failure，基线已过期*」现象**完全吻合**
（并非基线真的过期，而是**身份格式失配**导致基线整体失效）。

**修复**：比较前对**两侧**都做归一化 `norm_key()`（`unicode_escape` 解码；仅对含反斜杠的串做，失败则原样返回）：

```python
def norm_key(key: str) -> str:
    if not key or '\\' not in key:
        return key
    try:
        return key.encode('latin-1', 'backslashreplace').decode('unicode_escape')
    except Exception:
        return key
```

**效果（真实 e2e junit 复验，修复后）**：那 12 条**全部被正确识别**——其中
4 条仍红被正确判为**「基线内」**（不再误报），另 8 条本机**被跳过（SKIP）**，
被单独列为「被跳过」而不是「已转绿」（见 §2.5）。

同时 `--write-baseline` 生成的新基线**只写原始字符形态**，并在文件头明确
「**不要**写 `\uXXXX` 转义形态」，从源头堵住复发。

> ⚠️ 未修改 `tests/ci_baseline_failures.txt` 与 `tools/ci/check_regression.py`：
> 前者是既有基线快照（改动应随一次真实的转绿/入账发生），后者是 CI 在跑的脚本。
> **建议**：后续用 `--write-baseline` 在 CI 上重新生成一次基线并提交，
> 即可让 `tools/ci/check_regression.py` 这条恒红也一并消除（**属另一 PR 范围，本任务不擅动**）。

### 2.4 【第二个发现】SKIP ≠ 转绿：基线门不能把「跳过」当「修好了」

**现象**：修复身份格式后重跑真实 e2e junit，最初把 8 条基线条目报成了「已转绿」。

**真因**：本机 `.venv` 里 `pandas / matplotlib / sklearn / sympy / numpy` **全部缺失**，
那些用例内部 `pytest.skip()` 掉了。junit 里它们是 `<skipped/>` 而非 `<failure/>`，
所以不在「打红清单」里；而旧实现用 `fixed = 基线 − 本次打红` 计算，
**SKIP 的条目被误算成「已转绿」**。

**危害**：使用者看到「8 条已转绿，请刷新基线」，一执行 `--write-baseline`，
就把这 8 条真实欠账**静默从基线里删掉**了 —— 之后 CI 真跑起来（库可见、用例真执行）
会重新打红，而基线里已经没它们，**直接造成假回归报警**。

**修复**：junit 采集阶段额外收集 `skipped` 集合；`fixed` 改为
`基线 − 本次打红 − 本次跳过`；并新增「被跳过」独立小节 + 「勿据此刷新基线」告警：

```
以下基线条目本次**被跳过（SKIP，未真正执行）**——既非转绿也非回归，**请勿据此刷新基线**：
   ~ tests.e2e.test_e2e_chain::test_duan_compile_and_run_product[L3_domain/demo3_math.light]
   ~ tests.e2e.test_e2e_chain::test_duan_run[L4_python/demo5_sklearn_iris.light]
   ...
   ℹ️ 常见原因：依赖的第三方库/外部程序在当前机器不可见，用例 `pytest.skip()` 掉了。
```

JSON 报告同步新增 `skipped_in_baseline` 字段，便于 CI 侧后续加工。

### 2.5 【使用注意】基线是**平台相关**的

用 Windows 本机全量 e2e junit 跑门，会得到 `新增打红 28 条`。这**不是本轮回退**，而是：

- `tests/ci_baseline_failures.txt` 的 12 条是**在 FreeBSD CI 宿主上**生成的，内容全是
  `E4_L4_沙箱隔离`/`demo3_math`/`all_in_one_demo`/`demo2_pandas_csv`/`demo3_matplotlib`/`demo5_sklearn`
  这些**第三方库缺失类**欠账（基线文件头的「快照汇总 collected=1203 failures=12」即其出处）。
- Windows 本机同一批用例的**结局不同**：本机 `.venv` 里 `pandas/matplotlib/sklearn/sympy/numpy`
  **全部缺失**，其中 8 条**被 SKIP**（→ §2.4，正确报为「被跳过」）、4 条**真失败**
  （`all_in_one_demo`/`demo2_pandas_csv` 各两条腿 → 正确判为「基线内」）。
- 与此同时，本机因 **L-155 词法残口**（`basic.light` / `hello.light` / `class_*.light` /
  `test_L068.light` / `_test_nested_closure.light` / `Z7` / `L0_core/06` / `L3_domain/demo1_sql` /
  `calculator.light` 等）**额外红 28 条** —— 这批**不在基线内**，在 FreeBSD CI 上是否红**需在 CI 上实测**，
  本机结论不能直接外推。

⇒ **口径**（与本仓 memory 一致）：

| 场景 | 正确用法 |
|---|---|
| CI（FreeBSD 宿主） | `check_ci_baseline.py --junit .ci/report.xml` —— 与基线**同平台**，判据有效 |
| 开发机（Windows） | 用 `--soft-classname` 屏蔽平台差异，或**改用「相对 HEAD 的新增打红 = 0」**口径（先在同一台机器上对 HEAD 采一次基线） |

**接入 CI 的建议位置**：在既有回归步骤之后追加一步（CI 主机与基线同平台）：

```yaml
- name: 基线外打红门（只拦新增回归）
  run: python3 scripts/check_ci_baseline.py --junit .ci/report.xml --soft-classname 'tests.test_*'
```

（`--soft-classname 'tests.test_*'` 与 `tools/ci/check_regression.py --soft-classname` 同口径，
用于把某类用例降级为「只报不拦」。）

### 2.6 【第三个发现】交付脚本被 `.gitignore` 静默吃掉

**现象**：脚本写好后 `git status` 里**看不到它**。

**根因**：`light-merge/.gitignore:183` 有一条通用调试脚本规则 `check_*.py`，
恰好把本轮要求的交付文件名 `scripts/check_ci_baseline.py` **整体忽略**。

**危害**：脚本在干净克隆里**根本不存在** ⇒ CI 步骤引用它会报文件缺失，门禁整条失效；
而且因为「本地跑得好好的」，这个问题**不会被本地测试发现**。

**修复**：按本仓**既有惯例**加一条精确豁免（`.gitignore:212`）。仓里早有同类先例
——`!tools/ci/check_regression.py`（L208）就是为同一个 `check_*.py` 坑加的：

```gitignore
# CI 基础设施：必须入库，豁免上面的通用忽略规则
# （check_*.py 会误伤闸门脚本，*.txt 会误伤基线清单）
!tools/ci/check_regression.py
!tests/ci_baseline_failures.txt
# 第40轮任务4 交付的「基线外打红」本地/CI 门：同样被上面的 `check_*.py` 吃掉。
# 漏了这条豁免，脚本在干净克隆里根本不存在，门禁整条失效（与 check_regression.py 同坑）。
!scripts/check_ci_baseline.py
```

**验证**：`git check-ignore -v scripts/check_ci_baseline.py` 现在命中 `!` 豁免规则；
`git status --short` 能看到 `?? scripts/check_ci_baseline.py` ✅

> 对比：`lightharness/scripts/互举反跑.py` 与 `互举反跑基线.json` 在 lightharness 仓内
> **未被任何规则忽略**（`git status` 正常显示 `??`），无需豁免。
> ⚠️ 若后续把基线门挪到别的目录，注意同名 `check_*.py` 规则会再次生效。

---

## 3. 子任务 4.2：互举反跑脚本正式化

### 3.1 脚本定位与用法

**位置**：`lightharness/scripts/互举反跑.py`；基线：`lightharness/scripts/互举反跑基线.json`

**为什么需要它**：R25~R39 每轮都靠**临时探针**（`_antirun_r2x_*.py`）手工跑「light 编译器能否吃下
lightharness 全树」，没有正式件、无法回归。本脚本把它固化。

```
python scripts/互举反跑.py                       # 常规：与基线对比
python scripts/互举反跑.py --update-baseline      # 首次接入 / 收口刷新基线
python scripts/互举反跑.py --roots src examples   # 只跑部分根目录（省时）
python scripts/互举反跑.py --json reports/反跑.json --report reports/反跑.txt
python scripts/互举反跑.py --warn --detail        # 只警告 + 打印全部失败摘要
```

**判据**：`0 新增解析失败` = 绿（rc=0）；有新增 = 红（rc=1）；环境错误 rc=2；
基线内失败 → 不拦；基线里失败但本次通过 → 报「已修复」（提示刷新基线）。

**实现要点**：
- 扫描 `src / stdlib / examples / tests` 全部 `.light`（跳过 `.git`/`__pycache__`/`.venv`/`node_modules` 等）。
- 对每个文件用 light-merge 的 `Lexer().tokenize` + `LightParser().parse`，
  结果状态分四类：`OK / LEX（词法失败）/ PARSE（语法失败）/ READ（读取失败）`。
- 基线记录**编译器指纹**（`light_merge_rev` + 版本）与每条失败的 `digest`（消息摘要），
  因此**编译器换代导致的信息变化**也能被区分出来（不是只有「成败」两态）。
- 编译器路径来自 `LIGHT_MERGE` 环境变量（默认本机 `G:\dswork\duan-light-merge\light-merge`）。

### 3.2 验证证据（本轮实测）

```
==============================================================================
互举反跑：lightharness 全树 .light × light 编译器可解析性
==============================================================================
编译器：light-merge d8cf337d+dirty(src)（光明 v7.0.0）   roots: src stdlib examples tests
待检：644 个 .light 文件
耗时 25.8s ｜ 可解析 640 ｜ 词法失败 0 ｜ 语法失败 4 ｜ 读取失败 0

基线：scripts\互举反跑基线.json（4 条，生成于 2026-09-16 15:18:36，标定编译器 d8cf337d+dirty(src)）
对比：新增失败 0 ｜ 基线内仍失败 4 ｜ 已修复 0 ｜ 信息变化 0

判据：✅ 0 新增解析失败 —— 绿
```

**基线内 4 条（存量欠账，非本轮回退）**：

| 文件 | 状态 | 报错要点 |
|---|---|---|
| `examples/test_L101.light` | PARSE | L8 `「回调」是保留关键字，不能直接作为语句开头` |
| `examples/test_L143.light` | PARSE | L8 `「作用域」是保留关键字，不能直接作为语句开头` |
| `examples/test_R22_嵌入关键字冗余验证.light` | PARSE | L19 `期望'为'或'等于'，但得到 「了」` |
| `examples/test_R26_词首并入混合.light` | PARSE | L59 `期望 冒号「:」，但得到 关键字（附近: '返回'）` |

> 这 4 条都是**测试用例刻意构造的边界样本**（用来钉住保护表边界），
> 与 L-155 家族同源：属**已知词法边界**，不是编译器新退化。
> 脚本把它们写进基线 ⇒ **将来修好会报「已修复」并提示刷新基线**，形成闭环。

---

## 4. 铁律核对

| 铁律 | 核对结果 |
|---|---|
| 只新增脚本文件，不修改 `src/` 与 `examples/` | ✅ 新增 `light-merge/scripts/check_ci_baseline.py`、`lightharness/scripts/互举反跑.py` + 基线 JSON；**`src/`、`examples/` 零改动**。<br>⚠️ **唯一额外的非脚本改动**：`light-merge/.gitignore` +1 条精确豁免（`!scripts/check_ci_baseline.py`）——不做这一步，脚本会因 `check_*.py` 通用规则**不入库**、门禁整条失效（§2.6）。仓内已有同类先例 `!tools/ci/check_regression.py`。 |
| 基线门验证必须含「故意引入新红→报警→还原」证据 | ✅ §2.2 五步实录（含真实退出码 0→0→1→0） |
| 互举反跑必须输出可读报告（JSON+文本），0 新增解析错误为绿 | ✅ 支持 `--json`/`--report`/`--detail`；实测 **0 新增** |
| 脚本不依赖未安装的三方库（标准库即可） | ✅ 只用 `argparse/fnmatch/glob/json/os/subprocess/sys/tempfile/xml.etree`（门）与 `argparse/hashlib/json/os/re/subprocess/sys/time`（反跑） |
| PowerShell 旧版不支持 `&&`；用 `;` + `$LASTEXITCODE` | ✅ 两脚本均为纯 Python 入口，不依赖 shell 串联；CI 步骤按 `;`/单命令写法给出 |

---

## 5. 已知限制与后续建议

1. **基线文件身份形态**：`tests/ci_baseline_failures.txt` 仍是转义形态（本脚本已能在比较时归一化，
   但 `tools/ci/check_regression.py` 不能）。建议在 CI 上用 `--write-baseline` 重生成并提交。
2. **平台相关基线**：见 §2.5。跨平台使用务必配合 `--soft-classname`，或改用「相对 HEAD 新增 = 0」口径
   （先在同一台机器上对 HEAD 采一次基线）。
3. **SKIP 条目不是绿**：门已把「被跳过」单独列出并告警；但**基线本身**仍可能包含会在某平台 SKIP 的条目。
   正确做法是**让基线只在其生成平台上使用**（CI 上用 CI 的基线、本机用本机的基线）。
4. **反跑脚本的编译器指纹**：工作树有未提交改动时显示 `d8cf337d+dirty(src)`。基线标定了指纹并会提示变化，
   但**不会因此判红**（避免正常开发被指纹挡住）。
5. **未接 CI 的自动触发**：本轮只交付脚本与接入位置建议；实际写入 `ci.yml` 需与 CI 负责人确认步骤顺序。

---

## 6. 附：本轮验证命令清单（可照抄复现）

```bash
# —— 4.1 门：受控实验（在临时迷你套件上）——
cd G:/dswork/duan-light-merge/_r40tmp/gate_demo
G:/dswork/duan-light-merge/light-merge/.venv/Scripts/python.exe -m pytest tests -q \
    --junitxml=run1.xml                                   # 基线态：1 红 1 绿
G:/dswork/duan-light-merge/light-merge/.venv/Scripts/python.exe \
    G:/dswork/duan-light-merge/light-merge/scripts/check_ci_baseline.py \
    --junit run1.xml --baseline base.txt --write-baseline  # 生成基线
# 追加 test_introduced_red 后：
... -m pytest tests -q --junitxml=run2.xml                 # 2 红
... check_ci_baseline.py --junit run2.xml --baseline base.txt   # rc=1，点名新红
# 删除 test_introduced_red 后：
... -m pytest tests -q --junitxml=run3.xml
... check_ci_baseline.py --junit run3.xml --baseline base.txt   # rc=0 绿

# —— 4.1 门：真实 e2e 复验 ——
cd G:/dswork/duan-light-merge/light-merge
./.venv/Scripts/python.exe -m pytest tests/e2e/test_e2e_chain.py -q \
    --junitxml=G:/dswork/duan-light-merge/_r40tmp/e2e_full.xml
./.venv/Scripts/python.exe scripts/check_ci_baseline.py \
    --junit G:/dswork/duan-light-merge/_r40tmp/e2e_full.xml

# —— 4.2 反跑 ——
cd G:/dswork/duan-light-merge/lightharness
../light-merge/.venv/Scripts/python.exe scripts/互举反跑.py
../light-merge/.venv/Scripts/python.exe scripts/互举反跑.py --update-baseline   # 收口刷新
```

> ⚠️ 本机用 Git-Bash 时，传给**原生 Windows Python** 的路径必须写 `G:/...` 形式；
> 写成 `/g/...` 会被 MSYS 路径转换弄成 `G:\g\...`（实测踩坑）。
> 控制台出现 `shell-runtime-bash-env.sh: line 3: dirname: command not found` 是**环境噪音**，命令本身正常。
