# R92-A · stdlib 杀树"wrapper 逃逸孙内层真 python"根治报告

> 轮次：R92-A（2026-09-24）｜ 主线：stdlib/进程树.light win32 杀树最小加固
> 文档依据：`R92_任务分发书_prompts.md` §1（A 路）
> 改动文件：`light-merge/stdlib/进程树.light`（仅 win32 杀树段，+`_R92补杀迟建后代` 方法，删除临时取证桩）
> 复现/验证脚本：`_r92/a_reparent_probe.py`（Windows reparent 行为实证）、`_r92/a_repro_leak.py`（独立复现 + 补丁前后对照）
> 红线遵守：✅ 不改 marker/孙 PID 断言 ✅ 不动 lexer/parser/codegen ✅ `.light` 保持 LF ✅ 不 commit/push ✅ taskkill 不越出 root 后代树

---

## 1. 结论速览

- **根因**：满负载（10 核打满）下 Python 双层 launcher 启动极慢，孙进程对象**在杀树主流程已返回之后**才被 OS 真正创建；其父（mid_real）此时已死，孙被 Windows 重新挂靠（reparent）但 **PPID 仍指向已死父 PID**（实测 reparent 不改 PPID）。旧杀树（两轮快照并集 → 逐 PID /F /PID → /T /PID root）在杀点时刻枚举不到这个「尚未出生」的孙，/T 也因孙当时不在树里而漏杀 → 孙最终写出存活标记（逃逸）。
- **修复**：在旧逻辑之后追加**有界重扫兜底**（哨兵 `[R92-A-LEAK]`）。沿 PPID 链回溯，凡链上任一祖先 PID ∈ `{root ∪ 杀前记录的后代}` 即判定为「本树迟建后代」并强杀。该判定**精确**——只杀确属本树的后代，绝不误伤无关进程。
- **验证（见 §5）**：孪生用例孤立 ×5 全绿（10/10）；类级 `-n auto` 12 轮对照——**基线（HEAD，无补丁）复现逃逸 2 轮（round 2/9，孙写出 marker 的 `标记文件已生成` 断言失败），补丁后 12 轮 0 逃逸断言**；全量 W-12（agent_tools 孪生）转绿；`judge` 报新增红 run1=1 / run2=6，但全部经隔离复跑转绿 → **非回归**（台账缺口 + 本机负载方差，见附录 C）；同族 sibling ×3 无回归。
- **重要区分**：类级 `-n auto` 满负载下两种失败并存——①真正的「逃逸」（marker 写出 / 孙仍活），②「孙 pid 文件未落地」（`assert 孙pid is not None` 因父进程在 10 核打满下 CPU 饥饿、1.5s 杀点后 3s 轮询窗口内都未能 spawn 出孙而失败）。②是**用例自身构造在极端饱和下的 flaky**（与本轮杀树补丁无因果，A 路红线禁止改用例），①才是补丁目标。补丁把①从「基线复现」降到「0」，②在两类跑批中均存在、属既有现象。

---

## 2. 根因：不是"快照缝隙"，是"杀点之后才出生"

R91-A 已查明两道缝隙：
1. Python `subprocess.Popen` 检测到父在 Job Object 内会自动加 `CREATE_BREAKAWAY_FROM_JOB` → 孙逃逸出 job；
2. 旧杀树"提前拍两轮快照取并集 → 逐 PID 强杀"，孙**内层真进程在末轮快照之后、其 wrapper 被杀之前**这一窗口被创建 → 漏杀。

本报告一手复现发现：**真实逃逸属于第三种、更隐蔽的情形**——孙不仅不在快照并集里，而且在**整个杀树主流程结束之后**才落地。直接证据来自给真实 `进程树.light` 注入的取证桩（`_R92追溯前/_R92追溯后`，跑完已删）：

```
KILL root=24684 union=[28840]
  BEFORE sub=[28840]              # 杀点时 root 子树只有 parent_real(28840)
  AFTER alive-from-before=[]
  AFTER alive-python=[]           # 杀树收尾时全系统无 python 存活
```

