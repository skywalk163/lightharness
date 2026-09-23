# R87 任务 B4 交付报告：命令执行 / 配置扩展 / 客户端逻辑移植（shell / workspace / settings / preset / bundle / extensions / hooks / util / web / test-support / client）

> 轮次：R87 路 B4　｜　日期：2026-09-23
> 上游增量：deepseek-harness `ddefc45fbc`（0.1.6 锚点）.. `877717787c`（fork HEAD，已合 0.1.7-alpha.1）
> 范围：packages/shell / workspace / settings / preset / bundle / extensions / hooks / util / web / test-support / client（纯逻辑部分）
> 结论：**11 项移植全部落地（8 新建模块 + 9 更新模块，钩子协议零变化），9 个新增回归用例，全量 pytest 517 passed / 1 skipped / 0 failed，新增红 0。**

---

## 1. 结论速览

| 指标 | 结果 |
|---|---|
| 新建 .light 模块 | 8 个 |
| 更新 .light 模块 | 9 个（预设、预设深化、设置、外壳环境、工具_bash、bash渲染、远程mock、工作区、toolcordis） |
| 零变化模块 | 1 个（钩子协议.light：runner.ts 增量仅宿主接线） |
| 新增回归用例 | 9 个 |
| 拒绝/暂缓项 | 见 §5（web 真实 API、client UI/tsx/css、cordis runner guard/sandbox、package-manifest fs 宿主等） |
| 全量回归（合流后） | **517 passed / 1 skipped / 0 failed**（180s） |
| commit/push | 未执行（红线） |

---

## 2. 逐模块移植表

### 2.1 配置族（4 项：1 新建 + 3 更新 + 1 零变化）

| # | 模块 | 状态 | 对齐上游文件:行号 | 复刻要点 | 回归用例 |
|---|---|---|---|---|---|
| 1 | `src/流式JSON.light` | 新建 | `bundle/headless/src/json-stream.ts` L18-213（truncateUtf8/boundKey/boundValue/boundJsonEvent/boundJsonLine/parseArguments/resultText/addUsage） | `--json` 运行投影的有界序列化侧：MAX_DEPTH=64 递归切尾、truncateUtf8 丢劈开尾字节、深度/字符串/事件三级封顶、参数解析、用量累计；projectJsonRun 主循环属宿主接线已拒绝 | `examples/test_R87_B4_配置_流式JSON.light` |
| 2 | `src/钩子协议.light` | 零变化 | `hooks/hook-protocol/src/runner.ts` | 增量仅 `bash.run→execute().result()` 宿主执行器调用面变化 + ShellExecutor 类型收窄，纯逻辑面零变化；既有 DEFAULT_HOOK_TIMEOUT_MS/时长解析/退出码归一/故障产出已覆盖 | 既有 `test_钩子协议.light` 维持绿 |
| 3 | `src/预设.light` | 更新 | `preset/agent-preset-registry/src/definition.ts` L28-31（entryListProblem 嵌套分支）<br>`display.ts` L47-66（isBuiltInPreset + presetDisplayText 改判据） | 条目列表问题嵌套非列表分支；新增 `是内置预设`（name 缺省且 id∈BUILT_IN_PRESET_KEYS）；显示文本判据从 trust==='system' 改为 name 缺省 | `examples/test_R87_B4_配置_预设登记.light` |
| 4 | `src/预设深化.light` | 更新 | `preset/agent-preset-registry/src/composition-inventory.ts` L140-166（definitionComposition + mountedCompositionRows）<br>`types.ts` L15-46（AgentPresetRow 去 trust 加 broken、authorable→modeSelectionEnabled、删 read-only 错误） | 新增 `定义组合`（先闸门→{broken}，否则展平→{rows}）；`挂载行带前缀`（剥 owner.id: 前缀）；新 registry 形 `是登记行`/`是登记表`/`登记错误码表`（3 码）并列；旧 wire 形保留锁定既有绿 | 同上 |
| 5 | `src/设置.light` | 更新 | `settings/settings/src/redact.ts` L90-117（walk union/transform + redactSecrets 去重）<br>`schema.ts` L11-86（plainConfig/plainSchema/volatileForm/isExpression/projectForm/isVolatilePath） | `走查` 加联合/交叉/变换分支；`脱敏值` 末尾去重；新增 `普通配置`/`克隆模式`/`易变表单`/`是表达式`/`投影表单`/`是易变路径` | `examples/test_R87_B4_配置_设置schema.light` |

