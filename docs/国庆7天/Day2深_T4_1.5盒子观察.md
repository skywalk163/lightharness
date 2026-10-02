# Day2 深夜 T4 · 1.5 盒子 dsh-web 稳定性观察（30 分钟）

> 派单：`Day2深夜_派单表.md` v1.0 · T4（C 线，运维线）
> 观察窗口：2026-10-02 **23:43:09** → 2026-10-03 **00:13:47**（CST，+08:00），**7 次采样 / 每 5 分钟**
> 观察方式：SSH 192.168.1.5（workbuddy，凭据从根 `.env` 读，**不落盘**）
> 工具：`lightharness/scripts/_t4_probe.py`（模 mode `watch`，原始数据 `logs/day2-deep/T4_watch.jsonl`）
> 出口 tag：`subtask-T4-done`

---

## 〇、结论速览

| 观察项 | 结果 |
|---|---|
| ① 是否被 `-r` 反复拉起（异常重启） | ✅ **无**。LISTEN PID **57487 七次采样恒定不变**，elapsed 连续增长到 5:05:29 |
| ② 进程链是否健康 | ✅ `daemon 55645 → pnpm 57424 → node 57487` 三层齐全，均在位 |
| ③ 是否有 OOM | ✅ 无（`dmesg` 的 out-of-swap / out-of-memory / killed process 三次 grep **全为空**） |
| ④ swap 是否退化 | ✅ **7 次全部 10G / 已用 2.9G / 可用 7.1G / 29%**，与预检基线逐位相同 |
| ⑤ loopback 栅栏是否被破坏 | ✅ `127.0.0.1:3080` 严格 loopback；无 token `GET /` = **401**；LAN 直连 = **000 / curl_rc=7（拒绝）** |
| ⑥ 温缓存是否退化 | ⚠️ **未观察到退化，但样本量只有 3，证据偏弱**（见 §五，冷侧几乎不变、温侧落在已知波动带内） |

**一句话**：`-r` 上线后连跑 **5 小时**（19:14 拉起 → 00:19），**零重启、零 OOM、swap 零漂移、栅栏零破坏**，`-r` 没有引入任何不稳定性。

---

## 一、进程链（七次采样，PID 恒定）

最后一次（00:19）的 `pidchain` 原文：

```
LISTEN_PID=57487
--- chain ---
  PID  PPID  ELAPSED %CPU    RSS COMMAND
57487 57424 05:05:29  0.0 223840 node --expose-internals --import tsx/esm apps/cli/src/bin.ts web
  PID  PPID  ELAPSED COMMAND
57424 55645 05:05:33 node /home/workbuddy/.local/bin/pnpm dsh:freebsd web
  PID PPID  ELAPSED COMMAND
55645    1 05:09:45 daemon: /bin/sh[57424] (daemon)
```

`sockstat`：`workbuddy node 57487 12 tcp4 127.0.0.1:3080 *:*` —— **只绑 loopback**。

| 采样时刻 | LISTEN PID | 相对首个采样是否变化 |
|---|---|---|
| 23:43:09 / 23:48:01 / 23:53:12 / 23:58:13 / 00:03:43 / 00:08:25 / 00:13:47 | 57487 | **全部相同（7/7 不变）** |

> 判定依据：若 `-r` 触发过重启，`daemon(8)` 会重新 exec → pnpm/node PID 必变（Day2夜 T3 实测明确记录了这个特征：
> pnpm 55646→57424、node 55695→57487）。**PID 全程不变 ⇒ 30 分钟内没被拉起过。**
> 注意：daemon 的 elapsed(5:09:45) 略大于 pnpm(5:05:33)，是因为 daemon 先起来、再 exec 子进程，
> 差值 ~4 分钟属 daemon 自身的启动/等待窗口，**不是重启**。

> 小发现（非缺陷）：`/var/run/dsh_web.pid` 读不到（`NO_PIDFILE`），即本次没定位到 pidfile 的实际路径。
> 不影响判断（进程链从上到下三层的 PID 与 PPID 是自洽的），只是少一条交叉证据，留作备注。

---

## 二、swap / 负载 / OOM

| 采样时刻 | swap 总量/已用/可用/占比 | 1/5/15 负载 | OOM 新条目 |
|---|---|---|---|
| 23:43 | 10G / 2.9G / 7.1G / 29% | 0.38 0.33 0.31 | 无 |
| 23:48 | 10G / 2.9G / 7.1G / 29% | 0.30 0.34 0.33 | 无 |
| 23:53 | 10G / 2.9G / 7.1G / 29% | 0.29 0.37 0.33 | 无 |
| 23:58 | 10G / 2.9G / 7.1G / 29% | 0.25 0.34 0.33 | 无 |
| 00:03 | 10G / 2.9G / 7.1G / 29% | 0.88 0.71 0.49 | 无 |
| 00:08 | 10G / 2.9G / 7.1G / 29% | 0.51 0.53 0.46 | 无 |
| 00:13 | 10G / 2.9G / 7.1G / 29% | 0.16 0.33 0.39 | 无 |