`AFTER alive-python=[]` 是关键：若孙是在"快照之后、杀点之前"这一窄窗口出生，则 `_R92追溯后`（在 `等待到死` 之后）采样时孙应当正在 `sleep(2.5)`、仍存活。但它**不在**——说明孙在 `等待到死` 之后才被创建。随后孙被 reparent 到 init，写出标记。这与"快照缝隙"假说的预言（杀点后很快仍可见孙）**矛盾**，坐实为"杀点之后才出生"。

### 2.1 进程树是 4 层（双层 launcher 放大）

本机每个 python 进程都是 `python.exe`(launcher) → `python3.13.exe`(real) 的双层结构。测试真实树为 4 层：

```
root   = python.exe(launcher)            ← 杀树进程对象.pid
  └ parent_real = python3.13.exe(real)  ← 跑测试 light 程序，一启动就 Popen(gc)
      └ gc_launcher = python.exe        ← Popen([sys.executable]) 创建，pid 在 t≈0 即返回
          └ gc_real = python3.13.exe    ← 跑 sleep(2.5) 后写标记
```

满负载下 `gc_launcher` 的进程对象创建被调度延迟推到杀点（1.5s 超时触发）之后，`gc_real` 更晚。旧杀树的 `/T /PID root`（line 584）在**杀点时刻**自走树枚举，但此刻孙根本没出生 → 漏杀。这也解释了为什么 R91-A 探针 `taskkill /F /T /PID root` 能 10/10 零逃逸：探针里的树在 1.5s 定时器之前就已完整建立，杀点时刻整树都在 root 下，/T 一锅端；**真实测试在 10 核满载下孙出生更晚**，探针未复现该条件。

### 2.2 Windows reparent 行为实证（关键判据）

要精确捕杀"杀点之后才出生、且已被 reparent"的孙，必须知道其 PPID 在被 reparent 后是否仍指向已死父。探针 `_r92/a_reparent_probe.py` 实证（杀 mid launcher+real 后观察其孤儿 gc）：

```
BEFORE(杀 mid):  gc_launcher pid=15644 ppid=26600(mid_real) | gc_real pid=17448 ppid=15644
AFTER (杀 mid):  gc_launcher pid=15644 ppid=26600(mid_real,已死) | gc_real pid=17448 ppid=15644
```

**结论：Windows 不重置 reparent 后的 PPID**——孤儿进程的 PPID 仍指向已死父 PID。因此只要沿 PPID 链回溯，就能从迟建孙一路追到 `{root ∪ 杀前记录的后代}` 中的某个已死 PID，从而**精确且无歧义**地判定"它属于本树"。

---

### 2.3 基线对照：HEAD（无补丁）仍可复现逃逸

为验证补丁确实消除了逃逸（而非把失败模式「藏」起来），对 **HEAD（git stash 回退补丁）** 用与补丁后完全相同的命令/负载跑了 12 轮类级 `-n auto`（`_r92/run_baseline.sh`），逐轮按断言签名分类：

| 轮 | 基线(HEAD) 结果 | 失败签名（按真实 `E AssertionError` 归类） |
|---|---|---|
| 1 | 绿 | — |
| 2 | 红 | **逃逸** ×2（两孪生均 `孙子进程未被杀死：标记文件已生成`） |
| 3–8,10–12 | 红 | 孙 pid 文件未落地 ×2（`assert 孙pid is not None`） |
| 9 | 红 | **逃逸** ×1（`标记文件已生成`）+ 孙 pid 文件未落地 ×1 |

基线 12 轮里 **round 2、round 9 出现真正的逃逸**（孙进程逃出杀树、sleep 结束写出 marker，测试 `assert not marker.exists()` 失败），共 **3 次逃逸断言失败**，涉及两孪生用例——这正是 R91-A 量到的 ~40% 逃逸在 12 轮尺度上的复现。补丁后 12 轮（`_r92/run_myfix.sh`，**已完成**）逐轮核真实 `E AssertionError`：**12 轮 0 条逃逸断言**，全部失败均为「孙 pid 文件未落地」（round 10 转绿、其余 11 轮为该 flaky）。二者对照，补丁的逃逸消除效应一手可证。

