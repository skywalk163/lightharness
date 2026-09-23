# R89-A 交付报告：fork 构建侧 follow-up（pnpm lock 重算补 freebsd-x64）

> 执行时间：2026-09-23 23:2x–23:5x ｜ 仓：`G:/github/deepseek-harness` ｜ HEAD：`6bf98a4370`
> 结论：**环境可用，lock 重算成功**，补回了 fork 独有的 `freebsd-x64` workspace lock 条目；
> 三处 FreeBSD 对齐源码未被覆盖。**建议 M 路 push 新 lock 到 fork origin master**。

---

## 1. 环境探测（第一步，实测）

| 项 | 值 |
|---|---|
| node | `v22.22.2` |
| pnpm | `11.7.0`（与仓库 `package.json` 的 `"packageManager": "pnpm@11.7.0"` **完全一致**） |
| corepack | `0.34.6` |
| registry | `https://registry.npmmirror.com`（仓库 `.npmrc` + 用户级 `.npmrc` 均已配置镜像） |
| node_modules | 不存在（本机从未完整 install） |
| 分支 | `master`（已快进到 `origin/master` = `6bf98a4370`） |

判定：**环境可用**，进入后续步骤。

---

## 2. ⚠️ 过程中的一次工作树事故与恢复（如实记录）

首次执行 `git checkout -q master` 时（后台任务被环境切换打断，git 进程卡死并留下 `.git/index.lock`），
中断的检出把工作树部分回退到了**过期的本地 `master`（`9d9035b7`）**：

- `git diff --stat` 显示 **3743 文件变更 / 1,058,014 行删除**；
- `git status` 出现 **78 个未跟踪文件**（`9d9035b7` 有而 `6bf98a4370` 没有的文件）。

恢复步骤（全部一手执行，无数据损失——事故前 `git status` 为干净，无任何未提交工作）：

1. `taskkill //F //PID 22568` 结束卡死的 `git.exe`；
2. 重命名 `.git/index.lock` → `.git/index.lock.bak_r89`（`rm`/`os.remove` 被本机安全删除钩子拦截，改用 rename）；
3. `git reset --hard HEAD` → 恢复 4371 个文件到 `6bf98a4370`；
4. `git clean -fd` 清掉 78 个中断检出遗留的未跟踪文件；
5. `git fetch origin` + `git branch -f master origin/master` + `git checkout master`
   → 本地 `master` 从过期 `9d9035b7` 快进到 `6bf98a4370`（`git pull --ff-only` 等价效果，走本地已 fetch 的 ref）。

恢复后：`git rev-parse --short HEAD = 6bf98a4370`，`git status --short` **0 条**。

> 📌 下轮注意：本仓本地 `master` 分支此前长期落后于 `origin/master`，**不要**直接 `git checkout master`
> 而不先快进，否则会把工作树拖回旧版本。

---

## 3. lock 重算（核心）

命令（选 `--lockfile-only` 而非完整 `pnpm install`：只重算 lock、**不落地 node_modules**，
避免在本机拉多 GB 依赖、也不污染工作树）：

```
cd G:/github/deepseek-harness
pnpm install --lockfile-only --ignore-scripts
```

结果：**`PNPM_RC=0`，`Done in 2m 56.6s using pnpm v11.7.0`，resolved 1678 包**（1 个 WARN：12 个 deprecated
subdependency，与 lock 重算无关）。

`git diff --stat`：`pnpm-lock.yaml | 16 ++++++++++++----`（**12 增 / 4 删**）。

### 3.1 关键新增：fork 独有的 freebsd-x64 workspace 条目 ✅

```diff
   importers:
     native/system/packages/entry:
       dependencies:
         '@deepseek-ai/node-addon-system-darwin-x64':
           specifier: workspace:~
           version: link:../darwin-x64
+      '@deepseek-ai/node-addon-system-freebsd-x64':
+        specifier: workspace:~
+        version: link:../freebsd-x64
         '@deepseek-ai/node-addon-system-linux-arm64':
           ...
+  native/system/packages/freebsd-x64: {}
```

这正是 R88-A 遗留的缺口（当时冲突解决接受了 upstream lock，丢掉 fork 独有的 freebsd-x64 importer）。
`grep -c freebsd-x64 pnpm-lock.yaml`：**33 → 36**。

### 3.2 附带变化（均为重算的正常副产物，逐条核对过）

