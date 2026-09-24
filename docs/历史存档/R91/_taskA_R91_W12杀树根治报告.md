# R91 · A 路：W-12 杀树用例根治报告（孙 PID pid 文件化 + 全量资源采样）

> 轮次：R91-A ｜ 2026-09-24 ｜ 承接 R90 §6.1 / §6.2
> 改动面：仅 tests/（`tests/test_agent_tools_light.py`、`tests/test_process_tree_light.py`）；⛔ 未动 stdlib/lexer/parser/codegen；⛔ 未 commit/push。
> 一句话结论：**W-12 旧签名（stdout 丢 PID → `孙pid=None`）已根治**——10 轮负载取证 0 次复发；但 pid 文件方案把掩盖在旧签名之下的**第二层问题**暴露了出来：**满负载下 stdlib 杀树偶发漏杀孙进程的内层真 python（双层 wrapper 逃逸）**，属 stdlib 杀树竞态，按分发书指示**交 D 路联动**。资源采样坐实：**内存不是放大器，CPU 满载是**。

---

## 1. 改动内容（R91-PIDFILE，断言语义未削弱）

### 1.1 核心：孙 PID 从"stdout 时序"改为"pid 文件轮询"

两处孪生用例同构修改：

| 文件 | 位置 | 改动 |
|---|---|---|
| `tests/test_agent_tools_light.py` | `TestRunCommand::test_超时杀整棵树含孙子进程`（约 557-624 行） | 父脚本 Popen 后立刻 `open(sys.argv[3],'w').write(str(gc.pid))` 落盘 pid 文件（保留 print 不删）；测试侧轮询 pid 文件最多 3s 取 PID；取不到如实失败 |
| `tests/test_process_tree_light.py` | `Test超时杀树::test_超时杀整棵树含孙子进程`（约 160-204 行） | 同构修改，命令行追加第 3 个参数传 pid 文件路径 |

**为什么 pid 文件比 stdout 宽**：pid 文件在 Popen 后立刻落盘且不随杀树截断 stdout 而丢失；且若 root 因"刚 Popen 未初始化完成"杀不掉而等满 30s 宽限，父脚本仍活着会把 PID 写出来——窗口反而更宽。

**断言强度对比（未削弱）**：
- 旧：grep stdout 纯数字行 → `孙pid is not None` → `_进程活(孙pid)` 轮询 6.0s → marker 5.0s 不出现。
- 新：轮询 pid 文件 3s → `孙pid is not None`（取不到照样失败）→ `_进程活(孙pid)` 轮询 6.0s → marker 5.0s 不出现。
- **未循环加大 timeout/窗口**：run_command timeout 仍 1.5s；死亡/标记窗口时长仍 6.0/5.0s，仅把起算点从"绝对起点"改为"拿到 PID 之后"——原绝对写法在异常慢返回（30s 宽限）时窗口必然已过期、循环体一次都不跑 → 恒失败，属假红修复，非放宽。
- 哨兵串：两文件均可 grep `R91-PIDFILE` 确认改动落盘。

## 2. 取证（一手）

### 2.1 孤立串行 5 轮（任务 2a）——5/5 全绿

命令（坑 1 姿势，`-o addopts= --basetemp=仓内 CODEBUDDY_SAFE_DELETE_ENABLED=0`）：
`pytest tests/test_agent_tools_light.py::TestRunCommand::test_超时杀整棵树含孙子进程 tests/test_process_tree_light.py::Test超时杀树::test_超时杀整棵树含孙子进程`

| 轮次 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| RC | 0 | 0 | 0 | 0 | 0 |
| 耗时 | 19.9s | 17.1s | 20.0s | 19.7s | 17.3s |

日志：`_r91/a_iso_run1-5.log`、`_r91/a_iso_rc.txt`。

### 2.2 类级负载 `-n auto` 5 轮（任务 2b）——3/5 绿，2 轮红（新签名）

`pytest tests/test_agent_tools_light.py tests/test_process_tree_light.py -q -o addopts= -n auto --basetemp=../_r91/basetemp_cls`

| 轮次 | RC | 结果 | 红的签名 |
|---|---|---|---|
| 1 | 0 | 88 passed | — |
| 2 | 1 | 2 failed | ① agent_tools：`孙子进程未被杀死：标记文件已生成`；② 孪生：`assert not marker.exists()` 失败（见 §3.2 跨轮残留） |
| 3 | 0 | 88 passed | — |
| 4 | 0 | 88 passed | — |
| 5 | 1 | 1 failed | agent_tools：`孙子进程未被杀死：标记文件已生成` |

