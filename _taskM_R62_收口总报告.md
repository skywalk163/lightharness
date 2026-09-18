# R62 收口总报告 —— sync 瘦身与 unified 缺口清零轮

- 轮次：R62 ｜ 日期：2026-09-19 ｜ 收口：主 agent（路M）
- 基线链：133701(R58) → 172617(R59) → 201545(R60) → 233330(R61) → **R62 = 051950（7884 用例 / 0 红）**
- **门：PASS ✅（新增红 0；R61 的 4 红全部转绿）**

## 1. 唯一一次 0.82 全量（`082全量回归.py all --mode fast --py /usr/local/bin/python3.12`）

| 项 | R61 基线 | **R62** | 变化 |
| --- | --- | --- | --- |
| 用例总数 | 7884 | **7884** | 持平（排除的都不是测试输入 ✅） |
| 失败 | 4 | **0** | −4（R61 处置的 4 条全部转绿） |
| 通过 | 7880 | **7799 + 74 跳过 + 11 xfail + 2 xpass** | — |
| warnings | 53617 | **53455** | −162 |
| pytest 自报耗时 | 509.8s | **402.8s** | −21%（拆仓 + 中间产物排除后副本更轻） |
| 打包体积 | 120.3 MB / 5312 文件 | **30.3 MB / 4344 文件** | **−74.8% / −18.2%** |

```
[082全量] 摘要：共 7884 用例，通过 7799，失败 0（failure 0 / error 0），跳过 74，xfail 11
[082全量] 失败数 4 → 0（7884 → 7884 用例）
[082全量] 新增红 0 ｜ 已修复 4 ｜ 持平 0
[082全量]   ✅ 零新增红（含 0 条存量失败）
[082全量] 门：PASS ✅
```

**已修复 4 条**（正是 R61 判定为「2 真回归已修 + 2 环境性」的那 4 条，本轮证实全绿）：
1. `tests/test_ffi_phase2.py::test_ffi_full_workflow`（R61 判环境性抖动 → 本轮绿）
2. `tests/test_lightpub_bridge.py::test_获取JSON`（R61 判 httpbin 502 外网瞬时 → 本轮绿）
3. `tests/unit/test_native_leg_capability.py::test_内置函数证据行号可定位`（evidence 行号重定位修复生效）
4. `tests/unit/test_原生腿_R11B_中文工具.py::test_中文分词_O0对拍`（中文分词 `截取` 修复生效）

⛔ 全程**仅此 1 次** 0.82 全量，未并行全量，本机零全量。

## 2. 三项任务结果

### 任务1：sync 打包瘦身 —— ✅ 达标

- 根因复核：拆仓后包体暴涨不是拆仓失败，而是 **266MB 本地中间产物**被一起打包
  （`_taskR11B_test_*` 143.7MB / `docs/历史存档` 92.9MB / `demo_video` 12.7MB /
  `2026-09-11-d613c31d` 10.9MB / `light_verify.tar.gz` 5.8MB / `data/finetune` 9.9MB）。
- 改动：`同步0.82.py` 新增**目录名前缀排除**（`_taskR11B_test_`，解决 49 个随机名无法枚举）
  与**相对仓根路径排除**（5 条）；`build_tarball` 由 `rglob` 改 `os.walk` + **目录剪枝**。
- 实测：**120.43MB / 5338 文件 → 30.32MB / 4336 文件**（−74.8%），打包耗时 8.3s → 3.8s。
  0.82 实际同步：**30.3MB / 4344 文件 / 5.1s**。验收线 ≤35MB：**PASS**。
- 依赖自查：`_taskR11B_test_*` 是测试运行期自建的临时目录；`docs/历史存档` 在 tests/ 里
  唯一出现是注释；`demo_video` / `finetune` 全仓零测试引用。
- 只改排除逻辑，**未物理删除任何已跟踪文件**。
- 详见 `lightharness/_task1_R62_sync瘦身.md`。

### 任务2：unified（ANTLR）腿 `去除空格` 缺口 —— ✅ 补齐

- 差集：hook 腿 276 键 / unified 腿 124 键 → 缺口 174；补后 unified 149 键，缺口 149。
- 补 **25 条「字符串处理同族」映射**（核心：`'去除空格': '_light_builtin.去除空白'`），
  全部经 `stdlib/builtins.py` 的 `hasattr` 核查确有实现。
- 改前实测产物是裸名 `去除空格(' x ')`（运行期 NameError）→ 改后 `_light_builtin.去除空白(' x ')`。
- ⚠️ **环境事实**：ANTLR **生成产物缺失**（只有 `.g4`，没有 `LightLangLexer.py`），
  `cli/light_unified.py --backend antlr` 在本机与 0.82 都跑不起来。
  已补装 `antlr4-python3-runtime`，但生成产物需 Java antlr4 工具链。
  故端到端验证改为**等价的 AST 级验证**（手工构造 light_ast 直接驱动 UnifiedCodeGenerator）。
- 行为差异登记 7 项（同键不同值），其中 `反转`（hook 返回迭代器 / unified 返回列表）
  最值得关注，**只登记不改语义**，留待 R63 裁决。
- 详见 `light-merge/_task2_R62_unified去除空格缺口.md`。

### 任务3：`段落 名 接收 参数` 现代化（tests/ 阶段一）—— ✅ 完成

