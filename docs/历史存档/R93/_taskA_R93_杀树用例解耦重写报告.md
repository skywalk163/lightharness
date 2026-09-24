# R93 任务A · 杀树两用例结构解耦重写 — 交付报告

> 轮次：R93-A ｜ 2026-09-24 ｜ 承接 R93 任务分发书 A 路
> 改动面：**仅 `tests/`**（两杀树用例），`.light` / `src/` / `stdlib/` 零改动。不 commit / 不 push（M 路统一）。
> 哨兵：`[R93-A-DECOUPLE]`（两用例均可 grep）

---

## 1. 病根（一手查明，前几轮一直留尾巴的根因）

两用例：
- `tests/test_agent_tools_light.py::TestRunCommand::test_超时杀整棵树含孙子进程`
- `tests/test_process_tree_light.py::Test超时杀树::test_超时杀整棵树含孙子进程`（孪生同构）

旧写法：用 `run_command(timeout=1.5)` 或 `_跑(超时=1500)` 让**超时计时从 root 启动那一刻就开始**。
沙箱下 python 是**双层 wrapper**（launcher → real，探针实测），root 自己 bootstrap 到
「能 `Popen(孙)` + 写 pid 文件」这一步，在 10 核打满时可能 **>1.5s**。于是 1.5s 到、杀树把
还没写完 pid 的父脚本杀了 → pid 文件永不出现 → `3s 内 pid 未落地` 假红（R90/R91/R92 一直靠
调赌注参数：timeout 0.8→1.5、窗口 3→6、stdout→pid 文件，但**「赌 1.5s 内能建好树」这个前提
在满载下不成立**，根子从没动过）。

R92-A 已把「真逃逸」（杀树漏杀孙）修掉（`stdlib/进程树.light` 的 `[R92-A-LEAK]` 有界重扫兜底）。
剩下的纯是「用例触发时机赌 CPU 调度」的假红。本路按用户授权**重写用例结构解耦**，断言不削弱。

---

## 2. 解耦设计（核心）

把「触发杀树」与「树已建好」彻底分离：

1. **树自建**：测试直接用生产 `进程树` 类拉起 root（`进程树.启动()` = `run_command` 内部同款
   启动路径，含 Windows Job Object 绑定），但**不**走带短超时的 `等待()` —— 杀树计时根本没启动。
2. **先确认树建好**：独立轮询等 pid 文件落地 **且** `_进程活(孙pid)` 为真（最多 **10s**）。
   这一步给足时间，满载下也不怕，因为此时还没开始杀树。
3. **再主动杀树**：树确已建好后，才调用真实杀树入口 `进程树.杀树(200)` —— 内部走
   `taskkill /F /T /PID root` + 按 PID 逐个补杀 + **`[R92-A-LEAK]` 有界重扫兜底**
   （精确覆盖 R92-A 修的「迟建内层真 python」场景），**绝不绕开它自写 taskkill**。
4. **断言一字不削弱**：
   - 断言一：孙必须按 PID 确认真死（轮询 `_进程活` 最多 5s；进程被强杀后对象/PID 会短暂残留，需轮询）。
   - 断言二：孙若活着会在 2.5s 后写 marker；被杀死则不会。给 3s 观察窗 —— 若杀树**过迟**
     （孙已写出 marker 才被杀）也会被这一条抓出，是比断言一更敏锐的「杀树过迟」探针。

父脚本保持双层 wrapper（`sys.executable` 拉起，孙也是 launcher→real 两层），真覆盖迟建内层场景。

---

## 3. 改动文件

| 文件 | 改动 |
|---|---|
| `light-merge/tests/test_agent_tools_light.py` | 新增 `from 进程树 import 进程树`；重写 `TestRunCommand::test_超时杀整棵树含孙子进程`（去掉 `run_command(timeout=1.5)` 赌时序，改 `进程树.启动()` + 轮询 + `进程树.杀树()`），加 `[R93-A-DECOUPLE]` 哨兵与注释 |
| `light-merge/tests/test_process_tree_light.py` | 重写 `Test超时杀树::test_超时杀整棵树含孙子进程`（同上解耦，孪生同改），孙脚本 sleep 30→2.5 使断言二非恒真 |

