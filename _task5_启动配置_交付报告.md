# 任务5（启动配置域）交付报告 —— boot/app-boot profile 解析 + patch 层组合 + cmdline

> 日期：2026-09-12 ｜ 路：任务5 ｜ 对标：#75 boot/app-boot profile + cmdline

## 一、上游依据

| 上游文件 | 行号 | 被复刻的函数/常量 |
|---|---|---|
| `packages/boot/app-boot/src/profile.ts` | L42-45 | `PROFILES_DIR='profiles'` / `PROFILE_PATCH_FILENAME='cordis.patch.yml'` |
| 同上 | L100-107 | `resolveProfileDir(name, home)` —— 名称合法性校验 + join |
| 同上 | L110-131 | `PROFILE_TEMPLATES`（acp/web/headless/sdk/sdk-minimal） |
| 同上 | L139-142 | `DEFAULT_PROFILE_BUNDLES` / `DEFAULT_PROFILE_PATCH_RELOAD='live'` |
| 同上 | L170-190 | `initProfile(dir, bundles, patchReload)` —— 幂等建目录/写 manifest/写空 patch |
| 同上 | L658-672 | `readProfileManifest(binName, dir)` —— 读 JSON 对象校验 |
| 同上 | L679-681 | `writeProfileManifest(dir, manifest)` —— 2 空格缩进 + 尾换行 |
| 同上 | L846-853 | `composeEntries(layers, warn)` —— 空根叠加 + 扁平化 |
| `packages/boot/cmdline/src/index.ts` | L27-89 | `CmdlineArgs` / `provideCmdline` 语义（launcher flags 之外的 inner args 原样透传） |
| `apps/cli/src/args.ts` | L66-117 | `collect`（--patch 可重复）/ `resolveBoot`（dump 互斥、defaultOnly 不带 patch、dump 不带 args） |
| 同上 | L126-211 | `parseDshArgs(argv, version)` —— 三态（profile/dump-config/plugin）+ web 别名 + desktop 保留名 + 缺 --profile |

## 二、实现要点

新模块 `src/启动配置.light`（约 380 行），纯函数化 + 显式注入，对齐 `src/主目录路径.light` 风格：

