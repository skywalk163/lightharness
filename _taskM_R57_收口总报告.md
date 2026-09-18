# 第57轮 路M 收口总报告

> 日期：2026-09-18 ｜ 收口人：主 agent（豆包）
> 前置：任务1-4 由 WorkBuddy 交付（各自 _task*_R57_*.md），任务5 与路M 由主 agent 完成
> 全量纪律（用户指示）：**全程 0.82 全量 pytest 共 2 次**（首跑 092604 发现 1b 未闭环 → 修复后终跑 100010 定门），无子任务并行全量、本机未跑任何全量。

---

## 一、最终门（终跑 100010，与真基线 072454 同口径对拍）

```
0.82 py3.12 fast ｜ 7807 用例 ｜ 90 failed + 9 errors = 99 红 ｜ 370.1s
对比 072454（7806/100红）：新增红 0 ｜ 已修复 1（test_lexer_performance_10000_lines）｜ 持平 99
门 === PASS ✅  rc=0（diff 零新增红）
```

## 二、本轮最重要的翻转：1b「16 条红」从"不可复现"到"已修复"

R57 任务1 初判「16 条 `错误` 红不可复现、不改 parser_stmt」**被路M 首次全量证伪**：

| 阶段 | 现象 | 结论 |
|---|---|---|
| 定向（phase9 单跑） | 57 passed | 假象：钩子未装 |
| 首次全量（092604） | 116 红，其中 phase9 16 条 NameError | **真实存在**（R56 归因方向正确） |
| 本机组合复现（bootstrap+phase9，9s） | 16 failed | 机制实锤：bootstrap 装 `_light_import_hook` → 编译纯光明 `断言工具.light` → `class 断言失败异常(错误):` 基类未映射 |
| codegen 修复后组合 | 16 条转绿 | 修复生效 |
| 终跑全量（100010） | 99 红，phase9 消失 | 闭环 |

**根因**：`code_generator.py` 类定义基类名只过 `_sanitize_name`，没走 `exception_name_map`。`继承 错误` 编译成 `class X(错误):`，纯光明 stdlib 经 `_light_import_hook` 编译加载时运行期 NameError。R56 各轮红绿抖动（5 轮红/1 轮绿）根因 = py3.12 xdist 下 phase9 所在 worker 是否导入过 bootstrap（随机）。
**修复**：类基类经 `_resolve_exception_type` 映射（`错误→Exception`，18 键全生效；非异常名基类原样；Generic[T] 跳过）。登记 **L-175（已修）**。
**归因修正**：#195「R54 引入 16 条新红」措辞改为「R54 后存在（触发=钩子+全量），修复落在 codegen 非 parser_stmt」。

## 三、验收清单（全过）

- [x] 4 例 example 红修复后三环境定向 rc=0；token A/B 全语料仅 4 目标文件变化（任务1a）
- [x] 互举反跑 0 新增解析失败（并修复基线内 2 条）
- [x] **16 条 `错误` 红转绿**（codegen 修复，L-175）；L-170 复现用例仍绿
- [x] flaky 用例 0.82 10/10 绿（30%→0）；性能断言并行下不再假红（LEXER_PERF_LIMIT 10.0）
- [x] 复现用例挂进 tests/（test_R57_复现回归.py 11 例 + test_R57_L170回归.py 1 例）并被全量收集
- [x] 101 存量红画像完成（12 类 + 18 缺依赖环境红 + cross_platform 不稳定红预警）
- [x] 全程 0.82 全量 2 次（首跑暴露缺陷 + 终跑定门），无并行全量，本机零全量
- [x] 门 PASS（新增红 0）；红数 100→99（perf 转绿）
- [x] 对标清单 #196 追加+更正（无损往返自证通过）、MEMORY 更新、R57 探针移档 11 个
- [x] 新工具 dispatch.ps1 固化（CodeBuddy CLI 指挥，deepseek-v4-flash/1M 上下文，实测通过）

## 四、交付物清单

| 仓库 | 文件 |
|---|---|
| light-merge | `src/lexer.py`（L-173）、`src/code_generator.py`（L-175）、`tests/test_distributed_eval_light.py`、`tests/unit/test_lexer_perf.py`、`tests/test_R57_L170回归.py`（新）、`_task1_R57_解析链修复.md`（含更正块） |
| lightharness | `tests/test_R57_复现回归.py`（新）、`scripts/多平台矩阵.py`（--py 透传）、`docs/CI.md`（惯例章节）、`docs/功能对标/对标清单.json`（#196）、`_task2/3/4/5_R57_*.md`、`reports/082_lightmerge基线_2026-09-18-100010.json`（latest 已刷新）、`reports/_task4_R57_存量红明细_*`、`docs/历史存档/R57探针/`（11 文件） |
| 项目根 | `dispatch.ps1`（新工具）、`复刻_第57轮_任务prompt分发_*.md`（任务书） |

## 五、未做 / 遗留（明确声明）

1. **L-174**（`设甲为三` 无空格赋值 `为` 丢失）登记未修，留给专门词法轮（需扩 `_emb_value_heads`，扩大语义面）。
2. `test_cross_platform.py::test_stdlib_modules_importable` 为已知不稳定红（任务4 预警），本轮终跑未复现；若下轮出现按已知不稳定登记，不算新增红。
3. **未提交**：本轮未 commit（用户未授权；任务书规定收口提交，等用户确认后执行）。
4. `examples/harness/评测报告.md` 工作树有 R56 阶段遗留改动（9+/9-，非本轮成果），提交时不纳入。
5. light-merge 工作树有历史遗留未跟踪探针（`_r24_*`/`_ssh_*` 等）与 `.blocking_backup/`/`.bugfix/` 目录，均为旧轮次遗留，未清理（尊重既有状态）。

## 六、全量纪律备忘（R57 起生效）

- 全量只走 0.82 `/usr/local/bin/python3.12`（绝对路径）；本机 Windows 不跑全量。
- 子任务禁止并行全量；整轮全量配额由路M 收口统一执行；修复验证走定向子集。
- ⛔ 新教训：**定向全绿 ≠ 缺陷不存在**——依赖装载顺序/钩子/生成路径的缺陷只有全量或组合复现能暴露（phase9 16 条就是定向假象翻车的案例）。
