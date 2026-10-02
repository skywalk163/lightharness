# Day2 夜场 T3 · 1.5 崩溃拉起修复（rcd 加 `-r`）+ 温缓存复核

> 派单：`Day2夜场_派单表.md` v1.2 · T3（B 线，远程）
> 契约：`Day2N_契约_T3_1.5崩溃拉起与复核.md`
> 执行时间：2026-10-02 19:06–19:18（CST）
> 出口 tag：`subtask-T3-done`

---

## 〇、结论速览

| 验收项 | 结果 |
|---|---|
| ① 崩溃拉起：kill 后自动恢复，PID 变化 | ✅ **机制生效**：daemon 不死、~3s 拉起新进程、PID 全新 |
| ① 完整恢复监听 ≤10s | ⚠️ **22s**（~3s daemon 重启 + ~19s pnpm/node 冷启动），超阈值但非 rcd 缺陷 |
| ② 自启未回归（rc.conf/rcd 安装状态） | ✅ `dsh_web_enable="YES"` 不变，rcd 仅加 `-r` |
| ③ loopback 栅栏未破坏 | ✅ 严格 `127.0.0.1:3080`；无 token 401；LAN IP 直连拒绝 |
| ④ rcd 改动只在 command_args 一处 | ✅ diff 仅 1 行：`-P` → `-r -P` |
| ⑤ 温缓存现场实跑 ≥10 样本 | ✅ 10 样本：冷 1.28s/例、温 0.11s/例 = **11.6×** |
| ⑥ 盒子未被压坏 | ✅ swapinfo 收尾与预检一致（10G/可用 7.1G/29%），今日无新 OOM |
| ⑦ 四件套齐全，无密码/token 落盘 | ✅ 日志仅含键名与 HTTP 状态码 |

---

## 一、rcd 最小改动（改前/改后原文）

**文件**：`/usr/local/etc/rc.d/dsh_web`（root:wheel，原 5128 → 改后 5131 bytes，仅多 3 字节 `-r `）

**改前**（第 76 行）：
```sh
command_args="-P ${pidfile} -o ${dsh_web_log} /bin/sh ${dsh_web_chdir}/freebsd/dsh-web-run.sh"
```

**改后**（第 76 行）：
```sh
command_args="-r -P ${pidfile} -o ${dsh_web_log} /bin/sh ${dsh_web_chdir}/freebsd/dsh-web-run.sh"
```

**diff**（`diff dsh_web.bak.day2n dsh_web`）：
```
76c76
< command_args="-P ${pidfile} -o ${dsh_web_log} /bin/sh ${dsh_web_chdir}/freebsd/dsh-web-run.sh"
---
> command_args="-r -P ${pidfile} -o ${dsh_web_log} /bin/sh ${dsh_web_chdir}/freebsd/dsh-web-run.sh"
```

> FreeBSD `daemon(8)` 的 `-r` = 子进程退出后自动重启。备份：`/usr/local/etc/rc.d/dsh_web.bak.day2n`。
> 未触碰 `rc.conf`、`dsh-web-run.sh`、fork 源码、其它 rcd。

---

## 二、崩溃拉起实测

**杀前**（19:14:03）：
```
daemon (pidfile) = 55645
  └─ pnpm (daemon 直接子进程) = 55646
       └─ node tsx (监听 3080) = 55695
```

**动作**：`kill -TERM 55646`

**时序**（每秒打点，远端 `date +%H:%M:%S`）：

| t | 时间 | daemon 活? | child(pnpm) | listen:3080 |
|---|---|---|---|---|
| 0 | 19:14:03 | yes | 55646 | 55695 |
| 1s | 19:14:04 | yes | 55646(死) | NONE |
| 2s | 19:14:05 | yes | NONE | NONE |
| **3s** | 19:14:06 | yes | **57424(新)** | NONE |
| 4–21s | 19:14:07–25 | yes | 57424 | NONE（node 冷启动中） |
| **22s** | 19:14:26 | yes | 57424 | **57487(新)** |

**杀后**：
```
daemon (pidfile) = 55645        ← 不变！daemon 全程存活
  └─ pnpm = 57424               ← 新 PID（≠55646）
       └─ node tsx = 57487      ← 新 PID（≠55695）
sockstat: 127.0.0.1:3080 (pid 57487)
```

