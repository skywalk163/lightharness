# 任务1 交付报告 · R61 拆分提速量化 + 积木库裸路径清障

> 轮次：R61（拆分后首轮全量与存量红清零轮）· 任务1
> 执行：WorkBuddy（分发执行 agent）· 基线链：R60 门 **201545**（4 红）
> 日期：2026-09-18 · 未 commit / 未 push（留路M 统一收口）

---

## 0. 结论速览

| 子项 | 判据 | 结果 |
|---|---|---|
| 1A 裸路径清障 | 全仓 0 处**裸运行期**路径引用（测试/脚本/CI） | ✅ **0**（修 5 文件 + 删 2 文件；纯注释 34 处登记不动） |
| 1B 拆分提速量化 | 出 sync 体量 / 用例数 / 耗时对比 | ✅ 报告见 §2（**含一处反直觉重大发现**） |
| 1C 全量前自检 | TestBitwiseInBlocks 2 passed（不红）；互举反跑 0 新增 | ✅ 2 passed + **0 新增解析失败** |
| 双端定向 | 本机 + 0.82（py3.12） | ✅ 全绿（本机 105 passed / 0.82 69+68 passed，双分支） |

**两条必须上行的发现：**

> 📌 **后续（同日）**：2 条被删的积木库流水线**已按用户指示迁入 lighting 仓**（gitea/github/gitcode 三平台），
> 并顺带修掉迁移暴露的 4 类拆分遗留缺陷；端到端门禁 **24/24 全绿**。
> 详见 **`lightharness/_task1_R61_lighting_CI迁移.md`**（⚠️ lighting 仓需单独提交）。

1. **⚠️ 拆分把文件数砍掉 87%，但 sync 包体积反而涨了 291%**（30.71MB→120.24MB）。
   与积木库无关——真因是 9-16 之后两侧新增的**探针中间产物 / 构建产物**：
   `LM _taskR11B_test_*` **143.73MB** + `LH docs/` **93.55MB** + 媒体归档 29.34MB ≈ **266MB**。
   ⇒ **本轮的实际提速来自「少打 37047 个文件」，不是「少传字节」。** 详见 §2.1。
2. **⚠️ R60 全量（201545）并不是在拆分后的树上跑的**：0.82 的 R60 副本仍含 `积木库/`（37047 文件），
   拆分提交 `be178387` 发生在 R60 路M sync **之后**。⇒ **R61 才是真正的「拆分后首轮全量」**，
   对拍 201545 属**跨树对比**，需注意这一口径。详见 §5.3。

---

## 1. 任务1A：积木库裸路径全仓排查

### 1.1 判定口径
- **裸运行期路径** = 代码/配置里**真正参与文件系统访问**的 `积木库/...` 字面量（未走 `LIGHT_BLOCKS_DIR`）。
- **纯注释/文档** = 说明性文字，不动代码，仅登记。

### 1.2 运行期引用 —— 全部处置（5 改 + 2 删）

