# R110 D 路：fork FreeBSD 脚本对账（2026-10-03）

> 路：D（脚本同步/移植）｜ 基准修正说明见 A 清单 §0
> 任务书原指令：对 `git diff e5b5ccbfcb..dsh-v0.2.0-rc.2 -- freebsd/` 15 文件对账。
> **实机核查结论：该两点 diff 为 fork 锚点的假删除**（-1163 行，纯删除、零新增）——freebsd/ 是本地 `dsh-v0.2.0-rc.1` 标签（`e5b5ccbfcb`，fork 合流提交）自带的 fork 文件，上游 rc.2 树中**不存在 freebsd/ 目录**（`git ls-tree dsh-v0.2.0-rc.2 freebsd/` 为空）。上游 rc.1→rc.2 对 freebsd/ 的真实增量 = **0 文件**。
> D 路对账基准据此改为 fork 侧：`git diff e5b5ccbfcb 8bf6c9250f -- freebsd/`（rc.1 锚点 → fork HEAD，HEAD 已合 rc.2）。**结果为空：fork 在本轮区间对 freebsd/ 零改动。**

## 1. 15 文件逐一对账结论

| 上游文件（fork freebsd/） | 上游 rc.1→rc.2 变更 | fork rc.1锚点→HEAD 变更 | lightharness 对应 | 结论 |
| --- | --- | --- | --- | --- |
| freebsd/dsh-jail-run.c | 无（上游无此文件） | 无 | `lightharness/freebsd/dsh-jail-run.c`，与 fork HEAD **逐字节一致**（diff 校验） | 无需同步；无 C 改动，**无需重编 setuid** |
| freebsd/dsh_web.rcd | 无 | 无 | 同名文件，逐字节一致 | 无需同步 |
| freebsd/verify-sandbox.mjs | 无 | 无 | 同名文件，逐字节一致 | 无需同步 |
| freebsd/audit-merge.sh | 无 | 无 | 缺（lightharness 无对应；fork 审计工具） | 不同步：fork 专属流程工具，无上游增量 |
| freebsd/build-lib.sh | 无 | 无 | 缺（功能由 `编译安装.sh` 覆盖） | 不同步：同上 |
| freebsd/build-new.sh | 无 | 无 | 缺（同上） | 不同步 |
| freebsd/commit.msg | 无 | 无 | 缺（fork 提交模板） | 不同步 |
| freebsd/dsh-web-restart.sh | 无 | 无 | 缺（功能由 `远程回归.sh`/`初始化.sh` 覆盖） | 不同步 |
| freebsd/dsh-web-run.sh | 无 | 无 | 缺（同上） | 不同步 |
| freebsd/probe-binary.sh | 无 | 无 | 缺 | 不同步 |
| freebsd/push.sh | 无 | 无 | 缺（lightharness 三远端 push 走 M 路流程，不搬 fork push 脚本） | 不同步 |
| freebsd/run-e2e.sh | 无 | 无 | 缺（功能由 `远程回归.sh` 覆盖） | 不同步 |
| freebsd/run-verify.sh | 无 | 无 | 缺（同上） | 不同步 |
| freebsd/stage-build.sh | 无 | 无 | 缺 | 不同步 |
| freebsd/sync-build-verify.sh | 无 | 无 | 缺 | 不同步 |

## 2. 任务书各项处置

1. **可同步部分**：本轮为零（上游与 fork 两侧 freebsd/ 均无增量），未对 `lightharness/freebsd/` 做任何改动，无需标注"同步自上游"头。
2. **dsh-jail-run.c 重编评估**：不适用（无 C 改动）。
3. **`freebsd/初始化.sh` 联动**：无需改动（上游脚本零变更，无联动点）。
4. **红线遵守**：未覆盖任何用户私有配置；未上 FreeBSD 实机（无变更，0.82 复验不适用）。

## 3. 校验记录（Windows 侧）

- `bash -n 初始化.sh / 编译安装.sh / 远程回归.sh` → 3/3 语法通过。
- `diff <(git show 8bf6c9250f:freebsd/<f>) <lightharness 同名文件>`（dsh-jail-run.c / dsh_web.rcd / verify-sandbox.mjs）→ 3/3 逐字节一致。
- `git diff e5b5ccbfcb 8bf6c9250f -- freebsd/` → 空（fork 侧零改动）。
- `git ls-tree dsh-v0.2.0-rc.2 freebsd/` → 空（上游 rc.2 无该目录）。

## 4. 判据核销

- "15 个文件逐一对账有结论"：✅ 见 §1（结论均为"无上游增量，无需同步"，理由=两侧零变更；同步/不同步均写明）。
- "可同步部分 0.82 实机 run-e2e 5/5"：不适用（无可同步部分）；已按替代判据完成 Windows 侧 `bash -n` 校验，**无"待 0.82 实机复验"挂账项**。