### 2.2 命令族（3 项：1 新建 + 4 更新）

| # | 模块 | 状态 | 对齐上游文件:行号 | 复刻要点 | 回归用例 |
|---|---|---|---|---|---|
| 6 | `src/外壳环境.light` | 更新 | `shell/shell/src/types.ts`（ShellExpiryPolicy、ShellExecSpec.onExpiry 默认化） | 到期策略词汇常量；`归一到期策略`：缺省/非 none→kill，显式 none 保留 | `examples/test_R87_B4_命令_外壳渲染.light` |
| 7 | `src/bash渲染.light` | 更新 | `shell/tool-bash/src/render.ts`（tool-pwsh 同构） | `渲染结果` 新增 stopped 标记（插在 timedOut 后、signal 前）；新增 `渲染已提升`（转后台交接文本）；`渲染作业读取` 新签名；旧 `渲染进程读取` 保留薄封装 | 同上 |
| 8 | `src/工具_bash.light` | 更新 | `shell/tool-bash/src/background.ts`（tool-pwsh 同构） | 新增 `沙箱备注`（runnerFailed/denied+升级）、`进程结局`（killed/completed+细节）、`环块增量`（stdout 顺拼、stderr 合为 [stderr] 段、缺尾换行补 \n） | 同上 |
| 9 | `src/文件关联.light` | 新建 | `util/native-command/src/desktop-entry.ts` L31-48<br>`file-applications.ts` L130-177<br>`file-applications-linux.ts` L63-81<br>`file-applications-windows.ts`（List） | .desktop 主段键值解析、XDG 目录优先级、应用形状校验、点版数字序、Mac 同 bundle 折叠、区域/应用名回退、MIME 解析、gio 输出解析、Windows 默认标记+id 去重；剔除真实注册表/文件系统/进程调用 | `examples/test_R87_B4_命令_文件关联.light` |
| 10 | `src/远程mock.light` | 更新 | `test-support/remote-mock/src/streams.ts` L178（HandleUplink）<br>`test-support/session-snapshot/src/normalize.ts` L123-262 | HandleUplink 上行队列同步步进状态机（队列/半关/单消费者信箱）；`列cwd拼法`（cwd+别名去重、mac /private 别名、最长优先）；记录钟归零（createdAt/time0/dt 等）；`稳定id`（JSON-RPC id 首见序） | `examples/test_R87_B4_命令_上行快照.light` |

### 2.3 客户端族（3 项：6 新建 + 2 更新）

