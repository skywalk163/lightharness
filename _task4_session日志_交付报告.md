# 任务4 交付报告（第 13 轮 · session 日志域）

- 轮次：第 13 轮 任务4（session 日志域 / session-log-deepseek 纯逻辑面）
- 日期：2026-09-13
- 上游基线：`G:\github\deepseek-harness` @ `a305303422`（0.1.5-rc.2；HEAD `9d9035b7c1` 为 FreeBSD fork +2 平台提交）
- 交付状态：**完成**（测试 PASS + 反跑 3/3，见 §4/§5）

## 一、交付清单

| 文件 | 行数 | 说明 |
| --- | --- | --- |
| `lightharness/src/会话日志增量.light` | 265 | 上游 `session-log-deepseek` 线格式翻译 + 水印折叠（纯逻辑面） |
| `lightharness/examples/test_会话日志增量.light` | 223 | 68 条断言（≥12 达标） |
| `lightharness/_antirun_sesslog.py` | 99 | 字节级备份/变异/恢复反跑，3 判据 → `ALL OK` |
| `lightharness/examples/_repro_L093.light` | 58 | L-093 最小复现（绕法形态 rc=0，与任务3 共用） |

## 二、上游对应表（文件 / 行号 / 核心语义）

| 光明实现 | 上游位置（实际行号） | 核心语义 |
| --- | --- | --- |
| `线头` | `session-log-deepseek/src/index.ts:56-69`（`wireHeader`） | `version`/`id: String(id)`/`createdAt` + 条件展开 `cwd?`/`parentSession?:String(...)`/`isSeeded→seedLength=inheritedEventCount`/`origin?`/`delegationDepth?`/`agentPreset?` |
| `线事件` | `index.ts:72-104`（`wireEvent`） | 公共 `{seq,time,data}` + 可选 `ignorable`；类型分发：`system|user|tool` 加 `surfaceOp` + 可选 `sourceEventSeqs.map(Number)`；`assistant/message` 加 `surfaceOp`（**不带** sourceEventSeqs）；未知且 `ignorable===true` → 不透明保留 `{type,ignorable:true,surfaceOp?,sourceEventSeqs?}`；其余 `{...common,type}` |
| `线化操作` | `index.ts:106-110`（`wireSurfaceOp`） | `append` 原样；否则展开 `{op:'replace', startSeq:Number, endSeq:Number}` |
| `接受至` | `index.ts:117-150`（`acceptedThrough`） | 增量扫描（起点 = 上次扫描数）+ 严格校验 + 水印取最大通过序号，未接受前 `-1` |
| `构造增量` | `index.ts:160-178`（`prepare` 的 value） | `afterSeq=接受点`、`throughSeq=末事件序号`、`events=接受点+1 起`；事件表为空 → `undefined` |
| `确认接受` | `index.ts:181-188`（`accept`） | 构造 `delivery-accepted{sessionId, sessionFormatVersion, throughSeq}` 事件（追加动作归宿主/测试） |
| 输出键形状 | `types.ts:7-70`（WireHeader/WireSurfaceOp/WireEvent/Extension） | 线协议 ASCII 键与「可选键仅在存在时落键」语义 |
| `接受至` 抛错分支 | `invariant.ts:17-43`（`validateDeliveryAccepted`） | 非安全整数格式版本 / 水印越界 / 会话标识非非空字符串 → 畸形 |
| `已知事件类型集` | `core/session/src/known-event-types.ts:22-79` | `KNOWN_SESSION_EVENT_TYPES` **56 项**，逐项核对完全一致（顺序与内容） |

> 行数说明：任务书标注 `index.ts` 328 行，实测 **192 行**（`types.ts` 90 + `invariant.ts` 74 为另外两个文件）。

## 三、实现要点

1. **会话视图入参（纯函数化，不 import 会话/会话格式 模块）**：
   `{"头": 会话头, "事件表": 事件列表, "记忆表": 记忆表}`
   - 会话头中文键 + 英文别名（`取字段` 双形态）：`版本/标识/创建时间/工作目录/父会话/已播种/继承事件数/来源/委派深度/代理预设`；
     版本号兼容 **数字 / `{"主","次"}` / `[主,次]`** 三种承载（`取版本号`）。
   - 事件用 `会话.light` 规范形状 `{"类型","序号","时间","数据"}` + 可选 `"可忽略"/"表面操作"/"来源事件序号"`。
   - `记忆表` 对齐上游 `WeakMap<Session, AcceptanceFold>`（`{scannedEvents, throughSeq}`）：
     缺省 `扫描点=0`、`水印=-1`，由调用方持有以跨调用**增量扫描**；`接受至` 会把 `扫描点/水印` 写回该字典。