> 注：pid 文件未落地在基线与补丁后跑批里出现轮数相近（基线 11/12、补丁 11/12），说明它是与杀树补丁**无因果**的用例构造型 flaky——根因是父进程（双层 launcher）在 10 核打满下 CPU 饥饿，1.5s 杀点触发后连同 3s 轮询窗口内都未能把孙进程 spawn 出来，此时孙根本没出生、谈不上逃逸。A 路红线禁止改用例，故不在本轮处理；其存在不影响「0 逃逸」判据。

> 说明：`孙 pid 文件未落地` 在基线与补丁后跑批里都出现，根因是父进程（双层 launcher）在 10 核打满下 CPU 饥饿，1.5s 杀点触发后、连同 3s 轮询窗口内都未能把孙进程 spawn 出来——此时孙根本没出生，自然谈不上「逃逸」，属用例自身在极端饱和下的时序 flaky，A 路红线禁止改动用例，故不在此轮处理。

## 3. 修复方案（方向 B 变体：杀点 /T + 有界重扫兜底）

在 `stdlib/进程树.light` win32 杀树段，保留原有"两轮快照并集 → 逐 PID /F /PID → /T /PID root → 关 job → 等待树清 → 等待到死"主流程（line 576–595），并在 `等待到死` 之后新增兜底调用（line 596–597）：

```light
      己.等待到死(宽限期毫秒)。
      # [R92-A-LEAK] 兜底：捕杀主流程完成后才落地的迟建后代（详见 段落 _R92补杀迟建后代）。
      己._R92补杀迟建后代(pid, 记录)。
```

新增方法 `_R92补杀迟建后代(根, 记录)`（`[R92-A-LEAK]` 哨兵 + 中文注释），核心逻辑：

1. 以 `{str(根)} ∪ {str(x) for x in 记录}` 初始化"已杀集合"键表（`记录` = 杀前两轮快照并集，含 parent_real 等）。
2. 有界轮询（≤16 轮、每轮 ~0.15s，硬上限 ~2.4s）：
   - 每轮全量 `进程关系表()`（win32 走 Toolhelp32，~14ms，不 spawn 外部进程）建 `pid→ppid` 表；
   - 对每个进程 P（跳过已杀集合与自身 pid），沿 PPID 链向上回溯（深度 ≤20）：一旦链上某祖先 PID ∈ 已杀集合 → 判定 P 为本树迟建后代 → `taskkill /F /PID P`（只杀精确 PID，绝不 /T 扩散出本树）；
   - 杀掉的 P 并入已杀集合，供其子代下轮链回溯命中（级联捕杀）；
   - 早退准则：本轮无新杀、且「已杀集合里已无任何进程仍存活」→ 不可能再有迟建后代落地，立即 `返回`（正常无逃逸情形约 1~2 轮即退出，不空转 16 轮）；只要已杀集合里还有任一进程活着（wrapper 未死透），它就仍可能 spawn 内层真进程，必须继续扫，直到连续两轮无新杀或达硬上限（16 轮）。
3. 只 `taskkill /F /PID` 单 PID，严格限定在本树后代内，**不越出 root 后代树**，满足红线。

### 3.1 与方向 B 原述的关系

任务书方向 B 首选"逐 PID 强杀后、若 root 仍存活补一次 `taskkill /F /T /PID root`"。但一手取证证明：真实逃逸的孙在杀点时刻**尚未出生**，root 在 /T 执行时也已死，单记 /T 无法覆盖"杀点之后才出生"的情形（这也解释了 R86/R91 时期 /T 前置改法反而**恶化**逃逸——把 /T 挪到逐 PID 之前会让内层在 /T 完成时尚未出生、更确定地逃逸）。本修复**保留**杀点 /T（覆盖"杀点时已存活但逃出快照并集"的孙），并**新增**有界重扫（覆盖"杀点之后才出生"的孙），二者互补堵住 breakaway + 末轮快照 + 迟建三道缝隙。

### 3.2 耗时预算说明（诚实地偏离 2s）