| # | 模块 | 状态 | 对齐上游文件:行号 | 复刻要点 | 回归用例 |
|---|---|---|---|---|---|
| 11 | `src/工作区.light` | 更新 | `workspace/workspace/src/spec.ts`（defaultWorkspaceId/pinnedSessionIds）<br>`types.ts`（SessionActivityKindMap/SessionActivityItem/SessionActivity） | 域状态归一/初始（pinned 缺省 []）；待决变更标记（operation 仅 create/delete）；钉选/归档互斥（钉会话移出归档、归档丢钉）；会话活动构造 | `examples/test_R87_B4_客户端_工作区与目录.light` |
| 12 | `src/toolcordis.light` | 更新 | `extensions/tool-cordis/src/config.ts`（liveConfig/listing/parseQuery/queryLiveConfig）<br>`providers.ts` L32（HOST_EVENTS 剥前缀）<br>`api-catalog.ts` L7745-7818（queryServiceApi/queryEventApi/referencedTypeClosure） | Config 条目五态归类（tree/inactive/absent/unsupported/schema）；查询校验+分页（offset≥0、limit 1..100）；HOST_EVENTS 丢 cordis/ 前缀；服务/事件目录投影+引用声明闭包（BFS 整词匹配） | 同上 |
| 13 | `src/客户端RPC.light` | 新建 | `client/connection/src/rpc.ts` + `rpc-host.ts` + `client/rpc.ts` | 传输错（gateway/internal）、成功/失败结果信封、client-request/server-response 信封、通道/端点段正则校验、`端点自路径`、`校验目标`、`解析服务端响应` | `examples/test_R87_B4_客户端_RPC协议.light` |
| 14 | `src/客户端认证.light` | 新建 | `client/connection/src/browser-auth.ts` | Cookie 头精确名取值、dsh-auth-+摘要 Cookie 名形状、v1.体.签 信封拆/造、过期窗口四向判定；HMAC-SHA256 签名以入参函数注入 | 同上 |
| 15 | `src/客户端模块不变式.light` | 新建 | `client/modules/src/invariant.ts` | boot 图逐行 row.id 必须能解析出客户端包路径，否则累积失败文案 | 同上 |
| 16 | `src/客户端语言设置.light` | 新建 | `client/locale/src/locale-settings.ts` | 命名空间 locale、preference 字段、BCP47 校验（首段 2..8 字母、子段 1..8 字母数字）、设置段归一 | `examples/test_R87_B4_客户端_杂项协议.light` |
| 17 | `src/客户端上传协议.light` | 新建 | `client/file-upload/src/protocol.ts` + `types.ts` | 上传路由 /api/session/uploadFileBinary 与相对形、编码上传请求 {data,name?}、回执 {receiptId,file} | 同上 |
| 18 | `src/客户端HMR事件.light` | 新建 | `client/hmr/src/events.ts` | /plugins/events 端点、graph\|rebuilt 帧三态判别（frame/unknown/invalid） | 同上 |

---

## 3. client 逐子目录 逻辑/宿主甄别

