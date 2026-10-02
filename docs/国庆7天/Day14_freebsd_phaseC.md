# Day14 · 轨道 C：FreeBSD Phase C 生产化 · 交付报告（三段式）

> 日期：2026-10-02｜契约：`Day2_契约_S6_FreeBSD_PhaseC.md`｜派单：`Day2_派单表.md`（S6，轨道 C，资源型·网络等，需门=否）
> 盒子：**1.5（192.168.1.5）** FreeBSD 14.3-RELEASE-p7 amd64｜fork 仓：`/home/workbuddy/github/deepseek-harness` ｜ fork HEAD：**`e5b5ccbfcb`**（两端一致）｜基线 tag：`fork-after-upstream-v0.2.0-rc.1` → `a8873ab003`（**既有，未新建/移动**）
> 出口 tag：`fork-phaseC` 已打（1.5 本地 + 本地 clone，**未推送**）；派单表出口 `subtask-S6-done` 为派单流转标记，与代码仓 tag 是两回事

---

## 一、根因

Phase B2+（Day6）已把 FreeBSD 三件套跑通（3/3），但距离「生产化」仍差四步，且前三步此前**从未实测**：

1. **真实 LLM 调用路径**：计划假设「用 `.env` 的 DeepSeek 推理 key」，但 `.env` 与模型相关的只有 `AIStudio_Access_Token`，**没有 DeepSeek 类键**——key 到底在不在必须在 1.5 上先确认（30 分钟可行性确认先行），在则实测、不在则如实降级，**不许用 mock 冒充**（契约 §3.1）。
2. **守护/看门狗**：`dsh_web.rcd` 已就位，但「崩溃后能否自动拉起」从未验证——自启配置存在 ≠ 崩溃拉起可用，两者必须分开实测（契约 §3.2）。
3. **温缓存首次在 FreeBSD 实测**：v0.3.0 的「11.0×」出自 Day6 §3.6 **本地 Windows 开发机**，Day6 §五 明确「15s/例 应是 0.82/1.5 资源更紧盒子的数」——**FreeBSD 上没有任何温缓存实测数**，本次是第一次，不得把 Windows 数字搬用（契约 §3.3、§十.2）。
4. **打 `fork-phaseC` tag**：契约交付物要求两端本地命中，不 push。

## 二、做了什么

| 项 | 变更 / 动作 | 说明 |
|---|---|---|
| 共享盒预检（铁律第一步） | `swapinfo` / dmesg+messages OOM / CI 进程 / load | swap 总 10G、可用 7.2G（31%）；dmesg/messages 无近期 OOM；无 pytest/gcc/clang 重载，仅常驻 `pnpm dsh:freebsd web`；load 0.28 → **预检通过**，落盘 `S6_preflight.log` |
| ① 真实 LLM 路径 | 凭据可行性确认（30 分钟先行） | 本地 `.env` 仅 `AIStudio_Access_Token`（非 DeepSeek）；1.5 fork `.env` 仅 GIT\*/GITEA\* 类键；`~/.dsh/.credentials.yaml` 为结构记录无 key 明文 → **无 DeepSeek 凭据** |
| ① 替代证明 | `curl https://api.deepseek.com/v1/models` | **401**（connect=0.0387s / dns=0.0203s）：端点可达、鉴权握手成功、因无 key 被拒 → 证明「链路通、缺凭据」，非环境不可达 |
| ② 守护/看门狗 | rcd 安装与自启配置核查 + 崩溃拉起实测 | `/usr/local/etc/rc.d/dsh_web` 已安装（root）、`rc.conf dsh_web_enable="YES"`；`kill -TERM 1202` → 8s 后 3080 无监听、daemon 755 退出 → **未自动拉起（真实发现，daemon 缺 `-r` 自动重启标志）**；`service dsh_web start` 手动恢复成功（pid 73703/73758，监听 127.0.0.1:3080） |
| ② 鉴权与栅栏复核 | token 流 + loopback 栅栏 | 带 repo 日志 token 303→200 `<title>DSH Local Build</title>`；无 token 401、伪造 `Host: 192.168.1.5` 401；LAN 直连 `192.168.1.5:3080` connection refused（rc=7）——**loopback 信任栅栏真实语义确认** |
| ③ 温缓存（**首次 1.5 实测**） | `scripts/compiler_bench.py 6 --verbose`（基准搬运 `~/dswork/ltbench/`） | Python 3.11.14，samples=6：冷 7.70s 总计/1.28s 每例、温 0.98s 总计/0.16s 每例、**7.9×**；被测 SHA：light-merge `d6b84a716`、fork HEAD `e5b5ccbfcb` |
| fork-phaseC tag | 1.5 fork 仓 + 本地 clone `/g/dswork/AI/deepseek-harness` | 两端均 `git tag -f fork-phaseC` → 指向 `e5b5ccbfcb`（Merge branch 'fix/i18n'）；**未 push**；基线 tag `a8873ab003` 未动 |
| 反跑判据（正向验证 + 语义说明） | audit-merge.sh / pnpm lockfile-only | `dsh:freebsd` 条目 `[OK]`、`RESULT: 全部 [OK]` rc=0；`Already up to date` rc=0；语义：`wc -l` 最少匹配断言、freebsd-x64 锁条目在位（详见 §四）——**未实际破坏共享盒** |
| 收尾复核 | 再次 `swapinfo` / uptime / dmesg OOM | swap 可用 7.4G（**29%，低于开工时 31%**）、load 0.39、无新 OOM → 共享盒未被压满 |

