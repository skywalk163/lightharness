# 第12轮·任务1｜会话查询域：冷读 + 查询工具 —— 交付报告

- 分支：任务1（会话查询域），工作区 `G:\dswork\duan-light-merge\lightharness`
- 对照基准：上游 `G:\github\deepseek-harness` @ `a305303422`（0.1.5-rc.2，只读参考）
- 涉及文件：**新建** `src/会话冷读.light`（105 行）+ `src/查询工具.light`（541 行）+ `examples/test_会话冷读.light`（127 行）+ `examples/test_查询工具.light`（202 行）+ `_antirun_coldread.py`（62 行）
- 任务书：`复刻_第12轮_任务prompt分发.md` §任务1（会话查询域：cold-read 冷读 + tool-session-query 纯逻辑面）
- 只读遵守：`src/会话查询.light` / `src/会话查询过滤.light` / `src/会话存储.light` / `docs/功能对标/` / `scripts/` / `运行.py` / `stdlib/` 全部只读，零改动

## 1. 上游对应表

| 上游源文件（a305303422） | 上游语义 | 本路实现位置 |
|---|---|---|
| `packages/session-query/session-query/src/cold-read.ts`（54 行） | `readColdSessionLog`：打开只读句柄 → read(0, undefined) 读全量 → 关闭句柄 → 事件表追加 `interruptedTurnClosers(events)` 合成平衡转写（不写回存储）→ 返回 `ColdSessionLog { eventState, header, inheritedEventCount, events }`；读失败尽力关闭句柄、错误原样上抛（关闭失败不掩盖读错误） | `src/会话冷读.light`（冷读会话日志 / 打开只读句柄 / 句柄读取 / 关闭句柄 / 拆分行；`冷读事件状态 = "detached"`） |
| `packages/session-query/tool-session-query/src/input.ts` | 会话搜索参数 / 事件搜索参数 / 目标会话参数 schema；规范化查询（非空、无 NUL）；会话 id 区间、created-at 时间戳区间、seq 区间、event_types、surfaces 过滤构造 | `src/查询工具.light`（会话搜索参数 / 事件搜索参数 / 目标会话参数 / 规范化查询 / 序号区间 / 非负安全整数 / 非空数组断言 / 解析ISO时间戳 / 比较时间戳 / 时间下界 / 时间上界 / 时间戳区间 / 构造会话过滤器 / 物化父会话标识 / 构造事件过滤器） |
| `packages/session-query/tool-session-query/src/presentation.ts` | 搜索结果呈现：格式化会话/事件搜索文本、调用卡片（标题视图由宿主注入） | `src/查询工具.light`（标题文本 / 格式化时间 / 可用性文本 / 序号表文本 / 格式化空会话搜索 / 格式化会话搜索 / 格式化事件搜索 / 格式化事件追踪 / 呈现会话搜索调用 / 呈现事件搜索调用 / 呈现会话追踪调用 / 呈现事件目标调用） |
| （跳过）`service-boundary.ts` / `workspace-access.ts` | 宿主胶水：工作区访问、工具边界 | 未移植（见 §6 未移植项） |

## 2. 实现要点

### 2.1 冷读（对齐 cold-read.ts，54 行 readColdSessionLog）

- **存储口径**：`会话存储.light` 是消息级 webui 面，不承载事件日志；冷读改走**持久化只读面**（`持久化.日志路径` + `文件系统.读取文件`），按上游"打开只读句柄 → 读全量 → 关闭句柄"语义实现为：路径解析 → 读全量 → 拆行 → 解码。本口径差异在报告 §5 注明。
- **解码链路**：复用以 `会话格式.解码V2头` / `解码V2事件` / `中断轮闭合器`。关键教训：初始用 解码V3事件(行, 上一序号) 遇 user/message 载荷校验报错（lightharness 宽松写入、V3 事件载荷校验要求 `消息` 键），**改用 解码V2事件(行, 上一序号) 后通过**。
- **中断轮闭合器合成**：事件表追加 `中断轮闭合器(事件表)` 合成平衡转写（写崩中断轮折叠为 tool/result `TOOL_OUTCOME_UNKNOWN` + turn/end `{interrupted}`），**不写回存储**。
- **返回值**：`{事件状态="detached", 头, 继承事件数, 事件表}`；读失败错误原样上抛、关闭失败不掩盖读错误；全程只读（测试以读前后字节对比验证不写回）。

