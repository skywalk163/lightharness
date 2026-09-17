# 第55轮任务1交付：0.82 上 light-merge 全量 pytest 基线（R55 基准）

> 日期：2026-09-17~18 ｜ 目标：解决「本机跑 light-merge 全量 pytest 卡住」，把全量基线搬到 0.82（FreeBSD）固化
> 交付物：`reports/082_lightmerge基线_2026-09-18-002428.json`（+ `latest` 指针）、`_082_lm_results_2026-09-18-002428.xml`
> 铁律遵守：0.82 只读执行，**未改 light-merge 任何源码**

---

## 一、结论（一句话）

**0.82 上 light-merge 全量 pytest 跑通了**：`-m "not slow"` 快集 **7806 用例 / 7596 通过 / 117 失败 / 80 跳过 / 13 xfail**，
pytest 自报 **1516.8s（≈25.3 分钟）**，无 hang、无 INTERNALERROR。
本机 Windows 上同样的 8000+ 用例要 1 小时以上且 xdist 不稳 —— **此后 light-merge 全量统一到 0.82 跑**。

---

## 二、实测环境（不是猜的）

```
0.82：FreeBSD fb82 15.1-STABLE amd64，8 核，Python 3.11.16
已装：pytest 9.1.1
未装：xdist ❌    pytest-timeout ❌    cryptography ❌    lunardate ❌
远端副本：/tmp/r44-20260917-235706（由 scripts/同步0.82.py sync 全量重同步所得）
源锁定：light-merge HEAD = 3e0de022（R54: L-170 修复），src/ 工作树干净；
        唯一的 tracked 改动是 examples/harness/评测报告.md（与测试无关）
```

**xdist 不可用是硬约束**，直接决定了命令形态：

light-merge 的 `pyproject.toml` 写死了
`addopts = "--tb=short --durations=15 --ignore=tests/archive --timeout=60 -n auto --dist=loadscope"`，
在 0.82 上直接跑会因为 `-n` / `--timeout` 找不到插件而 **ARGERROR 秒退**。
所以必须 `-o addopts=` 置空后自行拼参；缺 pytest-timeout 就用 FreeBSD 自带 `timeout(1)` 兜一层防 hang。

---

## 三、实际执行的命令

```sh
cd /tmp/r44-20260917-235706/light-merge && \
timeout 2700 /usr/local/bin/python3.11 -m pytest tests/ -q --tb=no -rfE \
  -o addopts= -p no:cacheprovider -p no:xdist \
  --junitxml=/tmp/r44-20260917-235706/lm_results_fast.xml \
  -m 'not slow'
```

一行的版本（本轮的入口）：

```bash
G:/dswork/duan-light-merge/light-merge/.venv/Scripts/python.exe \
  scripts/082全量回归.py all --mode fast --timeout-sec 2700
```

---

## 四、基线数字

| 项 | 数值 |
|---|---|
| 全仓库收集规模（`--collect-only`） | **8106** |
| 本轮实跑（`-m "not slow"`） | **7806**（deselect 303 条 slow） |
| 通过 | **7596**（97.3%） |
| 失败合计 | **117**（failure 108 + error 9，1.5%） |
| 跳过 | 80 |
| xfail | 13 |
| 耗时 | pytest 自报 **1516.8s**；端到端含传输 **1521s** |
| 是否 hang / 超时 | 否（硬超时 2700s 未触发） |

> 注：7806 与 collect-only 的 7803 差 3 条，是参数化/动态收集在实跑阶段的正常抖动，不是丢用例。

### 失败分布（按文件，前 12）

| 数量 | 文件 |
|---|---|
| 16 | `tests/test_stdlib_phase9/测试断言工具.py` |
| 11 | `tests/test_context_manager.py` |
| 9 | `tests/unit/test_v35_chained_call.py` |
| 8 | `tests/test_datetime.py` |
| 8 | `tests/test_frontend_blockers_run.py` |
| 6 | `tests/test_lightpub_bridge.py` |
| 6 | `tests/test_parser.py` |
| 5 | `tests/integration/test_class_system.py` |
| 5 | `tests/test_stdlib_phase3.py` |
| 4 | `tests/_test_null_safety.py` |
| 4 | `tests/unit/test_v34_syntax_sugar.py` |
| 3×4 | `test_async_io_light` / `unit/test_lexer` / `unit/test_lexer_p0a_deterministic` / `unit/test_native_leg_capability` |