| # | 文件:行 | 原形态 | 拆分后后果 | 处置 |
|---|---|---|---|---|
| 1 | `tests/test_pure_light_hook.py:224`→**230**（+新增 skip 235-239） | `_BLOCKS = os.path.join(_ROOT, "积木库")` → L253 `glob` | **静默假绿**：目录不存在 ⇒ glob 空集 ⇒ `缺口==[]` 恒成立，判据**空转通过**（R60 全量 7871 用例里这条就是假绿） | 改 `os.environ.get("LIGHT_BLOCKS_DIR") or _ROOT/积木库`；**路径不存在时 `pytest.skip`**（不再空转） |
| 2 | `.gitea/workflows/ci.yml:274-279` | `python 积木库/评估/ci_eval.py --并发 8`（「积木库门禁」step，硬判） | **每次必红**（路径不存在），且掩盖真实回归信号 | **删除该 step**，原位留 11 行说明（迁移去向 + 3 份原文取回命令） |
| 3 | `.github/workflows/eval.yml`（整文件） | paths 过滤 `积木库/**` + `run: python 积木库/评估/ci_eval.py` + artifact `积木库/评估/报告/` | 该流水线**只服务积木库**，必然红 | **删除文件**（blob `fb98e3ef`，`git show fb98e3ef:.github/workflows/eval.yml` 可取回） |
| 4 | `.gitcode/workflows/eval.yml`（整文件） | 同上（EulerOS 版，`python3 积木库/评估/ci_eval.py` + 读 `积木库/评估/报告/ci_eval.json`） | 同上 | **删除文件**（blob `b710e307`） |
| 5 | `blocks_pkg/打包数据.py:10` | `_SRC = os.path.join(_ROOT,'积木库')` | 运行即 `SystemExit('找不到 积木库')` | 新增 `_源目录()`：`LIGHT_BLOCKS_DIR` → `../lighting` → `./积木库`（兼容旧树），实测命中 `G:\dswork\duan-light-merge\lighting` ✅ |
| 6 | `blocks_pkg/light_blocks/cli.py:20-36` | 定位顺序 `LIGHT_BLOCKS_LIB` → 包内 `_data/积木库` → 向上找 `积木库` | 开发模式回退失效（不硬红，但链路断） | 抽出 `_是库(p)`；定位链补 `LIGHT_BLOCKS_DIR`（第 2 位），报错文案更新 ✅ |
| 7 | `pyproject.toml:72 / 78 / 84` | `packages.find.include` 含 `积木库*`；`exclude` 4 条 `积木库/...`；`package-data` 键 `"积木库"` | 构建配置指向不存在的包（不硬红，但 wheel 内容声明失真） | 三处删除；TOML 复验合法 ✅（include=`['src*','cli*','stdlib*','antlrparser*']`，package-data 键=`['*','stdlib']`） |

**顺带修正**（同一拆分主题的陈旧文案，非路径）：
- `.github/workflows/ci.yml:22` 去掉「+ 积木库门禁」；`:34` 改为 eval.yml 移除说明。
- `.gitea/workflows/ci.yml:125` 注释「测试侧与积木库门禁硬依赖」→「测试侧硬依赖」（依赖包本身保留：pypinyin 16 / opencc 9 / lunardate 11 / aiohttp 10 / cryptography 58 处仍被 tests·stdlib·examples 引用）。

### 1.3 纯注释 / 文档引用 —— 登记不动（34 处）

| 位置 | 处数 | 说明 |
|---|---|---|
| `src/{code_generator,lexer,parser_stmt}.py` | 5 | 注释里引用积木库样本文件（如 `积木库/blocks_v5/网络/HTTP方法判断.light`）作为设计判据来源 |
| `stdlib/文件系统.light` | 4 | 门面承诺注释（「积木库/工具/列目录文件.light 要的 文件列表」） |
| `tests/*.py`（test_codegen / test_feature_core_light / test_llm_client_light / test_l0_char_aliases… / test_lexer_compound_safe_alignment） | 8 | docstring 引样本文件 |
| `light.egg-info/{SOURCES.txt,top_level.txt,PKG-INFO}` | 构建产物 | 陈旧清单，随下次 build 自动刷新（本次未动） |
| `_r58_lexer_base.py`、`.scratch/lexer_*.py` | 备份/草稿 | 未跟踪 |
| `CHANGELOG.md`、`任务书/**`、`第三/四轮留档/**`、`自测报告_*.md`、`*_交付报告.md` | 历史文档 | 按任务书「纯文档登记即可」 |
| **`lightharness/` 侧** | **0 运行期** | grep `scripts/ tests/ src/ stdlib/ cli/ tools/ .gitea/ .github/` **零命中**；仅 `stdlib/文件系统.light` 注释 + `docs/历史存档/R5x探针` + lexer 快照注释 |

### 1.4 残留（非路径 / 环境级）—— 已登记，未改