### 2.2 查询工具（对齐 input.ts / presentation.ts 纯逻辑面）

- **工具参数 schema**：会话搜索参数 / 事件搜索参数 / 目标会话参数，剔除宿主胶水字段（service-boundary / workspace-access）。
- **参数规范化**：`规范化查询`（非空、无 NUL）；`序号区间`（非负安全整数 ≤ 2^53-1、from ≤ to）；`非空数组断言`。
- **时间戳精确解析**：ISO 8601 精确解析 `{毫秒, 余数}`——余数去尾零，毫秒位 `padEnd` 右填充对齐上游 `.padEnd(3)`；支持 `+08:00` 偏移与 `.12345Z` 亚毫秒余数（实测余数 "45"）。
- **时间戳区间含入界但排除纯毫秒整点**：余数非空时 下界 = `math.nextafter(毫秒, +∞)`、上界 = `nextafter(毫秒+1, -∞)`（亚毫秒边界用浮点位推进实现，对齐上游 open 区间语义）。
- **过滤构造**：会话过滤器 / 事件过滤器（kind: id / created-at / availability / seq / time / type / surface）；`物化父会话标识` 去重（排序 + 去重）。
- **呈现**：格式化会话/事件搜索文本与调用卡片（标题视图由宿主注入）；`格式化时间` 用 datetime.fromtimestamp(t/1000, UTC) + strftime + 截取 "%f" 前 3 位对齐 `new Date().toISOString()`；`可用性文本`（live/persisted/detached）、`序号表文本`；空搜索结果走 `格式化空会话搜索` 分支。
- **历日天数**：用 Howard Hinnant `days_from_civil` 实现（对齐上游日期计算语义）。

## 3. 测试与验证

### 3.1 定向测试（新增，全绿）

`examples/test_会话冷读.light` → 输出 `会话冷读测试通过`，RC=0，覆盖：

| 组 | 覆盖 |
|---|---|
| 平衡日志读取 | 完整轮次日志读回，事件数/头/继承事件数正确 |
| 未闭合轮合成 | 中断轮闭合器合成 tool/result `TOOL_OUTCOME_UNKNOWN` + turn/end `{interrupted}`（对齐 repair 语义） |
| 序时复用 | 既有 会话查询1.5 的序时复用语义不受影响 |
| 只读不写回 | 读前后文件字节对比一致 |
| 错误传播 | 缺文件 / 坏 JSON 行 / 非 session 首行 抛错原样上抛 |

`examples/test_查询工具.light` → 输出 `查询工具测试通过`，RC=0，覆盖：

| 组 | 覆盖 |
|---|---|
| 过滤构造 | 会话 id 区间 / 时间戳区间（含亚毫秒 nextafter 边界）/ seq 区间 / 事件类型 / 表面 |
| 参数规范化 | 各类抛错（空查询、含 NUL、负数/超界序号、from>to） |
| ISO 精确解析 | `+08:00` 偏移、`.12345Z` 余数 "45"、毫秒 padEnd 对齐 |
| 呈现 | cap 截断、`[outside workspace]` 分支、标题不可用分支 |

### 3.2 反跑判据（机器验证）

`python _antirun_coldread.py` → **2/2 PASS（改反即红 rc=1，恢复即绿 rc=0），输出 ALL OK**：

1. **A｜冷读合成**：源串 `设 合成表 为 中断轮闭合器(事件表)` 改反（去掉中断轮闭合器合成）→ 断言红；恢复 → 绿
2. **B｜查询工具时间下界**：源串 `返回 math.nextafter(时间戳["毫秒"], float("inf"))` 改反（去掉 nextafter）→ 断言红；恢复 → 绿

脚本自含字节级备份/恢复 src，恢复后源文件与备份逐字节一致。

### 3.3 既有回归（任务书指定，全绿）

- `examples/test_会话查询1.5.light`（PASS）
- `examples/test_会话查询过滤.light`（通过）
- `examples/test_修复_repair接入.light`（通过）

### 3.4 CI 说明

