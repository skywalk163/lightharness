# _taskE_R87_flaky根治报告.md —— R87 任务 E · flaky 根治（4 条旧账）

> 执行：R87-E 路 agent ｜ 日期：2026-09-23 ｜ 依据：`R87_agent任务分发_prompts.md` §7
> 结论速览：**2 条根治（R21 超集本轮落地修复 / 子进程后台 R45 修复本轮复核确认）+ 2 条登记（终端PTY / async_await，既有加固维持不改码）**；取证为对应平台连续全量 2 轮。
> 红线遵守：未 commit / 未 push；改动仅限 flaky 相关用例/台账/判据接线；未动宿主接线文件；未扩语法。

---

## 1. 逐条处置与取证

### 1.1 test_R21_词法确定性_超集.py（FreeBSD 0.82）—— ✅ 根治（本轮落地）

* **现象**：0.82 全量偶发 ERROR（FileNotFoundError），单跑恒绿；git archive 子进程在并行/负载下瞬时 spawn 失败。
* **修复**：`lightharness/tests/test_R21_词法确定性_超集.py` 新增 `_run_with_retry`——git archive 与扫描子进程对瞬时 `FileNotFoundError` 做 **3 次线性退避重试**；连续失败才按环境故障**降级 skip**（spawn 失败不再产生红/ERROR）。真回归（断言失败路径）不受豁免，仍硬判红。
* **取证**：
  * 0.82 串行全量 2 轮：run1 577.41s / run2 471.45s，两轮该用例均无失败（各轮仅 E 范围外 3 条红，见 §3）；
  * 本机 Windows 单跑：2 passed（重试路径无副作用）。
* **为何不入 flaky 台账**：根治后 spawn 瞬时故障走 skip、断言失败即真回归——无「偶发红」需豁免，入账反而弱化判据。

### 1.2 test_子进程后台.light（Windows）—— ✅ 根治确认（R45 修复 + 本轮复核）

* **背景**：R44 时代全量偶发红（固定 5s 等待撞全量高负载）。R45 已加固：解释器取 `HARNESS_PY` 绝对路径、正常等待 5s→20s、失败信息带 输出/错误 归因。
* **本轮取证（Windows 本机，LM venv python，xdist -n auto + timeout 60）**：
  * run1：**1396 passed / 0 failed / 4 skipped**，173.59s（`_taskE_R87_win_run1.log`）；
  * run2：**1396 passed / 0 failed / 4 skipped**，247.65s（`_taskE_R87_win_run2.log`）。
* **处置**：连续全量 2 轮无复发 → R45 根治确认，不改码。

### 1.3 test_终端PTY.light（FreeBSD 0.82）—— 📋 登记（flaky_registry F-01）

* **现象**：0.82 全量偶发红、单跑恒绿（R81 起观察），PTY 轮询计时类。R68 已落「轮询+累积读取（15s 预算）」加固。
* **本轮取证**：0.82 串行全量 2 轮（run1 577.41s / run2 471.45s）该条均无失败。
* **处置**：**维持 R68 判据不改码**（避免为偶发现象扩改动面）；因历史上低频复现、2 轮干净不能证伪偶发，按任务书「登记」路径写入 `tests/flaky_registry.txt` F-01（freebsd 平台豁免同类偶发红，稳定复现须人工归因）。

### 1.4 test_async_await.light（0.86 Linux）—— 📋 登记（flaky_registry F-02）

* **现象**：0.86 xdist 高负载计时抖动（R85 全量 conc 0.26s > 旧阈值 0.18s 偶发）。R86-C 已落「绝对阈值 0.18→0.35 + 顺序-并发≥0.05s 相对收益兜底」双层判据。
* **本轮取证（0.86 xdist -n auto，/tmp/r85-venv，与 CI 同口径）**：
  * run1：**1371 passed / 0 failed / 4 skipped**，335.03s（`_taskE_R87_086_run1.log`）；
  * run2：**1371 passed / 0 failed / 4 skipped**，451.75s（`_taskE_R87_086_run2.log`）。
* **处置**：维持 R86-C 判据不改码；登记 F-02（linux 平台）豁免负载抖动，稳定复现须人工归因。

### 取证环境口径

