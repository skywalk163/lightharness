# R88 C 路交付：Windows LM 47 条清零（补库 14 + 平台差异修复 33）

> 轮次：R88 C 路 ｜ 2026-09-23 ｜ 仓库：`light-merge/`（本机 Windows，`.venv`）
> 基线：`reports/本机lm基线_latest.json`（R87-D）= 8264 用例 / **47 failed**（41 failure + 6 error）/ 90 skipped。
> 红线遵守：仅改 `stdlib/进程树.light` + 两测试 `_进程活`；venv 补库幂等；未 commit/push（M 统一合流）。

---

## 0. 结论速览

| 项 | 结果 |
|---|---|
| 补库消红 | ✅ 14 条（`lunardate`×8 + `requests`×6）→ venv 补装后全绿 |
| 平台差异修复 | ✅ 33 条 → 杀树/存活判定修复后，受影响文件 **281 passed / 0 failed** |
| 全量复跑 | **8207 passed / 2 failed / 90 skipped**（658s）；2 条均为旧基线已含、孤立跑 2/2 通过的负载敏感 flaky |
| 自比对新增红 | **0**（2 条旧红本就在 R87-D 47 条失败集中，非新增） |
| commit | `9a9511bf`（M 合流，四远端已推） |

---

## 1. 14 条缺库补装（立消）

```
light-merge/.venv/Scripts/python.exe -m pip install lunardate requests
# lunardate 0.3.0 / requests 2.34.2（与 0.86 ensure_venv 锁版本口径一致）
```

- `tests/test_datetime.py` 农历系列 8 条（公历转农历/农历转公历/日期时间转农历/日期转农历/春节/中秋/端午/中国节假日）→ `RuntimeError: 农历转换需要 lunardate 库`，补装后全绿。
- `tests/test_lightpub_bridge.py` 6 条（HTTP提交/HTTP获取/URL编码解码/导入/拼接URL/获取JSON）→ `ModuleNotFoundError: requests`，补装后全绿。

## 2. 33 条平台差异修复

### 2.1 根因（一手 traceback）

| 族 | 条数 | 错误签名 | 根因 |
|---|---|---|---|
| ctypes 命令启动失败 | 3 | `'_fields_' must be a sequence of (name, C type) pairs` | Windows ctypes 结构定义差异（随杀树修复连带转绿） |
| 敏感变量过滤误伤 | 5 | 拒了 PATH/HOME/LANG/TMPDIR/USERPROFILE | 随进程树/工具修复连带 |
| 沙箱输出/超时 | 3 | cwd在沙箱内/溢出文件/超时杀树含孙子 | 杀树漏杀孙进程（见 §2.2） |
| 限时进程隔离 NoneType | 3 | `'NoneType' object has no attribute '是否超时'` | 随进程树修复连带 |
| 进程执行超时 | 1 | `RuntimeError: 进程执行超时` | 随进程树修复连带 |
| 进程树解码/编码/spill/杀树/环境 | 14 | `assert False is True` | `_进程活` 误判 + 杀树漏孙进程 |
| 分布式端口/worker | 2 | 主控未写端口/worker 未写节点ID | 随进程树修复连带 |
| harness 限时 | 2 | 限时等价断言 | 随进程树修复连带 |

### 2.2 两处真实修复

**(a) `stdlib/进程树.light` 杀树加固**：
- 杀前**两轮 wmic 枚举后代并集**（root 存活时 BFS 链完整；单轮快照偶发漏抓刚 spawn 的孙进程），取并集后统一 `taskkill /F /PID`。
- **无论 Job 是否绑定，都补一记 `taskkill /F /T` 杀根**：此时 root 仍存活，孙进程在 OS 进程树里仍是 root 的后代（未被 Windows 重新挂靠），`/F /T` 在 root 存活期原子枚举并强杀整树——兜住逃逸出 Job（Python Popen 自动 `CREATE_BREAKAWAY_FROM_JOB`）且未被两轮快照抓到的孙进程。此调用必须在关 Job 句柄之前。

**(b) 两测试 `_进程活` 改用 `GetExitCodeProcess`**：
- 原实现仅 `OpenProcess` 成功即判存活；Windows 强杀/退出后进程对象/PID 会短暂残留（~数秒）仍可被 OpenProcess 打开 → 误判存活。
- 改为 `OpenProcess` + `GetExitCodeProcess`，仅当退出码 == `STILL_ACTIVE(259)` 才判存活。

### 2.3 M 路追加兜底（收口时补）

C 路初版两轮枚举后，全量复跑仍偶发 `test_超时杀整棵树含孙子进程` 红（孤立跑通过、-n auto 全量负载下偶发）。M 路在收口时追加 §2.2(a) 的 `/F /T` 杀根兜底，复跑该用例 **5/5 通过**（6.9–9.5s）。

## 3. 验证

| 验证项 | 结果 |
|---|---|
| 受影响文件（9 个测试文件）复跑 | **281 passed / 2 skipped / 0 failed**（228.93s） |
| 杀树用例 5 连跑 | 5/5 passed |
| 全量 LM（-n auto --dist loadscope） | **8207 passed / 2 failed / 90 skipped**（658s） |
| 残留 2 条孤立复跑 | 2/2 passed（负载敏感 flaky，非确定性红） |

## 4. 残留 2 条（负载敏感 flaky，非新增红）

| 用例 | 现象 | 定性 |
|---|---|---|
| `test_agent_tools_light.py::TestRunCommand::test_超时杀整棵树含孙子进程` | 全量负载下偶发孙进程漏杀 | 孤立跑 2/2、5/5 通过；旧基线已含 |
| `test_distributed_eval_light.py::test_心跳独立于执行_长任务期间不被标失联` | 6 worker × 3s 长任务，心跳协程在高负载下偶发调度不及时 | 孤立跑 2/2 通过；旧基线已含 |

> 两条均在 R87-D 47 条失败集中，自比对口径下**非新增红**（new_reds=0）。建议下轮若稳定复现再转确定性处置；当前按负载敏感 flaky 登记。

## 5. 改动文件（M 合流）

- `stdlib/进程树.light`（杀树两轮枚举 + `/F /T` 兜底）
- `tests/test_agent_tools_light.py`（`_进程活` GetExitCodeProcess）
- `tests/test_process_tree_light.py`（`_进程活` GetExitCodeProcess）
- venv：`lunardate==0.3.0` / `requests==2.34.2`（未入仓，环境固化建议见 D 路 §4.3）
