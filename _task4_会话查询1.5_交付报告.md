# 第5轮·任务4｜会话查询新能力 1.5 —— 交付报告（#36）

- 分支：`task-5-query-4`（worktree `wt-Q4`，基 `4e06d53`＝第4轮收口点）
- 对照基准：上游 `a305303422`（0.1.5-rc.2），仓库 `G:\github\deepseek-harness`（只读参考）
- 涉及文件：**新建** `src/会话查询.light`（26 段 / 596 行）+ `examples/test_会话查询1.5.light`；既有 `会话查询过滤.light` 只做接口衔接（引入新模块），其既有段落零改动
- 任务书：`0.15遗留_第5轮_任务prompt分发.md` §任务4（会话查询新能力，缺口 #36）

## 1. 上游对应表

| 上游源文件（a305303422） | 上游语义 | 本路实现位置（`会话查询.light`） |
|---|---|---|
| `packages/session-query/session-query/src/extraction.ts`（89 行） | 逐事件类型文本抽取：user/message、assistant/message 走 contentText；tool/call 名称+参数；tool/result 内容+error；todo/write 状态+内容；turn/end 按 reason（error/aborted/max-tokens/interrupted/completed）；turn/start、step/*、assistant/attempt、request/header 及未知类型 → 空串；块文本：text 贡献、reasoning 不贡献、tool-call 名称+参数、tool-result 递归、未知块不贡献；多段 trim+滤空+换行连接 | `连接文本`、`块文本`、`内容文本`、`结束原因文本`、`抽取事件文本`、`块文本流` |
| `packages/session-query/session-query/src/documents.ts`（74 行） | buildSessionEventRecords（每条事件 sessionId/seq/type/time/surface 记录）、buildSessionEventSearchDocuments（文本非空才成文档）、classifySurface（折叠后 nodes→current、replacements 的 shadowedSeqs→shadowed） | `构建事件记录`、`构建事件搜索文档`、`分析事件日志`（含 surface 分类；折叠语义由 `折叠表面` 提供） |
| `packages/core/session/src/surface.ts`（foldSurface 语义） | 表面合格类型 = system/message、user/message、assistant/message、tool/result；replace 两种形态——字符串 `"replace"`（替换 surface 节点 0，即 lightharness V3 节点 0 语义）与字典 `{op:replace,startSeq,endSeq}`（区间替换）；序号连续校验；替换范围须在 surface 中 | `是表面合格`、`表面操作取`、`索引查找`、`折叠表面`（只做形状与序号连续校验，深层校验由宿主剔除） |
| `packages/session-query/session-query/src/tracing.ts`（253 行） | 事件日志分析（records/replacedBy/replacedEventSeqs/currentSeqs）、eventRecords、currentSurfaceEvents、traceEvent（目标记录+被替换为+替换链+来源/派生序号）、traceSession（祖先链+后代树+循环检测+缺父 partial+complete/root） | `分析事件日志`、`追踪事件`、`事件来源序号`、`追踪会话`（循环父抛错、缺父 partial、complete/root） |
| `packages/session-query/session-query/src/sources.ts`（25 行） | assertSessionHeadersCompatible——id/createdAt/cwd/parentSession/isSeeded/delegationDepth 六字段全等 | `校验头兼容`、`头取字段`、`头是否种子`、`复制头加标识` |
| `packages/session-query/session-query/src/corpus.ts`（315 行，纯逻辑面） | 逻辑会话（头+继承事件数+事件表）、listSessions（live 优先，同 id 校验头兼容）、load（live 优先→持久冷读）、projectMany | `解析逻辑会话`、`解析会话语料`、`合并会话记录`（持久化 seam / Cordis / 并发 worker 剔除，见 §5） |

## 2. 语义实现方式

### 2.1 抽取族（对齐 extraction.ts）
- **块文本**：text 块贡献 `文本` 字段；reasoning 块不贡献；tool-call 块贡献 名称+参数；tool-result 块递归抽取；未知块不贡献。多段 `去除首尾空白` + 滤空 + 换行连接。
- **抽取事件文本**：user/message、assistant/message 走 消息内容文本；assistant/message 将 **内容+流** 合并后抽取（对齐 `会话.投影内嵌消息` 语义）；tool/call 名称+输入；tool/result 消息内容+错误；todo/write 逐项 状态+内容；turn/end 按 原因 映射（error/aborted/max-tokens/interrupted → 对应英文原词，completed → `completed`）；request/header、turn/start、step/*、assistant/attempt、未知 → 空串。

### 2.2 表面折叠族（对齐 surface.ts foldSurface，只做形状判定）
- **是表面合格**：system/message、user/message、assistant/message、tool/result 四类；纯非表面事件（step/start、turn/end 等）不参与折叠，保持 `log-only` 表面。
- **表面操作取**：事件数据 `表面操作` 字段；字符串 `"append"` / `"replace"` 与字典 `{op:replace,startSeq,endSeq}` 两种形态。
- **折叠表面**：字符串 `"replace"` 取代表面节点表首元素（lightharness V3 节点 0 语义，产出 `{序号,开始,结束,遮蔽序号表}`，遮蔽序号=被替换节点 0 的序号）；字典形态按 startSeq/endSeq **闭区间**替换；序号连续校验、替换范围须在 surface 中。**不做深层校验**（工具改写/来源引用等宿主校验剔除，对齐上游「本模块只做形状判定」注释）。
- **分析事件日志**：每条事件产出 `{序号,类型,时间,表面}` 记录 + `替换表`；折叠后节点 → `current`，替换表遮蔽序号 → `shadowed`，其余（非表面事件）→ `log-only`。

### 2.3 追踪族（对齐 tracing.ts）
- **追踪事件**：按 序号 查目标记录 → 被替换为（替换表）→ 替换链（遮蔽序号反向链）→ 来源/派生序号。
- **追踪会话**：按 父会话 建立祖先链（子→根逐级），根 = 最祖先；后代树按 子按父 分组 + `会话比较`（创建时间降序）排序 + 游标式栈遍历（光明无 `栈.移除`，用顺序游标 BFS，后代嵌套结构与上游 DFS 一致）；**循环父抛错**、缺父 → `partial`、完整 → `complete`、目标缺失 → 抛错。

### 2.4 头族（对齐 sources.ts，适配 lightharness 头信息形状）
- lightharness 会话头信息 = `版本`/`创建时间`/`工作目录`/`父会话`/`种子长度`，**无 id 键**（id 在会话对象 `.标识` 属性）。
- `复制头加标识`：拷贝头字典并补 `标识` 键——语料/血缘/合并统一用头标识字段。
- `校验头兼容`：六字段全等——标识、创建时间、工作目录、父会话、头是否种子（种子长度非空投影）、委托深度（缺省 0，`头取字段` 带默认）。任一不等抛错。

### 2.5 语料族（对齐 corpus.ts 纯逻辑面）
- `解析逻辑会话`：头（补标识）+ 继承事件数 + 事件表（会话对象 `汇集全部事件` 投影）。
- `解析会话语料`：拷贝 + `排序会话记录`（创建时间降序，插入排序，不修改入参顺序）。
- `合并会话记录`：存活表（会话对象）+ 持久表（头字典）合并——同 id 先 `校验头兼容`（通过 → `live` 与 `persisted` 双标记；冲突抛错），缺省分别标记。

## 3. 测试与验证

### 3.1 定向测试（新增）
`examples/test_会话查询1.5.light` 全绿（输出 `test_会话查询1.5 PASS`），5 组判据：

| 组 | 覆盖 | 反跑点 |
|---|---|---|
| 1 抽取 | user/message、assistant/message 内嵌流合并（`天气晴朗\n适合出行`）、tool/call（`bash\necho hi`）、tool/result、todo/write 4 项；request/header、turn/start、assistant/attempt → 空串 | user 文本断言改空 → 红 |
| 2 表面三分类 | append 节点 0 + user + replace → seq0 `shadowed`、其余 `current`；step/start 与 turn/end → `log-only`；搜索文档只留 1 条语义事件 | shadowed 改 current → 红 |
| 3 血缘 | 孙→根完整谱系/祖先 2/根 r1；根→后代 c1→g1 嵌套树；循环父 `x→x` 抛错；缺失目标抛错 | — |
| 4 头兼容 | 同头通过；时间/父/种子差异各抛错 | 时间不等放行 → 红 |
| 5 语料 | 合并存活+持久 3 条按创建时间降序、live/persisted 标记；同 id 头兼容 → 双标记；冲突头抛错；料排序不修改入参 | — |

### 3.2 反跑判据（机器验证）
`python _antirun_sessionquery.py` → **3/3 全红**（改反即 rc=1，改回恢复）：
1. 抽取 user/message 文本断言改空 → 红
2. surface「replace 后旧事件 shadowed」改 current → 红
3. 头兼容时间不等放行（断言反转）→ 红

### 3.3 既有回归（任务书指定 5 项 + 相关模块，全绿）
`test_会话查询过滤`（会话查询过滤子系统通过）、`test_会话格式`、`test_会话V3迁移`、`test_会话`、`test_压缩`（PASS），另验 `test_压缩自动`、`test_压缩配套`、`test_消息`、`test_会话格式冒烟` 全绿——任务4 未触及上述模块既有行为。

### 3.4 全量 CI
本 worktree 跑 `python scripts/ci_test.py`：**208 passed / 2 failed**（基线 207/2）。新增通过 1（test_会话查询1.5）；2 failed 为既有 `test_agentE5钩子.light` / `test_压缩E5.light`（第5轮路M 统一口径基线，与本路无关）。核心模块冒烟 5/5 通过。

## 4. 光明语言适配（本任务实测记录）

- **字典键表不存在** → 用 `字典键列表` 遍历字典键。
- **列表无 `.移除`** → 追踪会话后代树改用 游标顺序遍历（BFS 等价，嵌套结构一致）。
- **列表下标写须 `设 记录表[i] 为 值`**（带 `设` 前缀，对齐 `事件.light` 注释）。
- **链式下标/属性写静默无效**（`存活[0].头信息["创建时间"] 为 2`、`存活[0].头信息 为 [...]` 均不生效）→ 先 `设 活1 为 新建会话(...)` 再 `活1.头信息 为 [...]` 整字典替换。
- 字符串工具需显式 `从 字符串工具 导入 去除首尾空白`；补丁脚本统一 utf-8-sig 读 + utf-8 写 + CRLF。

## 5. 未移植项（明确保留）

- **持久化 seam / Cordis 生命周期 / 并发 worker / 多工作区监听**（corpus.ts 宿主面）：lightharness 持久化由 `会话`/`会话查询过滤` 既有机制承担，`会话查询.light` 保持纯逻辑；宿主接入点在 `合并会话记录`/`解析逻辑会话` 入参投影，留给路M 或宿主侧。
- **foldSurface 深层校验**（工具改写/来源引用一致性等）：上游注释明确「本模块只做形状判定」，深层校验由宿主侧 `会话查询过滤.light` 承接，未移植。
- **turn/end 结构化 reason 分类**：抽取文本映射覆盖 5 类原因；reason 字段枚举强校验留给宿主。

## 6. 移交清单

- `src/会话查询.light`（新建，26 段 / 596 行）——任务4 核心纯逻辑模块
- `examples/test_会话查询1.5.light`（新建）——5 组判据定向测试，`test_会话查询1.5 PASS`
- `_antirun_sessionquery.py`（新建）——反跑判据机器验证 3/3 全红
- 既有 `会话查询过滤.light` 仅加一行接口衔接（引入新模块），其既有段落零改动
- 临时补丁/冒烟文件（_task4_*、_task4_smoke.light）已全部清理；worktree 仅含上述 3 个新文件待提交
- 全量 CI 2 个既有失败（agentE5钩子/压缩E5）由路M 统一口径；其余涉及模块回归全绿