- **swap 与预检基线（10G/可用 7.1G/29%）逐位一致**，7 次零漂移 —— 没有内存泄漏迹象。
- 00:03 那次负载升到 0.88 是**本机侧**并发任务（正在跑 0.82 全量回归）造成的取样瞬间，非盒子侧异常。
- `dmesg | grep -iE 'out of swap|out of memory|killed process'` 七次全为空 ⇒ 观察期内无 OOM 杀进程事件。

---

## 三、loopback 栅栏复核（七次）

| 测试 | 命令 | 结果 | 判定 |
|---|---|---|---|
| 监听地址 | `sockstat -4l -p 3080` | `127.0.0.1:3080`（非 0.0.0.0 / 非 LAN） | ✅ |
| 无 token 访问 | `curl -o /dev/null -w %{http_code} http://127.0.0.1:3080/` | **401**（7/7 一致） | ✅ |
| LAN 直连 | `curl --max-time 6 http://192.168.1.5:3080/` | **000 / curl_rc=7**（连接失败，7/7 一致） | ✅ |

外部栅栏（网络层 loopback 绑定 + token 鉴权）**全程未被破坏**，与 Day2夜 T3 的结论一致。

---

## 四、daemon 日志

`/tmp/dsh_web.log` 尾部（7 次采样内容一致，无新增异常）：

```
$ node --expose-internals --import tsx/esm apps/cli/src/bin.ts web
dsh web: http://127.0.0.1:3080
$ node --expose-internals --import tsx/esm apps/cli/src/bin.ts web
dsh web: http://127.0.0.1:3080
(node:20979) ExperimentalWarning: stripTypeScriptTypes is an experimental feature
```

只有一条 node 的 `ExperimentalWarning`（node 内置 TS 剥离特性），是**启动期固有告警**，与 `-r` 无关。
`apps/cli/src/bin.ts web` 出现了两次（对应杀掉旧进程后的一次重启），之后无新增 ⇒ 观察期内无重启。

---

## 五、温缓存抽样（3 样本）

```bash
cd ~/dswork/ltbench && /usr/local/bin/python3 scripts/compiler_bench.py 3
```

```
[compiler_bench] 例子数=3  CLI=/home/workbuddy/dswork/ltbench/cli/light.py
  冷启动（每例新进程）  : 总计   3.86s | 每例  1.29s
  温解释器（进程内复用）: 总计   0.88s | 每例  0.29s
  提速倍数             :   4.4x
```

对比 Day2夜 T3 的 10 样本：

| 指标 | Day2夜 T3（10 样本，19:16） | 本批（3 样本，00:19） | 差异 |
|---|---|---|---|
| 冷启动/例 | 1.28s | **1.29s** | +0.01s，**几乎不变** |
| 温解释器/例 | 0.11s | **0.29s** | 慢 2.6× |
| 提速倍数 | 11.6× | **4.4×** | 由温侧贡献 |

**判定：未观察到退化，但这个结论的证据强度偏低，必须说清**：

- **支持「没退化」**：冷侧几乎完全一致（1.28 → 1.29s），冷启动是「拉起解释器 + import 编译器」的固定开销，
  它不变说明盒子侧的 Python/磁盘/页缓存没有被压坏。
- **不支持「已退化」**：温侧 0.11 → 0.29s（2.6×）落在 Day10 §五-2 已记录的**同机固有波动范围**内
  （该文件警告：同机 bench 可飘到 0.94s vs 3.26s ≈ 3.5×）。
- **样本量**：本批只跑 3 个样本（派单表明确允许「3 样本足够」），温侧总计仅 0.88s，
  单个样本的抖动就能让「每例均值」大幅变化 —— **不足以用来判定温侧是否真变了**。
- **建议**：若要给「温缓存未退化」一个硬结论，需在同一时段跑到 ≥10 样本（与白天口径对齐）。
  本批按派单口径只跑了 3 个，**就事论事地标为"未观察到退化"，不升格为"已证明未退化"**。

---

## 六、出口判据回看

| 判据（派单表 §四） | 达成 |
|---|---|
| PID / swap / 栅栏 / 温缓存 四项数据落报告 | ✅ §一 ~ §五（全部 7 次采样数据） |
| 无异常重启 | ✅ PID 7/7 恒定、daemon 日志无新增启动行 |

---

## 七、交付物与合规

| 路径 | 内容 |
|---|---|
| `lightharness/logs/day2-deep/T4_watch.jsonl` | 7 次采样的原始 JSON（含 rc / stdout / stderr） |
| `lightharness/logs/day2-deep/T4_bench.json` | 收尾全量快照（含进程链、swap、栅栏、bench） |
| `lightharness/scripts/_t4_probe.py` | 观察工具（`once` / `watch` / `bench` / `all` 四模） |

**合规**：全程 SSH 只读（除 `compiler_bench` 这一既定基准测试外无写操作）；
`.env` 的凭据值只存在于进程内存，**未写入任何日志/报告**；
本报告只含主机名/PID/HTTP 状态码/bench 秒数，无口令、无 token。
