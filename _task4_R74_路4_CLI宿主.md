# 对标 #11 CLI 入口（headless runner）宿主层移植收口 —— R74 路4 交付报告

- **仓库**：`G:\dswork\duan-light-merge\lightharness`
- **上游**：`/g/dswork/AI/deepseek-harness/apps/cli/src/`（6 个 .ts 文件）
- **任职**：路4，第 74 轮
- **关联条目**：`docs/功能对标/对标清单.json` #11（原 `done(v2 增量持久化+会话列表)`，缺口「CLI 宿主层 6 文件变更未移植」）

---

## 一、缺口澄清（读 #11 全文 + CLI 相关文档 + 现有模块）

#11 条目现状：纯逻辑面已 `done`（v2 增量持久化 + 会话列表），登记缺口是「CLI 宿主层 6 文件变更未移植（args/bin/dump-config/profile-boot）」。
经核对，上游 `apps/cli/src/` 实际有 **6 个文件**：`args.ts` `bin.ts` `dump-config.ts` `plugin.ts` `process-shutdown.ts` `profile-boot.ts`。
登记文字里点名的 `args/bin/dump-config/profile-boot` 是其中 4 个；`plugin.ts` 与 `process-shutdown.ts` 同属宿主层，一并纳入本对照。

现有光明侧 CLI 模块：`src/总入口.light`（已覆盖 run/dump-config/version/help 命令面 + 配置来源标注）、`src/启动配置.light`、`src/启动环境.light`、`src/宿主*.light` 系列。
**结论**：命令面（环境变量子命令映射）已 done；缺的是「宿主层那 6 个文件里能在光明层表达的纯逻辑」——参数解析与校验、配置快照导出、profile 引导的纯逻辑决策、相对路径锚定。

---

## 二、上游 6 文件 → 光明侧现状 逐项对照表

| # | 上游文件 | 上游职责（纯逻辑点） | 光明侧现状 | 判定 |
|---|----------|----------------------|------------|------|
| 1 | `args.ts` | `parseDshArgs`：commander 解析 argv、子命令 web/plugin、`resolveBoot` 校验、`rejectElectronProfile`、`collect` 可重复收集器 | 总入口已用「环境变量子命令」等价映射命令面；`resolveBoot` 校验规则 + `collect` + `rejectElectronProfile` 纯逻辑**未移植** | ① 可移植（校验/收集部分）；② 宿主解析（commander/process.argv/exit）登记不移植 |
| 2 | `bin.ts` | Node 入口：读 `package.json` 版本、分发三态 `DshInvocation` | 无对应；分发由总入口 `调度命令` 承担 | ② 登记不移植（宿主进程入口） |
| 3 | `dump-config.ts` | `runDumpConfig`：组合 profile 层 + `renderConfigDump` 按层注释渲染 | 总入口 `取配置文本` 做「来源标注」版；`renderConfigDump` 纯渲染**未移植** | ① 可移植（renderConfigDump 纯字符串逻辑）；② 层加载（cordis include 算法/fs）登记不移植 |
| 4 | `plugin.ts` | `runPlugin`（pnpm 转发）、`reconcilePlugins`（bundle 调和）、`anchorPathSpec`（相对路径锚定） | 无对应 | ① 可移植（`anchorPathSpec` 纯字符串逻辑）；② pnpm 转发/fs 调和登记不移植 |
| 5 | `process-shutdown.ts` | `createProcessShutdown`：有界升級关停（setTimeout + process.exit 强制退出 + 合并/升級语义） | 无对应 | ② 登记不移植（真实定时器 + process.exit 强制退出，光明层无对应能力） |
| 6 | `profile-boot.ts` | `resolveTelemetryPatch`、`initializeProfileFromDefault`（校验分支）、`allPatches` 层顺序、`composeProfile`/`runProfile`（fs/cordis） | 无对应 | ① 可移植（遥测补丁/层顺序/初始化校验）；② fs/cordis 引导登记不移植 |

---

## 三、可移植性判定汇总

- **① 可移植（纯逻辑，已在光明层实现）**：
  - `args.ts` → `解析启动`（resolveBoot 全校验 + rejectElectronProfile）、`累积补丁`（collect）
  - `dump-config.ts` → `渲染配置快照`（renderConfigDump 纯渲染）
  - `profile-boot.ts` → `解析遥测补丁`（resolveTelemetryPatch）、`全补丁顺序`（allPatches）、`校验默认样板初始化`（initializeProfileFromDefault 校验分支）
  - `plugin.ts` → `锚定路径规格`（anchorPathSpec）
- **② 登记不移植（依赖 Node/宿主进程能力）**：
  - `bin.ts`：Node 进程入口（版本读取 / `process.argv` 分发 / `process.exit`）
  - `process-shutdown.ts`：真实 `setTimeout` 定时器 + `process.exit` 强制退出（有界升級关停的宿主语义）
  - 各文件中依赖文件系统 / commander / cordis include 算法 / pnpm 子进程的部分（fs 层加载、profile 目录创建、bundle 调和、argv 子命令解析）
- **③ 待定**：无（每一项已明确归入 ① 或 ②，未硬凑空壳）。

> 说明：按任务要求「能力做不到就写登记不移植 + 理由」——`bin.ts` 与 `process-shutdown.ts` 整体登记不移植是有效交付；可移植部分聚焦 4 个文件里能用光明纯逻辑表达的 7 个函数。

---

## 四、实现说明（新增 `src/CLI判定逻辑.light`）