| 项 | 说明 | 建议 |
|---|---|---|
| `.gitea/workflows/ci.yml:359` `--mark 闸门与积木库` | **计时标签**（非路径）；改名会动 CI 计时口径输出 | 留主 agent 裁决（可选改成 `--mark 闸门`） |
| `light-merge/.venv/Lib/site-packages/__editable___light_7_0_0_finder.py` | 陈旧 editable 安装映射，仍把 `积木库` / `积木库.blocks_v5` 等 180+ 子包指向不存在的路径。**未跟踪**，不参与 0.82 门禁 | 本机可 `pip install -e .` 刷新（本轮刻意未动，避免扰动本机 venv） |
| `lighting/archive/*.py`、`lighting/export_blocks.py` | 引用 `积木库_导出_v*.json` / `积木库/评估/...` —— 但这些文件在 **lighting 仓内**，属正常的「仓内自引用」（该仓根即原 `积木库/` 内容） | 不动 |
| 本机 3 个已解压目录 `2026-09-11-d613c31d/`、`_taskR11B_test_*/`、`demo_video/` | 见 §2.1，**是 sync 体量问题不是路径问题** | 见 §6.2 |

**1A 判据达成**：`grep` 复扫（代码+配置面，排除历史文档/探针）后，**运行期裸路径 = 0**。
唯一允许残留的运行期字面量是 `blocks_pkg` 的**包内数据目录名** `light_blocks/_data/积木库`
（wheel 内部布局名，非仓库路径，`_是库()` 会校验其含 `组合.py`）与 `blocks_pkg` 的「旧路径兼容」末位回退。

---

## 2. 任务1B：拆分提速量化

### 2.1 sync 打包体量（**同函数、同排除表**的严格口径）

- 测量函数：直接调用 `lightharness/scripts/同步0.82.py::build_tarball`（`compresslevel=1`；排除 10 个目录 + 5 类后缀；`--with-git` 未开）。
- 「拆分前」实测：解析历史包 **`G:\dswork\duan-light-merge\r43_sync.tar.gz`**（2026-09-16 22:36，拆分前最后一次同类打包）的成员清单——**这是真实测量，不是引用任务书数字**。

| 类别 | 拆分前（R43 包 · 09-16） | 拆分后（R61 实测 · 09-18） | 变化 |
|---|---:|---:|---:|
| `light-merge/积木库/` | 37 047 文件 / 23.89 MB | **0 / 0** | **−37 047 / −23.89 MB** |
| `light-merge/_taskR11B_test_*/` | 0 / 0 | **245 / 143.73 MB** | +245 / **+143.73 MB** |
| `light-merge/` 其余 | 2 645 / 61.94 MB | 2 652 / 91.86 MB | +7 / +29.92 MB |
| `lightharness/docs/` | 20 / 0.65 MB | **731 / 93.55 MB** | +711 / **+92.90 MB** |
| `lightharness/` 其余 | 1 485 / 24.71 MB | 1 681 / 42.72 MB | +196 / +18.01 MB |
| **未压缩合计** | **41 197 文件 / 111.19 MB** | **5 309 文件 / 371.86 MB** | **−35 888 / +260.67 MB** |
| **tar.gz 实测** | **30.71 MB** | **120.24 MB**（126 083 673 B） | **+291%** |
| 打包耗时 | —（未留档） | **15.0 s**（冷盘首测 26.8 s） | — |

> R61 单次权威读数：**5 309 文件 / 120.24 MB / 15.0 s**（`lightharness/_r61_sync_measure.py`）。
> 拆出仓体量：`lighting/` = **38 340 文件 / 90.28 MB**（不再计入 sync）。

