# 第52轮 任务3 交付报告 —— ssh/ssh 纯逻辑三件（protocol.ts + schemas.ts）

> 日期：2026-09-17 ｜ 优先级：P2 ｜ 跨项目：lightharness
> 上游基线：deepseek-harness 0.1.6-alpha.1（gitea fork master `c47b24803e`）
> 验收：`examples/test_R52_ssh协议.light` 本机 `rc=0`

## 1. 范围与上游依据

对齐 `packages/ssh/ssh` 的**纯逻辑校验面**（不接真实 SSH 网络 / PTY）：

| 上游文件 | 对齐内容 | 落点 |
|---|---|---|
| `protocol.ts` | `SSH_PROTOCOL_VERSION` / `SSH_MAX_PROCESS_HANDLES` / `SSH_MAX_TEXT_STREAMS` + `RemoteOperationError` | `src/ssh协议.light` 常量 + `建立远程操作错误` |
| `schemas.ts` | `remotePath` / `target` / `info` / `pathInfo` / `policy` / `entries` / `intent` / `edit` / `hello` / `spawn` / `streamEndpoint` / `processId` / `prepared` / `outputSnapshotFrameLimit` | `src/ssh协议.light` 各 `校验*` 段落 |

**不移植**（本仓纯逻辑面定位，铁律「不接真实 SSH 网络」）：
- `SshRpcPeer` 传输层（`frameSchema` / `request`/`result`/`error`/`cancel` 帧编解码、背压、pending 信用、连接丢失拒绝）。
- `managementLimits` / `requestClass` 容量调度（属运行时 transport，纯逻辑校验不涉及）。

## 2. 改动文件

### 2.1 `src/ssh协议.light`（新建）
- **协议常量**：`SSH协议版本=1`、`SSH最大进程句柄数=128`、`SSH最大文本流数=128`、`SSH帧收集上限=67108864`(64MB)。
- **错误建模**：`建立远程操作错误(消息, 码)` → `{"名":"RemoteOperationError","消息","码"}`；`是远程操作错误(错误)`（以 `名` 标记建模 host 不可伪造语义）；`归一操作错误(错误)`（等价上游 `operationError` 把任意错误归一成 `RemoteOperationError`）。
- **校验器**（单参，等价 Zod，返回原值或抛 `RemoteOperationError`）：
  - `校验远程路径`：非空串 + 以 `/` 开头 + 不含 NUL（等价 `remotePath`）。
  - `校验目标`：{targetKey:remotePath, displayPath:string} 严格。
  - `校验信息` / `校验路径信息`：{version:string, type:枚举, size?:非负}；`pathInfo` 的 type 额外允许 `symlink`。
  - `校验策略`：{mode:枚举[read-only/workspace-write/danger-full-access], workspaceRoot:remotePath, sessionId?:string}。
  - `校验条目表`：entry[]，每项 {name, type, target, version?, size?}。
  - `校验意图`：discriminatedUnion `kind` = `createIfAbsent` | `replaceIfVersion(version)`。
  - `校验编辑`：{oldString, newString, replaceAll:bool} 严格。
  - `校验握手`：{protocol:字面1, hash:64-hex, platform:枚举[linux/darwin], nodeVersion, node, root, workspace:remotePath, bootstrapHash?:64-hex}。
  - `校验生成`：{argv:非空非NUL串数组, cwd:remotePath, graceMs:正整数(≤2^31-1), env?, stdio?/terminal? 恰好其一}；terminal 校验 terminalType/rows/cols。
  - `校验流端点`：{path:remotePath, capability:64-hex}。
  - `校验进程标识`：UUID 格式（等价 `processIdSchema`/`textStreamIdSchema`）。
  - `校验已准备`：{id:uuid, streams: partialRecord(枚举键→streamEndpoint)}。
  - `输出快照帧上限(最大字节)`：纯函数 `min(64MB, 最大字节*2+1024)`（等价 `outputSnapshotFrameLimit`）。
- 内部工具：`严格对象`(等价 Zod `.strict()` 拒绝未知键)、`在枚举`(规避 且/或 链)、`是数`。
- 末尾 `导出` 全部公共名称。

