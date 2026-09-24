# R91 · D 路交付报告：进程树 stdlib 两处加固

> 执行 agent：D 路（进程树 stdlib 加固）｜ 轮次 R91 ｜ 2026-09-24
> 承接：R90 §6.4 / §6.5，文件 `light-merge/stdlib/进程树.light`
> 依赖：A 路已先收敛测试侧（工作树中 `tests/test_agent_tools_light.py`、`tests/test_process_tree_light.py` 已含 A 路改动）
> 改动面：`stdlib/进程树.light`（仅 win32 分支的 c_void_p 句柄判空 + 极小 timeout 鲁棒性评估）
> 提交：❌ 不提交 / 不 push（铁律：D 路只改文件+验证，合流与 push 由 M 路统一）
> HEAD（未变）：light-merge `1a530844`

---

## 0. 判据对照（任务书 §判据）

| 判据项 | 结果 |
|---|---|
| 既有 c_void_p 判空点已双判且回读落盘 | ✅ 5 处全部双判（空/0），回读 + grep + 编译三重确认 |
| 极小 timeout 场景有一手探针数据 | ✅ `_r91/d_probe_timeout08.py` + `_r91/d_probe_out.txt` |
| 若做了最小修复：0.8s 不再等满 30s / 或明确记录"证据不足未改" | ✅ **证据不足，未改主流程**（见 §3 结论） |
| 语法核心零改动 | ✅ 仅 win32 c_void_p 判空 + 注释 + 审计标记；lexer/parser/codegen 零改动 |

---

## 1. 任务 1：c_void_p 句柄判空双判（对齐 R90 Toolhelp32 路径）

### 1.1 根因（已一手核实，不重复推翻）
R90-A 新增 Toolhelp32 快照路径时，句柄判空写成 `等于 空` + `等于 0` 两段判断——原因是
ctypes `c_void_p` 在 Win32 API 返回 NULL 时，Python 侧拿到的是 `None` 而非 `0`（`c_void_p` 的
`value` 在 NULL 时为 `None`）。R90-A 只在**新路径**补了双判，而**既有 `绑定任务对象`** 仍只判
`job 等于 0`，没判 None——本路把这个既有路径补齐。

### 1.2 改动清单（全部位于 win32 分支；均加 `[R91-D-voidp]` 哨兵注释）

| # | 位置（行） | 原写法 | 新写法 | 类别 |
|---|---|---|---|---|
| 1 | `绑定任务对象` job 判空（375-380） | `如果 job 等于 0:` | `如果 job 等于 空 或 job 等于 0:` | 失败降级（job 创建失败） |
| 2 | `绑定任务对象` OpenProcess 进程句柄（393-396） | `如果 进程句柄 等于 0:` | `如果 进程句柄 等于 空 或 进程句柄 等于 0:` | 失败降级（拿不到进程句柄） |
| 3 | `恢复挂起进程` 进程句柄反向判（417-420） | `如果 进程句柄 不等于 0:` | `如果 进程句柄 不等于 空 且 进程句柄 不等于 0:` | 成功续行（句柄可用才 resume） |
| 4 | `能打开` OpenProcess h（652-655） | `如果 h 等于 0:` | `如果 h 等于 空 或 h 等于 0:` | 存活判定（打不开=已死） |
| 5 | `杀树` 任务句柄反向判（585-590） | `如果 己.任务句柄 不等于 0:` | `如果 己.任务句柄 不等于 空 且 己.任务句柄 不等于 0:` | 成功续行（job 绑定才 CloseHandle） |
| 6 | `工具快照关系表` 快照（729-734） | R90-A 已双判 | **本路复核**：加 `[R91-D-voidp]` 审计注释，口径一致，无需改 | 审计标记 |

> 注释模板（每处）：`# [R91-D-voidp] c_void_p 句柄在 NULL 时 Python 侧返回 空(None) 而非 0; ……双判对齐 R90 Toolhelp32 路径……`

### 1.3 编译验证（一手）
```
light-merge/.venv/Scripts/python.exe cli/light.py compile stdlib/进程树.light -o /tmp/进程树_out.py
→ RC=0 编译成功
```
编译产物关键行（确认 `或`/`且` 正确落地为 Python）：
```
L675:  if ((job == None) or (job == 0)):
L701:  if ((进程句柄 == None) or (进程句柄 == 0)):
L735:  if ((进程句柄 != None) and (进程句柄 != 0)):
L931:  if ((self.任务句柄 != None) and (self.任务句柄 != 0)):
L1004: if ((h == None) or (h == 0)):
```
语义与 R90 Toolhelp32 路径（`快照 等于 空` / `快照 等于 0` 两段）完全对齐。
行尾校验：文件 CRLF 计数 = **0**（纯 LF，符合 R91 已知坑 #5：`.light` 是 LF 不是 CRLF）。