**结论（反直觉，必须上行）**：
- **文件数 −87.1%**（41 197 → 5 309）——sync 的 **walk / tar / 解压** 三段工作量确实大幅下降；
- **包体积 +291%**（30.71 → 120.24 MB）——因为 9-16 之后两侧积累了 266 MB 中间产物：
  - `light-merge/_taskR11B_test_*/**` **143.73 MB**（49 个目录 × `main.ll` 4.12 MB + `main.o` 2.58 MB，mtime 从 09-10 一直刷新到 **09-18 10:59**，即 R59 还在往里写）
  - `lightharness/docs/历史存档/R5{7,8,9}探针/**` **92.90 MB**（单个 `_r58_tok_A_detail.txt` 就 **49.91 MB**；另有 10 × 2.83 MB 的 `*_tok_*.tsv`）
  - `light-merge` 媒体/归档 3 文件 **29.34 MB**（`demo_video/*.mp4` 12.70 MB、`2026-09-11-d613c31d/output/.../lv_full.tar.gz` 10.85 MB、`light_verify.tar.gz` 5.79 MB）
  - 这三类占未压缩总量 **266.0 / 371.9 = 71.5%**

⇒ **「拆分提速」在本轮的实际收益是「文件数量级下降」（对 walk/tar/解压/远端落盘 inode 友好），
而不是「传输字节下降」；后者反而被中间产物吃掉了。** 想真正压 sync 时间，下一步该清 §6.2 清单。

### 2.2 pytest 用例收集数（本机 `--collect-only`，不跑全量）

| 口径 | 用例数 | 备注 |
|---|---:|---|
| 本机 collected（全量） | **8 136** | `pytest tests/ --collect-only -q` |
| 本机 deselected（`-m "not slow"`） | 303 | fast 口径排除 |
| **本机 fast 收集数** | **7 833** | 与 R60 门同 marker 口径 |
| R60 门 0.82 fast 实跑数 | 7 871 | 基线 201545 `totals.total` |
| 差值 | **−38（−0.48%）** | 0.82（FreeBSD/py3.12）vs 本机（Windows/py3.13）的**存量平台口径差**：R59 基线 7 854 亦为 0.82 口径，本机历轮同向偏低 |

→ 拆分**不改变用例数**：积木块用例只集中在 `test_feature_core_light.py::TestBitwiseInBlocks`
（2 条）与 `test_pure_light_hook.py`（1 条），且前者拆分后**空转**（文件不存在即 `return`），
故「拆积木库」对 pytest 本体耗时的贡献 **≈ 0**。

### 2.3 全量耗时（口径对齐）

| 数据点 | 用例数 | pytest 自报 `duration_sec` | 脚本级总耗时 | 口径 |
|---|---:|---:|---:|---|
| R57 口径 | 7 806 | — | **477 s** | 0.82 py3.12 fast（R55 后首次 3.12 并行） |
| **R60 门（201545）** | **7 871** | **390.1 s** | **408 s**（任务书口径） | 0.82 py3.12 fast，**树仍含积木库** |
| R61（本轮） | 待测 | — | **待路M 唯一一次全量** | 0.82 py3.12 fast，**拆分后首轮** |

> 基线文件 `lightharness/reports/082_lightmerge基线_latest.json` 实测：`totals = {total:7871, passed:7782, failed:4, error:0, skipped:74, xfailed:11, duration_sec:390.146}`。
> **口径差异提示**：R57 的 477 s 是 7 806 用例（R55/R56 期），R60 的 390 s 是 7 871 用例——**用例多了 65 条、耗时反而快 87 s**，主因是 R56 的 py3.12+xdist 并行口径定型，两者不可直接当作「提速」比。

### 2.4 提速归因结论（回答任务书的核心提问）

| 环节 | 拆分带来的影响 | 定性 |
|---|---|---|
| sync 打包（walk+tar） | 文件数 41 197 → 5 309（−87.1%）；耗时实测 15.0 s | **主要收益**（数量级） |
| sync 传输（SFTP） | 字节 30.71 → 120.24 MB（**+291%，被中间产物吃掉**） | **负收益**（需清理才转正） |
| 远端解压 | 少展开 35 888 个 inode | **主要收益** |
| 全仓扫描（门禁/断言质量/bootstrap 率等 5 道 `--root .`） | 少扫 37 047 个 `.light` | **收益**（但扫描器本已按后缀过滤，量级有限） |
| **pytest 本体** | 用例数不变；积木块用例本就空转 | **≈ 0** |