| 平台 | 副本 | 运行方式 | git HEAD |
|---|---|---|---|
| Windows 本机 | `G:\dswork\duan-light-merge\lightharness` | LM venv python，pytest.ini addopts（xdist+timeout60） | ac4be9d（工作树） |
| 0.82 FreeBSD | `/tmp/r44-20260923-142451`（sync --with-git） | `/usr/local/bin/python3.12` **串行**（`-o addopts=`，见 §4 环境欠账），与 R86 收口串行口径一致 | ac4be9d |
| 0.86 Linux | `/tmp/r85-20260923-142453`（sync --with-git） | `/tmp/r85-venv` python，xdist -n auto（同 0.86 CI 口径） | ac4be9d |

---

## 2. 改动清单（均未 commit，供 M 路显式 git add）

| 文件 | 改动 | 性质 |
|---|---|---|
| `lightharness/tests/test_R21_词法确定性_超集.py` | +`_run_with_retry`（3 次退避重试）；git archive/扫描子进程接入；连续失败降级 skip | 根治修复 |
| `lightharness/tests/flaky_registry.txt` | **新建**：F-01（PTY/freebsd）、F-02（async_await/linux）登记 + 取证链；根治 2 条留档不入账 | 台账 |
| `lightharness/tests/test_回归.py` | 接线 flaky 台账：`_load_flaky_registry` / `_flaky_platform_hit` / `_FLAKY_FAILED`；`test_example_exit_code` 对本平台登记条目豁免新增红；`test_env_red_baseline_report` 扣减 flaky 豁免并打印豁免清单 | 判据接线 |
| `lightharness/tests/ci_environment_reds.txt` | 备注更新：PTY/R21 两条偶发记录指向 flaky_registry（与 F 路任务 3 互引） | 台账互引 |

**判据强度说明**：豁免仅作用于「本平台 + 已登记文件」的偶发失败且必须命中登记；未登记文件/平台失败仍硬判回归红。登记条目转稳定复现时按台账约定人工归因。本机验证：`FLAKY_REGISTRY` 正确加载 2 条；Windows 平台对 freebsd 登记项不误豁免（`_flaky_platform_hit('test_终端PTY.light')`=False）；含台账加载的 `tests/test_回归.py` 过滤跑 1 passed。

---

## 3. ⚠️ E 范围外发现（移交 M 路，非本路处置）

0.82 两轮全量出现**确定性复现（2/2）**的 3 条 E 范围外红（+1 条汇总报告测试连带失败）：

* `test_事件循环.light`（R86 环境红 E-01，R86-B 已销账）
* `test_套接字.light`（E-02，R86-B 已销账）
* `test_进程树接线.light`（E-06，R86-D rlimits 兜底已销账）
* `test_env_red_baseline_report`：新增红=3 断言失败（判据如实上报，行为正确）

**归因线索**：R86 收口时同口径串行复跑（HEAD f151503）为 1372/0/0；本轮同步树 HEAD ac4be9d 已含 R87 B1–B4 移植改动（工作树含未提交内容一并同步）。2/2 确定性、集合稳定 → **非 flaky**，疑似 B 路移植面（或其带来的 light-merge 副本变化）在 0.82 平台引入回归。**此三项不在 E 路 scope（只动 flaky 相关），未做任何改动**，请 M 路三平台复核时归因处置；若确认为 B 路引入，应在合流前修复，否则 0.82 门禁新增红=0 判据不成立。

## 4. 环境欠账（供 F/D 路参考）

* 0.82 `/usr/local/bin/python3.12` 当前**缺 xdist / pytest-timeout**：pytest.ini `addopts=-n auto --timeout=60` 直接触发 usage error（rc=4，诊断见 `_taskE_R87_082_diag*.log`）。本轮以 `-o addopts=` 串行绕开（与 R86 口径一致）；D 路 FreeBSD LM 复跑与 F 路 `freebsd/初始化.sh` 若需并行/超时插件，需先补装（`pip install pytest-xdist pytest-timeout` 到 3.12 用户侧）。
* 0.86 本轮两次全量均正常（venv 插件齐全）。

## 5. 产物与日志索引

* 修复/台账：`tests/test_R21_词法确定性_超集.py`、`tests/test_回归.py`、`tests/flaky_registry.txt`、`tests/ci_environment_reds.txt`
* 取证日志：工作区根 `_taskE_R87_win_run{1,2}.log`、`_taskE_R87_082_run{1,2}.log`、`_taskE_R87_086_run{1,2}.log`、`_taskE_R87_082_diag.log`、`_taskE_R87_082_diag2.log`
* 远端副本：0.82 `/tmp/r44-20260923-142451`、0.86 `/tmp/r85-20260923-142453`（均为 /tmp 副本，未动远端源仓库与系统环境）