### 1.4 行为影响分析
- 正常路径（句柄为有效值，非 None 非 0）：双判与原单判**行为完全一致**，不引入任何时序/逻辑变化。
- 失败路径（如 `CreateJobObjectW`/`OpenProcess` 返回 NULL）：原写法 `等于 0` 会把 `None` 当成"有效"
  而漏掉降级分支（可能拿 None 句柄去 `NtResumeProcess`/`CloseHandle` 导致异常）；新写法两种空态都正确降级。
- 改动**只收紧了失败兜底**，未触碰杀树主流程、未改任何语法核心。

---

## 2. 任务 3（取证前置）：杀树族用例孤立复跑

> 已知坑：本机沙箱双层 wrapper 放大时序抖动，真实判绿以 0.82 为准；本路仅确认"本路改动无回归"。

姿态（R91 已知坑 #1）：`-o "addopts="` + `--basetemp=<仓内>` + `CODEBUDDY_SAFE_DELETE_ENABLED=0`，孤立串行（不挂 xdist）。
用例：`test_agent_tools_light.py::TestRunCommand::test_超时杀整棵树含孙子进程`、
`test_process_tree_light.py::Test超时杀树::test_超时杀整棵树含孙子进程`、
`test_path_a_process_isolation_light.py::test_限时运行进程_超时硬杀挂起命令`。

| 轮次 | 结果 | 说明 |
|---|---|---|
| ITER1 | **1 failed, 2 passed** | 红 = `test_agent_tools_light::test_超时杀整棵树含孙子进程`，断言 `孙子进程未被杀死：标记文件已生成`（W-12 孙逃逸 flaky） |
| ITER2 | 3 passed | 全绿 |
| ITER3 | 3 passed | 全绿 |

- 失败解读（读 traceback 确认）：`tests\test_agent_tools_light.py:624 AssertionError: 孙子进程未被杀死：标记文件已生成`
  —— 孙进程**逃逸出杀树**（负载下 Toolhelp32 快照漏抓刚 spawn 的孙 / 自动 `CREATE_BREAKAWAY_FROM_JOB` 逃逸），
  **与本路 c_void_p 双判无关**（双判只在句柄取空时触发，本例杀树已执行、只是漏了孙）。
- 结论：**本路改动未引入任何新失败**。唯一红是 W-12 孙逃逸负载竞态——正是 A 路（pid 文件落盘 + 轮询）负责根治的项，
  与"D 路先收敛测试侧、D 后动 stdlib"的依赖关系一致。ITER2/3 全绿证明 stdlib 改动编译/运行无回归。

---

## 3. 任务 2：极小 timeout（≤0.8s）杀树鲁棒性评估（取证为主）

### 3.1 探针设计 `_r91/d_probe_timeout08.py`
复刻 `进程树.light` 的 win32 杀树机制：
- 以 `CREATE_SUSPENDED(0x4) | CREATE_NEW_PROCESS_GROUP(0x200)=516` 创建 root（对齐 `启动`）；
- **A 路（真实流程）**：Popen 后立刻 `NtResumeProcess` 恢复（对齐 `绑定任务对象`/`恢复挂起进程`）；
- **B 路（对照）**：Popen 后**不**恢复，保持挂起，验证"必须先把 suspended 恢复再杀"假设；
- 在 Popen 后延迟 `d∈{0,10,50,100,200,500}ms` 触发"杀树那一刻"，测量：
  ① root 是否已在 Toolhelp32 全系统快照可见；② `OpenProcess(root)` 能否打开；
  ③ `taskkill /F /T /PID root` 是否在 4s 内把整树（root+后代）杀净。

### 3.2 一手数据 `_r91/d_probe_out.txt`