> 语法核心（lexer/parser/codegen）零改动；`.light` / `stdlib/进程树.light` 零改动；仅 `tests/`。

---

## 4. 验证结果（一手，落盘 `_r93/`）

### (a) 孤立串行 ×5 —— ✅ 全绿
`_r93/a_validate.py` 驱动，两用例单独串行 5 轮：
```
iso #0..#4: RC=0  2 passed   (rc_list=[0,0,0,0,0])
```

### (b) 类级 -n auto 15 轮 —— ✅ 两用例 0 假红
两测试类（`TestRunCommand` / `Test超时杀树`）在 `-n auto`（10 worker）下跑 15 轮，每轮换 basetemp：
```
round #00..#13: RC=0  25 passed, 2 skipped
round #14:     RC=1  1 failed, 24 passed, 2 skipped   ← 非本路用例（见 §6）
rc_list=[0,0,0,0,0,0,0,0,0,0,0,0,0,0,1]
```
**两杀树用例在 15 轮中全部通过（0 假红）**，正是 R92 类级 12 轮里反复出现的「pid 未落地」假红已被消除。

### (b') 复跑 10 轮 —— ✅ 全绿，佐证 round#14 是瞬时峰值
`_r93/a_rerun.py` 再跑 10 轮类级 -n auto，逐轮记录失败用例：
```
round #00..#09: RC=0  failed=[]  OUR_FAILED=[]   （含多轮 55s 峰值负载）
```
**两杀树用例 25/25 全绿（15+10），0 假红**。

### (c) 全量 1 轮（坑①姿势：串行，`-o addopts= --basetemp + CODEBUDDY_SAFE_DELETE_ENABLED=0`，pit①未含 `-n`）
- **结果：✅ 两用例绿**。后台 `1W3a4S`（`_r93/a_full_run3_serial.log`）：`1 failed, 8207 passed, 90 skipped, 12 xfailed, 2 xpassed`（3991s）。
- 两杀树用例**均未出现在 FAILED 列表**；全量唯一失败 = `tests/test_http_client.py::test_connection_error`（网络连通性测试，本路未触碰该文件 → 环境/网络预存失败，与进程树/杀树无关，交 B 路 judge 判定）。
- 判据「全量 1 轮两用例绿」达成；「judge 新增红=0」由 B 路补登后判定（本路两用例非新增红）。

### (c') 全量 `-n auto`（=10）跑过一次，暴露**新**失败模式（非本路之过，交 B 路）
曾按 `-n auto` 跑全量（`_r93/a_full_run2.log`，RC=1 / 11 failed / 8198 passed）：
`tests/test_process_tree_light.py::Test超时杀树::test_超时杀整棵树含孙子进程` 失败于
`assert gc_pid is not None`（10s 内 pid 文件未出现）。**但这是与旧写法完全不同的失败模式**：
- 旧假红根因 = 杀树计时从 root 启动就开、1.5s 赌 bootstrap；**解耦已消除该竞态**（类级 25/25 全绿已证杀树逻辑正确）。
- 本次失败 = 整机被 **8000 并发测试子进程打满 10 核**，root（双层 wrapper python）**自身 bootstrap 到「Popen 孙+写 pid」这一步 >10s**，pid 文件来不及落地。
- 断言文案已显式归因：「树根本没建好（非杀树之过）」——**不是杀树漏杀**，是负载饱和下的启动延迟。
- 同轮还有 `Test基本退出::test_非零退出码`、`test_stderr与stdout分离`、`Test环境控制::test_环境黑名单过滤`、`TestL167等待进程超时回收` 等一众**进程类用例**集体失败 → 系统性负载敏感，正是 B 路（Windows 门禁 worker 固化）要降 worker 数解决的。
- **A 路不靠加窗口压**：bootstrap 等待是合法等待，但若在 `-n auto=10` 满载下加窗口仍可能因机器持续饱和而失败；正确处置是 B 路降 worker（如 -n 6/4）使 bootstrap 得以完成，届时即便全量 `-n auto`(降后) 也会绿。本路保持 10s 合法 bootstrap 窗口，不退化成掩盖。