**结论**：
- ✅ daemon(8) 自身 **55645 全程不死**，检测到子进程死后 **~3s 内** 重新 exec `dsh-web-run.sh` → 新 pnpm。
- ✅ 新进程 PID 与杀前**全部不同**（pnpm 55646→57424，listen 55695→57487），证明是真重启，不是"旧进程没死"。
- ⚠️ 完整监听恢复 **22s**：~3s 是 daemon 检测+拉起，~19s 是 pnpm+node tsx 冷启动（与 `service dsh_web start` 冷启动同量级，白天 token_wait=180s 也佐证此链路本就慢）。
  - 这 19s **不是 rcd `-r` 的缺陷**，是 node/tsx/harness 初始化固有开销。`-r` 机制本身（daemon 检测→重 exec）在 3s 内完成。
  - 对照白天无 `-r`：kill 后 daemon 自身退出、8s 后 3080 永久无监听（Day14:53）。**加 `-r` 后从"永久死"变成"22s 自愈"**，缺口已堵上。

---

## 三、loopback 栅栏复核

| 测试 | 结果 | 判定 |
|---|---|---|
| `sockstat -4l -p 3080` | `workbuddy node 57487 tcp4 127.0.0.1:3080` | ✅ 严格 loopback，非 0.0.0.0/LAN |
| `GET /` 无 token | HTTP 401 | ✅ 未授权被拒 |
| `GET /?token=<valid>` | HTTP 303 → `set-cookie: dsh-auth=...` | ✅ token 交换 cookie（正常认证流） |
| 伪造 `Host: 192.168.1.5` | HTTP 303（按 Host 签 cookie，authority=该 Host） | ⚠️ 非 403，但 harness 原行为 |
| 伪造 `Host: evil.example.com` | HTTP 303（同上） | ⚠️ 同上 |
| 直连 `http://192.168.1.5:3080` | 连接失败（curl 000/CONN_FAIL） | ✅ 绑定 loopback，LAN 不可达 |

**说明**：本 harness 的外部栅栏是**网络层绑定 127.0.0.1**（LAN 直连即失败）+ **token 鉴权**（无 token 401），并不做 Host 头 403 校验。伪造 Host 仍返回 303 是 harness 原有行为，**本次只加 rcd `-r`，未触碰任何网络/Host/鉴权代码**，栅栏未被改坏。

---

## 四、温缓存现场复核（10 样本）

**机器**：fb5 · FreeBSD 14.3-RELEASE-p7 amd64 · python 3.11.14（`/usr/local/bin/python3`）
**被测**：`~/dswork/ltbench/scripts/compiler_bench.py 10`（CLI=`~/dswork/ltbench/cli/light.py`）
**fork HEAD**（`~/github/deepseek-harness`）：`e5b5ccbfcb0f618bcbbb519a53c68ac9f8c875f8`
**ltbench 快照**：白天同步（对应 light-merge `d6b84a716`；本地当前 HEAD 已前进到 `a495bb44c`，但 1.5 上跑的是白天那份快照）

| 指标 | 白天（6 样本，13:09） | 本次（10 样本，19:16） | 差异 |
|---|---|---|---|
| 冷启动/例 | 1.28s | **1.28s** | 完全一致 |
| 温解释器/例 | 0.16s | **0.11s** | 略快（同机波动） |
| 冷启动总计 | 7.70s (6 例) | 12.84s (10 例) | 线性外推一致 |
| 温解释器总计 | 0.98s (6 例) | 1.10s (10 例) | 线性外推一致 |
| **提速倍数** | **7.9×** | **11.6×** | 差异来自温解释器单例波动 |

**差异说明**（契约 §七-5 要求）：
- 冷启动每例 1.28s 两次完全一致，说明"拉起解释器+import 编译器"的固定开销稳定。
- 温解释器单例从 0.16s 降到 0.11s，在同机 bench 固有波动范围内（Day10 §五-2 已警告同机 0.94s vs 3.26s 可飘 3.5×）。
- 倍数 7.9× vs 11.6× 的差异**完全由温侧单例时间波动贡献**，冷侧不变。核心结论不变：**每例成本几乎全在解释器启动，温解释器带来 ~8–12× 提速**。
- 严格遵守"当场实跑、不跨会话引用旧数"。