## 三、现在能跑什么

### 3.1 真实 LLM 调用路径 —— **降级（无凭据，如实记录，不用 mock）**

```bash
ssh workbuddy@192.168.1.5 # 可达（Day6 已通，hostname=fb5）
# 凭据确认：本地 .env / 1.5 fork .env / ~/.dsh/.credentials.yaml 均无 DeepSeek 类 key
curl -s -o /dev/null -w '%{http_code}\n' https://api.deepseek.com/v1/models   # -> 401
```
结果：**降级**——真实 LLM 调用路径因无 DeepSeek/AIStudio 凭据未测（契约 §3.1 允许的降级情形）；替代证明为 provider 端点 401 鉴权握手（链路通、无凭据被拒）。已落盘 `logs/day2/S6_llm.log`（脱敏，无任何凭据值）。

### 3.2 守护 / 看门狗 —— **自启：通过；崩溃拉起：未配置（真实发现）**

```bash
service dsh_web status   # -> dsh_web is RUNNING on :3080 (pid 73703)
kill -TERM 1202 && sleep 8 && sockstat -4l -p 3080   # -> 无监听（未自动拉起）
service dsh_web start    # -> 恢复成功，73703/73758 监听 127.0.0.1:3080
```
| 判据 | 结果 |
|---|---|
| 自启机制 | `/usr/local/etc/rc.d/dsh_web` 已安装（root）+ `rc.conf dsh_web_enable="YES"` → **开机自启路径存在** |
| 崩溃拉起 | `kill -TERM` 后 8s 无监听、daemon 退出 → **未自动拉起**。根因：rcd `command_args` 为 `daemon -P pidfile -o log /bin/sh dsh-web-run.sh`，**缺 `-r` 自动重启标志** |
| 手动恢复 | `service dsh_web start` 拉起成功，监听严格 `127.0.0.1:3080` |
| 鉴权 | 带 token 303→200 `<title>DSH Local Build</title>`；无 token 401；伪造 `Host: 192.168.1.5` 401 |
| loopback 栅栏 | LAN 直连 `192.168.1.5:3080` connection refused（rc=7）→ 确认服务只信任 loopback，不做 LAN 暴露 |

### 3.3 温缓存（**首次在 1.5 FreeBSD 实测**）

```bash
ssh workbuddy@192.168.1.5 "cd ~/dswork/ltbench && python3 scripts/compiler_bench.py 6 --verbose"
```
```
machine: fb5 FreeBSD 14.3-RELEASE-p7 | python: Python 3.11.14 | samples: 6
light-merge SHA: d6b84a716 | fork HEAD: e5b5ccbfcb
  冷启动（每例新进程） : 总计   7.70s | 每例  1.28s
  温解释器（进程内复用）: 总计   0.98s | 每例  0.16s
  提速倍数            :   7.9x
```
**实测机器 = 1.5 FreeBSD**，与 Windows 本地测的 11.0×（Day6 §3.6）**分列，不予混用**：FreeBSD 每例成本更高（冷 1.28s vs Win 3.26s 口径差异源于 Win 为 Windows 解释器+11× 为另一基准），1.5 上温解释器把每例从 1.28s 压到 0.16s（7.9×）。结论不变：每例成本几乎全在「拉起解释器+import 编译器」，真正杠杆是**温解释器（编译守护进程）**而非 .py 产物缓存。

### 门数字（本轨为 FreeBSD 实测，无 0.82 权威门要求，需门=否）

| 量 | 基线（开工前） | 本轮实测 | 判定 |
|---|---|---|---|
| 三件套（Day6） | 3/3 通过 | 未回退（audit 全部 [OK]、pnpm Already up to date、web UI 200） | PASS |
| 真实 LLM 路径 | 计划假设有 key | 无凭据 → **降级**（替代证明 401 握手，无 mock） | 降级（§3.1 允许） |
| 崩溃拉起 | 未验证 | **未配置**（daemon 缺 `-r`）；手动恢复 OK | 如实发现，待后续加 `-r` |
| 温缓存（1.5） | 无任何 FreeBSD 实测 | 冷 1.28s/例 → 温 0.16s/例 = **7.9×** | 首次实测 PASS |
| fork-phaseC tag | 未打 | 两端 `e5b5ccbfcb`，**未 push** | PASS |

