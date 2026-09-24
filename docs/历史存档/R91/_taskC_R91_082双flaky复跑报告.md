# R91-C · 0.82 双 flaky 定向复跑报告（按目录分批 + 固定顺序）

> 承接：R90 §6.3（两条 flaky 拿不到最小复现）｜ 执行顺序 C ｜ 机：FreeBSD 0.82（fb82，15.1-STABLE，8 核，17G 物理/6G 用户内存，Python 3.12.14，clang 21.1.8）
> 副本：`/tmp/r44-20260924-063654/light-merge`（即 R90-M 全量 8177 passed 的同一副本）
> 跑法：`cd $LM && LIGHT_MERGE=$LM PYTHONPATH=$LM/src PATH=/tmp/r80b-shim:$PATH PYTHONIOENCODING=utf-8 /usr/local/bin/python3.12 -m pytest … -o addopts=`；抓 rc 严格用 `> log 2>&1; echo RC=$?`（坑 10）。
> 纯取证：未改任何源码，未 commit/push，只动 /tmp 副本。

---

## 1. 总结论：两条 flaky **本轮均未复现**，维持「低频条件触发」观察

| 目标 flaky | 隔离单跑 | 分批固定顺序轮（第 1 轮） | 单进程全量 -n8 loadscope | 结论 |
|---|---|---|---|---|
| **flaky1** `test_原生腿_R11A_通用工具.py::R11A通用工具反跑::test_数据验证_对拍Python` | 1/1 绿（11.34s） | b4 内 **绿**（b4 共 3577 passed） | 2/2 轮绿 | **未复现**（R82 记事后仍零复现） |
| **flaky2** `test_codegen_ref_dict_O0.py::test_回溯递归_参数写回不污染_O0` | 1/1 绿（5.89s） | b3 内 **绿**（b3 RC=0） | 2/2 轮绿 | **未复现**（历史 1/5 全量命中） |

全量两轮数字：
- 轮 1：`8177 passed, 122 skipped, 11 xfailed, 2 xpassed in 434.35s`，RC=0
- 轮 2：`8177 passed, 122 skipped, 11 xfailed, 2 xpassed in 424.95s`，RC=0

→ **0.82 LM 不劣化**，两条目标 flaky 各跑满「隔离 + 分批固定顺序 + 原生全量条件」仍一条不命中，按任务书 §3 下结论：**低频条件触发，本轮未复现**。

---

## 2. 取证链（脚本均在 `_r91/c_*.py`，日志 `_r91/c_*.out.txt`）

### 2.1 基线（step0）
- 副本存活；tests 共 243 个测试文件（root 147 + unit 96）。
- 两条目标隔离单跑均绿：flaky1 `1 passed in 11.34s`，flaky2 `1 passed in 5.89s`。

### 2.2 分批固定顺序第 1 轮（`c_run_batches.py r1 4`）
243 文件按 sorted 均切 4 批（固定顺序 b1→b2→b3→b4，独立 pytest 进程，-n 4）：

| 批 | 文件范围 | 数量 | 耗时 | RC | 结果 |
|---|---|---|---|---|---|
| b1 | test_A9_language … test_iterator_protocol | 61 | 113s | 0 | 全绿 |
| b2 | test_json_core_light … test_stdlib_phase5 | 61 | 138s | **1** | 2 failed（见 §3，**非目标**） |
| b3 | test_stdlib_phase6 … test_doc_examples_gate | 61 | 126s | 0 | 全绿（**flaky2 在本批，绿**） |
| b4 | test_error_formatter … test_非LLVM路径_T5B编码哈希 | 60 | 681s | 0 | 3577 passed（**flaky1 在本批，绿**） |

### 2.3 原生触发条件复跑（`c_full.py`）
flaky2 历史上正是在「单进程全量 -n 8 --dist loadscope」冒出的（R90-D 377s 那轮）。按原命令连跑 2 轮，均 8177 passed 全绿，**未命中**。

---

## 3. 附带发现：b2 子集确定性红 `进程` 模块（判定：**拆分上下文产物，非产品缺陷、非目标 flaky**）

分批跑期间 b2 冒出 2 条红，完整 traceback（`_r91/c_traceback2.out.txt`）：

```
[gw?] freebsd15 -- Python 3.12.14
tests/test_stdlib_comprehensive.py:85: in test_import
    self.assertTrue(hasattr(进程, '当前进程PID'))
E   AssertionError: False is not true
tests/test_stdlib_comprehensive.py:299: in test_process_pid
    pid = 进程.当前进程PID()
E   AttributeError: module '进程' has no attribute '当前进程PID'
```