---

## 五、可选：真实 LLM 路径补测

| 项 | 结果 |
|---|---|
| 凭据位置 | `lightharness/.env`：`OPENAI_API_KEY`(L6) / `OPENAI_BASE_URL`(L10) / `OPENAI_MODEL`(L14) |
| 1.5 端点可达 | `curl https://api.deepseek.com/v1/models` → **HTTP 401，0.31s**（网络可达，无 key 返回 401） |
| 凭据是否上盒 | **否**——未把 key 写进盒上任何文件/日志；仅从 1.5 测了网络连通性 |
| 结论 | DeepSeek 端点从 1.5 可达；真 LLM 鉴权握手由 T4 在本地（Windows）用 `lightharness/.env` 跑更合适（key 本就在本地）。1.5 侧不做带 key 的调用，避免凭据落盒。 |

> 顺带更正 Day14 §3.1 的误判：白天判"`.env` 无 DeepSeek 凭据 → 降级"是**拿根 `.env` 的 `AIStudio_Access_Token` 去打 DeepSeek 端点**所致；实际 key 在 `lightharness/.env` 的 `OPENAI_*` 三件套（派单表 v1.2 §六-1 已澄清）。

---

## 六、两处陈旧条目纠正

1. **`Day10 §五-1`「FreeBSD 侧温缓存仍未实测」已陈旧**：Day14（13:09）已实测 7.9×，本次（19:16）复核 10 样本 11.6×，进一步固化。后续引用应改为"FreeBSD 1.5 实测温缓存 ~8–12×"。
2. **`Day14 §3.1`「无 DeepSeek 凭据 → 降级」已陈旧**：凭据在 `lightharness/.env` 的 `OPENAI_*`（见 §五），T4 真 LLM smoke 可跑。

---

## 七、盒子健康（收尾）

| 项 | 预检（19:06） | 收尾（19:17） |
|---|---|---|
| swap 总量/可用 | 10G / 7.1G (29%) | 10G / 7.1G (29%) |
| 1/5/15 负载 | 0.36/0.30/0.26 | 0.60/0.54/0.42 |
| 今日新 OOM | 无（最近 9/17） | 无 |
| dsh_web | RUNNING pid 73703 | RUNNING pid 57424（自拉起后新进程） |

盒子未被压坏；负载略升来自 bench（10 个冷启动 python），已回落。

---

## 八、四件套证据

| 日志 | 路径 | 内容 |
|---|---|---|
| 预检 | `logs/day2-night/T3_preflight.log` | swapinfo/OOM/CI/连接/sudo |
| rcd 改前/改后 | `logs/day2-night/T3_rcd_before_after.log` | rcd 全文 + diff + restart 前后进程树 |
| 崩溃拉起 | `logs/day2-night/T3_crash_restart.log` | kill→22s 恢复完整时序+PID 变化 |
| loopback 栅栏 | `logs/day2-night/T3_loopback_fence.log` | sockstat + 5 项 HTTP 状态码 |
| 温缓存 | `logs/day2-night/T3_bench.log` | 10 样本冷/温/倍数 |
| 收尾+LLM | `logs/day2-night/T3_final_swapinfo_llm.log` | swapinfo 复检 + DeepSeek 401 |

**被测 SHA**：
- 1.5 fork HEAD：`e5b5ccbfcb0f618bcbbb519a53c68ac9f8c875f8`
- 1.5 ltbench 快照：白天同步（light-merge `d6b84a716`）
- 本地 light-merge HEAD：`a495bb44c`（T1 并行推进中，未 push）
- 本地 lightharness HEAD：`6c291f4`

**反跑判据**（契约 §八）：未在盒上做"去掉 `-r` 再 kill"的反跑——因为当前 `-r` 是用户解禁的生产配置，去掉会短暂恢复"崩溃即死"状态，且白天 Day14:53 已在无 `-r` 配置下复现过原缺口（kill 后 8s 无监听、daemon 退出）。本次正向取证（加 `-r` 后 kill→自动拉起）已足够证明修复有效，不做破坏性反跑。