1. **profile 目录解析** `解析profile目录(名称, 主目录, 配置=空, 环境=空)`：
   - 名称校验：空串 / `.` / `..` / 含 `/` / 含 `\` / `node_modules` 一律抛 `"invalid profile name"`（对齐 L101-105）。
   - 路径拼接走 `主目录路径.主目录路径(主目录, ["profiles", 名称], 配置, 环境)`，**$DSH_HOME 语义完全复用**主目录路径模块（配置 > 环境 > ~/.dsh）。

2. **manifest 读写**：
   - `读取profile清单(bin名, 目录)`：读 `目录/package.json`；文件缺失抛 `"failed to read profile manifest"`；JSON 解析后必须是 dict（null/数组/标量抛 `"must hold a JSON object"`）。
   - `写入profile清单(目录, 清单)`：`序列化JSON(清单, 2) + "\n"`（对齐 L680）。

3. **initProfile** `初始化profile(目录, bundles, patchReload)`：
   - `创建目录(目录)` + 已有文件不覆盖（manifest / patch 文件 / pnpm-workspace.yaml 三段幂等）。
   - manifest 形状：`{name:"dsh-profile-<basename>", private:true, dependencies:{}, dsh:{profile:{bundles, patchReload}}}`。

4. **patch 层组合**：
   - `加载补丁层(bin名, 路径)`：读 JSON 数组；文件缺失返回 `[]`（对齐 `loadOptionalPatches` 的 missing = no layer）。
   - `组合条目(layers)`：输入 `layers: 列表[列表[patch]]`，按外层顺序、内层顺序依次应用。每条 patch：
     - 有 `id`：按 id 在索引表查找；找到则浅合并 `config` 字段（后写覆盖先写）；没找到则新建 entry。
     - 有 `insert`（数组）：把子 entry 按其 `id` 加入输出表（已存在则合并非 id 字段，否则新建）。
   - 输出：按首次出现顺序的 entry 列表。

5. **launcher flags 解析** `解析启动参数(argv)`：
   - 支持 `--profile <name>` / `--from-default-profile <name>` / `--patch <path>`（可重复）/ `--dump-config` / `--dump-default-config` / `-V|--version` / `-h|--help`。
   - 三态：`profile` / `dump-config` / `plugin`；`web` 子命令 = `--profile web` 别名。
   - 校验：缺 --profile 抛错；--patch 空串抛错；profile="desktop" 抛 Electron 保留错；--dump-config 与 --dump-default-config 互斥；--dump-default-config 不能带 --patch；dump 模式不能带 inner args。
   - 第一个不认识的 token 起就是 inner args（`passThroughOptions` 语义）。

## 三、光明现实差异（已在报告标注）

| 项 | 上游 | 光明 | 说明 |
|---|---|---|---|
| patch 文件格式 | YAML（`cordis.patch.yml`） | JSON（`cordis.patch.json`） | 光明无 YAML 解析；patch 为 JSON 数组，每条 `{id, config, insert}` |
| applyEntryPatches 完整算法 | group/disable/`!!js` 表达式/路径锚定 | 只复刻 id 覆盖 + insert 追加 | group/disable/!!js 属 Cordis 宿主面，留后续轮 |
| resolveBundleDir | Node 双锚点 require.resolve | 调用方显式注入层列表 | 光明无 Node 模块解析器；bundle 目录不做 fs 探测 |
| healProfilesModuleFallback | pnpm 软链/ESM 代理 | 不移植 | 宿主安装面，纯逻辑层不涉及 |
| PROFILE_TEMPLATES bundles | `@deepseek-ai/dsh-base` 等真实 npm 包 | 保留同名常量，不解析 | 实际 bundle 目录由调用方注入 |

## 四、测试与 CI

- 新增 `examples/test_启动配置.light`：**32 个断言**（≥12 要求），覆盖 ① 目录解析（7 非法名）/ ② manifest 读写往返 / ③ manifest 校验（数组+缺失）/ ④ initProfile 幂等 / ⑤ patch 组合顺序覆盖 / ⑥ insert 追加 / ⑦ 用户 patch 覆盖 / ⑧ flags 收集 / ⑨ inner args 透传 / ⑩ 校验抛错（缺 profile/空 patch/desktop）/ ⑪ dump 三态与互斥 / ⑫ --from-default-profile。
- 运行：`python 运行.py examples/test_启动配置.light` → **rc=0，PASS**。
- 既有回归：
  - `test_主目录路径.light` → PASS（"主目录路径子系统（模块34）测试通过"）。
  - `test_CLI命令面.light` → PASS（"test_CLI命令面 PASS"）。
  - `python -m pytest tests/ -q -k "主目录 or 总入口"` → 241 deselected（pytest 侧无按名匹配用例，光明测试走 `python 运行.py` 通道，已手动验证）。

## 五、反跑判据

`_antirun_boot.py`（字节级备份/恢复 `src/启动配置.light`）：

| 判据 | 篡改 | 红 | 绿 |
|---|---|---|---|
| A | `组合条目` 把 layers 倒序叠加 | rc=1 | rc=0 |
| B | `解析profile目录` 去掉 `profiles` 段（直接 join 名称） | rc=1 | rc=0 |
| C | `--patch` 收集改覆盖（`patches=[路径值]`）而非追加 | rc=1 | rc=0 |

运行 `python _antirun_boot.py` → **3/3 PASS**（篡改→红，恢复→绿）。

## 六、未移植项（宿主面，留后续轮）

1. **healProfilesModuleFallback / ensureSymlink / ensureModuleProxy**（profile.ts L407-650）：pnpm hoisted 软链 + pkg 虚拟文件系统 ESM 代理，属 Node 安装面。
2. **resolveBundleDir 的 Node require.resolve 双锚点**：光明无 Node 模块解析器；bundle 目录由调用方注入。
3. **applyEntryPatches 完整算法**：group 子条目 patch / disable / `!!js` 表达式 / 路径锚定（`./` 转 file:// URL）。
4. **watchUserPatches / HMR**：cordis HMR 热重载宿主面。
5. **normalizeShippedProfile / INSTALLATION_OWNED_PROFILE_TUPLES**：已退役 profile tuple 迁移逻辑（仅 0.1.5 升级路径使用，新 profile 不触发）。
6. **`web` / `plugin` 子命令的完整 commander 集成**：光明只复刻了纯解析逻辑，未接 commander 树。
7. **未接入 `src/总入口.light` 命令面**：评估为跨域风险（总入口已有"未映射宿主面：profile/patch/plugin 层"明确登记，且 test_CLI命令面 已锁定命令面行为）。本轮仅新增模块不接入；后续轮次如需接入 `HARNESS_PROFILE` 环境变量，可在总入口 dump-config 分支加只读查询。

## 七、移交清单

| 交付物 | 绝对路径 |
|---|---|
| 新模块 | `G:\dswork\duan-light-merge\lightharness\src\启动配置.light` |
| 新测试 | `G:\dswork\duan-light-merge\lightharness\examples\test_启动配置.light` |
| 反跑脚本 | `G:\dswork\duan-light-merge\lightharness\_antirun_boot.py` |
| 本报告 | `G:\dswork\duan-light-merge\lightharness\_task5_启动配置_交付报告.md` |

**未改其他域文件**：`src/总入口.light` 保持只读（未接入命令面，理由见第六节第 7 条）；`src/主目录路径.light` 只读复用。
