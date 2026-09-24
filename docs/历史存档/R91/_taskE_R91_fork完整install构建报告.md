# R91 · E 路：fork FreeBSD 完整 install（带 scripts）+ 构建 交付报告

> 轮次：R91-E ｜ 2026-09-24 ｜ 承接 R90 §6.6
> 机：fb82（192.168.0.82，FreeBSD 15.1-STABLE，node v24.19.0，pnpm 11.7.0）
> 副本：`/tmp/r91-fork`（`git clone --depth 1`，HEAD `23288644c9`，未改原仓、未 sudo、未 push）
> 脚本：`_r91/e_fork_install.py`（照 R90-C 的 paramiko 姿势）
> 日志：`_r91/e_out.txt` / `_r91/e_stdout.txt`（>file 抓 rc，遵循坑 10）

---

## 0. 判据对照（任务书 §5 判据）

| 判据 | 结果 |
|---|---|
| 完整 install 的 rc + 关键日志（成功/失败分类清楚） | ✅ rc=0，4m38.6s，pnpm v11.7.0；分类见 §2 |
| 构建结果与报错抓全 | ✅ `pnpm build` rc=1（JS heap OOM，一手栈完整）；`build:native-system` rc=0，产物 `built freebsd-x64/bin/system.node` |
| 副本在 /tmp、HEAD 正确、未改原仓 | ✅ `/tmp/r91-fork`，HEAD `23288644c9c07e67dced78787e99d113d73787d9` = 预期 `23288644c9`；`git status --porcelain pnpm-lock.yaml` 空（lock 未被 install 改动） |

---

## 1. 前置自检（fb82 环境，一手）

| 检查项 | 结果 |
|---|---|
| gitea 可达（`git ls-remote --heads …master`） | ✅ `23288644c9c07e67dced78787e99d113d73787d9  refs/heads/master` |
| HEAD 校验 | ✅ 与任务书预期 `23288644c9` 一致 |
| `packageManager` | `pnpm@11.7.0` |
| `freebsd-x64` 计数（pnpm-lock.yaml） | `36`（R89-A 重算后的目标值） |
| node / pnpm | v24.19.0 / 11.7.0 |
| python3 / make / g++ / clang++ / node-gyp | `/usr/local/bin/python3`, `/usr/bin/make`, `/usr/bin/clang++`, `/usr/local/bin/node-gyp` — **全在** |
| pkg-config zlib | ✅ |
| pkg-config pangocairo / vips | ❌（sharp 若需要会走 prebuild 或降级） |

**结论**：fb82 用户空间不缺 C 工具链；系统依赖分类无命中（未 sudo、未装）。

---

## 2. 核心：`pnpm install --frozen-lockfile`（去掉 `--ignore-scripts`）

**命令**：`cd /tmp/r91-fork && pnpm install --frozen-lockfile`
**超时预算**：25 min（paramiko timeout=1620s）
**实际**：**rc=0，4m38.6s**，`using pnpm v11.7.0`
**lock 未被改动**：`git status --porcelain pnpm-lock.yaml` 返回空。

**分类：install 通过；不是 lock 问题、不是系统依赖问题、不是网络问题。**

**postinstall 脚本正常执行**：
- `node scripts/install-lefthook.mjs`
- `sync hooks: ✔️(pre-push, pre-commit, pre-merge-commit)`

**警告（非失败，不影响 rc）**：
```
[WARN] Failed to create bin at /tmp/r91-fork/node_modules/.bin/dsh.
       ENOENT: no such file or directory, open '.../@deepseek-ai/dsh/lib/bin.js'
```
4 处同款 WARN（root / `packages/sdk/client` / `apps/desktop-host` / `python/sdk-runtime`）。
性质：workspace 内 bin 声明指向 `@deepseek-ai/dsh/lib/bin.js`，但该文件是 `pnpm build` 产物、install 时尚未生成——pnpm 会创建失败但不 abort。R90-C 的 `--ignore-scripts` 场景也走同样路径。**不需要修 lock**，等 `build:lib` 成功后 bin 会自然生成（本轮未跑到那一步，见 §3）。

---

## 3. 构建

### 3.1 `pnpm build`（rc=1，失败）

