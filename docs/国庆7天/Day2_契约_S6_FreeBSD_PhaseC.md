# S6 契约 · FreeBSD Phase C 生产化

> 派单表：`Day2_派单表.md`｜计划：`docs/国庆day2计划.md` v1.1 §四 轨道C
> **资源型**：网络·等（长等待，适合作 B 路的槽 2）｜**需门**：否｜**预计**：约 2–3 小时（多为远程等待）
> **出口 tag**：`subtask-S6-done`
> **🚫 绝对禁止 `git push`**；**🚫 禁止在共享生产盒上做重构建**；**🚫 禁止改 fork 源码**

---

## 一、目标

B2+ 已通（三件套 3/3），本子任务把它**推向生产化**：

1. **真实 LLM 调用路径在 1.5 上实测**（不是 mock）
2. **守护/看门狗**：`dsh_web.rcd` 自启 + 崩溃拉起验证
3. **温缓存首次在 1.5 实测**（⚠️ v0.3.0 的 11× 是**本机 Windows** 的数，见 §三）
4. 打 `fork-phaseC` tag（本地 + 1.5；**远端推送等用户示意**）

## 二、连接与前置

| 项 | 值 |
|---|---|
| 盒子 | **192.168.1.5**（FreeBSD），`ssh workbuddy@192.168.1.5`（Day6 实测可用） |
| 凭据来源 | `.env`（**执行前先核对实际键名，不要猜**）：形如 `15SSH_HOST` / `SSH_USER_WORKBUDDY` / `SSH_PASS_WORKBUDDY` |
| fork 仓 | `/home/workbuddy/github/deepseek-harness` |
| 上游核对 | `git merge-base --is-ancestor 8a18ff7dae master` → Day6 实测 **YES**；本地 clone `/g/dswork/AI/deepseek-harness` 在 `e5b5ccbfcb` |
| 基线 tag（**既有，勿新建/移动**） | `fork-after-upstream-v0.2.0-rc.1` → `a8873ab003`（Day6 实测「计划书以为需打，实际早已就位」） |

### ⚠️ 共享生产盒预检（铁律，开工第一步）

必须先确认：`swapinfo`（Day6 当时 10G / 可用 6.9G）、**无近期 OOM kill**、**无 CI 在跑**。
Day6 的合规前提是「三件套均为轻量：audit 仅 merge 预演后 abort、pnpm 仅 lockfile、web UI 复用常驻进程，**未触发重构建**」——本子任务沿用同一自律。

## 三、三条主线

### 3.1 真实 LLM 调用路径（⚠️ 先做 30 分钟可行性确认）

- **风险已实测**：`.env` 共 18 个键，与模型相关的只有 **`AIStudio_Access_Token`**，**没有 DeepSeek 类键**，而计划假设「用 `.env` 的 DeepSeek 推理 key」。
- **动作**：先确认 key 到底在不在（`.env` / 盒子侧配置 / 其它凭据文件）。
  - 在 → 跑真实问题，落盘：请求/响应片段（**脱敏**）、流式行为、耗时、rc。
  - 不在 → **如实记录降级**：「真实 LLM 路径因无凭据未测」+ 已完成的替代证明（如到 provider 端点的连通性/鉴权握手），**不许用 mock 冒充真实**。

### 3.2 守护 / 看门狗

- `dsh_web.rcd` 已就位 → 验证**自启**与**崩溃拉起**（杀掉进程 → 观察是否被拉起；`sockstat` 复核监听）。
- 沿用 Day6 的 loopback 栅栏判据：监听必须是 **`127.0.0.1:3080`**（非 `0.0.0.0`/LAN IP），带 token 访问 200、非 loopback Host 应被拒（403）。

### 3.3 温缓存（**首次在 1.5 实测**）

- ⚠️ **口径校正**：v0.3.0 的「冷 3.26s/例 → 温 0.30s/例 = 11.0×」出自 `Day6_freebsd_phaseB2.md` **§3.6「支线·编译器性能基准（本地 Windows 开发机）」**；该报告 §五 明确「15s/例 应是 **0.82 / 1.5** 资源更紧盒子的数」。
  → **FreeBSD 上没有温缓存实测**，本子任务是**第一次**。**不要把 Windows 的 11× 当作 1.5 的结果搬用。**