2. **线格式输出一律 ASCII 键**（`version/id/createdAt/cwd/parentSession/seedLength/origin/delegationDepth/agentPreset`；
   `seq/time/data/ignorable/type/surfaceOp/sourceEventSeqs`），与上游 JSON 线协议逐字对齐；
   `sourceEventSeqs` 做 `map(Number)` 归一（`转数字表`，测试用字符串 `"2","3"` 验证）。
3. **接受水印校验顺序与上游一致**（顺序不可换，测试 §4 逐条覆盖）：
   ① 格式版本非安全整数（含负数，含 `-0`：光明侧 `0.0` 不是整数 → 与上游 `Object.is(-0)` 同结果）→ **抛畸形**；
   ② 格式版本 ≠ 会话头版本 → **跳过**（不抛）；③ 通过序号非安全整数 或 ≥ 事件自身序号 → **抛畸形**；
   ④ 会话标识非「非空字符串」→ **抛畸形**；⑤ 会话标识 ≠ 会话头标识 → **跳过**；⑥ 取最大。
   「安全整数」用自实现 `是安全整数`（`是整数 && 0 ≤ 值 ≤ 9007199254740991`），因为光明的整数是任意精度。
4. **偏差登记（1 处）**：`invariant.ts:29-33` 允许「继承分叉」事件（`parentSession` 存在且 `!isOwnSeq`）保留父会话标识而**不**判为不符；
   本模块按 `index.ts` 的**运行时折叠**语义实现（标识不符一律跳过），未移植 invariant 的继承豁免 —— 已登记 §6 未移植项。
5. **命名避坑**：标识符不用「为」字（L-084）；循环变量用 `序号`/`项` 而非「事件」（L-004 同源拆分）；
   布尔链避免行内 `且`；字符串子串判定手写循环（不依赖 `.包含`）。

## 四、测试与反跑结果

- 运行命令：`cd G:\dswork\duan-light-merge\lightharness; $env:LIGHT_MERGE="G:\dswork\duan-light-merge\light-merge"; python 运行.py examples/test_会话日志增量.light`
- 输出：`test_会话日志增量 PASS`，**rc=0**（68 条断言）
- 覆盖：线头（最小头 6 项缺省不落键 + 全字段头 6 项落键 + `父会话` 字符串化 + `已播种=假` 不落 seedLength + 版本三种形态）、
  线化操作（append 原样 / 英文 replace 展开 / 中文别名等价）、
  线事件（三种带来源表面事件 + 来源序号数字归一 + 助手不带来源序号 + 已知非表面类型仅公共段 +
  未知可忽略的不透明保留（surfaceOp/sourceEventSeqs 原样不动）+ 未知不可忽略丢弃元数据 + 词汇 56 项）、
  水印折叠（`-1` 初始 / 多接受取最大且末个更小不回退 / 写回记忆表 / 扫描点推进 /
  版本不符跳过 / 会话不符跳过 / 头版本 0 与缺省格式版本相符 / 非安全整数与负数格式版本抛畸形 /
  越界水印抛畸形 / 空会话标识抛畸形 / 增量扫描推进）、
  构造增量（version/sessionFormatVersion/afterSeq/throughSeq/后缀起点/内嵌线头/空事件表返回空）、
  确认接受（事件形状 4 键 + 追加后水印推进）。
- 反跑：`python _antirun_sesslog.py` → **3/3 ALL OK**
  - A 水印不再取最大（`如果 通过序号 > 水印` → `如果 水印 < 0`，退化为取首个）→ 红（rc=1）
  - B 线头 `seedLength` 无条件落键（去掉 `已播种 == 真` 条件）→ 红（rc=1）
  - C 畸形接受事件不再抛错（格式版本畸形改 `抛出` 为 `跳过`）→ 红（rc=1）
  - 恢复后 sha256 字节级一致 + 回归绿（rc=0，PASS 已打印）
- 回归门禁抽样：`python -m pytest tests/ -q -k "u76ee or u4f1a or L092"` → **23 passed, 242 deselected**（含本用例）

## 五、未移植项（宿主面登记）