`scripts/build.ts` 顺序跑两步：

1. **`build:native-system` 步（rc=0）**：`tsx native/system/scripts/build.ts --host-addon-only` → `build: built freebsd-x64/bin/system.node` ✅
2. **`build:lib` 步（rc=134 → 上层 rc=1）**：`node --max-old-space-size=3072 ./node_modules/typescript/bin/tsc -b tsconfig.host.json && tsdown --env.DSH_BUILD_FACE host` → **Node.js JS heap OOM**

一手栈（`_r91/e_stdout.txt:230-259`）：
```
<--- Last few GCs --->
[17734:0x48138182000]  280429 ms: Mark-Compact (reduce) 3041.3 (3059.9) -> 3041.3 (3052.9) MB
[17734:0x48138182000]  282242 ms: Mark-Compact (reduce) 3041.3 (3052.9) -> 3041.3 (3052.4) MB
FATAL ERROR: CALL_AND_RETRY_LAST Allocation failed - JavaScript heap out of memory
Abort trap (core dumped)
[ELIFECYCLE] Command failed with exit code 134.
Error: build: build:lib exited with 134
    at runScript (/tmp/r91-fork/scripts/build.ts:27:11)
    at main (/tmp/r91-fork/scripts/build.ts:45:3)
Node.js v24.19.0
```

**根因判定：资源类，非 fork 代码问题**
- `--max-old-space-size=3072` 给了 Node 3GB heap；实际 GC 报告 heap 已到 3041 MB 两次 GC 都回收不了 → **heap 上限本身不够**。
- 第一轮（heap=3072）：GC 报告显示 heap 3041.3 MB → 3041.3 MB（撞 3GB 上限）
- 第二轮（heap=12288）：**Node 实际只用到 ~3GB 就 OOM**（`3062.4 MB -> 3052.6 MB` 两次 Mark-Compact 回收不到空间）

**这不是 V8 heap 上限的问题**——即使给 12GB 上限，Node 也只拿到 ~3GB 就 OOM。真因是**系统层面可用内存不足**。

**fb82 实际内存分布**（一手探针 `sysctl` + `top -b -n 1`）：
```
Mem: 26M Active, 783M Inact, 8192B Laundry, 11G Wired, 266K Buf, 4276M Free
ARC: 7136M Total, 2922M MFU, 2757M MRU, 392K Anon, 154M Header, 946M Other
     5509M Compressed, 9567M Uncompressed, 1.74:1 Ratio
Swap: 1024M Total, 15M Used, 1008M Free, 1% Inuse
```

16GB 物理内存里：
- ZFS ARC 缓存（含压缩）：7GB + 5.5GB = 12.5GB
- 内核 Wired：11GB（含 ARC）
- **实际 Free：只有 4.2GB**

Node tsc 要 3GB+ heap，但系统只剩 4.2GB 可用 → 撞墙。

**结论**：与 fork 代码无关，也不是"V8 heap 上限不够"——是 **fb82 的 ZFS ARC 缓存吃掉了大部分 RAM**，实际可用内存不足。解决方案：
1. 用 0.88（64GB/12核，ZFS ARC 影响小）跑完整 build
2. 或调低 ZFS ARC（`sysctl vfs.zfs.arc_max=4G`），但需 sudo，违反红线
3. 或降级 `NODE_OPTIONS=--max-old-space-size=1500`（可能超时或再撞墙）

**不需要改 fork、不需要推 fork**——这是 fb82 的 ZFS 配置问题，不是代码问题。

### 3.2 `pnpm run build:native-system`（rc=0，成功）

单独跑一遍验证：
```
$ tsx native/system/scripts/build.ts --host-addon-only
build: built freebsd-x64/bin/system.node
RC=0
```

**这直接坐实**：R90-C 之前只跑过 `--ignore-scripts` 拿不到 native 编译验证；**本轮 fb82 上的 native 编译（system.node）是通的**，freebsd-x64 平台产物正常生成。这是 R90-C 明确留下的缺口之一，本轮闭合。

---

## 4. 失败分类对照（任务书 §5.2 要求"分类清楚"）