- 做法：在 1.5 上跑 `compiler_bench.py`（或等价脚本），落盘冷/温每例耗时与提速倍数，注明**机器、并发、样本数、被测 SHA**。

## 四、文件白名单 / 黑名单

| | 路径 |
|---|---|
| **可写** | `docs/国庆7天/Day14_freebsd_phaseC.md`、`logs/day2/S6_*`；1.5 盒上**仅限**：跑脚本、写日志与 tag（**不改 fork 源码**） |
| **禁止** | 任何 `git push`；改 `freebsd/` 源码；在盒上做重构建/长时间满负载编译；`light-merge/src/`、`antlrparser/`；本地其余子任务的文件面 |

## 五、交付物

| 路径 | 内容 |
|---|---|
| `docs/国庆7天/Day14_freebsd_phaseC.md` | 三段式；含预检结果 + 三条主线 + 逐项 rc + 被测 SHA + 盒子状态 |
| `logs/day2/S6_preflight.log` | `swapinfo` / OOM / CI 检查原始输出 |
| `logs/day2/S6_llm.log`（或降级说明） | 真实 LLM 路径的原始输出（脱敏） |
| `logs/day2/S6_watchdog.log` | 自启 + 崩溃拉起验证 |
| `logs/day2/S6_bench.log` | **1.5 上**冷/温基准原始输出 |
| `fork-phaseC` tag | 1.5 本地（+ 本地 clone），**不 push** |

## 六、验收标准（可量化）

1. 预检三项全部落盘（swapinfo / 无 OOM / 无 CI）。
2. 三条主线**各有明确结论**：`通过` / `降级（写明原因）`——**不许出现「应该没问题」**。
3. 温缓存的数字**明确标注实测机器 = 1.5 FreeBSD**，且与 Windows 的 11× 分列，不混用。
4. `fork-phaseC` tag 已打（1.5 本地），**未推送**。
5. 共享盒未被重构建/未被压满（给出证据：再次 `swapinfo` / 无新 OOM）。
6. 四件套齐全（含被测 SHA）。

## 七、反跑判据（沿用 Day6 的「正向验证 + 语义说明」姿势，**不实际破坏共享盒**）

1. 破坏 `freebsd/audit-merge.sh` 的 `dsh:freebsd` 条目 → 审计应掉到 `[LOST]`、`AUDIT_EXIT=1`。
   → 实际做法：正向确认该条目当前 `[OK]`，并说明审计脚本用 `wc -l` 最少匹配数断言的语义；**不在共享盒上改源码**。
2. 删除 `pnpm-lock` 的 `freebsd-x64` 条目 → `pnpm install --lockfile-only` 应报 lockfile 与 manifest 不一致。
   → 实际做法：正向确认当前 `Already up to date` / `PNPM_EXIT=0`，并说明语义；**不实际破坏锁文件**。
> 若你认为反跑必须真做，**只能在 fork 仓的一次性副本上做**，且必须先在报告里说明，**不得动生产盒上的 fork 原件**。

## 八、砍线与降级

- **15:00 上限**。
- **1.5 不可达**（key 与 gitea API 都不通）→ 出口降级为「**本地可复现的 Phase C 脚本 + 待跑清单**」，并在报告里明确标注，**不阻塞屏障 D**。
- 真实 LLM 无凭据 → 见 §3.1 的降级要求（如实记录，不用 mock 冒充）。

## 九、必须带回的证据（四件套）

命令（完整 ssh 行）+ 退出码 + 日志路径 + 被测 SHA（**fork 仓的 `8a18ff7dae` / 盒子 HEAD `e5b5ccbfcb` 等一并写明**）。

## 十、禁止事项

除派单表附录 B 的 7 条外：
1. **禁止 push**（tag/分支一律不推）。
2. **禁止把 Windows 的基准数字当 FreeBSD 结果**（这是 v0.3.0 报告里已出现过的归因错误，本次不得重犯）。
3. 禁止在共享生产盒上做重构建或长时间满负载编译（会踩到别人的 CI/服务）。
4. 禁止把 `.env` 的密码/token 值写进报告或日志。