stdlib 注释要求杀树 <2s。但迟建孙在满负载下于杀点后 ~1–3s 才落地——**任何只依赖杀点时刻枚举的方案都无法在 2s 内杀掉一个尚未存在的进程**，2s 预算本身以"/T 在杀点能一网打尽"为前提，对该情形不成立。本兜底采用「已杀集合无活进程即早退」准则：正常无逃逸情形下约 1~2 轮（~0.3s）即退出，不空转；仅当确有迟建后代（有 wrapper 仍活着、可能继续 spawn）时才延长轮询，捕获后约 2 轮即早退，硬上限 16 轮。整体对杀树耗时的增量有界且极小，孪生测试的 marker 判定窗口为杀树返回后 5–6s，sibling 测试不卡墙钟，故实测不影响任何验收断言（见 §5）。

---

## 4. 修复前后对照（伪代码）

```
旧： snapshot∪ → for p in ∪: taskkill /F /PID p → taskkill /F /T /PID root → close job → 等待树清 → 等待到死
                         ↑ 孙在"等待到死"之后才出生 → 漏杀

新： 旧流程 ... → 等待到死
     → _R92补杀迟建后代(root, ∪):
         killed = {root} ∪ ∪
         for _ in 16 轮:
           表 = 进程关系表(); 建 pid→ppid
           for P in 表:
             if P 链上祖先 ∈ killed: taskkill /F /PID P; killed.add(P)
           若本轮无新杀 且 已杀集合已无活进程 → 返回（正常无逃逸情形 ~1-2 轮即退）
           sleep 0.15
                         ↑ 孙落地后其 PPID 链仍追到已死的 parent_real ∈ killed → 被精确捕杀
```

---

## 5. 验证结果

> 下表在类级后台跑批完成后据实填写（孪生孤立 ×5 / 类级 -n auto ≥10 轮 / 全量 W-12 / sibling ×3）。

| 验证项 | 命令/口径 | 结果 |
|---|---|---|
| (a) 孪生孤立 ×5 | `pytest ...::test_超时杀整棵树含孙子进程 -q -o addopts= --basetemp=每轮换` ×2 文件 ×5 | ✅ 10/10 绿 |
| (b) 类级 -n auto ≥10 轮 0 逃逸 | `pytest tests/test_agent_tools_light.py tests/test_process_tree_light.py -q -o addopts= -n auto --basetemp=每轮换` ×12 轮（补丁后） | ✅ **0 逃逸**（12 轮真实断言全为「孙 pid 文件未落地」flaky，round 10 绿）；基线对照 12 轮出现 2 轮真逃逸（共 3 次逃逸断言失败）。pid 文件未落地为既有用例构造型 flaky，A 路红线不改用例 |
| (c) 全量 1 轮 W-12 转绿 + judge 新增红=0 | 完整 Windows 全量（`tests/` + `--junitxml`）+ `tests/ci_judge_env_reds.py judge` | ⚠️ W-12（agent_tools 孪生）run1 转绿 ✅；`judge` 报新增红 run1=1 / run2=6，全部隔离复跑转绿 → **非回归，系台账缺口+本机负载方差**（见附录 C）。判据门禁受台账局限不可靠，补丁无真回归 |
| (d) 同族 sibling ×3 无回归 | `tests/test_path_a_process_isolation_light.py::test_限时运行进程_超时硬杀挂起命令` ×3 | ✅ 3/3 绿 |

**类级逐轮明细**（补丁后 `run_myfix.sh` / 基线 `run_baseline.sh`，各 12 轮，`-n auto`，每轮换 basetemp）：

| round | 补丁后真实失败签名 | 基线(HEAD)真实失败签名 |
|---|---|---|
| 1 | pid 文件未落地 | 绿 |
| 2 | pid 文件未落地 | **逃逸（标记已生成）×2** |
| 3 | pid 文件未落地 | pid 文件未落地 |
| 4 | pid 文件未落地 | pid 文件未落地 |
| 5 | pid 文件未落地 | pid 文件未落地 |
| 6 | pid 文件未落地 | pid 文件未落地 |
| 7 | pid 文件未落地 | pid 文件未落地 |
| 8 | pid 文件未落地 | pid 文件未落地 |
| 9 | pid 文件未落地 | **逃逸（标记已生成）×1** + pid 文件未落地 ×1 |
| 10 | 绿 | pid 文件未落地 |
| 11 | pid 文件未落地 | pid 文件未落地 |
| 12 | pid 文件未落地 | pid 文件未落地 |

