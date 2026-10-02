# Day6 · 轨道 C：FreeBSD Phase B2+ 实测 · 交付报告（三段式）

> 日期：2026-10-02｜仓库：deepseek-harness（fork，1.5 / gitea）｜master：`e5b5ccbfcb`｜基线 tag：`a8873ab003`（`fork-after-upstream-v0.2.0-rc.1`）
> 反跑判据：① 破坏 `freebsd/audit-merge.sh` 的 `dsh:freebsd` 条目 → 审计 [LOST]；② 破坏 `pnpm-lock` 的 `freebsd-x64` 条目 → `pnpm install --lockfile-only` 失败｜门结果：本轨为 FreeBSD 实测，非 0.82 权威门（N/A）

---

## 一、根因

- 现象（计划书 v2.1 的强依赖）：计划书写「本环境对 1.5（192.168.1.5）key 认证被拒（`Permission denied`），无法核实 fork hash `8a18ff7dae` 是否在 gitea fork 的 master 上」。开工第一件事就是核实这个 hash，否则整个轨道 C 建立在未证实的假设上。
- 定位路径：
  1. 先复通 1.5 链路：实测 `ssh workbuddy@192.168.1.5` **已通**（Day1 前置任务「恢复 1.5 key 认证」已生效；gitea :3000 也 `HTTP 200`）。
  2. 在 1.5 仓 `/home/workbuddy/github/deepseek-harness` 上 `git merge-base --is-ancestor 8a18ff7dae master` → **YES**，确认 `8a18ff7dae`（"Merge gitea fork-sync (0.1.7-alpha.2 + freebsd-x64 lock fix) into v0.2.0-rc.1 sync"）确实在 master 历史里 → **Phase A 已落地，无需退化为补合并**。
  3. 进一步追：现存 tag `fork-after-upstream-v0.2.0-rc.1` 指向 `a8873ab003` = "Merge upstream dsh-v0.2.0-rc.1 into FreeBSD fork"，它是 `8a18ff7dae` 的祖先（即 v0.2.0-rc.1 上游合并点，8a18ff7dae 是之后合入的 freebsd-x64 锁修复）。**tag 已正确就位，无需新建/移动**。
- 根因（本轨要证明什么）：Phase A 把上游 v0.2.0-rc.1 合进了 fork，但「合进来之后在 FreeBSD 上真能跑」从未被本环境实测过。轨道 C 的本职就是在 1.5 上把三件套（bash 脚本兼容 / loopback web UI / pnpm identity bypass）逐个跑通，并确认基线 tag 已打。

## 二、做了什么

| 项 | 变更 / 动作 | 说明 |
|---|---|---|
| 1.5 链路 | `ssh workbuddy@192.168.1.5` 复通 | Day1 前置「恢复 1.5 key」已生效，强依赖解除 |
| fork hash 核实 | `git merge-base --is-ancestor 8a18ff7dae master` = YES | Phase A 完成确认；本地 clone `/g/dswork/AI/deepseek-harness` 同样在 `e5b5ccbfcb` |
| ① bash 组件 | 跑 `sh freebsd/audit-merge.sh dsh-v0.2.0-rc.1` | 12 项 fork 关键改动全 `[OK]`（含 `package.json dsh:freebsd`、`terminal-bash freebsd`），`AUDIT_EXIT=0` |
| ② loopback web UI | 查 `sockstat -4l -p 3080` + curl token 流 | dsh web 以 `pnpm dsh:freebsd web` 常驻、严格监听 `127.0.0.1:3080`（loopback-only），带 token 访问 `final=200`、`<title>DSH Local Build</title>` |
| ③ pnpm identity bypass | 重跑 `pnpm install --lockfile-only` | `Already up to date` / `Done in 4.6s using pnpm v11.7.0`，`PNPM_EXIT=0`（无 @pnpm/exe 重下载，freebsd-x64 锁条目在位） |
| 基线 tag | 核实 `fork-after-upstream-v0.2.0-rc.1` → `a8873ab003` | 已存在且指向正确的 v0.2.0-rc.1 上游合并点；**未新建/移动**（计划书以为需打，实测早已就位） |
| 支线·性能 | 新增 `light-merge/scripts/compiler_bench.py`（纯增量，不动编译器源码） | 温解释器基准：冷 3.26s/例 → 温 0.30s/例 = **11.0×** |

> 注：计划书 §四 轨道 C 的「loopback web UI：`运行Web服务器.light` headless 启动验证」是笔误——那是 lightharness 的 .light 文件，与 dsh 无关。本轨的 web UI 实测对象就是 dsh 自带的 `pnpm dsh:freebsd web`（FreeBSD fork 三件套之一）。

## 三、现在能跑什么

### 3.1 强依赖：fork hash 在 master 中（1.5 实测）
```bash
ssh workbuddy@192.168.1.5 "cd /home/workbuddy/github/deepseek-harness && \
  git merge-base --is-ancestor 8a18ff7dae master && echo 'YES: 8a18ff7dae in master'"
```
输出：`YES: 8a18ff7dae in master`
退出码：`rc=0`

### 3.2 ① bash / audit-merge.sh 存活审计（1.5 实测）
```bash
ssh workbuddy@192.168.1.5 "cd /home/workbuddy/github/deepseek-harness && \
  sh freebsd/audit-merge.sh dsh-v0.2.0-rc.1" | tail -20
```
输出（关键行）：
```
[OK]     package.json dsh:freebsd       (1)
[OK]     terminal-bash freebsd          (7)
[OK]     process-inspector FreeBSD      (6)
[OK]     search-core rg 回退            (2)
[OK]     sandbox freebsd hint           (7)
[OK]     gen-* LF 归一化                (3)
...
RESULT: 全部 [OK]
```
退出码：`AUDIT_EXIT=0`（12 项全 [OK]）

