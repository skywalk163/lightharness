# 第45轮 任务4：`test_子进程后台` flaky 加固

## 1. 真因链（不是「时序问题」这种含糊结论）

现象：全量 pytest 偶发红；单独复跑恒绿。

复现过程与数据：

| 复现方式 | 结果 |
|---|---|
| 直接 `python 运行.py examples/test_子进程后台.light` × 6 | 6/6 绿 |
| 复刻 `_run()` 条件（cwd=临时目录 + 管道捕获）× 15 | 15/15 绿 |
| 全量 pytest（1232 个用例，每个 spawn 一个解释器） | 偶发红 |

⇒ flaky 只在**高系统负载**下出现，根因是两条叠加：

1. **等待阈值太紧**：正常场景固定 `等待后台(进程, 5)`。全量回归时系统要连跑
   400+ 个子进程，spawn 一个解释器的耗时被拉长，撞上 5s 就判超时 → 断言
   「后台进程成功」失败。
2. **命令写死 `python`**：依赖 PATH 上恰好有这个名字——Windows 上可能是应用商店
   别名（或压根没有），FreeBSD 上只有 `python3`。PATH 上若解析到别的东西，
   退出码分支也会走偏。

### 顺带发现并修复的真缺陷：**L-167 超时 kill 后不收尸**

`stdlib/外部命令.py::等待进程` 原实现：

```python
except subprocess.TimeoutExpired:
    进程.kill()
    return 命令结果(返回码=-1, ...)
```

`kill()` 之后**没有再 `communicate()`**：

- POSIX：进程进入「已终止但未回收」状态，成为**僵尸**占着 PID 表项；
- Windows：管道读线程仍在跑，`Popen` 析构时抛 `ResourceWarning`；
- 全量回归连跑数百个用例时这些残留**累积**，抬高系统空闲负载，
  进而让**后续**用例的进程启动更慢——正是本例 flaky 的放大器。

修复：`kill()` 后补 `communicate()`（既回收僵尸，也排空管道），异常不影响超时语义。

## 2. 加固内容（**不掩盖语义，只消除环境敏感性**）

`examples/test_子进程后台.light`：

| 项 | 改前 | 改后 | 理由 |
|---|---|---|---|
| 解释器 | 写死 `"python -c ..."` | `环境变量("HARNESS_PY", "python")` + 加引号 | 不依赖 PATH 上恰好有 `python`；容纳路径空格 |
| 正常场景等待 | 5s | **20s** | 外层护栏上限 300s，安全；消除负载敏感性 |
| 超时场景等待 | 1s | 2s | 仍必然超时（子进程 sleep 3s），判定不变 |
| 失败诊断 | 只给标签 | 带 `输出` / `错误` | 下次再红可直接归因 |

`lightharness/运行.py`：注入 `HARNESS_PY = sys.executable`（`setdefault`，不覆盖用户设置）。

`examples/test_子进程码.light`：同一根因（写死 `python`），一并改为 `HARNESS_PY`。

**语义断言一条没少**：成功 / 退出码 / `输出含 done` / 超时成功=假 / 超时码=-1，全部保留。

## 3. 验收

| 项 | 结果 |
|---|---|
| `test_子进程后台.light` | rc=0 |
| `test_子进程码.light` | rc=0 |
| 反跑（把 `done` 改 `nope` 即红） | 语义未弱化，断言未减少 |
| 全量回归 | 见 `_task1_R45_双平台回归.md` |

## 4. 交付物

- `lightharness/stdlib/外部命令.py`（L-167 收尸修复）
- `lightharness/运行.py`（注入 `HARNESS_PY`）
- `lightharness/examples/test_子进程后台.light`（加固）
- `lightharness/examples/test_子进程码.light`（同根因加固）
- 缺陷账新增 **L-167**