**关键：10 轮（含 §2.1）负载取证中，旧签名"没抓到孙 PID / pid 文件未出现"出现 0 次**——R90 收口轮的 W-12 直接死因已根治。红的全部是另一层问题（§3）。日志：`_r91/a_cls_run1-5.log`。

### 2.3 完整 Windows 全量 1 轮 + judge（任务 2c）

命令：`pytest tests/ -q -o addopts= -n auto --dist loadscope --basetemp=../_r91/basetemp_full --junitxml=../_r91/a_full_junit.xml`

- 结果：**1 failed / 8208 passed / 90 skipped / 11 xfailed / 2 xpassed**，**9m58s**（R90 收口轮 18m34s）。
- 唯一红：`tests/test_agent_tools_light.py::TestRunCommand::test_超时杀整棵树含孙子进程`，签名 **`AssertionError: 孙子进程未被杀死：标记文件已生成`**（`_r91/a_full.log`）——**不是**"没抓到孙 PID"。
- 孪生用例本轮全量绿。
- judge（`tests/ci_judge_env_reds.py judge --current _r91/a_full_junit.xml`）：本轮失败 1 条**命中台账 W-12**，**新增红 = 0，判据绿**（JUDGE_RC=0）。
- **判据口径如实说明**："全量 1 轮 W-12 转绿"未达成——但失败签名已从"测试时机假红"换成了"杀树真漏杀"（§3），后者不是测试侧能根治的，见降级处置。

## 3. 第二层发现：满负载下 stdlib 杀树偶发漏杀孙的内层真进程（交 D 路）

### 3.1 现场签名与机理

marker 断言红意味着：**孙的内层真 python 活到了 `sleep(2.5)` 结束并写出 marker**，而 `_进程活(孙wrapper_pid)` 却判死通过——即 **wrapper 被杀、内层逃逸**。这与 `stdlib/进程树.light` 杀树注释自认的两个竞态完全吻合（stdlib/进程树.light:529-545）：

1. Python `subprocess.Popen` 检测到父进程在 Job 内自动加 `CREATE_BREAKAWAY_FROM_JOB` → **孙进程逃逸出 Job Object**（2026-09-03 实测在案）；
2. "刚 spawn 的孙进程偶发不在快照内" → 两轮快照并集 + 逐 PID 强杀仍有窗口：**内层真进程在末轮快照之后、其 wrapper 被杀之前这一缝隙里被创建，即逃逸**。

满负载（10 worker 打满 10 核）放大了它：双层 wrapper 下孙的 wrapper→内层启动拉长到 ~1s+，缝隙概率上升。

### 3.2 孪生用例 run2 红的"跨轮残留"旁证

孪生用例孙进程 `sleep(30)` 后才写 marker，测试 ~10s 即结束——run2 的 marker 却已存在。唯一解释：**上一轮某次逃逸的孙内层进程存活 ≥30s，把 marker 写进了本轮重建的同名 tmp 目录**（`--basetemp` 仅会话启动时清空，轮间不清）。这直接证明**逃逸进程可跨 pytest 轮次长期存活**。

### 3.3 对照探针：taskkill /F /T 自走树 0/10 逃逸（`_r91/a_probe_kill_leak.py`）

精确复刻用例构造（父 Popen 孙 + 孙自报内层 PID），10 个忙循环 hog 打满 10 核，1.5s 后 `taskkill /F /T` 杀根，观测 16s：
**10/10 轮孙 wrapper 死、内层真进程无逃逸、无 marker**。差异指向：taskkill /T 在杀点时刻自走树枚举，窗口远小于 stdlib"提前两轮快照并集+逐 PID"路径。

### 3.4 给 D 路的联动建议（A 路不改 stdlib）

- 方向 A：逐 PID 强杀**全部完成后**，若 root 已死则无法再 BFS——可改为"先杀后代、最后杀 root"的顺序，杀完 root 前补第三轮快照重扫并集；
- 方向 B：杀树序列末尾在 **root 仍存活时**补一次 `taskkill /F /T /PID root` 兜底（其自走树枚举更贴近杀点，探针 0/10）；
- 方向 C（任务书 §3 极小 timeout 评估的正向结论）：杀树前轮询 ≤500ms 等 root 出现在 Toolhelp32 快照（D 路既定评估项），与上述互补。
- 风险提示：两轮快照+杀需 <2s 的既有时间预算约束（stdlib/进程树.light:543-545）必须保持。