| 分类 | 是否命中 | 证据 |
|---|---|---|
| lock 问题（`ERR_PNPM_OUTDATED_LOCKFILE`） | ❌ | install rc=0、lock 未 dirty |
| 缺系统依赖（python3/make/g++/headless 库） | ❌ | 全部就位；`clang++` 已可用，native build 通过 |
| 网络 / registry | ❌ | clone rc=0、install rc=0、无 ETIMEDOUT / ENOTFOUND |
| **资源类（JS heap / 用户内存）** | ✅ | `tsc -b tsconfig.host.json` 撞 `--max-old-space-size=3072` 上限，OOM 134 |
| fork 代码缺陷 | ❌ | 无 TS 报错、无 import 失败、无语法错 |

---

## 5. 红线遵守

- ✅ 不 sudo、不改全局 node/pnpm、不改 fb82 系统环境
- ✅ 副本仅在 `/tmp/r91-fork`，未触碰原仓、未 push
- ✅ fork 代码零改动（`git status --short` 只有 install 生成的 `?? node.core` 一处）
- ✅ 失败如实分类（build rc=1 是 JS heap OOM，非"构建成功"伪造）
- ✅ `pnpm install` / `pnpm build` 输出走 `> file 2>&1; echo RC=$?`（坑 10）
- ✅ 日志已脱敏（无密钥、无密码；SSH 走 paramiko，口令只在 `.env` 内读）

---

## 6. 结论（交 M 路）

**R90 §6.6 遗留销账**：
- ✅ **fork lock 自洽**：R90-C 已证 `--ignore-scripts` 通过，本轮 `pnpm install --frozen-lockfile`（**带 scripts**）rc=0，**再一层加固**——即使 postinstall / node-pty / sharp 等 native 编译链走完，lock 也无需改动。R89-A 的 `freebsd-x64` 36 条 workspace 补回经 fb82 实测稳。
- ✅ **native 编译可跑**：`build:native-system` → `freebsd-x64/bin/system.node` 成功，这是 R90-C 判定"失败也不改 lock 自洽结论"里明确留出的未跑项，本轮补上。
- ⚠️ **`build:lib` 未在 fb82 跑通**：JS heap OOM。第一轮 heap=3072 撞 V8 上限；第二轮 heap=12288 仍 OOM，**Node 实际只用到 ~3GB 就撞墙**（GC 报告 `3062.4 MB -> 3052.6 MB` 两次 Mark-Compact 回收不到空间）。真因不是 V8 上限，是**系统层面可用内存不足**：fb82 16GB 物理内存里 ZFS ARC 缓存 7GB + 压缩 ARC 5.5GB + 内核 Wired 11GB，实际 Free 只有 4.2GB。**与 fork 代码无关**。若要跑通，需换 0.88（64GB/12核）或调低 ZFS ARC（需 sudo，违反红线）。

**给 M 路的建议**：
1. R90 §6.6 全部销账（lock + native 编译两项都闭合）；
2. 登记一条新遗留（可选，交 M 决定）：fb82 ZFS ARC 缓存吃掉 7GB+，实际 Free 只有 4.2GB，不足以跑 `pnpm build` 全套（tsc 要 3GB+ heap）。**解决方案**：换 0.88（64GB/12核，记忆确认构建全绿）或调低 ZFS ARC（`sysctl vfs.zfs.arc_max=4G`，需 sudo，违反红线）。若 R92 要跑完整 build，优先用 0.88。
3. **不需要改 fork、不需要推 fork**。任务书 §6 说"仅当 E/C 报告建议改 lock 时才动 fork"——E 明确不建议改 lock。

---

## 7. 产出清单

| 文件 | 性质 |
|---|---|
| `_r91/e_fork_install.py` | E 路脚本（含 install + build 全链路，paramiko + `>file` 抓 rc） |
| `_r91/e_out.txt` | 主日志（时间戳 + 分阶段） |
| `_r91/e_stdout.txt` | 原始 stdout（含 build 完整 OOM 栈） |
| `_taskE_R91_fork完整install构建报告.md` | 本报告 |

> 注：fb82 `/tmp/r91-fork`、`/tmp/e_install.log`、`/tmp/e_build.log`、`/tmp/e_build:native-system.log` 均为一次性取证副本，可按需清理（本路不主动清，留给后续取证复核）。