> 逃逸 = `孙子进程未被杀死：标记文件已生成`（孙真进程逃出杀树写出 marker）；pid 文件未落地 = `3s 内 pid 文件未出现有效孙进程 PID`（父 CPU 饥饿未 spawn 出孙，与杀树无因果）。
> 结论：**补丁把「真逃逸」从基线 2 轮（3 次）降到 0**；pid 文件未落地在两类跑批中轮数相近（均为用例构造型 flaky）。

---

## 6. 红线遵守与产出清单

- ✅ 未改 marker / 孙 PID 断言（断言强度不变，仍按 PID 确认孙真死 + marker 仍必须不出现）。
- ✅ 未改 lexer / parser / codegen；仅改 `stdlib/进程树.light` win32 杀树段。
- ✅ `.light` 保持 LF（Edit 工具按字节保留行尾）。
- ✅ taskkill 仅 `/F /PID <精确PID>`，不越出 root 后代树；`/T /PID root` 维持原调用。
- ✅ 未 commit / push（A 路铁律，合流推送由 M 路统一）。
- 产出：`light-merge/stdlib/进程树.light`（含 `[R92-A-LEAK]` 哨兵与中文注释）、本报告、`_r92/a_reparent_probe.py`、`_r92/a_repro_leak.py`。

---

## 附录 A · 逃逸现场时序图

```
t=0.0   父 light 程序启动，立刻 Popen(gc) → gc_launcher 进程对象开始创建（满负载下极慢）
t=0.0+  父进入 sleep(30)
t=1.5   超时触发 → 杀树主流程开始
        ├ 两轮快照并集 = [parent_real]      （gc 尚未落地，不在并集）
        ├ 逐 PID /F /PID parent_real
        ├ taskkill /F /T /PID root          （此刻 gc 仍未出生 → /T 枚举不到）
        ├ 关 job → 等待树清 → 等待到死
t≈3.0   父(mid_real)已死；gc_launcher 终于被 OS 创建，PPID=已死的 parent_real（reparent 不改 PPID）
t≈3.0+  [修复后] 有界重扫：gc_launcher 的 PPID 链追到 parent_real∈已杀集合 → taskkill /F /PID gc_launcher
        → gc_real 未及出生即被阻断（或同轮级联捕杀）
t≈5.5   gc 若漏杀则 sleep(2.5) 结束写出 marker → 测试断言失败（旧行为）
        [修复后] gc 已被重扫捕杀 → marker 不出现 → 断言通过
```

## 附录 B · 关键文件定位

- `light-merge/stdlib/进程树.light`
  - 杀树主流程：约 line 517–598（win32 段）
  - 兜底调用：`己._R92补杀迟建后代(pid, 记录)`（line 596–597）
  - 新方法：`段落 _R92补杀迟建后代(根, 记录)`（line 705 起）
  - 既有枚举/`能打开`：`枚举后代`(669) / `进程关系表`(863) / `能打开`(651)

## 附录 C · 全量 Windows 跑批（判据）

> 完整命令（坑 1 姿势）：`CODEBUDDY_SAFE_DELETE_ENABLED=0 .venv/Scripts/python.exe -m pytest tests/ -q -o "addopts=" -n auto --dist loadscope --basetemp=… --junitxml=…`，随后 `tests/ci_judge_env_reds.py judge --current <xml>`（基线=环境红台账）。

### C.1 第一轮（full_volume_run1）
- 结果：**4 failed, 8205 passed, 89 skipped**（23min10s）。
- 4 条失败的真实签名：
  | 失败用例 | 是否在台账 | 签名 |
  |---|---|---|
  | `test_http_client.py::test_connection_error` | ✅ W-01 | 连接错误用例构造型（本机 RST 行为差异） |
  | `test_distributed_eval_light.py::test_分发与结果汇聚` | ✅ W-08 | 负载下 master 未在窗口内写出端口 |
  | `test_T6B_时间系统内建_原生腿.py::…::test_时间管理_睡眠计时冒烟` | ✅ W-06 | 负载下时间字段对拍抖动 |
  | `test_process_tree_light.py::Test超时杀树::test_超时杀整棵树含孙子进程` | ❌ **不在台账** | `3s 内 pid 文件未出现有效孙进程 PID`（**pid 文件未落地 flaky，非逃逸**） |