---

## 3. 任务1C：全量前定向自检

| 检查项 | 命令 | 结果 |
|---|---|---|
| `TestBitwiseInBlocks` 无 `LIGHT_BLOCKS_DIR` | `pytest "tests/test_feature_core_light.py::TestBitwiseInBlocks" -q` | **2 passed**（0.86 s，空转跳过、不红）✅ |
| 同上·**带** `LIGHT_BLOCKS_DIR=…/lighting` | 同上 + env | **2 passed**（20.69 s，真编译真跑）✅ |
| 互举反跑 677 文件 | `python scripts/互举反跑.py` | **新增失败 0**（rc=0）✅ 可解析 675 / 词法失败 0 / 语法失败 2（均为基线内存量） |

互举反跑附加信息：基线 `scripts/互举反跑基线.json`（4 条，2026-09-16 标定，编译器 `d8cf337d`）
→ 本轮「新增失败 0 ｜ 基线内仍失败 2 ｜ 已修复 2（`examples/test_R22_嵌入关键字冗余验证.light`、`examples/test_R26_词首并入混合.light`）」。
**未刷新基线**（基线刷新属路M 收口动作，且需用户裁决），已登记。

---

## 4. 双端定向验证

### 4.1 本机（Windows / py3.13 / `light-merge/.venv`）

| 目标 | 结果 |
|---|---|
| `tests/test_pure_light_hook.py::test_积木库导入的名字必须在纯光明门面的导出面内`（无 env） | **1 skipped**（1.20 s）——skip 分支生效，不再空转假绿 ✅ |
| 同上（`LIGHT_BLOCKS_DIR=…/lighting`） | **1 passed**（25.43 s）——**真实覆盖恢复**，`缺口==[]` 真判 ✅ |
| 受影响文件定向回归：`test_pure_light_hook.py` + `test_capture_encoding_guard.py` + `test_version_single_source.py` + `test_link_libs_guard.py` + `test_feature_core_light.py` | **105 passed, 1 skipped, 1 xfailed**（10.09 s，rc=0）✅ |
| `blocks_pkg/打包数据.py::_源目录()` | 无 env → `G:\dswork\duan-light-merge\lighting`（含 `组合.py`）✅；有 env 同上 ✅ |
| `blocks_pkg/light_blocks/cli.py::积木库路径()` | 有 env → lighting ✅；无 env → `RuntimeError: 找不到积木库目录：请设置 LIGHT_BLOCKS_DIR…` ✅ |
| `pyproject.toml` | `tomllib` 解析合法 ✅ |
| `.gitea/workflows/ci.yml` / `.github/workflows/ci.yml` | `yaml.safe_load` 合法 ✅（steps 20 / 34） |

### 4.2 门禁平台 0.82（FreeBSD / `/usr/local/bin/python3.12`）

做法：复用 `同步0.82.py::connect()`，**只上传改动的那 1 个测试文件**到已同步副本（`/tmp/r44-20260918-202728`），
用 py3.12 跑定向（不重同步、不跑全量）。

| 目标 | 结果 |
|---|---|
| `tests/test_pure_light_hook.py`（该副本**仍含积木库**，走「目录存在」真跑分支） | **69 passed, 1 xfailed**（6.24 s，rc=0）✅ |
| 同上 + `LIGHT_BLOCKS_DIR=/tmp/__no_such_blocks__`（走 skip 分支） | **68 passed, 1 skipped, 1 xfailed**（1.24 s，rc=0）✅ skip 文案正确落盘 |
| `tests/test_feature_core_light.py::TestBitwiseInBlocks` | **2 passed**（2.71 s，rc=0）✅ |

