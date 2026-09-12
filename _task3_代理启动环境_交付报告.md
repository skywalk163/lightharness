# _task3_代理启动环境_交付报告

> 第12轮 · 任务3（代理与启动环境域）｜http-proxy policy + launch-environment
> 日期：2026-09-12 ｜ 仓库：`G:\dswork\duan-light-merge\lightharness` ｜ 编译器：`light-merge`（LIGHT_MERGE）
> 上游（只读）：`G:\github\deepseek-harness` @ `a305303422`（0.1.5-rc.2）

---

## 1. 上游依据（文件:函数）

| 上游 | 函数 / 常量 | 光明侧投影 |
|---|---|---|
| `packages/util/http-proxy/src/policy.ts` | `EnvLookup`（字典或带 `获取` 方法对象，含 `{value,...}` 条目形态） | `读环境`（小写优先、大写回退、空白判空、对象条目取 value） |
| 同上 | `LOOPBACK_NO_PROXY` | `环回豁免表` = `["localhost","127.0.0.1","::1","[::1]"]` |
| 同上 | `POLICY_ENV_NAMES` / `PROXY_ENV_NAMES` | `代理环境名表`（8 个，含 ALL_PROXY 回退，本包解析不写回） |
| 同上 | `DIRECT_POLICY` | `直连策略` = `{"无代理":"","来源":"none"}` |
| 同上 | `isSupportedProxyUrl` | `判定支持代理URL` |
| 同上 | `acceptProxyUrl` | `接受代理URL`（SOCKS / unsupported 逐字文案拒绝，诊断表收集） |
| 同上 | `resolveScheme` | `解析方案`（己方接受→用己方；被拒→直连；缺位→回退） |
| 同上 | `withLoopback` | `并入环回`（去重保序、`*` 短路） |
| 同上 | `splitHostPort` | `拆分主机端口`（方括号 IPv6、多冒号不拆） |
| 同上 | `isLoopbackHost` | `判定环回主机`（localhost/.localhost/::1/::/0.0.0.0/127.0.0.0/8 正则/::ffff: 映射） |
| 同上 | `bypassesProxy` | `判定豁免`（主机/子域/*.、:port、默认端口 443/80、* 全豁免） |
| 同上 | `resolveProxyPolicy` | `解析代理策略`（all_proxy 回退、https 回退 http——undici 语义） |
| 同上 | `proxyForUrl` | `选中代理`（协议选择 → 环回豁免 → NO_PROXY 豁免） |
| `packages/util/launch-environment/src/index.ts` | `createLaunchEnvironmentSnapshot` | `构造启动环境快照`（不可变：构造时复制并折叠键） |
| 同上 | 快照 `lookupKey` / 层级解析 | `查找键`（win32 大写折叠）/ `取` / `取从`（全来源序最可信优先） |
| 同上 | `launchedThroughSsh` | `判定SSH启动`（仅进程层、trim 后非空） |

**跳过**：`install.ts`（undici 宿主传输装配）、Cordis Context 宿主面（`launchEnvironmentOf` / `DSH_LAUNCH_ENVIRONMENT_KEY` / declare module）。

## 2. 实现要点

- **来源层**：`来源序 = ["process","project-env","user-env"]`（进程继承 > 调用目录 .env > 家目录 .env），`取从` 按允许表过滤后按来源序取第一命中；每值返回 `{值, 来源, 路径?}`（对齐上游 `EnvEntry`）。
- **不可变性**：构造时对每层值表做键折叠复制（win32 大写折叠），外部后续改动不透传进快照。
- **环回 IPv4 正则**：整段 `127.0.0.0/8`，八位组 `25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d`（127.999.1.1 不豁免，对齐上游 LOOPBACK_IPV4）。
- **IPv4-mapped IPv6**：`::ffff:7f00:1` 十六进制组形态走 `映射IPv6模式` + `十六进制转整数`（`码位` 取 ASCII 手写进制）；`::ffff:127.0.0.1` 点分形态走 `::ffff:` 剥离后套 127 正则。
- **网址表示**：光明无 URL 类，用 `HTTP解析URL`（urllib urlparse）→ `{协议带冒号, 主机, 端口}` 投影；`拆分网络位置` 剥 userinfo / 方括号 IPv6 / 单冒号端口。
- **豁免条目**：`拆豁免条目`（`/[,\s]+/` 投影）；条目匹配主机及其全部子域，前导 `.` / `*.` 同义，可带 `:port`，`*` 全豁免，CIDR 不支持（与上游一致）。
- **SSH 判定口径**：仅进程层可信（.env 不得伪造 SSH 会话），trim 后非空即建立。
- **SSH 判定修正**：本期将口径修正为「仅进程层、trim 后非空」（早期版本曾把 .env 层也纳入，测试 7 组断言据此对齐）。

## 3. 测试与 CI

| 测试 | 断言数 | 覆盖 |
|---|---|---|
| `examples/test_代理策略.light` | 66（要求 ≥10） | 环回豁免 / NO_PROXY 条目解析（主机、主机:端口、通配）/ proxyForUrl 选中与大小写 / 不支持代理 URL（SOCKS、ftp 逐字文案）/ 直连默认 / ALL_PROXY 回退 / https 回退 http / 读环境优先级 / 拆分主机端口（方括号、裸 IPv6）/ 十六进制映射环回 |
| `examples/test_启动环境.light` | 25（要求 ≥6） | 层级优先级（进程 > 项目 .env > 家目录 .env）/ 来源记录 / 不可变快照（外部改动不透传）/ win32 键折叠（PATH/path 互命中、POSIX 精确）/ SSH 判定仅进程层 |

运行：`python 运行.py examples/test_代理策略.light`、`python 运行.py examples/test_启动环境.light`（均输出通过标记）。

**相关既有回归**（铁律 6，任务书点名）：`test_主目录路径` ✅、`test_工作区` ✅（模块未直接 import 二者，家目录 .env 路径语义已与 `解析主目录` 核对并登记口径）。

## 4. 反跑判据（`_antirun_proxy_env.py`，字节级备份/恢复 src，3/3 通过）

| 项 | 改错内容 | 红 | 绿 |
|---|---|---|---|
| A 环回豁免去掉 | `判定环回主机` 中 `localhost` 判定改反 | rc=1 ✅ | rc=0 ✅ |
| B 层级优先级反转 | `来源序` 进程层排最后 | rc=1 ✅ | rc=0 ✅ |
| C proxyForUrl 选中改错 | `选中代理` https 分支误取 `http代理`（对仅 https 代理的策略必红） | rc=1 ✅ | rc=0 ✅ |

## 5. 未移植项 / 语言差异（登记）

1. **URL 类缺失**：上游用 URL 类解析；光明用 `HTTP解析URL`（urlparse）宽松解析 + 手写 `拆分网络位置` 还原 hostname/port。空协议 → 不在支持表 → invalid 诊断，语义对齐。
2. **`{1,4}` 花括号量词破坏**：光明字符串把 `{1,4}` 当重复语法，`"[0-9a-f]{1,4}"` 被编译破坏（SyntaxWarning: 'int' object is not callable）。绕法：等价无花括号量词 `[0-9a-f][0-9a-f]?[0-9a-f]?[0-9a-f]?`（本模块 `映射IPv6模式` 用此写法）。测试与模块中的正则一律不用花括号量词。
3. **字符串原语裸名**：`转小写/转大写/去除空白/截取/开头/结尾/查找子串/码位/字符串包含/列表包含` 全部用编译器内置映射裸名（自动 `_light_builtin.` 前缀），不 import `字符串工具轻量`/`字符串处理` 模块——被导入模块内部再 import 这些 .light 模块会在运行.py 内联路径下产生名称解析错乱（实测 'int' object is not callable）。正则表达式（完全匹配/分组匹配）与 HTTP（HTTP解析URL）保留模块导入。此组合下测试稳定通过。
4. **`是否在列表` 不可用** → 用 `列表包含`；`是字符串/是列表/是字典` 可用；`转整数(x)` 无基数参数 → 十六进制解析手写（`十六进制数位` + `十六进制转整数`）。
5. **platform 显式入参**：上游 `lookupKey` 读 `process.platform`；光明侧平台标识作显式入参（"win32" 折叠大写、其余精确），纯函数化可测。
6. **hostname 大小写**：豁免匹配前统一 `去括号去点小写`（上游 sameHostname 同理），端口默认 443/80 补齐。
7. **无代理字段缺省**：DIRECT_POLICY 的 `无代理` 为空串，`判定豁免` 遍历空串安全。

## 6. 移交清单

- 新增（任务3 文件互斥表范围内）：`src/代理策略.light`、`src/启动环境.light`、`examples/test_代理策略.light`、`examples/test_启动环境.light`、`_antirun_proxy_env.py`、`_task3_代理启动环境_交付报告.md`。
- **未触碰** `docs/功能对标/`（只读，路M 统一）：语言缺陷条目（`{1,4}` 量词、字符串原语内联怪癖、`当前目录` 内置名冲突）在报告中登记，未写入 语言缺陷账.md，需路M 收口时统一落账。
- 无越界改其他域 src；`src/主目录路径.light`、`src/工作区.light` 只读。
- 后续接入点：`启动环境快照` 可被 launcher 物化接受值给配置表达式/第三方库（上游 launcher 面，本轮未接）；`代理策略` 可被 HTTP 客户端模块消费（上游 install.ts 宿主面，跳过后由路M 统一决策）。
