# R126 D 路：fork FreeBSD 对账（合流 dsh-v0.2.1-alpha.1）

> 路：D（fork 侧 freebsd/ 实况核实 + 与 lightharness/freebsd 对账）
> 基准：fork 合流提交 `36ec2a4157`（parent₁ = fork 侧 `8bf6c9250f`，parent₂ = 上游 `5badb15009` = dsh-v0.2.1-alpha.1）；上游基线 `639ed01539` = dsh-v0.2.0-rc.2。
> 纪律：只读 git 对象 + 本文档，未改代码、未 git commit/push。
> **总结论（三选一）：零同步。** fork 侧 freebsd/ 在本轮合流中零变更，与 lightharness/freebsd 重叠文件逐字节一致，无任何待同步/待移植项。

## §0 对账基准与命令

| 核查项 | 命令 | 退出码 | 结果 |
| --- | --- | --- | --- |
| 合流提交确认 | `git log --oneline -3 36ec2a4157` | 0 | Merge upstream dsh-v0.2.1-alpha.1 into FreeBSD fork |
| fork→合流 freebsd/ 变更 | `git diff --stat 8bf6c9250f 36ec2a4157 -- freebsd/` | 0 | **空输出，零变更** |
| 合流树 freebsd/ 清单 | `git ls-tree 36ec2a4157 --name-only freebsd/` | 0 | 15 文件（与 R110 清单一致） |
| 上游树有无 freebsd/ | `git ls-tree 5badb15009 --name-only freebsd/` | 0 | **空（上游无该目录）** |
| 合流 vs 上游 freebsd/ | `git diff --stat 5badb15009 36ec2a4157 -- freebsd/` | 0 | 15 files changed, 1163 insertions（全为 fork 新增，零删除） |
| 上游增量适配面过滤 | `git diff --name-only 639ed01539 5badb15009 \| grep -iE "freebsd\|jail\|rcd\|verify-sandbox\|dsh-web"` | 1 | **零命中**（无 freebsd 命名文件） |
| 交集分析 | `comm -12 <(git diff --name-only 639ed01539 8bf6c9250f\|sort) <(git diff --name-only 639ed01539 5badb15009\|sort)` | 0 | 7 文件（见 §2） |

## §1 fork 侧 freebsd/ 变更明细

- `git diff 8bf6c9250f 36ec2a4157 -- freebsd/` → **空**。fork 的 15 个 freebsd/ 脚本在本轮合流中**一字未动**（R110 时 fork HEAD 已是 `8bf6c9250f`，本轮合流直接沿用）。
- 合流树相对上游树的 freebsd/ 差异 = 15 文件全量新增（+1163 行、零删除），即 freebsd/ 整体仍是 fork 专属目录，上游 v0.2.1 树中不存在。
- 15 文件：audit-merge.sh / build-lib.sh / build-new.sh / commit.msg / dsh-jail-run.c / dsh-web-restart.sh / dsh-web-run.sh / dsh_web.rcd / probe-binary.sh / push.sh / run-e2e.sh / run-verify.sh / stage-build.sh / sync-build-verify.sh / verify-sandbox.mjs。

## §2 上游增量触及 fork 适配面清单

上游 rc.2→v0.2.1-alpha.1 增量中，`freebsd|jail|rcd|verify-sandbox|dsh-web` 命名文件**零命中**（grep 退出码 1）。排除 `.agents/notes` 文档后，源码层面触及 loader/sandbox/rcd/verify 的有：`packages/sandbox/sandbox-policy/`（新增子包 invariant.ts 等）、sandbox 各包 README/package.json、`vendor/loader/`（README/package.json/entry.ts）、`packages/typert/loader/tests/loader.spec.ts`、`packages/client/modules/tests/loader.client.spec.ts`、`scripts/verify-*.ts/mjs` 系列、`snapshots/session/pty-tools-sandbox-backend/tool-schemas.expected.json` —— 均为测试/文档/校验脚本级，未触及 fork 的运行时适配逻辑。

fork 适配总量：`git diff 639ed01539 8bf6c9250f` 共 82 文件。与上游增量的文件交集仅 **7 个**：
`.github/workflows/ci-master.yml`、`package.json`、`pnpm-lock.yaml`、`pnpm-workspace.yaml`、`packages/boot/app-boot/src/profile-resolution/resolver.ts`、`scripts/gen-cordis-catalog.ts`、`vendor/README.md`。

关键存活抽查（合流树 vs 上游树的 fork 改动留存）：
- `vendor/loader/src/internal.ts` **不在交集内**（上游未触碰）；合流树 L108–120 的 FreeBSD guard（`process.platform === 'freebsd'` 双分支 + 注释）与 fork 提交 `8bf6c9250f` **逐字一致**；上游 `5badb15009` 同文件 grep freebsd 零命中。
- `pnpm-workspace.yaml`：fork 的 "Cross-platform native binary support (FreeBSD port + CI + dev machines)" 注释块在合流树完整保留。
- `resolver.ts`：fork 的 `process.platform === 'freebsd'` 分支在合流树保留。