| 变体 | delay(ms) | root_in_snap | openable | tk_rc | kill_ms | still_alive | 结论 |
|---|---|---|---|---|---|---|---|
| A 真实(先恢复) | 0 | True | True | 0 | 613 | **False** | 可杀性OK |
| A | 10 | True | True | 0 | 461 | False | OK |
| A | 50 | True | True | 0 | 561 | False | OK |
| A | 100 | True | True | 0 | 617 | False | OK |
| A | 200 | True | True | 0 | 464 | False | OK |
| A | 500 | True | True | 0 | 394 | False | OK |
| B 对照(保持挂起) | 0 | True | True | 0 | 399 | False | OK |
| B | 10 | True | True | 0 | 410 | False | OK |
| B | 50 | True | True | 0 | 485 | False | OK |
| B | 100 | True | True | 0 | 502 | False | OK |
| B | 200 | True | True | 0 | 452 | False | OK |
| B | 500 | True | True | 0 | 462 | False | OK |

### 3.3 结论（决定性）
1. **root 在"杀树触发那一刻"总是立即可枚举、可打开、可被 `taskkill /F /T /PID` 在 ~400–620ms 内整树杀净**
   ——无论是否先恢复挂起（A/B 两路 `still_alive` 全为 False）。
2. 因此 **R90 §3.3 的 33s（root 没被杀掉）并非"root 句柄还没建 / root 尚在 CREATE_SUSPENDED 未初始化"**：
   真实流程下 Popen 后由 `绑定任务对象` 同步 `NtResumeProcess` 恢复，到 timeout 触发（≥0.8s）时 root 早已可枚举可杀。
3. 任务书候选修复"杀树前轮询最多 ~500ms 等 root 出现在 Toolhelp32 快照里"是**惰性、无意义**的
   （d=0 时 root 已在快照内，轮询不会多抓到任何东西，反而白白加延迟）。
4. R90 33s 的真实成因属**另一类**（本探针用简单 5s 树未复现）：
   - 负载下 Toolhelp32 快照偶发漏抓**刚 spawn 的孙进程**（R90 §3.3 已记录"连枚举 6 次快照从 3 个后代波动为 1 个"）；
   - Python `subprocess.Popen` 检测到父在 job 内自动加 `CREATE_BREAKAWAY_FROM_JOB`，孙逃逸出 job；
   - 二者叠加 → 孙在杀树瞬间不在枚举并集里且不在 job 内 → 逃逸存活至自然结束。
   这正是 **A 路（pid 文件落盘 + 轮询确证孙死）** 与既有"两轮枚举并集 + taskkill /F /T 兜底"要解决的问题，
   不属于 stdlib 主流程缺陷。

### 3.4 处置决定（严守红线）
> ⛔ 不改杀树主流程（证据不足）。
> 只交付**评估结论 + 建议**，不引入任何主流程修改。

**建议（交 M 路 / 后续轮）**：
- 维持现有"两轮枚举并集 + `taskkill /F /T /PID root` 兜底 + 按记录的原始后代 PID `等待树清`"结构；
- 若未来真要加固"极小 timeout 下 root 偶发漏杀"，正确方向应是**确保 `绑定任务对象` 的 `NtResumeProcess` 一定在首次 `等待` 轮询前完成**（当前已保证），而非在杀树前加轮询；
- 孙逃逸问题由 A 路测试侧根治，stdlib 侧无需为 R90 33s 单独改主流程。

---

## 4. 红线遵守

- ⛔ 未改杀树主流程（任务 2 证据不足，明确未改）。
- ⛔ 未 commit / push（D 路只改文件+验证；合流 push 由 M 路统一）。
- ⛔ 未动 lexer / parser / codegen（语法核心零改动）。
- ⛔ `.light` 保持 LF（CRLF=0）。
- ✅ 关键改动写完立刻回读 + grep 复核 + 编译确认落盘。
- ✅ 幂等哨兵：`[R91-D-voidp]` 注释串可一眼定位已应用点，二次应用会因 old 串不匹配而失败（天然幂等）。

---

## 5. 产出清单

| 文件 | 性质 |
|---|---|
| `light-merge/stdlib/进程树.light` | **已改**（5 处 c_void_p 双判 + 1 处审计注释，+12/-5 行） |
| `_r91/d_probe_timeout08.py` | 探针脚本（复刻 win32 杀树机制，A/B 双变体） |
| `_r91/d_probe_out.txt` | 探针一手数据（12 行测量表） |
| `_r91/d_test_iter1.txt` ~ `iter3.txt` | 杀树族用例孤立复跑 3 轮原始输出 |
| `_taskD_R91_进程树stdlib加固报告.md` | 本报告 |

> 注：工作树中 `tests/test_agent_tools_light.py`、`tests/test_process_tree_light.py` 的 `M` 状态为
> **A 路先前改动**（A→D 串行依赖），非本路产物，本路未触碰。