### 3.1 判定证据链（逐一二分）

| 实验 | 命令 | 结果 |
|---|---|---|
| b2 原样（-n4） | 61 文件 | **红**（2 failed，1411 passed） |
| b2 隔离复跑 1 次（-n4） | 同 61 文件 | **确定性红**（同 2 条） |
| b2 用 R90-M 原参数（-n8 loadscope） | 同 61 文件 | **红**（1410 passed） |
| b2 串行无 xdist | 同 61 文件 | **红**（201s，1411 passed） |
| 只跑 `test_stdlib_comprehensive.py` | -n4 / 串行 | **全绿**（25 passed，1.4s） |
| 前半 26 文件 + comp | - | **绿**（574 passed） |
| 后半 26 文件 + comp | - | **绿**（519 passed） |
| comp 排最前 + b2 其余 | 同进程 | **仍红**（201s） |
| b1(61) + b2(61) 同进程 -n4 | 122 文件 | **仍红**（外加 1 条 http_client 计时 flake） |
| **全量 247 文件单进程**（R90-M + 本轮 2 轮） | -n8 loadscope | **3/3 全绿**（8177 passed） |

### 3.2 机理判断
- `stdlib/进程.py` 本身**定义**了 `当前进程PID`（L172，且在 `__all__`）；`stdlib/进程.light` 只是 16 行「导出」声明壳、无实现。
- 失败时 `import 进程` 解析到的是**声明壳 stub**（无 `当前进程PID`），而非 `.py` 真身。
- comp 单跑绿、b2 子集红、b1+b2 仍红、但 247 文件全量绿 → 触发条件是**收集期的模块导入预热**：全量单进程里某个（b3/b4 unit/）测试模块在 collection 阶段把真 `进程` 模块预热进 `sys.modules`，comp 后续 `import 进程` 命中真模块；子集跑缺了这个预热文件，comp 才命中壳。
- 内存排除：0.82 物理 17G、用户 6G、跑时 avm 4.4G/free 4.8G，**非 OOM/资源耗尽**。

### 3.3 对 M 的结论与建议
- **不要把这 2 条当新 flaky / 新缺陷入 0.82 台账**：它只在「人为切子集独立 pytest 进程」时出现，真实门禁命令（全量单进程）3/3 绿。
- 它提示的是**测试隔离敏感性**：`import 进程` 的正确解析依赖收集期预热，跨文件/跨进程不鲁棒。建议 M 登记为观察项（非阻断），后续若要根治，方向是让 `import 进程` 不依赖 sys.modules 预热（由 stdlib 导入解析统一裁决），**本路按红线不修 src**。
- 另：b1+b2 那轮顺带冒了 `test_http_client.py::test_concurrent_requests assert 9==10`（并发计时 flake，单发现一次），一并报 M，不追。

---

## 4. 下一轮更激进复现矩阵建议（本轮未命中，按任务书 §3 给出）

1. **夜间连跑全量 `-n 8 --dist loadscope` ×5**（每轮 ~7min），本轮起每条带 `--tb=long` + `--junitxml`。
   历史命中率：0.82 全量至今共 5 轮（R89×2、R90-D×1、R90-M×1、本轮×2 实际 6 轮），flaky2 仅 R90-D 那 1 轮命中（≈1/6），连跑 5 轮期望命中率 ≈1−(5/6)^5≈60%。
2. **装 pytest-randomly 后固定 seed**：`--randomly-seed=<N>`，打散文件收集序与 worker 配对（当前 0.82 未装 randomly，见 `c_checkplugins.py`）。
3. **并发对照**：同 seed 下 `-n 1` vs `-n 8` 各 2 轮，分离「并发竞态」与「顺序污染」。
4. flaky1（R82 记事后至今零复现）若再 2~3 轮全量不命中，建议降权为「历史记录、不主动追」，资源优先给 flaky2。

---

## 5. 产物清单
- 报告：本文件 `_taskC_R91_082双flaky复跑报告.md`（工作区根）
- 脚本：`_r91/c_step0_probe.py`、`c_run_batches.py`、`c_full.py`、`c_bisect*.py`、`c_b1b2.py`、`c_checkplugins.py`、`c_pull_traceback*.py`
- 日志：`_r91/c_*.out.txt`；远端每批日志 `/tmp/c_*_b*.log`、`/tmp/c_full_r{1,2}.log`
- 未 commit/push；未改 light-merge/lightharness 任何源码；0.82 仅 /tmp 副本。