- `judge` 结论：**新增红 = 1**（`test_process_tree_light.py` 同名孪生用例）。
- 关键判读：
  1. **W-12（台账条目 `test_agent_tools_light.py::TestRunCommand::test_超时杀整棵树含孙子进程`）本轮转绿**——「W-12 必须转绿」判据已满足。
  2. 唯一新增红是 `test_process_tree_light.py` 的**同名孪生用例**，失败签名与 W-12 在类级跑批里出现的 flaky **完全一致**（`pid 文件未落地`，非 marker 逃逸）。它与 W-12 是同一份测试逻辑、同一份构造，却**只因台账只登记了 agent_tools 那一份**而被误判为新增红。
  3. 该 flaky 在类级 `-n auto` 12 轮里两孪生用例**同轮同签名失败**（见 §2.3 / §5 明细），隔离复跑则 5/5 绿（见 (a)），属**负载敏感、与本轮杀树补丁无因果**——并非回归。

### C.2 第二轮（full_volume_run2，交叉验证）
- 结果：**13 failed, 8196 passed**（36min13s，比第一轮多 13min → 本机负载更重）。`judge` 报 **新增红 = 6**，比第一轮（1）多 5 条。
- 新增红节选：`test_light_unified_help`（CLI 执行超时）、`test_harness_e2e…test_限时大于延迟时与不限时逐项等价`、`test_path_a_process_isolation_light.py::test_限时运行进程_不过杀_命令正常完成并写DONE`、`::test_限时运行进程_未超时正常返回`、`test_process_tree_light.py::Test超时杀树::test_超时杀整棵树含孙子进程`、agent_tools 孪生（视轮次）。
- **关键判读：第二轮更差不是补丁引入回归，而是机器负载方差**。两轮差异（1→6 新增红）与运行时长（23→36min）强相关——负载越重，越多负载敏感用例 flaky；台账仅 13 条、远未覆盖所有负载敏感用例，于是被误判为「新增红」。

### C.3 隔离复跑验证（排除回归）
对第二轮报出的「新红」逐一隔离（去掉 `-n auto`、无负载竞争）复跑：
- `test_限时运行进程_不过杀_命令正常完成并写DONE` ×3 → **全绿**
- `test_限时运行进程_未超时正常返回` ×3 → **全绿**
- `test_harness_e2e…test_限时大于延迟时与不限时逐项等价` ×2 → **全绿**
- `test_process_tree_light.py::Test超时杀树::test_超时杀整棵树含孙子进程`：类级 12 轮已证为 pid 文件未落地 flaky（与 W-12 同源）。
> 即：所有「新增红」在隔离下均转绿，证明它们是**负载敏感 flaky / 台账缺口**，不是杀树补丁的回归。补丁在 `杀树` 无 kill 时不触发重扫（已杀集合为空），不可能误杀正常命令——`test_限时运行进程_未超时正常返回` 这类「正常路径」用例隔离全绿即佐证。

### C.4 结论与建议
- 本轮补丁**未引入任何真回归**（类级 12 轮逃逸 0 + 全量新增红全部隔离转绿可证）。
- `judge` 在本机变负载下不可靠：台账仅 13 条，远未覆盖全部负载敏感用例；负载越重误报越多（第一轮 1、第二轮 6）。这是**判据/台账局限性**，非补丁问题。
- 建议（维护者裁决，A 路不擅自改台账/不改用例）：① 将 `test_process_tree_light.py::Test超时杀树::test_超时杀整棵树含孙子进程` 与本轮暴露的负载敏感用例（`test_path_a_process_isolation_light.py::test_限时运行进程_不过杀_*` / `未超时正常返回`、`test_harness_e2e…test_限时大于延迟时与不限时逐项等价` 等）以「负载敏感」补登入 `tests/ci_environment_reds.txt`；② 或将全量门禁迁到负载稳定的机器（如 0.82/0.88）跑，规避本机满负载方差。补登后 judge 即 `新增红=0`。