> ⚠️ 0.82 的「跳过」分支必须用**显式假路径**触发（因为该副本仍有 `积木库/`，见 §5.3）。
> 拆分后真树上的 skip 由 **路M 的 R61 全量**覆盖（届时 `LIGHT_BLOCKS_DIR` 未设、`积木库/` 不存在 ⇒ 该判据 skip 1 条）。

---

## 5. 与任务书红线/预期的偏差 —— 如实声明

| # | 偏差 | 说明 |
|---|---|---|
| 5.1 | **修复范围超出 1A 字面要求**：任务书只说 `grep -rn "积木库" light-merge/`；实际做了 (a) 补查隐藏目录 `.gitea/.github/.gitcode`（ripgrep 默认跳过隐藏目录，首次 grep 漏了 3 个 CI 文件），(b) 扩到 `lightharness/`（结果 0 处），(c) 修 `blocks_pkg` / `pyproject.toml`（任务书未列，但不修则「0 处裸引用」判据不成立） | 方向更严，非放水 |
| 5.2 | **删除了 2 个 CI 流水线文件**（`.github/workflows/eval.yml`、`.gitcode/workflows/eval.yml`）。任务书 §1A 允许「删除依赖」但未明示可删**整文件** | 理由：这两条流水线**只服务积木库**，行为 = 对不存在的目录跑门禁 ⇒ 恒红。**已按用户后续指示把三平台流水线迁到 lighting 仓**（含 gitea 原内联门禁段），见 `_task1_R61_lighting_CI迁移.md`；删除仍可逆（`git show fb98e3ef:…` / `git show b710e307:…`） |
| 5.3 | **发现并上报口径瑕疵**：0.82 的 R60 副本 `ls -d …/light-merge/积木库` **存在**（94 条目，含 37 047 文件）⇒ R60 全量（201545，7 871 用例，4 红）是在**仍含积木库的树上**跑的，拆分提交 `be178387` 在其后。故 R61 对拍 201545 属**跨树对比**；也正是本轮标题「拆分后首轮全量」的事实依据 | 非我引入，但影响门判读，必须上行 |
| 5.4 | **R57 口径「42 283 文件 / 126.5 MB」未能复现** | 同函数实测 = 5 309 文件 / 120.24 MB；`git ls-files` 三仓 = 2 201 + 1 976 + 37 042 = 41 219。两个候选口径都不等于 42 283。故 §2.1 **改用可复现的 `r43_sync.tar.gz` 成员清单**做「拆分前」实测，并把任务书数字仅作参考、不参与结论 |
| 5.5 | 互举反跑「已修复 2 条（请刷新基线）」**未刷新基线** | 基线刷新 = 收口动作，归路M；且需用户裁决是否接受把 2 条从「基线内存量」转正 |
| 5.6 | `.gitea/workflows/ci.yml:359` 计时标签 `--mark 闸门与积木库` **未改** | 纯标签非路径；改名会动 CI 计时口径文本，留主 agent 裁决 |
| 5.7 | 本机 venv 装了 `pyyaml`（校验 CI YAML 语法用） | 附加依赖，不影响门禁；`.venv` 未跟踪 |
| 5.8 | **未 commit / 未 push / 未跑全量** | 遵守 §6 全局护栏（全量仅路M 1 次；本次只做定向，0.82 上未跑任何全量） |

---

## 6. 改动文件清单（行号级）与 路M 交接

### 6.1 `light-merge` 侧（8 个路径：6 改 2 删）

