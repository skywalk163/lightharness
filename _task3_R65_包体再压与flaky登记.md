# R65 任务3：同步包再压 + 本机 flaky 正式登记

- 轮次：R65 ｜ 日期：2026-09-19 ｜ 执行：主 agent

## 1. 同步包再压

### 起点与终点

| 指标 | R62 后 | **R65** | 变化 |
| --- | --- | --- | --- |
| tar.gz 体积 | 30.32 MB | **27.49 MB** | −2.83MB（−9.3%） |
| 文件数 | 4336 | **4277** | −59 |
| 打包耗时 | 5.1s | 5.1s | 持平 |

**验收线 ≤27MB：未达标（27.49MB）** —— 如实记录，见下方「收益递减」说明。

### 本轮新增排除（`lightharness/scripts/同步0.82.py`）

| 排除项 | 体积 | 规则类型 | 依赖自查 |
| --- | --- | --- | --- |
| `light-merge/light.egg-info/` | 1.65MB | 路径前缀 | **git 未跟踪**；`grep -rn "egg-info" tests/` → 零命中 |
| `lightharness/sessions/` | 2.56MB | 路径前缀 | **git 未跟踪**；`grep -rn "sessions" tests/` → 零命中。<br>唯一相关是 `examples/test_R40_会话存储.light:64-66`，但它操作的是**沙箱根**（用例 cwd 为系统临时目录）下的 `sessions`，不是仓库里这个 |
| `light-merge/.ci/` | 1.15MB | 路径前缀 | 目录内只有 `report_local.xml`（测试报告产物）;<br>真正的 CI 配置在 `.gitea/` `.github/` `.gitcode/`，不受影响 |
| `reports/_082_lm_results_*.xml` | 1.23MB/份 | **文件名前缀** `_082_lm_results_` | pytest 结果落盘，**只写不读**；<br>基线 JSON（`082_lightmerge基线_*.json`）仍在 `reports/` 内正常同步 |

> 文件名前缀复用了 R62 的 `EXCLUDE_DIR_PREFIXES` 机制——该判定遍历 `path.parts`，
> **最后一项就是文件名**，所以同一张表既能排目录也能排文件。

### 收益递减说明（为什么停在 27.49MB）

剩余 27.49MB 基本都是**两仓源码 + stdlib + examples + 已跟踪的 docs/功能对标 与 reports 基线**，
再压就要开始动「可能被测试读到」的内容，风险/收益比急剧变差。
再往下只有两个 1MB 级别的候选（`blocks_pkg/light-blocks-poster.png` 1.19MB、
`tools/ai_copilot` 3.52MB），但前者是文档配图、后者是源码，**都不该动**。
结论：**30.32 → 27.49MB 是本轮合理止点**，继续压不划算。

## 2. 本机 flaky 正式登记（R62 观察，非本轮引入，**只登记不改代码**）

> ⚠️ **先排除一个误判**：R65 首轮 0.82 全量出现 13 条新增红
> （`test_async_io_light.py` 8 条 + `test_harness_real_channel_light.py` 3 条），
> 一度被疑为「环境性抖动」。**实为 R65 任务1 的 stdlib 改动打坏了
> `取异步流式` 的函数签名**（参数名 `消息列表` 在括号式里被切成 `消息`+`列表`），
> 已回退修复，见 `_task1_R65_stdlib接收现代化首批.md` §5.1。
> **教训：看到「并发/网络类用例成片红」不要先归因为环境，先查是不是签名/参数被改坏。**

### F-01：`tests/unit/test_原生腿_R13C_对拍扩展.py` 并行抖动

- **现象**：xdist 并行下**不同批次报不同用例红**
  （R62 第一批：`test_字符串相似度` + `test_去除所有空白与组合`；
  R62 第二批：`test_空串边界族`）——失败集合不稳定。
- **错误信息**：
  `llvm.compiler.NativeImportError: 模块 '正则表达式' 的
  '…/stdlib/正则表达式.light' 是 decl 0 空壳（实现在同名 '…/stdlib/正则表达式.py'）。
  原生腿不加载 Python 实现，请在 .light 里提供真实实现后再导入。`
- **根因**：LLVM 原生腿的模块缓存争用，叠加 `stdlib/正则表达式.light` 是 decl 0 空壳
  （真实实现在同名 `.py`，原生腿不加载 Python 实现）。
- **判环境性手法**：**隔离复跑**——`pytest <该用例 ID> -q`，恒绿
  （R62 实测 `test_空串边界族` 单独跑 `1 passed`）。
- **处置**：不改代码。若要根治，需给 `stdlib/正则表达式.light` 补真实实现，
  或让原生腿接受 decl 空壳 + Python 实现回退 —— 登记为待办，需单独评估。

### F-02：`tests/e2e/test_e2e_chain.py` 本机 10 条 BOM 红

- **现象**：本机 `10 failed, 170 passed, 10 skipped`。
- **错误信息**：`lexer.LexerError: 词法错误 (行1, 列1): 未知字符: '\ufeff' (0xFEFF)`，
  发生在 `cli/light_unified.py` → `compile_with_src` → `lexer.tokenize`。
- **根因**：部分 `examples/*.light` 带 UTF-8 BOM；源码读取用 `encoding='utf-8'`（保 BOM）
  而非 `utf-8-sig`（剥 BOM）。
- **关键事实**：**0.82 全量里这 10 条全绿**（R62/R65 全量 0 红）→ 属 **Windows 环境差异**，
  不是语言缺陷。
- **判环境性手法**：同一用例在 0.82（FreeBSD）跑即绿。
- **处置**：不改代码。若要根治，可在读取 .light 时改 `utf-8-sig`——
  但那会改变字节语义，**需单独一轮评估 + 全量兜底**，登记为待办。

## 3. 交付物

| 文件 | 改动 |
| --- | --- |
| `lightharness/scripts/同步0.82.py` | `EXCLUDE_DIR_PREFIXES` 加 `_082_lm_results_`；<br>`EXCLUDE_REL_PREFIXES` 加 `sessions` / `.ci` / `light.egg-info` |
| `lightharness/_task3_R65_包体再压与flaky登记.md` | 本报告 |

⛔ 本任务**未删除任何文件**，只改同步排除逻辑；flaky 两项只登记、不改代码。