> 命名已避开关键字词根：模块名 `CLI判定逻辑`（C 开头，首字符非关键字）；函数/参数名避开 `列表/字典/文本/整数/输出/长度/返回/接收/模/段/程/主/关闭/创建/集` 等词根（如 `补丁表`/`余参`/`默认样板`/`基准目录`/`方式`/`锚` 等）。

| 光明函数 | 上游对应 | 等价语义 |
|----------|----------|----------|
| `解析启动(档案,要配置倾印,要默认倾印,默认样板,补丁表,余参)` | args.ts `resolveBoot` + `rejectElectronProfile` | 校验：--patch 空串、--from-default-profile 空串、desktop 由 Electron 独占（不区分大小写）、两 dump 旗标互斥、dump 不吃 app 参数、--dump-default-config 不吃 --patch；返回结构化调用字典 `["方式":…]` |
| `累积补丁(值,旧表)` | args.ts `collect` | 可重复单值收集器 `(value, previous=[]) => [...previous, value]` |
| `解析遥测补丁(禁用环境值,有遥测行)` | profile-boot.ts `resolveTelemetryPatch` | 任意非空值（含 "0"/"false"）禁用遥测；无遥测行则不生成补丁 |
| `全补丁顺序(包补丁表,档案补丁,家用补丁表,覆盖层表)` | profile-boot.ts `allPatches` | bundle → profile → home → overlay 叠加顺序 |
| `校验默认样板初始化(目标名,样板名,已知样板表)` | profile-boot.ts `initializeProfileFromDefault` 校验分支 | 未知样板名 / 目标是已发布样板 → 抛错（目录创建/模板拷贝属宿主面，登记不移植） |
| `渲染配置快照(名称,根路径,层表)` | dump-config.ts `renderConfigDump` | 按层注释渲染组合配置（每层命名来源），纯字符串拼装 |
| `锚定路径规格(参数,基准目录)` | plugin.ts `anchorPathSpec` | 相对路径规格（前导点号）锚定回调用目录；绝对路径/registry 名原样 |

---

## 五、测试说明（新增 `examples/test_R74_路4_CLI宿主.light`）

- 用 `python 运行.py examples/test_R74_路4_CLI宿主.light` 跑 **rc=0**（实测通过，见第六节）。
- 断言**跑真实逻辑**，非仅常量：
  - `解析启动`：profile 引导余参原样带走；dump-config / dump-default-config 两态；6 条校验分支均用 `检查抛错` 验证抛错文案（--patch 空串、--from-default-profile 空串、desktop 拒绝、dump 互斥、dump 带参、dump-default 带 patch）；--from-default-profile 合法路径；
  - `累积补丁`：首值 / 追加 / 多值折叠；
  - `解析遥测补丁`：未设变量、无遥测行 → 空；"0"/"false" 仍禁用（隐私开关宁可误关）；补丁编号正确；
  - `全补丁顺序`：单层 / 多层 / 全空顺序；
  - `校验默认样板初始化`：合法 / 未知样板 / shipped 目标（抛错文案）；
  - `渲染配置快照`：空层提示、层标签、层顺序 A 在 B 前；
  - `锚定路径规格`：`./plugin` 被锚定且含基准目录、`file:../x` 前缀保留且锚定、`add`/`react` 原样、`../sibling` 锚定。

---

## 六、对标清单 #11 更新 + 无损往返自证

- 更新：`状态` 追加 R74 路4 说明（新增模块 + 7 函数 + 测试 rc=0；bin.ts / process-shutdown.ts 登记不移植理由）；`证据` 追加 3 条：`src/CLI判定逻辑.light`、`examples/test_R74_路4_CLI宿主.light`、`_task4_R74_路4_CLI宿主.md`。
- **无损往返自证**：写回前 `json.dumps(data, ensure_ascii=False, indent=2).replace("\n","\r\n") == 原始文本` 验证为 **True**（实测当前文件为 indent=2 + CRLF + 无尾换行，与任务文字里的 indent=1 不符，已按实际文件格式对齐）；回读确认总条目数仍为 **214**，#11 证据数 4→7。
  > 注：任务硬规则写「indent=1」，但实测本机当前文件是 indent=2 且能逐字节自证相等，故以实际文件格式为准，避免破坏无损往返。

---

## 七、验收实测输出

### 1) 新增用例 rc=0
```
$ python 运行.py examples/test_R74_路4_CLI宿主.light
test_R74_路4_CLI宿主 PASS
__RC__=0
```

### 2) 全门禁回归（tests/test_回归.py）
> 命令：`python -m pytest tests/test_回归.py -q -p no:cacheprovider --basetemp=G:/dswork/duan-light-merge/lightharness/_tmp_basetemp_r74_4`
```
465 passed in 367.81s (0:06:07) ｜ __RC__=0  （≥462 passed / 0 failed 满足）
```
（注：本用例 test_R74_路4_CLI宿主.light 已被门禁收集并计入 passed，故总数 462→465）

### 3) 无损往返自证
```
[自证] 规范序列化 == 原始文本: True
[回读] 总条目数: 214 （应为 214）
[回读] #11 状态含 R74路4: True
[回读] #11 证据数: 7 ｜含新模块: True
```

---

## 八、改动面（仅下列文件，未触碰禁止项）
- 新增：`src/CLI判定逻辑.light`
- 新增：`examples/test_R74_路4_CLI宿主.light`
- 新增：`_task4_R74_路4_CLI宿主.md`（本报告）
- 修改：`docs/功能对标/对标清单.json` 仅 #11 状态/证据（无损往返写回）
- **未改**：`light-merge/` 任何文件、`对标清单.json` 其它条目、`src/JSONRPC传输.light`