### (d) 同族超时触发覆盖 `test_path_a_process_isolation_light.py::test_限时运行进程_超时硬杀挂起命令`（W-11）×3 —— ✅ 全绿
```
run 1/2/3: 1 passed   （RC=0 各）
```
W-11 走 `编排.限时运行进程 → 进程树.等待(超时) → 进程树.杀树()`，覆盖「超时能不能触发杀树」，
与 A 路两用例（专注「杀已建好的树」）互补，覆盖无缺口。

---

## 5. 覆盖性说明（消除"砍掉 run_command 超时测试"的疑虑）

- `代理工具集.run_command` 与 `编排.限时运行进程`（W-11）**底层都委托同一个 `进程树.杀树()`**
  （`代理工具集.light:629-634` 建 `进程树` 调 `等待()`；`编排.light:64` 同）。
- W-11 已覆盖「超时触发杀树」；A 路两用例改为覆盖「杀树能不能杀掉一棵已建好的双层 wrapper 树」。
- **A 路两用例仍走真实杀树路径**（直接调 `进程树.杀树()`，覆盖 `[R92-A-LEAK]` 兜底），未削弱、未 no-op。

---

## 6. 一轮异常的红（与本路无关，交 B 路）

`a_class_round_14.log` 显示 round#14 唯一失败为
`tests/test_agent_tools_light.py::TestRunCommand::test_正常执行取输出和退出码`
（一条平凡的 `print('hello from cmd')` 命令，返回 `[退出码: 1][超时: 进程树已被杀死]`——
即 `run_command` 把它当超时杀了）。该用例**未被本路改动**。

根因：**`-n auto` 峰值负载**（该轮总时长 50.7s vs 常态 ~30s，整机 10 核被打满）导致平凡 python
子进程启动/完成被调度饿死、超过其 `命令超时=10s`，被 `run_command` 判超时强杀。
- 复跑 10 轮（含 55s 峰值负载轮）**未复现** → 属瞬时全量负载敏感红，非本路引入、非本路两用例。
- 这正是 B 路（Windows 门禁 worker 固化 + 负载敏感台账补登）要登记/收敛的对象，**A 路不靠加窗口压**，如实移交 M/B。

---

## 7. 判据达成对照（任务书 §判据）

| 判据 | 状态 |
|---|---|
| 两用例改完，哨兵 `[R93-A-DECOUPLE]` 可 grep | ✅ |
| 类级 -n auto 15 轮 0 假红（针对两杀树用例） | ✅（25/25 含复跑） |
| 全量 1 轮两用例绿（坑①串行姿势） | ✅（8207 passed / 唯一失败=无关 http 网络测试） |
| 全量 `-n auto`=10 暴露的新失败模式 | 已定位：bootstrap 满载 >10s（系统负载敏感，非杀树之过，交 B 路降 worker） |
| 断言语义未削弱（孙按 PID 判死 + marker 不出现） | ✅ |
| 走真杀树路径（覆盖 R92-A 兜底 `[R92-A-LEAK]`） | ✅ |
| 语法核心零改动、`.light` 未动 | ✅ |
| 不 commit/push | ✅（M 路统一） |

## 8. 红线遵守

- ⛔ 未改 marker/孙 PID 断言为恒真（断言二仍 3s 观察窗，杀树过迟可抓）。
- ⛔ 未绕开真杀树路径自写 taskkill（直接调 `进程树.杀树()`）。
- ⛔ 未 commit/push；未动 lexer/parser/codegen；`.light` 不在本路改动范围。

## 9. 产物清单（工作区根 / `light-merge/`）

- `_taskA_R93_杀树用例解耦重写报告.md`（本报告）
- `light-merge/tests/test_agent_tools_light.py`（重写 + import）
- `light-merge/tests/test_process_tree_light.py`（重写）
- `_r93/a_validate.py` + `a_iso_*.log` + `a_class_round_*.log` + `a_summary.txt`
- `_r93/a_rerun.py` + `a_rerun_round_*.log` + `a_rerun_summary.txt`
- `_r93/a_full_run2.log`（全量，进行中）