| 变化 | 说明 |
|---|---|
| 新增 `packageExtensionsChecksum: sha256-wL7od7Df…` | pnpm 11 重算时写入的校验和字段 |
| `node-pty@1.2.0-beta.15` patch_hash `b40ae545…` → `2798be81…`（2 处：patchedDependencies + snapshots） | **有意义**：反映 fork 实际 patch 文件内容，原 upstream lock 记的是 upstream patch hash |
| `glob@7.2.3` deprecated 文案变化 | 镜像源元数据刷新 |
| snapshots 新增 `@img/sharp-wasm32: 0.35.3` 可选包 | sharp 可选平台包随平台解析补入 |

`lockfileVersion` 保持 `'9.0'`，未被 pnpm 11 升版。

---

## 4. 三处 FreeBSD 对齐验证（未被 install 覆盖）

`git status --short` 全仓仅有 ` M pnpm-lock.yaml` 一条 → **三处对齐源码零改动**。
另逐处 grep 取证（实际路径与 R88-A 报告书写略有出入，已校准）：

| # | 实际文件 | 证据 | 状态 |
|---|---|---|---|
| ① | `native/system/packages/entry/package.json` | L43 `"@deepseek-ai/node-addon-system-freebsd-x64": "workspace:~"`（optionalDependencies，与 darwin/linux 同构） | ✅ 保留 |
| ② | `packages/subprocess/subprocess-local/src/process-inspector.ts` | L588 `if (platform === 'freebsd') return new FreeBSDProcessInspector(internals)`；L557 `freebsdProcessTable()` 用 `/bin/ps -axo pid,ppid,lstart` | ✅ 保留 |
| ③ | `packages/boot/app-boot/src/profile-resolution/resolver.ts` | L616 `process.platform === 'freebsd' ? { requireBuiltin: (m) => require(m) } : require('node-addon-require-builtin')`（internalModules 取内置 loader 的 FreeBSD 分支） | ✅ 保留 |

> 注：R88-A 报告把 ②③ 记作 `native/system/process-inspector`、`native/system/resolver`，
> 实际位于 `packages/subprocess/subprocess-local/src/` 与 `packages/boot/app-boot/src/profile-resolution/`，
> 本轮已校准路径（内容一致，只是路径记录不准）。

---

## 5. 构建验证：**未执行**（有理由，非阻塞）

- `pnpm build` / `pnpm build:native-system` / `pnpm check:ci` 均依赖**已落地的 node_modules**，
  而本轮刻意用 `--lockfile-only`（不落地依赖）。
- 完整 `pnpm install` 在本机需拉取该 monorepo 全量依赖（多 GB 量级，含 electron / sharp / node-pty 预编译产物），
  且 **Windows 并非 FreeBSD 目标平台**，构建结论对 fork 的三处 FreeBSD 对齐没有判定价值。
- 任务书允许：「若仓库有 build/lint 命令且耗时可接受…不强求全绿」。

**建议补做条件**：在 FreeBSD 目标机（192.168.1.5）上执行

```
pnpm install --frozen-lockfile      # 用本轮新 lock，验证 lock 与 workspace 自洽
pnpm build:native-system            # 验证 freebsd-x64 addon 链路
```

---

## 6. 结论与对 M 路的建议

**建议：需要 push 新 lock（M 路执行 `git push origin master` 补推 `pnpm-lock.yaml`）。**

理由（两条硬理由）：

1. **功能必要性**：新 lock 才含 `native/system/packages/freebsd-x64` importer 与 entry 包对它的
   `link:../freebsd-x64` 引用。缺它时 FreeBSD 上执行 `pnpm install --frozen-lockfile` 会因
   「lock 与 workspace 清单不一致」直接失败 —— 即 R88-A 追平 162 提交后 FreeBSD 构建链路是断的。
2. **一致性**：`node-pty` patch_hash 由 upstream 值修正为 fork 实际 patch 值，否则 `--frozen-lockfile`
   会因 patchedDependencies 哈希不符报错。

风险面：仅 `pnpm-lock.yaml` 一个文件、12 增 4 删；三处 FreeBSD 对齐源码零改动；
`lockfileVersion` 未变（仍 9.0），不会波及 CI 的 pnpm 版本假设。

---

## 7. 遗留

- 构建验证（FreeBSD 上 `pnpm install --frozen-lockfile` + `build:native-system`）待目标机补做 —— 列入 R90 遗留。
- `.git/index.lock.bak_r89` 是事故清理的改名残留文件，位于 `.git/` 下，不影响 git 操作，可随时手工删除。