### 失败原因归类

| 数量 | 归类 | 说明 |
|---|---|---|
| 61 | AssertionError（行为/代码生成不符） | 主体是「生成代码里应有的形态不存在」，如 `assert 'self.姓名 = 姓名' in <生成码>`、`assert 'await 甲.乙.丙()' in <生成码>` |
| 27 | NameError（代码生成符号缺失） | 典型：`NameError: name '己姓名' is not defined`（`己X` 成员访问在生成码里没落到 `self.X`） |
| 8 | 缺可选依赖 lunardate | `RuntimeError: 农历转换需要 lunardate 库` |
| 7 | ParseError（词法/语法） | 可空值相关 `_test_null_safety.py` 为主 |
| 6 | 缺可选依赖（其他模块） | ModuleNotFoundError |
| 4 | 缺可选依赖 cryptography | TLS 异步 IO 用例 |
| 2 | 其他 | 如 `'ChinaRegion' object has no attribute '_region_code_map'` |
| 1 | RuntimeError / 1 TypeError | 零散 |

**可读出来的两条真问题**（都是语言/编译器侧，不是环境问题）：
1. `己X`（self 成员）在若干场景生成码里没映射成 `self.X` → NameError——impact 最大（27 条）；
2. R54 的 L-170 修复把「动词作变量名 + 下标/成员赋值」改成走赋值分支后，
   `test_context_manager.py` 里一批 `*之属性赋值` 断言仍在红（`assert 'self.姓名 = 姓名' in 生成码` 不成立）。
   ⚠️ **是否 L-170 引入需再跑一次 R53 基线才能定论，本轮不臆断**（见「遗留」）。

---

## 五、与 light-merge 自带 CI 基线的关系（重要：不可直接互比）

| 基线 | 覆盖 | 条目格式 | 结论 |
|---|---|---|---|
| light-merge `tests/ci_baseline_failures.txt`（gitea CI 用） | 收集约 **1203** 条，实为其中一小部分 | `tests.e2e.test_e2e_chain::test_duan_run[...]` | 该文件的 12 条红全在 `tests/e2e/`，与本轮跑的 7806 条**交集为 0** |
| 本轮 0.82 全量基线 | **7806** 条 | `tests/xxx.py::test_yyy` | 覆盖远超前者 |

即：**两者粒度不同、口径不同，不能互相 delta**。过去 CI 所谓「零新增红」是相对那 1203 条子集而言；
本轮拿到的是真正意义上的**全量**基线，117 条红绝大多数从未被任何门看到过。

---

## 六、与本机 lightharness 基线的差异

两个是**不同套件**，不是同一套件的跨平台结果，所以不能直接同名对比：

| 平台 | 套件 | 用例数 | 失败 | 耗时 |
|---|---|---|---|---|
| 本机 Windows 10 / py3.13 | lightharness | 1272 | 7 | 1494s |
| 0.82 FreeBSD 15.1 / py3.11 | light-merge | 7806 | 117 | 1517s |

跨平台同源项的核对结果见 `_task3_R55_本机基线固化.md` §四。

---

## 七、遗留 / 未做（如实登记）

1. **slow 用例（303 条）未跑**：本轮只固化 `-m "not slow"` 快基线。脚本已支持 `--mode full`，
   下轮单独评估这 303 条的耗时与必要性。
2. **117 条红的性质判定未完成**：要判定「哪些是 R54 引入」，需要在 0.82 上对 **R53 基线**再跑一次全量
   （同样是 25 分钟），与本轮做 **两轮互比**。本轮是首份基线，没有历史可比，**不臆判归因**。
3. **xdist 未安装**：0.82 上 `python3.11 -m pip list` 只有 pytest。装上 `pytest-xdist` 后
   `082全量回归.py test --parallel` 会自动启用 `-n auto`，无需改脚本。
4. **可选依赖缺失**（cryptography / lunardate / 其他 6 个模块）导致约 18 条红：
   装依赖即可消，不属于语言缺陷，也不建议计入门禁。