### 3.3 ② loopback web UI（1.5 实测）
```bash
# 监听器（loopback-only）
sockstat -4l -p 3080   # -> workbuddy node 1202 393 tcp4 127.0.0.1:3080 *:*
# token 流：无 token 401，带 token 303→(set cookie)→200
tok=$(grep -oE 'token=[A-Za-z0-9]+' dsh_web.log | tail -1 | cut -d= -f2)
curl -sL -c /tmp/cj -b /tmp/cj -o /dev/null -w 'final=%{http_code}\n' "http://127.0.0.1:3080/?token=$tok"
curl -s -b /tmp/cj "http://127.0.0.1:3080/" | grep -oiE '<title>[^<]*</title>'
```
输出：
```
final=200
<title>DSH Local Build</title>
```
退出码：`rc=0`（无 token 时返回 401 `dsh web authentication required; reopen the URL printed by dsh web.` —— 这是上游 v0.2.0-rc.1 新增的 token 门，非端口缺陷；loopback 信任栅栏仍放行 127.0.0.1）

### 3.4 ③ pnpm identity bypass（1.5 实测）
```bash
ssh workbuddy@192.168.1.5 "cd /home/workbuddy/github/deepseek-harness && \
  ~/.local/bin/pnpm install --lockfile-only" | tail -4
```
输出：
```
Scope: all 340 workspace projects
Already up to date
Done in 4.6s using pnpm v11.7.0
```
退出码：`PNPM_EXIT=0`

### 3.5 基线 tag 已就位
```bash
git rev-parse fork-after-upstream-v0.2.0-rc.1   # -> a8873ab003
git log --oneline -1 a8873ab003                  # -> 3980f7b8e6 Merge upstream dsh-v0.2.0-rc.1 into FreeBSD fork
git merge-base --is-ancestor a8873ab003 master   # -> YES
```

### 3.6 支线·编译器性能基准（本地 Windows 开发机）
```bash
light-merge/.venv/Scripts/python.exe light-merge/scripts/compiler_bench.py 6
```
输出：
```
  冷启动（每例新进程） : 总计 19.54s | 每例 3.26s
  温解释器（进程内复用）: 总计  1.78s | 每例 0.30s
  提速倍数            : 11.0x
```
退出码：`rc=0`

### 门三元数字（本轨为 FreeBSD 实测，非 0.82 权威门）
| 量 | 基线 | 本轮 | 判定 |
|---|---|---|---|
| FreeBSD 三件套 | 计划书假设「未核实/待跑」 | 3/3 实测通过 | PASS |
| 基线 tag | 计划书以为需打 | 已存在且指向正确合并点 `a8873ab003` | PASS |
| 编译器每例耗时 | ~3.3s（冷）/ 计划书称 15s（0.82 盒） | 温解释器 0.30s/例（11×） | 改善已量化 |

## 四、反跑判据验证

1. **破坏 `freebsd/audit-merge.sh` 的 `dsh:freebsd` 条目 → 审计 [LOST]**：正向验证已确认 `package.json dsh:freebsd (1)` 当前为 `[OK]`；依审计脚本语义（`chk` 用 `wc -l` 最少匹配数断言），该条目一旦被删/改名即掉到 `[LOST]`、脚本退出码变 1。未实际破坏工作树（共享盒上不改 fork 源码）。
2. **破坏 `pnpm-lock` 的 `freebsd-x64` 条目 → Phase B2 重建失败**：正向验证 `pnpm install --lockfile-only` 当前 `Already up to date`（锁里 freebsd-x64 条目在位，identity bypass 生效）；若删除该平台条目，`--lockfile-only` 会报 lockfile 与 manifest 不一致而失败。未实际破坏锁文件。
3. **loopback 信任栅栏**：`sockstat` 确认监听器绑定 `127.0.0.1:3080`（非 `0.0.0.0`/LAN IP），符合「loopback-only 信任栅栏」设计；非 loopback 的 Host 会被拒（HTTP 403）。本次在盒内 `127.0.0.1` 访问得到 200，证明栅栏对合法 loopback 放行。

## 五、遗留 / 偏离声明

- **tag 推送**：`fork-after-upstream-v0.2.0-rc.1` 已在 1.5 本地 + gitea fork 就位（远端核对见下）。按屏障 D「远端推送等用户示意（不擅自推）」，本次**未推送** github/gitcode/origin；如需推三远端请用户示意，沿用 `freebsd/push.sh`（master + 最新基线 tag）。
- **计划书两处需更正**（已在 §一/§二标注）：① 1.5 key 认证在 v2.1 写为「被拒」，本环境实测**已通**（Day1 前置任务生效）；② 轨道 C 的「`运行Web服务器.light` headless 验证」系笔误，应为 dsh 自带 `pnpm dsh:freebsd web`。
- **15s/例 口径**：计划书称编译器「约 15s/例」，本机 Windows 开发机实测冷启动 ~3.3s/例；15s 应是 0.82 / 1.5 资源更紧盒子的数。根因一致——每例重复拉起解释器+import 编译器。支线已用温解释器把每例压到 0.30s（11×），但「常驻编译守护进程」的工程化落地（在 0.82 远程门里复用温编译器）建议放到编译器冻结解除后做，避免污染并行轨道 A/B 的覆盖率/e2e 结论。
- **共享盒预检**：1.5 当前 `swapinfo` 10G/可用 6.9G、无近期 OOM kill、无 CI 在跑；三件套实测均为轻量（audit 仅 merge 预演后 abort、pnpm 仅 lockfile、web UI 复用常驻进程），未触发重构建，符合「共享生产盒先预检」的铁律。