| 上游位置 | 内容 | 处置 |
| --- | --- | --- |
| `index.ts:33-46` | `name`/`inject`/`Config`（`enabled` 缺省 `false`，schemastery 校验） | 宿主：插件注册与配置面 |
| `index.ts:157-192` | `apply(ctx, config)`：`ctx.deepseekLlmApiExtensions.register('dsh_session_log', {prepare, accept})` | 宿主：请求扩展注册点 |
| `index.ts:160-166` | `prepare` 前置：`request.sessionId === undefined` / `ctx.sessions.get` 未命中 → 返回 `undefined`（TODO 注释同上游） | 宿主：会话查表 |
| `index.ts:181-189` | `accept` 的 `session.append(...)`（真实写日志）+ TODO「立即轻量检查点」 | 宿主：会话追加；本模块只产出事件（测试注入追加） |
| `index.ts:53,117-121,148` | `acceptanceFolds` = `WeakMap<Session, AcceptanceFold>` 的对象身份缓存 | 光明用入参 `记忆表` 字典替代（语义等价，作用域由调用方持有） |
| `invariant.ts:1-74` | 包内不变量伴随插件：`validateSession`/`ctx.on('session/created')`/`internal/dispatch` 接线 | 宿主：invariants 服务；校验判定面（前 4 条）已在 `接受至` 落地 |
| `invariant.ts:29-33` | 继承分叉豁免（`parentSession !== undefined && !session.isOwnSeq(seq)` 时允许标识不等） | 偏差登记（§三.4）：需宿主提供 `isOwnSeq`，未移植 |

## 六、语言差异（新缺陷 + 建议编号）

> 编号已避开并行路已占用的 **L-091**（任务6 webhook：`哈希.HMAC_SHA256` 实为 pbkdf2 单轮近似）
> 与 **L-092**（任务5/2：标识符含「返回」等关键字字样被切碎），取 **L-093**。

| 编号 | 严重度 | 现象 | 绕法 / 复现 |
| --- | --- | --- | --- |
| **L-093** | 中（调试期误导，非运行期错误） | **跨模块抛出的异常、调用点未被 `尝试` 包住时，顶层报错「位置块」错配**：位置块恒锚定到**函数体末尾附近**，与真实抛出语句无关（message 本身正确）。实测两种落地：① 真实抛点在第 2 条语句 → 位置块显示该函数末尾收尾行，caret 无真实行归属；② 本轮任务4 测试初稿：真实抛点是 §4 中段的普通语句（`接受至(造视图(头, 异会话, {}))`），报错位置却指向其后 4 条语句处的 4k 尝试体（行号 171-172）——据此误判 3 次才定位真因。同模块内抛出时位置正确（见复现文件注释中的对照探针）。属 **L-061**（message/行号错配，2026-09-03 已修）的残留场景 | 绕法：跨模块调用可能抛错时在**调用点**用 `尝试/捕获` 包住，按 message 断言/打印；排查真因用自写调试运行器打印 Python 原生 traceback。复现：`examples/_repro_L093.light`（绕法形态 rc=0，含被破坏原写法说明与两种落地形态实测） |
| **L-094** | 低（工具层：运行器/导入钩子，**非** light-merge 编译器） | **入口文件所在目录会遮蔽 `src/` 同名模块**，且遮蔽失败是**静默**的：若 `examples/<X>.light` 存在，而某用例执行 `从 <X> 导入 ...`（本意导入 `src/<X>.light`），导入会解析到 examples 下的同名文件（Python `sys.path[0]` = 脚本目录），导出为空 → 运行期报 `name '...' is not defined`，无任何导入错误提示。本轮任务3 开发期实测：创建 `examples/甲模块.light` 后，`examples/甲模块.light` 自身及其后所有 `从 甲模块 导入` 的用例全部静默失败（清理该文件后立即恢复） | 绕法：用例文件名**不得**与被导入模块同名（本模块交付用例名为 `test_目标轮驱动.light` / `test_会话日志增量.light`，与被导入模块 `目标轮驱动` / `会话日志增量` 不同名）。**无 repro 文件**：稳定复现必须常驻一个与 src 模块同名的 `examples/*.light`，而该文件本身就会让引用同一模块的其它用例（含本任务交付用例）全部门禁红，故只作登记不落文件（如需落文件建议由语言侧在导入钩子中给出「模块名被入口目录遮蔽」的显式错误） |

## 七、移交清单

1. 交付物 4 件（§一 表格）+ 本报告；建议 路M 提交形如
   `任务4(session日志域): session-log-deepseek纯逻辑面复刻(线格式翻译+水印折叠; 反跑3/3)`。
2. 对标回填建议：**#89 = session-log-deepseek**（`src/会话日志增量.light` + `examples/test_会话日志增量.light`）。
3. 缺陷账：**新增 L-093、L-094**（repro：`examples/_repro_L093.light`；L-094 无 repro，原因见 §六）。
4. 未移植项（§五 表格）建议在 #89 状态串登记「宿主面：请求扩展注册/prepare 会话查表/accept 真实追加/invariant 伴随插件未移植」。
5. 备注：`src/会话日志增量.light` 为**新增文件**，未改 `src/会话.light` / `src/会话格式.light`（互斥表要求）。
