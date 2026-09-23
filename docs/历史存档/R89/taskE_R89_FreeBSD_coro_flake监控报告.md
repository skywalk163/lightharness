# R89-E 交付报告：FreeBSD 0.82 —— LM `test_coro_sleep_basic` flaky 监控

> 执行时间：2026-09-23 23:3x–23:5x（SSH 真机，后台跑完）｜ 目标机：`ai@192.168.0.82`（FreeBSD 15.1-STABLE）
> 结论：**维持 flaky 定性，未转为稳定红**；不新增确定性环境红台账条目。

---

## 1. 取证环境（一手，非推断）

```
$ uname -a
FreeBSD fb82 15.1-STABLE FreeBSD 15.1-STABLE stable/15-n285422-74c5995d2e8d GENERIC amd64
nproc = 8
```

| 项 | 值 |
|---|---|
| LM 副本 | `/tmp/r44-20260923-174825/light-merge`（**0.82 上最新副本，与 R88-B 同一份**；只动 /tmp，未碰系统/原仓） |
| 解释器 | `/usr/local/bin/python3.12` |
| 门禁三件套 | `LIGHT_MERGE=/tmp/r44-20260923-174825/light-merge`、`PYTHONPATH=<同上>/src`、`PATH=/tmp/r80b-shim:$PATH`（shim 内容实测 `exec /usr/local/bin/python3.12 "$@"`） |
| 用例定位 | `tests/test_llvm_net.py:722 def test_coro_sleep_basic`（`class TestB3EventLoop` 在 L719） |

---

## 2. (a) 隔离单跑 5 轮（不带 xdist）

命令：
```
cd /tmp/r44-20260923-174825/light-merge && \
LIGHT_MERGE=... PYTHONPATH=.../src PYTHONIOENCODING=utf-8 PATH=/tmp/r80b-shim:$PATH \
  /usr/local/bin/python3.12 -m pytest \
  'tests/test_llvm_net.py::TestB3EventLoop::test_coro_sleep_basic' -q --tb=long \
  -p no:cacheprovider -o addopts=
```

| 轮次 | PYTEST_RC | 用时 | 结果 |
|---|---|---|---|
| 1 | 0 | 4.06s | 1 passed |
| 2 | 0 | 3.65s | 1 passed |
| 3 | 0 | 3.66s | 1 passed |
| 4 | 0 | 3.63s | 1 passed |
| 5 | 0 | 3.70s | 1 passed |

**隔离通过率 5/5**，无一次失败 → 未出现「隔离也红」。

（另有一组更早的取证跑在旧副本 `/tmp/r41-1789552701/light-merge` 上，同样是 5/5 通过；
该组已作废并改用最新副本重跑，此处仅留痕说明曾有两个副本取样。）

---

## 3. (b) 负载复跑（全量 `tests/` + `-n 8 --dist loadscope`）

| 轮次 | PYTEST_RC | 结果 | 墙钟 |
|---|---|---|---|
| 1 | 0 | **8177 passed / 122 skipped / 11 xfailed / 2 xpassed / 0 failed** | 457s（7m37s） |
| 2 | 0 | **8175 passed / 124 skipped / 11 xfailed / 2 xpassed / 0 failed** | 391s（6m31s） |

两轮 `grep -n 'coro_sleep' <log>` **均无命中** → 在两轮全量负载下
`test_coro_sleep_basic` **一次都没失败**（连 R88-B 记录的那次「缺 `sleep后`」签名也未复现）。

### ⚠️ 方法论坑（本轮踩到并修正，建议写进下轮手册）

第一版取证用「单文件 `tests/test_llvm_net.py` + `-n 8 --dist loadscope`」制造负载，结果稳定
出现 3 条与本用例**无关**的失败：

```
FAILED tests/test_llvm_net.py::TestB2IOMultiplexing::test_poller_select_one_ready
FAILED tests/test_llvm_net.py::TestB3EventLoop::test_concurrent_echo
FAILED tests/test_llvm_net.py::TestB1SocketPrimitives::test_socket_connect_failure
RuntimeError: 端口 19100 被占用，测试无法继续（不自动+1重试）
OSError: [Errno 48] Address already in use
```

根因：`--dist loadscope` **按测试类分组**，同一文件里的多个 class 被拆到不同 xdist worker，
每个 worker 各自初始化模块级 `_port_cursor` 都从 19100 开始 → 端口撞车。
**这不是 coro 用例的负载信号，是取证方法本身的假红**。
修正后改用「全量 `tests/` + `-n 8 --dist loadscope`」（真实门禁口径），结论才有效。

---

## 4. 判定

**维持 flaky 定性，未转为稳定红。**

- 隔离 5/5 绿（不符合「确定性红」入账口径：确定性红要求隔离复跑 2/2 确定性 rc=1）；
- 负载 2 轮全量 0 failed、grep 无命中 → 本轮连「偶发红」都没复现；
- 因此 **不新增确定性环境红台账条目**（`tests/ci_environment_reds.txt` 仍为 3 条：E-01/E-02/E-06）；
- 继续沿用 R88-B 的处置通道：082 基线自比对（该条在基线失败集内）+ `lm-full` 关键词归因容忍。

`ci_judge_env_reds.py self-check` 复核：**台账条目数 3，新增红恒 0，全部 PASS**
（证明追加的取证留痕未破坏判据解析）。

### 已更新留痕

`lightharness/tests/ci_environment_reds.txt` 末尾追加「R89-E 复核」注释块（`#` 开头，不参与解析），
含：副本路径 / 隔离 5 轮 / 负载 2 轮数字 / 判定 / 上述方法论坑。

---

## 5. 若下轮转为稳定红的处置建议（预置）

1. **先分诊**：隔离单跑 ≥3 轮，若隔离也红 → 是真退化（kqueue 定时器未唤醒），
   走运行时归因（`stdlib/事件循环.light` 的 sleep 定时器注册/出列）；
   若仅负载下红 → 仍是调度/计时敏感，走 flaky 通道。
2. **修测试**（优先）：把「yield/恢复顺序」断言改成**有序子序列**判据
   （要求 `开始 → sleep前 → sleep后 → 结束` 的相对次序成立），而不是钉死完整列表——
   不削弱「sleep 之后必须恢复」这一本质语义。
3. **修运行时**（次选）：确认事件循环退出前是否 drain 了待触发的定时器
   （kqueue 的 `EVFILT_TIMER` 在负载下可能在最后一次 kevent 之后才到期）。
4. **转确定性红入账**（兜底）：满足「隔离 2/2 确定性 rc=1 + 对拍旧副本同签名」后，
   按现行口径写入 `ci_environment_reds.txt`。

---

## 6. 判据自查

| 判据 | 结果 |
|---|---|
| 5 轮隔离 + ≥1 轮负载复跑有数据 | ✅ 隔离 5/5、负载 2 轮（均全量 8k+ 用例） |
| flaky ↔ 稳定红判定明确 | ✅ 维持 flaky，未转稳定红 |
| 若转稳定红有处置建议 | ✅ §5 预置（本次未触发） |
| 只动 0.82 的 /tmp 副本 | ✅ |
| 未 commit/push | ✅ |