结论：上游 v0.2.1 增量未破坏任何 fork 适配面，合流树中 fork 适配改动全部存活。

## §3 mods/claude 包 fork 实况（佐证用户"不用复刻"判断）

- 合流树 `packages/experimental/` 共 **28 个包**，含 `claude-code-mods`（`git ls-tree -r` 计 **61 文件**）与 `client-ui-claude-code-mods`。
- `git diff 8bf6c9250f 36ec2a4157 --stat -- packages/experimental/claude-code-mods` → 61 files changed, **8096 insertions(+), 零 deletions**：合流把该包从上游全量带入。
- **决定性证据**：`git diff 639ed01539 8bf6c9250f -- packages/experimental` → **空**，即 fork 基线的 experimental 目录与上游 rc.2 **完全一致**。fork 从未对任何包做裁剪或打桩。
- claude-code-mods / client-ui-claude-code-mods / agent-team-profile / inspector-profile / session-inspector 这 5 个包是上游 v0.2.1 **新增**（fork 基线与 rc.2 均无），合流时按上游原样带入，未做 FreeBSD 化处理。

**定性：保留未裁剪。** 用户"不用复刻"的判断成立——fork 侧对无 FreeBSD 版本的包既未裁剪也未打桩，mods 包在合流树完整存在，lightharness 侧无需也无法从 fork 搬运任何 mods 相关差异化处理（fork 本就没有）。

## §4 与 lightharness/freebsd 对账表

lightharness/freebsd/ 现有 6 文件（dsh-jail-run.c、dsh_web.rcd、verify-sandbox.mjs、初始化.sh、编译安装.sh、远程回归.sh）。fork 侧以合流树 `36ec2a4157:freebsd/` 为准导出对比：

| lightharness 文件 | fork 对应（36ec2a4157） | 本轮有无改动 | 结论 |
| --- | --- | --- | --- |
| dsh-jail-run.c | freebsd/dsh-jail-run.c | 无（§1 零变更） | diff 校验**逐字节一致**，零同步 |
| dsh_web.rcd | freebsd/dsh_web.rcd | 无 | 逐字节一致，零同步 |
| verify-sandbox.mjs | freebsd/verify-sandbox.mjs | 无 | 逐字节一致，零同步 |
| 初始化.sh | 无对应（fork 无此文件） | fork 侧不适用 | lightharness 自有，无需同步 |
| 编译安装.sh | 无对应（功能覆盖 build-lib/build-new/stage-build） | 同上 | lightharness 自有，无需同步 |
| 远程回归.sh | 无对应（功能覆盖 run-e2e/run-verify） | 同上 | lightharness 自有，无需同步 |

反向缺口（fork 有、lightharness 无）：audit-merge.sh、build-lib.sh、build-new.sh、commit.msg、dsh-web-restart.sh、dsh-web-run.sh、probe-binary.sh、push.sh、run-e2e.sh、run-verify.sh、stage-build.sh、sync-build-verify.sh 共 12 文件——与 R110 结论一致（fork 专属流程工具，lightharness 功能由自有三脚本覆盖），本轮 fork 侧零变更，**维持"不同步"结论，无新增待移植项**。

## §5 结论（三选一）

**【零同步】** 依据：
1. fork 侧 freebsd/ 在合流 `8bf6c9250f→36ec2a4157` 中零变更（diff 空）；
2. 上游 v0.2.1 增量中 freebsd/jail/rcd/verify-sandbox/dsh-web 命名文件零命中，源码级触及均为测试/文档/校验脚本，未破坏 fork 适配（guard 逐字存活）；
3. 与 lightharness/freebsd 的 3 个重叠文件逐字节一致；
4. mods/claude 包：fork 保留未裁剪（上游新增包全量带入），佐证"不用复刻"。

待同步 0 文件；fork 自有改动待移植 0 文件；dsh-jail-run.c 无 C 改动，无需重编 setuid。

## 校验记录

- `git show 36ec2a4157:freebsd/<f>` 导出 15 文件至临时目录，`diff` 对 lightharness 3 重叠文件 → 3/3 IDENTICAL。
- `git show 36ec2a4157:vendor/loader/src/internal.ts | grep -n -i freebsd` → L108/111/116 命中，与 `8bf6c9250f` 版本逐字一致；`5badb15009` 同文件 grep freebsd → 零命中（exit 1）。
- `git ls-tree -r 36ec2a4157 --name-only packages/experimental/claude-code-mods/ | wc -l` → 61。
- 存疑项：无。所有结论均有上述命令直接输出支撑。