按铁律 6 只跑本路新增测试 + 直接相关既有回归（上列 5 项），未跑全量 CI（由路M 统一执行）。

## 4. 光明语言适配（本任务实测记录）

- **解码事件改用 V2**：解码V3事件(行, 上一序号) 对 user/message 载荷校验报错（要求 `消息` 键，lightharness 是宽松写入）→ 改用 解码V2事件 通过。属接口适配，非语言缺陷。
- **「空」保留字不能作变量名前缀**：`空事件文本` 触发解析问题 → 改名 `无事件文本`。该坑已由 L-030 覆盖（「空」子串边界拆碎，已修复），本次按既有约定规避。
- **空参数传 {} 而非 []**：呈现会话追踪调用([]) 的空参数应传 `{}` 空字典（list 无 `.获取`）。
- **序列化JSON 需显式导入**：`序列化JSON` 需 `从 JSON 导入` 而非读取全局（L-008 已登记）。
- **语言能力实测通过**：`导入 math` + `math.nextafter(x, float("inf"/"-inf"))`（浮点位推进）；`datetime.fromtimestamp(t/1000, timezone.utc)` + strftime + 截取 "%f" 前 3 位对齐 toISOString；`re.sub("\\s+"," ",s).strip()` 空白折叠；`副本()` 真身（L-082 已修）；闭包嵌套（L-078 已实现）；整除 `//` 已支持（L-080 修复链）。
- **工程提示**：直接 `python _tmp_qt.py` 跑生成代码会因导入钩子循环 import 失败，用 `python 运行.py` 可靠；超 15s 的命令自动转后台任务，用 TaskOutput(task_id) 读取。

## 5. 未移植项（明确保留）

- **存储口径差异**：冷读不经过 `会话存储.light`（消息级 webui 面、不承载事件日志），改走持久化只读面（日志路径 + 文件系统.读取文件）；语义与 readColdSessionLog 对齐（只读句柄→读全量→中断轮闭合器合成→返回 {事件状态, 头, 继承事件数, 事件表}），仅存储访问通道不同。
- **service-boundary.ts / workspace-access.ts（宿主胶水）**：工作区访问、工具边界校验不移植，查询工具保持纯逻辑面；呈现中的 `[outside workspace]` 分支作为宿主注入的标题不可用兜底保留。
- **工具注册**：查询工具**不注册进 src/工具.light 注册表**（任务书明确，避免与第11轮在飞任务冲突）；**注册接入点**：建议由路M 在 `src/工具.light` 注册表中为 `查询工具.light` 的 `呈现*` 系列 + 过滤构造函数登记工具条目（含 schema 导出），统一决策后接入。

## 6. 移交清单

- `src/会话冷读.light`（新建，105 行）——任务1 冷读核心（导出 冷读会话日志 / 打开只读句柄 / 句柄读取 / 关闭句柄 / 拆分行 / 冷读事件状态）
- `src/查询工具.light`（新建，541 行）——任务1 查询工具纯逻辑面（导出 工具参数 schema / 规范化 / 过滤构造 / 呈现 全族）
- `examples/test_会话冷读.light`（新建，127 行）——≥8 断言，`会话冷读测试通过`
- `examples/test_查询工具.light`（新建，202 行）——≥8 断言，`查询工具测试通过`
- `_antirun_coldread.py`（新建，62 行）——反跑判据 2/2 PASS（ALL OK）
- 临时文件清理：根下 `_tmp_*` 系列（verify_prim×3 / smoke / debug×6 / bisect×3 / qt / run_gen / cap×2 / clean / out）与测试数据目录 `tmp_coldread/` 已全部删除；`_antirun_coldread.py` 保留（交付物）；既有遗留 tmp_persist/tmp_repair_e2e/tmp_balanced 未动

## 7. 语言缺陷账判定

**无新缺陷，未新增 L-0xx 登记**。本任务用到的语言特性（`副本()` 真身、闭包嵌套、`math.nextafter`、datetime/re 标准库、整除 `//`）均已可用或已在账修复（L-030「空」保留字子串 / L-078 闭包 / L-082 副本真身 / L-080 整除）；「空」变量名前缀按 L-030 既有约定规避。docs/功能对标/ 保持只读，未改动。