## 四、反跑判据验证（正向验证 + 语义说明，**未实际破坏共享盒**）

1. **破坏 `freebsd/audit-merge.sh` 的 `dsh:freebsd` 条目 → 审计 [LOST]、`AUDIT_EXIT=1`**
   - 正向确认：`package.json dsh:freebsd (1)` 当前 `[OK]`，`RESULT: 全部 [OK]` rc=0。
   - 语义：审计脚本 `chk` 用 `wc -l` 最少匹配数断言，条目一旦被删/改名即低于最少匹配 → 掉 `[LOST]`、退出码变 1。按契约 §七「不实际破坏共享盒」执行。
2. **删除 `pnpm-lock` 的 `freebsd-x64` 条目 → `pnpm install --lockfile-only` 报 lockfile 与 manifest 不一致**
   - 正向确认：`Already up to date` / `Done in 4.6s using pnpm v11.7.0` rc=0（freebsd-x64 锁条目在位，identity bypass 生效）。
   - 语义：删除该平台条目后 lockfile 与 workspace manifest 不一致，`--lockfile-only` 必失败。未实际破坏锁文件。

## 五、遗留 / 偏离声明

- **崩溃拉起未配置（真实缺口，非偏差）**：1.5 上 dsh_web 守护进程缺 `daemon -r` 自动重启标志，进程被杀后不会自动拉起。本次已如实取证并落盘，**未改 fork 源码/未改 rcd**（契约禁止改 fork 源码；rcd 归属盒上运维配置，改动需另行示意）。后续生产化建议：在 rcd `command_args` 增加 `-r`，或由外部看门狗（如 monit/系统级）拉起——留待用户示意后执行。
- **真实 LLM 路径降级**：无 DeepSeek/AIStudio 凭据（本地 `.env` 仅 `AIStudio_Access_Token` 且非 DeepSeek 类；1.5 fork `.env` 无模型键）。未 mock、未伪造；替代证明为端点 401 鉴权握手。
- **`~/dswork/ltbench/` 留存**：1.5 上传的基准搬运目录（`src/antlrparser/cli/stdlib/scripts/compiler_bench.py`，4.7M），属契约 §四 白名单「跑脚本、写日志与 tag」用途，已保留并在本报告注明；如需清理请示意。
- **tag 推送**：`fork-phaseC` 已打 1.5 本地 + 本地 clone，**未推送**（契约禁止 push）；如需推远端请用户示意。
- **SSH 主机提示**：根 `.env` 的 `SSH_HOST` 值为 192.168.0.88（与 1.5 不一致）；本任务全程按契约以 `192.168.1.5` 实测（Day6 已通），后续沿用请以 192.168.1.5 为准。
- **共享盒状态**：收尾复核 swap 可用 7.4G（29%）< 开工 31%、load 0.39、无新 OOM；全程仅轻量操作（audit 预演后 abort、pnpm 仅 lockfile、bench 6 例、watchdog 短时杀/起），未触发重构建。
- **派单表出口 tag 区分**：代码仓 `fork-phaseC`（本次交付物）与派单表流转出口 `subtask-S6-done` 是两回事；`subtask-S6-done` 为派单管理标记，不在代码仓打。

## 六、四件套证据索引（命令 + 退出码 + 日志路径 + 被测 SHA）

| 件 | 日志路径 | 关键 rc | 被测 SHA |
|---|---|---|---|
| 预检 | `logs/day2/S6_preflight.log` | swapinfo rc=0 / dmesg rc=0 / CI rc=0（done rc=1 为检查链收尾约定值） | fork `e5b5ccbfcb` |
| LLM 降级 | `logs/day2/S6_llm.log` | curl 401（端点可达） | fork `e5b5ccbfcb` |
| 看门狗 | `logs/day2/S6_watchdog.log` | kill rc=0 / rcd start rc=0 / 鉴权 303→200 / LAN rc=7 | fork `e5b5ccbfcb` |
| 温缓存 | `logs/day2/S6_bench.log` | bench rc=0，冷 1.28s/例 → 温 0.16s/例（7.9×） | light-merge `d6b84a716`、fork `e5b5ccbfcb` |
| 反跑判据 | 并入 `S6_watchdog.log` 尾部 | audit rc=0 / pnpm rc=0 | fork `e5b5ccbfcb` |
| tag | git（1.5 + 本地 clone） | `fork-phaseC` → `e5b5ccbfcb`，未 push | — |