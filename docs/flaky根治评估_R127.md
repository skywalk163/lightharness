# R127（查缺补漏轮）flaky 台账根治评估

- 评估人：R127-B 线执行代理
- 日期：2026-10-08
- 评估对象：`tests/flaky_registry.txt` 全部生效条目 + 留档条目复核 + 任务书指定「BOM 归一化」类排查
- 评估口径：逐条「条目 / 现象 / 根因假设 / 根治方案 / 风险 / 结论」；**只允许对零风险项实施根治**（先复现再修，修后隔离复跑 3 次全绿才准出簿）；xdist 串扰类一律维持登记（R120 已实证机制）。

---

## 1. 生效条目逐条评估

### F-01 `test_终端PTY.light`（freebsd）

| 项 | 内容 |
| --- | --- |
| 现象 | 0.82 全量偶发红、单跑恒绿（R81 起观察）；PTY 轮询计时类。R87-E 取证 0.82 串行全量 2 轮无复发。 |
| 根因假设 | 高负载下 PTY 轮询节奏抖动：固定预算内轮询读不满输出即判负。R68 已落「轮询 + 累积读取（15s 预算）」加固，偶发空间已压缩至极端负载边缘。 |
| 根治方案 | 理论上可再加大预算或改为事件驱动读取；但需改 `examples/test_终端PTY.light` 判据并重做 0.82 多轮全量取证。 |
| 风险 | 非零风险：改判据会削弱 FreeBSD PTY 既有语义覆盖；且无法在本机（Windows）复现该平台现象，「先复现再修」前置条件不满足。 |
| 结论 | **维持登记**。登记豁免同类偶发抖动；若稳定复现须人工归因。 |

### F-02 `test_async_await.light`（linux）

| 项 | 内容 |
| --- | --- |
| 现象 | 0.86 xdist 高负载计时抖动（R85 全量 conc 0.26s > 0.18s 偶发）。R86-C 已落「阈值 0.18→0.35 + 顺序-并发≥0.05s 相对收益兜底」。R87-E 取证 0.86 xdist 全量 2 轮无复发。 |
| 根因假设 | xdist 高并发下调度延迟挤占并发收益测量窗口，属负载敏感计时，非逻辑缺陷。 |
| 根治方案 | 理论上可改测「相对加速比」而非绝对耗时；但改动即触及异步运行时语义覆盖面，且需 0.86 多轮全量复验。 |
| 风险 | 非零风险：判据重构改变断言语义；无法在本机复现 linux xdist 负载环境，「先复现再修」前置条件不满足。 |
| 结论 | **维持登记**（属 xdist 负载/串扰敏感类——R120 已实证 xdist 串扰机制，此类一律维持登记）。 |

## 2. 留档「已根治不入账」条目复核

| 条目 | 根治轮 | 复核结论 |
| --- | --- | --- |
| `test_R21_词法确定性_超集.py`（freebsd，git archive spawn 偶发 ERROR） | R87-E（`_run_with_retry` 3 次线性退避 + 降级 skip） | 根治机制在判据脚本内、平台无关，维持出簿状态，无回簿必要。 |
| `test_子进程后台.light`（windows，固定 5s 等待撞高负载） | R45（HARNESS_PY 绝对路径 + 等待 20s + 失败归因） | R87-E 复核 Windows 全量 2 轮无复发，维持出簿状态。 |

## 3. 「BOM 归一化」类专项排查（任务书零风险根治白名单）

- 任务书所举 `tests/e2e/test_e2e_chain.py`：**不在 lightharness 仓**（实测 `lightharness/tests/` 下无 e2e 子目录、全仓无 `test_e2e_chain*` 文件）。该文件属 **light-merge 仓**（`light-merge/tests/e2e/test_e2e_chain.py`），超出本线改动边界（禁改 light-merge）。
- 该 BOM 问题的历史状态：`docs/多平台差异清单.md:225` 记载「e2e_chain×8 实为 light-merge 示例语法 bug（… + `_test_nested_closure.light` UTF-8 BOM），修示例后 0.86 full 复跑 0 failed（commit 3b09301e）」——**已根治且不在本仓**，无需也不允许本轮处置。
- 本仓 `tests/flaky_registry.txt` 生效条目中**无任何 BOM 归一化类条目**（F-01/F-02 均为计时/负载类）；BOM 相关已有防护（`src/前置元数据.light` frontmatter 允许前置 BOM、`examples/test_会话标题.light` 断言 BOM 方向控制、多个 token 测试用 `utf-8-sig` 读取），未发现需根治的 BOM flaky 项。
- 结论：本轮**无可实施的零风险根治项，零代码改动**。

## 4. 总表

| 条目 | 平台 | 类别 | 结论 |
| --- | --- | --- | --- |
| F-01 test_终端PTY.light | freebsd | PTY 计时抖动 | 维持登记 |
| F-02 test_async_await.light | linux | xdist 负载计时抖动 | 维持登记（xdist 串扰类，R120 已实证机制） |
| 留档：test_R21_词法确定性_超集.py | freebsd | spawn 瞬时失败 | 已根治（R87-E），维持出簿 |
| 留档：test_子进程后台.light | windows | 固定等待撞负载 | 已根治（R45），维持出簿 |
| BOM 归一化类 | — | 编码归一化 | 登记簿内无此类条目；e2e_chain BOM 属 light-merge 仓且已根治（3b09301e），无可实施项 |