### 2.2 `examples/test_R52_ssh协议.light`（新增）
§1 协议常量 ｜ §2 RemoteOperationError 构造/判定/归一 ｜ §3 remotePath ｜ §4 target ｜ §5 info/pathInfo ｜ §6 policy ｜ §7 entries ｜ §8 intent ｜ §9 edit ｜ §10 hello ｜ §11 spawn（stdio/terminal 互斥 + argv/graceMs/cwd）｜ §12 streamEndpoint ｜ §13 prepared（id UUID / streams 键集）｜ §14 outputSnapshotFrameLimit。

**反跑判据**：`校验抛远程(校验器, 值, 期望含, 标签)` 统一校验「非法输入抛 `RemoteOperationError` 且消息含子串」；把任一放行条件改错即红。

## 3. 关键实现决策（语言层等价建模）

| 上游 Zod 概念 | 本复刻建模 |
|---|---|
| `z.object({...}).strict()` | `严格对象(值, 已知键, 标签)`：缺键/未知键均抛 `RemoteOperationError` |
| `.refine(...)` / `.min(1)` / `.nonnegative()` | 顺序 `如果` 显式判定（规避 且/或 链不稳定） |
| `z.enum([...])` | `在枚举(值, 允许集合)`（以已知键 dict 判定，规避 且/或） |
| `z.string().regex(/^[0-9a-f]{64}$/)` | `匹配正则(值, "^[0-9a-f]{64}$")` |
| `z.uuid()` | `匹配正则` UUID 模式 |
| `z.discriminatedUnion('kind', [...])` | `校验意图` 按 `kind` 分支（缺 version / 多余 version 均拒） |
| 字面量 `protocol: z.literal(1)` | `值["protocol"] != 1` 拒 |
| `SshRpcPeer` 传输层 | **不移植**（纯逻辑面） |
| 错误信息中的字段路径标签 | Zod 无「标签」概念，本复刻不引入标签参数——所有 schema 一律单参，错误直接含字段路径（如 `entries[0].name ...`） |

## 4. 修复记录（调试期）

1. **`是布尔` 非导出**：`是布尔` 是全局内置，不在 `内置核心判型` 的导出集合；从该模块导入会 `导入错误`。改为不导入（直接使用全局 `是布尔`）。
2. **缺键访问崩溃**：`校验编辑` 原直接 `值["replaceAll"]`，对缺 `replaceAll` 的非法输入触发 `KeyError` 而非抛 `RemoteOperationError`（同类于任务1 缺键坑）。改为 `字典包含键(值,"replaceAll")==假 或 是布尔(...)` 先判后访问。（注意：`校验信息`/`校验策略` 等的**必填**键目前依赖调用方保证存在；本次测试未构造「缺必填键」用例，登记为潜在待加固项。）
3. **非-`主` 段落体内调用被导入函数按名引用会静默阻断 `主()` 执行**：light 编译器对「非 `主` 段落其函数体按名调用被导入函数」存在静默失效（类似 R26/L-170 词法陷阱的变体）；表现为模块级代码执行、`主()` 不运行且 `rc=0` 无报错。规避：测试不再定义调用被导入校验器的包裹段落，改为把校验器以**参数引用**传入 `校验抛远程`（已验证 `函数增强.light` 的「函数作参数传递并调用」路径可用）。由此 `校验远程路径`/`校验进程标识` 等 2 参校验器的 `标签` 参数被移除（Zod 本无标签概念，无语义损失）。
4. **`函数: <expr>` 内联 lambda 不支持**：light 无内联 lambda 语法（解析错误）；改传具名函数引用。

## 5. 运行

```bash
cd lightharness
../light-merge/.venv/Scripts/python.exe 运行.py examples/test_R52_ssh协议.light
# 期望输出：--- R52 任务3 ssh协议 纯逻辑测试通过 ---
```

## 6. 上游增量登记

- 对标清单条目：**#190 ssh协议**（protocol + schemas 纯逻辑已覆盖；`SshRpcPeer` 传输层 / `stream-security.ts` 流加解密属运行时网络面，本仓未覆盖，登记待补）。