| 文件 | 行号 | 改动 |
|---|---|---|
| `tests/test_pure_light_hook.py` | 225-230（注释改 + `_BLOCKS` 改走 `LIGHT_BLOCKS_DIR`）、235-239（新增 `pytest.skip` 守卫） | 裸路径 → env 优先；不存在则 skip（消除空转假绿） |
| `.gitea/workflows/ci.yml` | 269-279（删除原 274-279 step，原位留说明注释）；125（注释文案） | 移除积木库门禁 step |
| `.github/workflows/ci.yml` | 22（注释）；34-36（替代原 34 的 eval.yml 说明） | 注释对齐 |
| `.github/workflows/eval.yml` | **整文件删除**（blob `fb98e3ef`） | 纯积木库流水线 |
| `.gitcode/workflows/eval.yml` | **整文件删除**（blob `b710e307`） | 纯积木库流水线 |
| `blocks_pkg/打包数据.py` | 1-34（docstring + 新增 `_源目录()` + `_SRC = _源目录()`） | 源目录改 env/`../lighting`/旧路径三级 |
| `blocks_pkg/light_blocks/cli.py` | 1-44（docstring + 新增 `_是库()` + 定位链补 `LIGHT_BLOCKS_DIR` + 报错文案） | 定位链补齐 |
| `pyproject.toml` | 71-82（`include` / `exclude` / `package-data` 三处去 `积木库`） | 构建配置对齐 |

`git diff --stat`（不含 2 个删除）：
```
 .gitea/workflows/ci.yml        | 24 ++++++++++++------------
 .github/workflows/ci.yml       |  6 ++++--
 blocks_pkg/light_blocks/cli.py | 24 ++++++++++++++++--------
 blocks_pkg/打包数据.py         | 28 ++++++++++++++++++++++++++--
 pyproject.toml                 |  4 +---
 tests/test_pure_light_hook.py  | 13 ++++++++++++-
 6 files changed, 71 insertions(+), 28 deletions(-)
```

### 6.2 建议进入 R61 路M / 下轮的「sync 体量治理」（本轮**只读统计，未清理**）
> ⚠️ 一律**未动**：personal-files 铁律 + 本轮范围外。仅登记供裁决。

| 目标 | 体量 | 说明 |
|---|---:|---|
| `light-merge/_taskR11B_test_*/`（49 目录） | 143.73 MB | 编译产物 `.ll/.o/.exe`；R59（09-18 10:59）还在写 ⇒ 建议加进 `同步0.82.py::EXCLUDE_DIRS` 或一次性归档 |
| `lightharness/docs/历史存档/R5{7,8,9}探针/*_tok_*.tsv / *_detail.txt` | 92.90 MB | 单文件 `_r58_tok_A_detail.txt` = 49.91 MB；探针产物本可移出打包面 |
| `light-merge/demo_video/*.mp4` + 2 个历史 tar.gz | 29.34 MB | 12.70 + 10.85 + 5.79 MB |
| 小计 | **266 MB / 71.5%** | 清掉后 sync 体量可回到 ~30 MB 量级，**匹配任务书预期的「个位数 MB」目标**（注：任务书预期 ~5000 文件 / ~10 MB，文件数已达标，体积需先治垃圾） |

### 6.3 `lightharness` 侧新增（探针，待路M 移档 `docs/历史存档/R61探针/`）

| 文件 | 用途 |
|---|---|
| `lightharness/_r61_sync_measure.py` | 1B 打包体量实测（复用 `同步0.82.build_tarball`） |
| `lightharness/_r61_082_targeted.py` | 0.82 定向验证（单文件上传 + py3.12 跑定向） |
| 本报告 `lightharness/_task1_R61_拆分提速量化.md` | 交付物 |

### 6.4 给路M 的门判读提示
1. **R61 全量是拆分后首轮**：`积木库/` 已不在树中 ⇒
   - `test_pure_light_hook.py::test_积木库导入的名字必须在纯光明门面的导出面内` 将 **skip 1 条**（用例总数 7 871 → 预计 ≈7 870，**属预期变化，不是红**）；
   - 若要保留真实覆盖，可在 0.82 上先 checkout/软链 lighting 并 `export LIGHT_BLOCKS_DIR=…`（本轮未做，避免污染 sync）。
2. R60 已修 3 条（身份证校验_O0对拍 / 钉桩 R22 ×2）预期转绿 + 任务2 的 `test_paragraph_call` ⇒ 预期 **0 红**。
3. 建议 commit 时**显式列 8 个路径**（含 2 个删除需 `git add -A <路径>` 或 `git rm`），切勿 `git add .`。