## 4. 资源采样（任务 3）：回答"是不是这台机器资源不够"

采样器：独立后台进程 `psutil` 每 5s 一针（PowerShell CIM 版卡死烧 CPU 已弃，见 §6 坑 N1），`_r91/a_resmon.csv`。覆盖全量主负载段（worker 满槽至收尾阶段，49 针，07:56:30→08:02:23；头尾各缺约 2-3 分钟）。

| 指标 | 峰值 | 均值 | 结论 |
|---|---|---|---|
| CPU 总占用 | **100%** | 50.0%（≥95% 占 35%、≥99% 占 29%） | **满载段长期 100%，10 个逻辑核全部打满**（各核峰值均 100%） |
| 可用物理内存 | 最低 **5675 MB** | 6939 MB | 空载可用 ~9.5GB，全量期间**始终余 5.6GB+**，远未耗尽 |
| commit charge | 1.64 / 6.23 GB（**26%**） | — | 提交内存水位很低 |
| 换页（Pages In/Out） | **0 / 0** | — | **零换页**，无 swap 迹象 |
| pytest worker 数 | 21 | 19（众数） | 高于 -n auto=10：沙箱双层 wrapper 使真实进程数翻倍 |
| 系统总句柄 | 105,879 | 102,197 | 平稳，无句柄泄漏迹象 |

**明确回答**：全量期间**内存没有逼近耗尽**（最低仍余 5.6GB、commit 26%、零换页），**CPU 确实长期 100%**（满载段 10/10 核打满）。**"内存是放大器"的假设被排除；放大器是 CPU 满载调度延迟**——与 R90 初步判断"负载敏感时序竞态、非硬件不足"一致，且现在有数据支撑。

## 5. 判据核对

| 判据 | 结果 |
|---|---|
| 孙 PID 改由 pid 文件获取，不再依赖 stdout 时序 | ✅ 两孪生用例均改，`R91-PIDFILE` 哨兵在案 |
| 孤立 5/5 | ✅ 5/5 绿 |
| 全量 1 轮 W-12 转绿 | ⚠️ **未达成（如实记录）**：全量仍 1 红，但签名已换——旧"没抓到 PID"根治后暴露的是 stdlib 杀树真竞态（§3），非测试侧可修；已按分发书"交 D 路联动"处置 |
| 全量 judge 新增红 = 0 | ✅ 唯一红命中台账 W-12，新增红 0，判据绿 |
| 资源采样表明确回答"是不是资源不够" | ✅ 不是内存/资源不足；是 CPU 满载调度延迟（§4） |
| 断言语义未削弱 | ✅ PID 取不到仍失败；真死仍按 PID 轮询；marker 仍必须不出现；窗口时长未放大 |

## 6. 新增坑（供 M 路固化）

1. **PowerShell CIM 采样循环会卡死烧 CPU**（Win32_PerfFormattedData 系列在满载下挂起，390 CPU-s 零输出）——全量期资源采样改用 venv **psutil**（本轮已装入 light-merge/.venv，7.2.2；脚本 `_r91/a_resmon.py`）。
2. `--basetemp` 只在会话启动时清空，**轮间不清**：逃逸进程可跨轮写 marker 污染下一轮同名 tmp 目录（§3.2）——跨轮对比取证时每轮应换 basetemp 或显式清理。
3. 全量 9m58s 远快于 R90 的 18m34s：机器当时负载状态不同，**跨轮耗时对比无意义**，以 judge 对拍为准。

## 7. 产出清单

- `_taskA_R91_W12杀树根治报告.md`（本文件，工作区根）
- `light-merge/tests/test_agent_tools_light.py` / `test_process_tree_light.py` 改动（R91-PIDFILE）
- `_r91/a_resmon.csv`（资源采样 49 针）+ `_r91/a_resmon.py`（psutil 采样器）+ `_r91/a_resmon.ps1`（弃用样本）
- `_r91/a_probe_kill_leak.py`（杀树逃逸对照探针）
- `_r91/a_iso_run1-5.log`、`_r91/a_iso_rc.txt`（孤立 5 轮）
- `_r91/a_cls_run1-5.log`、`_r91/a_cls_rc.txt`（类级负载 5 轮）
- `_r91/a_full.log`、`_r91/a_full_junit.xml`、`_r91/a_full_rc.txt`（全量 1 轮 + judge 输入）