- **等价性先行**：确认括号分支与接收分支只在 params 解析上有差异——
  括号分支**不支持** `*args/**kwargs`、默认值（`等于` 会被当参数名吞掉）、
  空格式类型、`为` 类型 → 只替换 **SAFE 形态**（纯参数 + 可选内嵌 `: 类型` + 空参数）。
- 规模：**287 行 / 46 文件**（`git diff` 严格 1:1，无整文件改写）。
  其中「段落/函数/段 名 接收」249 处、裸段名构造器（`构造`/`构`）38 处。
- 禁改项全部保留：匿名闭包 2、断言/期望文本、注释、FFI 声明 54 行、
  `tests/test_migration.py` 迁移测试本体。
- 两道工程护栏**都实际触发过**：① Python 语法自证抓到「参数名吞掉结尾引号」
  （`source = "段 添加(a, b")`）→ 已修字符集；② CRLF 保持（`io.open(newline="")`）。
- 验证：本机定向 **1320 passed / 9 skipped / 2 xfailed**（1 例
  `test_空串边界族` 经隔离复跑为绿，判 xdist+LLVM 缓存争用抖动，与改动无关）；
  0.82 全量 0 红；漏网 1 行（`test_light_examples_run.py:392`，`\n` 转义导致
  lookbehind 失效）已补改并在 0.82 定向复跑 **63 passed / 3 skipped**。
- stdlib 规模登记（**R63 主线**）：stdlib **1668**（1651 为段名形态）、examples 398、
  stdlib_v3 27、benchmarks 14。
- 详见 `light-merge/_task3_R62_接收语法现代化.md`。

## 3. warning 对比

| 口径 | R61 | R62 | 变化 |
| --- | --- | --- | --- |
| 0.82 全量 warnings | 53617 | **53455** | −162 |

⚠️ **如实说明**：降幅只有 −162，与「改了 287 行」不成比例。
原因：warnings 大头来自 **stdlib/ 的 1668 处旧式写法**（每份 stdlib 被每个测试重复编译），
tests/ 源串只占很小份额——这与任务3 登记的 stdlib 规模互相印证：
**warning 要真正降下来，必须动 stdlib（R63 主线）**。

## 4. 遗留与下轮（R63 建议主线）

1. **stdlib/ 旧式「接收」现代化**（1668 处）——warning 的真正大头；
   风险高（会切换编译路径、有 FFI/DEFAULT/STAR/SPTYPE 形态），需按模块 × 依赖闭包分批推进，
   遵守魔数护栏（改 stdlib/*.light 首两行之外不得出现「纯光明实现」）。
2. **unified 腿剩余 149 键缺口**全量对齐（数学族 / FFI 全族 / 文件进程族 / 类型转换别名）；
   以及 7 项行为差异裁决（`反转` 返回类型分歧优先）。
3. **ANTLR 生成产物缺失**：补 Java antlr4 或在仓内提交生成产物，否则 unified 腿永远无法端到端验证。
4. **sync 包再压**（30.3MB → ~25MB）：`reports/*.xml`（1.23MB）、`light.egg-info`（1.65MB）、
   `sessions/`（2.56MB）等仍是纯产物，收益递减，可选。
5. `_taskR11B_test_*`（143.7MB 未跟踪残留）物理清理——**须先列目录清单确认无用户文件**。
6. **本机 flaky 跟踪**：`test_原生腿_R13C_对拍扩展.py` 在 xdist 并行下不同批次报不同用例红
   （根因 LLVM 模块缓存争用 + `正则表达式.light` 是 decl 0 空壳），隔离复跑恒绿；
   另本机 `test_e2e_chain.py` 有 10 条 BOM（`0xFEFF`）LexerError 红——**0.82 全绿**，属 Windows 环境差异。

## 5. 交付物与提交清单

### light-merge（`git add` 显式文件）

| 文件 | 说明 |
| --- | --- |
| `src/code_generator_unified.py` | 补 25 条字符串同族 builtin 映射 |
| `tests/**`（46 文件 / 287 行） | 旧式 `接收` → 括号式参数 |
| `_task2_R62_unified去除空格缺口.md` | 任务2 报告 |
| `_task3_R62_接收语法现代化.md` | 任务3 报告 |

### lightharness

| 文件 | 说明 |
| --- | --- |
| `scripts/同步0.82.py` | 前缀/路径排除 + os.walk 剪枝 |
| `docs/功能对标/对标清单.json` | 追加 **#203**（无损往返自证通过；任务书写 #201，本轮打开时已有 202 条，编号顺延） |
| `_task1_R62_sync瘦身.md` | 任务1 报告 |
| `docs/历史存档/R62探针/`（7 个脚本） | R62 探针移档 |
| `reports/082_lightmerge基线_2026-09-19-051950.json` + `latest` + `_082_lm_results_*.xml` | R62 基线 |
| `reports/同步0.82_远程目录.txt` | 远程副本指针 |
| `_taskM_R62_收口总报告.md` | 本报告 |

⛔ **均未 push**（未授权）。未物理删除任何已跟踪文件。
本机两处测试运行噪声（`examples/harness/评测报告.md` 计时刷新、
`任务书/原生腿产品清单.json` 行尾归一）已 `git checkout` 复原，不入库。
