# freebsd/ 上游 rc.3 对账记录

> 卡：T-0172（D 路）｜基线：上游 `dsh-v0.2.1-rc.3` = `1f81c047fc48fa190a683e469daa699857e9afe8`，
> fork 合流提交 `caef03ee57`，fork HEAD `45285f4aad5852155a09318045443d487fa304e2`。
> 结论：**零同步**（可同步项 0，需重编 setuid 0）；新增 `install-service.sh` 判定为 fork 专属，不搬。

## §0 核查命令与结果

| 核查项 | 命令 | 结果 |
| --- | --- | --- |
| 上游 rc.3 有无 freebsd/ | `git ls-tree --name-only dsh-v0.2.1-rc.3 -- freebsd/` | 空（上游无该目录，freebsd/ 全为 fork 新增） |
| fork 侧 freebsd/ 自上次合流（`36ec2a4157` = alpha.1 合流）以来变更 | `git diff --stat 36ec2a4157..origin/master -- freebsd/` | 3 文件：`audit-merge.sh` 1 行、`dsh-web-run.sh` 1 行、`install-service.sh` 新增 374 行 |
| 变更提交 | `git log --oneline 36ec2a4157..origin/master -- freebsd/` | `9c0d710ebc`（pnpm 注释 11.7.0→11.28.5）、`1101fa2162`（新增 install-service.sh）、`e2bde389d5`（audit-merge 断言 glibc→wasm32） |
| 与 lightharness 重叠文件逐字节校验 | `git hash-object <local>` vs `git rev-parse origin/master:freebsd/<f>` | 3/3 一致（见 §2） |

## §1 16 文件逐一对账

| # | fork 文件 | lightharness 侧 | 本轮上游变动 | 结论 |
| --- | --- | --- | --- | --- |
| 1 | `audit-merge.sh` | 无 | 仅 1 行断言：`libc glibc/musl` → `cpu 含 wasm32`（跟随 `pnpm-workspace.yaml` 的 FreeBSD 适配） | **不同步**：审计对象是 fork 的 pnpm 适配面，lightharness 无 pnpm 工作区 |
| 2 | `build-lib.sh` | 无 | 无 | **不同步**：`pnpm run build:lib:host`，fork 构建链专属 |
| 3 | `build-new.sh` | 无（功能由 `编译安装.sh` 覆盖） | 无 | **不同步**：仅编译到 `/home/workbuddy/` 临时路径的 fork 调试脚本 |
| 4 | `commit.msg` | 无 | 无 | **不同步**：fork 提交说明文本，非可执行资产 |
| 5 | `dsh-jail-run.c` | 有（同名） | 无（对 rc.3 全量新增，但与本地一致） | **无需同步**：逐字节一致（blob `66c20b13…`） |
| 6 | `dsh-web-restart.sh` | 无 | 无 | **不同步**：`pkill -f "[d]sh:freebsd"` 按进程名匹配，与 lightharness「按自身 PID/进程组」红线冲突 |
| 7 | `dsh-web-run.sh` | 无 | pnpm 注释 11.7.0→11.28.5 | **不同步**：`pnpm dsh:freebsd web` 启动器，lightharness 无此前端 |
| 8 | `dsh_web.rcd` | 有（同名） | 无 | **无需同步**：逐字节一致（blob `a2ad1238…`） |
| 9 | `install-service.sh` | 无 | **新增（374 行）** | **不同步**，详见 §3 |
| 10 | `probe-binary.sh` | 无（功能由 `远程回归.sh --jail-only` + `编译安装.sh` 烟雾测试覆盖） | 无 | **不同步**：写死 `/var/dsh-jail-run`（fork 安装位），本地安装位为 `/usr/local/sbin/dsh-jail-run` |
| 11 | `push.sh` | 无 | 无 | **不同步**：含内网 gitea 地址与 `.env` token 读取，属 fork 专属推送流程 |
| 12 | `run-e2e.sh` | 无（`远程回归.sh` 覆盖） | 无 | **不同步**：跑 fork 的 vitest e2e 配置 |
| 13 | `run-verify.sh` | 无（`远程回归.sh` 覆盖） | 无 | **不同步**：仅一行 node 调用 `verify-sandbox.mjs`，本地已由回归脚本包裹 |
| 14 | `stage-build.sh` | 无 | 无 | **不同步**：fork tsc/tsdown 分阶段构建诊断 |
| 15 | `sync-build-verify.sh` | 无 | 无 | **不同步**：fork 同步后 构建+自检 全流程（pnpm/native/flock/vitest） |
| 16 | `verify-sandbox.mjs` | 有（同名） | 无 | **无需同步**：逐字节一致（blob `56ff9a8e…`） |

反向（lightharness 有、fork 无）：`初始化.sh`、`编译安装.sh`、`远程回归.sh` —— 均为本地自有运维脚本，本轮无上游对应物，无需改动。

## §2 重叠文件校验

| 文件 | 本地 blob | 上游 blob | 判定 |
| --- | --- | --- | --- |
| `dsh-jail-run.c` | `66c20b137de5dd40fe5acff146ac018c69658ea7` | 同左 | 一致 |
| `dsh_web.rcd` | `a2ad12388c1ad0035c05734112df988adc8748f1` | 同左 | 一致 |
| `verify-sandbox.mjs` | `56ff9a8ead27c061055f8122e9bb950e05fdfc9d` | 同左 | 一致 |

## §3 install-service.sh 处置

**不同步。** 依据：

1. 前置校验写死 `$REPO_ROOT/pnpm-workspace.yaml`，安装/拉起链路是 `pnpm dsh:freebsd web` + `node_modules` —— 都是 fork（dsh 宿主仓）的运行面，lightharness 树内不存在，照搬后在本地必然 `die "not a deepseek-harness checkout"`。
2. 其模板源 `freebsd/dsh_web.rcd` 依赖 `${dsh_web_chdir}/freebsd/dsh-web-run.sh`，而 lightharness 只有 rcd 副本、无启动器；装上也起不来。
3. lightharness 侧已有的等价能力：`编译安装.sh`（jail helper 编译 + setuid 安装 + 烟雾测试）与 `初始化.sh`（nullfs / helper / 垫片 / 插件 / 沙箱目录 幂等恢复），覆盖了安装器里与 lightharness 相关的那一段。
4. 若需在 FreeBSD 主机上装 `dsh_web` 服务，应直接在 fork 仓执行 `sh freebsd/install-service.sh`（脚本支持 `DSH_REPO=` 指路），无需在 lightharness 侧维护副本。

## §4 其他结论

- **`dsh-jail-run.c` 是否需重编 setuid**：否。与 fork HEAD 逐字节一致，已部署二进制无需重编。
- **`初始化.sh` 联动**：否。rc.3 未改动 jail helper 接口、nullfs 依赖或 python 垫片链路，现有幂等项无需增删。
- **fork 专属红线**：`push.sh`（内网 gitea 地址 + token 环境变量）、`build-new.sh`（`/home/workbuddy/` 私有路径）、`dsh-web-*.sh`（`dsh:freebsd` 进程名）均未搬入。