| 子目录 | 搬（纯逻辑） | 不搬（宿主耦合） |
|---|---|---|
| connection/src/rpc.ts | 信封形状、transportError、结果联合 | interface/type 声明（运行时擦除）、PeerScope/AbortSignal/Request/Response 绑定 |
| connection/src/rpc-host.ts | 通道正则、端点段正则、endpointFromPath、assertChannel/assertTarget | Cordis Service/effect、node:http bridge、Response/FormData/Blob 多段二进制 |
| connection/src/client/rpc.ts | parseConnectionResponse 信封校验、assertTarget | fetch 运输、randomUuid、multipart/form-data 二进制、signal.throwIfAborted |
| connection/src/http-bridge.ts | 仅常量 DEFAULT_MAX_REQUEST_BODY_BYTES（300 MiB）语义在册 | 全文 node:http/Readable/AbortController/背压 drain/413 桥接——硬抄 HTTP 红线 |
| connection/src/operator-peer.ts | 仅「peer 自为 scope 键」语义在册 | createScope/ctx/dispose 全 Cordis 宿主接线 |
| connection/src/browser-auth.ts | Cookie 头解析、信封形状、过期窗口 | node:crypto sha256/hmac/timingSafeEqual/randomBytes/base64url、URL、Response 303/401 |
| connection/src/index.ts | 无纯逻辑运行面 | Cordis plugin apply/webServer 接线、config schema 组装 |
| file-upload/src/protocol.ts | 路由常量 | — |
| file-upload/src/types.ts | 请求/回执字段形状 | FileAttachmentRef/FileUploadFetch 宿主 fetch 类型 |
| hmr/src/events.ts | parsePluginsEventFrame 三态判别、端点常量 | WebBootGraph 完整解析、EventSource 订阅 |
| locale/src/locale-settings.ts | 命名空间/BCP47 校验/设置段归一 | schemastery schema、navigator 兜底 |
| modules/src/invariant.ts | 逐行 clientPath(row.id) 可解析自洽 | Cordis internal/plugin 事件、invariants.register 接线 |
| 其余 client/*（store/resources/ui-*/*.tsx/*.css） | — | UI 渲染层、状态管理、资源文件，全部登记不搬 |

---

## 4. 关键语义对齐说明

1. **流式 JSON 定位修正**：任务书描述为「流式 JSON 读取状态机」，实读上游确认 json-stream.ts 是 `--json` 投影的**有界序列化**侧（深度跟踪=MAX_DEPTH=64 递归切尾，字符串截断=truncateUtf8 丢劈开尾字节），无逐字符增量解析器，故未编造状态机。
2. **钩子协议零变化**：runner.ts 增量仅 `bash.run→execute().result()` 宿主执行器调用面 + ShellExecutor 类型收窄，纯逻辑面零变化，文件未改一字。
3. **预设新旧 wire 形并存**：新 registry 形（去 trust/authorable、删 read-only、加 broken/modeSelectionEnabled）以新函数并列移植，旧形保留锁定既有绿测试，列为后续清型卡退役项。
4. **文件关联平台解析**：Windows 部分解析注册表路径字符串、Linux 部分解析 .desktop 文件格式，均为纯字符串解析，不实际读注册表或文件系统。
5. **HandleUplink 同步化**：上游 AsyncIterator/Promise/AbortController 异步上行队列改为同步步进状态机（队列/半关/单消费者信箱），由调用方驱动。
6. **client 密码学注入**：browser-auth 的 HMAC-SHA256 签名/验签、sha256 摘要、base64url 编解码以入参函数注入，未在光明侧实现密码学原语。
7. **toolcordis 引用闭包**：referencedTypeClosure 的 `\bname\b` 用「两侧非字字符」近似实现（光明无正则）。

---

## 5. 拒绝/暂缓/登记项

| 上游项 | 处置 | 理由 |
|---|---|---|
| packages/web/web-search-deepseek | 登记不搬 | 真实 API 宿主调用 |
| packages/settings-file、agent-presets、loader-smoke | 登记不搬 | 宿主持久化/预设装载/冒烟，非纯逻辑 |
| packages/llm-mock-server、llm-replay | 登记不搬 | mock/replay 宿主服务 |
| packages/client-runtime assembly | 登记不搬 | 运行时组装宿主 |
| client 全部 .tsx/.css/UI 渲染、store、resources、ui-* | 登记不搬 | UI 层，纯渲染 |
| extensions/cordis-host-runner / cordis-client-runner guard/sandbox | 登记不搬 | 宿主沙箱/守卫，直接操作宿主执行边界 |
| extensions/tool-cordis/src/api-catalog.ts 原始数据（7818 行） | 登记不搬 | 生成的第三方 API 数据注册表，属宿主侧数据；投影逻辑已搬 |
| extensions/tool-cordis/src/host.ts | 登记不搬 | 新增宿主装配文件（Cordis Service 注册） |
| util/package-manifest/src/index.ts | 登记不搬 | fs 宿主（readdir/package.json 探测） |
| shell/tool-bash/src/index.ts / tool-pwsh/src/index.ts | 登记不搬 | 工具注册与命令执行宿主面（外部命令子进程、超时、AbortSignal） |
| connection/http-bridge 字节桥、operator-peer scope | 登记不搬 | node:http/Cordis 宿主接线（见 §3） |
| preset/invariant.ts install/apply | 拒绝 | 全是 ctx.on/fail 宿主 Cordis 事件 |
| preset/preset.ts AgentPreset/Config | 暂缓 | 纯类型，无运行逻辑 |
| bundle/headless projectJsonRun/JsonSink/JsonProjection | 拒绝 | 依赖 ctx.on/agent.session/process.cwd/sink.write，宿主接线 |

---

## 6. 回归结果

### 6.1 新增用例（全部 rc=0）

| 用例 | 覆盖 |
|---|---|
| `test_R87_B4_配置_流式JSON.light` | truncateUtf8、boundValue 深度封顶、boundJsonLine 三级降级、parseArguments、addUsage |
| `test_R87_B4_配置_预设登记.light` | 是内置预设、定义组合、挂载行带前缀、是登记行/表、登记错误码表 |
| `test_R87_B4_配置_设置schema.light` | walk union/transform、脱敏去重、plainConfig/plainSchema、volatileForm、isExpression、projectForm |
| `test_R87_B4_命令_外壳渲染.light` | 归一到期策略、stopped 标记、渲染已提升、渲染作业读取、进程结局、环块增量 |
| `test_R87_B4_命令_文件关联.light` | desktop-entry 解析、XDG 目录、应用校验、点版序、Mac 折叠、区域/应用名、gio 解析、Windows 默认标记 |
| `test_R87_B4_命令_上行快照.light` | HandleUplink 四态、cwd 拼法、记录钟归零、稳定 id 序号 |
| `test_R87_B4_客户端_工作区与目录.light` | 工作区域状态、钉选/归档互斥、toolcordis 配置分页/目录投影 |
| `test_R87_B4_客户端_RPC协议.light` | 客户端RPC 信封/校验、客户端认证 Cookie/信封/过期、模块不变式 |
| `test_R87_B4_客户端_杂项协议.light` | 客户端语言设置 BCP47、上传协议、HMR 事件帧 |

### 6.2 全量回归（合流后）

```
lightharness> python -m pytest tests/test_回归.py
================= 517 passed, 1 skipped in 180.28s (0:03:00) =================
```

- **新增红 0**。各组单独运行时出现的临时红（_probe_r87 探针、编排工作区依赖顺序抖动、子智能体1.5 v1 变更、会话存储 xdist flaky）在合流后全部消除。
- 1 skipped = `test_env_red_baseline_report`（环境基线报告，非 B4 范围）。

---

## 7. 文件清单

### 新建模块（lightharness/src/）
1. `流式JSON.light`
2. `文件关联.light`
3. `客户端RPC.light`
4. `客户端认证.light`
5. `客户端语言设置.light`
6. `客户端上传协议.light`
7. `客户端HMR事件.light`
8. `客户端模块不变式.light`

### 更新模块（lightharness/src/）
1. `预设.light`（条目列表问题嵌套分支 + 是内置预设）
2. `预设深化.light`（定义组合/挂载行带前缀/是登记行/是登记表/登记错误码表）
3. `设置.light`（walk union/transform + 脱敏去重 + schema 表单族）
4. `外壳环境.light`（ShellExpiryPolicy 词汇 + 归一到期策略）
5. `bash渲染.light`（stopped 标记 + 渲染已提升 + 渲染作业读取）
6. `工具_bash.light`（后台纯逻辑：沙箱备注/进程结局/环块增量）
7. `远程mock.light`（HandleUplink 上行队列 + cwd 拼法 + 记录钟归零 + 稳定id）
8. `工作区.light`（域状态归一/待决变更/钉选归档互斥/会话活动）
9. `toolcordis.light`（Config 归类/分页/目录投影/引用闭包）

### 零变化模块
- `钩子协议.light`（runner.ts 增量仅宿主接线）

### 回归用例（lightharness/examples/）
9 个新增用例（见 §6.1）

### 分组报告（过程产物）
- `_taskB4_G1_配置族_报告.md`
- `_taskB4_G2_命令族_报告.md`
- `_taskB4_G3_客户端族_报告.md`

---

## 8. 红线自检

- ⛔ 未 commit / push；未 `git add` 任何文件。
- ⛔ 未写宿主接线文件（host/subprocess/terminal/sandbox/fs）。
- ⛔ 未硬抄 HTTP（http-bridge 字节桥整段登记不搬）。
- ⛔ 未扩 .light 语法。
- ✅ 产物全部在 `G:\dswork\duan-light-merge` 下。
- ✅ 新模块头注释均标注上游文件:行号。
- ✅ 每个移植项配最小回归用例，可独立复现语义。
- ✅ client 包严格区分逻辑/宿主，339 文件中只搬指定 5 个纯逻辑子目录。
