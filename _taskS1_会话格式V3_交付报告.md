# 路1（S）交付报告 —— Session 日志格式 V3 与迁移链

> 任务书：`0.15复刻_第4轮_任务prompt分发.md` 路1（S）｜Session 日志格式 V3 与迁移链（头号工程）
> 对照原版：`G:\github\deepseek-harness` @ `a305303422`（0.1.5-rc.2）
> worktree：`G:\dswork\duan-light-merge\wt-S1`（分支 `task-1-session-v3`）
> 完成日期：2026-09-11

---

## 1. 交付清单

| 文件 | 类型 | 说明 |
|---|---|---|
| `src/会话格式.light` | 新增 | Session 格式 V3 纯逻辑：数据模型 + V0/V1/V2/V3 编解码 + v0→v1→v2→v3 相邻迁移链 + catalog + 事件词汇（canonical 校验）+ 节点 0 / 内嵌助手流投影原语 |
| `src/会话.light` | 修改 | 头信息版本 [3,0]；新增 `记录系统提示`/`投影节点0`（surface 节点 0）；新增 `记录助手轮`/`投影内嵌消息`（内嵌助手流会话侧表示）；`投影消息` 支持流块并入；`整理消息` 节点 0 置于模型可见消息最前 |
| `src/持久化.light` | 修改 | V3 头行（version 对象 `{major,minor}` / parentSession / isSeeded+seedLength / inheritedEventCount）；事件行统一走 V3 编码器；读入走 V3 解码 + `strict`/`recoverable` 恢复策略（`读入会话` / `读入会话宽容`）；兼容旧整数 version 头 |
| `src/会话查询过滤.light` | 核对 | 纯谓词过滤器（header 的 id/cwd/createdAt/parentSession 英文键与 V3 模型一致），V3 下无需变更 |
| `src/会话标题.light` | 核对 | 标题规范化逻辑，与 V3 事件格式正交，无需变更 |
| `src/会话引用.light` | 核对 | 引用解析纯逻辑，与 V3 事件格式正交，无需变更 |
| `src/会话存储.light` | 核对 | 消息级 JSONL 存储（角色/内容键），与会话事件格式正交，无需变更 |
| `examples/test_会话格式.light` | 新增 | 定向测试：V3 编解码往返 / canonical 归一 / 紧凑 run 直通 / 节点 0 投影 / 内嵌流落盘往返 / strict-recoverable |
| `examples/test_会话V3迁移.light` | 新增 | 定向测试：v0→v1→v2→v3 全链迁移 / identity 保留 / 未知事件保留 / PTC 词汇重命名 / 序号重排 |
| `examples/test_会话格式冒烟.light` | 新增 | 开发期冒烟（保留作语法回归） |

## 2. 新模块与上游文件逐行对应表

| 上游文件（0.1.5-rc.2） | 会话格式.light 对应实现 |
|---|---|
| `session-format/src/json.ts` | `安全整数`/`非负整数`/`判版本`/`版本文本`/`同版本`/`版本小`/`校验快照` |
| `session-format/src/types.ts` | `造头`/`造事件`/`事件带来源`（SessionFormatHeader / SessionFormatEvent） |
| `session-format/src/index.ts` | `造V0编解码`/`V0编解码`/`V1编解码`/`V2编解码`/`V3编解码`（releasedV0/V1/V2/V3SessionFormatCodec） |
| `session-format/src/chain.ts` | `定义迁移`/`创建链`/`迁移会话`/`重排序号`/`标准链`（SessionFormatMigration / SessionFormatChain / migrateSession） |
| `session-format/src/catalog.ts` | `造目录`/`目录读头`/`目录恢复`/`目录编码头`/`目录编码事件`/`当前目录`（readHeader / createRestore / encodeCurrentHeader / encodeCurrentEvent） |
| `session-format/src/context.ts` | 上下文聚合（引用解析上下文）——简化为直接传入已解析头/事件，登记（见 §4） |
| `session-format/src/error.ts` | 抛错语义内联（缺失必选键/多余键/未知类型/空日志/坏行 strict） |
| `session-format/src/filename.ts` | `编码段本地`/`日志文件名`（路径段编码原语 `编码段` 沿用 `持久化.light`） |
| `session-format-v0-to-v1/src/{index,codec,dispositions}.ts` | `解码V0头`/`编码V0头`/`解码V0事件`/`解码V0打包行` + V0 事件词汇表 + `迁移头V0V1`/`迁移事件V0V1`（identity 直通） |
| `session-format-v1-to-v2/src/{codec,dispositions,migration}.ts` | V2 事件词汇增量 + `迁移头V1V2`/`迁移事件V1V2`（assistant/chunk → assistant/message 内嵌流） |
| `session-format-v2-to-v3/src/{codec,migration,payload,references,validation}.ts` | `V3编解码`/`解码V3事件`（canonical payload 校验）/`迁移头V2V3`/`迁移事件V2V3`（PTC 词汇重命名 + 系统提示提升）/`校验事件载荷`（validation）/`已知事件类型` |
| `session-format-catalog/src/{current,generated,index}.ts` | `当前目录`（current catalog：当前版本 3.0 + 标准链 + V3 编解码器） |

## 3. 语义要点实现方式

| 语义要点 | 实现方式 |
|---|---|
| V3 物理行 = header + 事件行（seq 连续 + sourceEventSeqs） | `编码V2事件` 输出 `{type, seq, time, data, redacted?, sourceEventSeqs?}`；`解码V3事件` 读回（`来源事件序号`/`遮蔽` 中文键 ↔ 磁盘 `sourceEventSeqs`/`redacted`） |
| v0/v1 物理行含打包行 runType/firstSeq/eventCount | `解码V0打包行` 识别 text-chunks/reasoning-chunks/tool-call-chunks → 单条 `assistant/chunk`（紧凑 run 直通不展开）；迁移无直通处理器时才并入 |
| v0→v1 identity 直通 | `迁移头V0V1` 仅推进版本 [1,0]，其余头字段原样；`迁移事件V0V1` 恒等 |
| v1→v2 内嵌助手流 | `迁移事件V1V2`：assistant/chunk → assistant/message，`块` 并入 `流`；会话侧 `记录助手轮`（attempt + message 带流）与 `投影内嵌消息`/`投影消息` 合并流块 |
| v2→v3 系统提示提升（surface 节点 0） | `记录系统提示` 写 `system/message`（`系统` + `表面操作` append/replace）；`投影节点0` 应用最近一条（replace 覆盖 / append 拼接），**跳过遮蔽事件**（历史替换后重投影）；`整理消息` 将节点 0 置于模型可见消息最前 |
| v2→v3 PTC 词汇 | `迁移事件V2V3`：request/header 工具模式 `codeMode`→`ptc`、`codeModeEnabled`→`ptcEnabled` 并移除旧键；tool/call 名称 `tool/code-dispatch-render|run` → `tool/ptc-dispatch-*`；`迁移头V2V3` 代理预设 `code`→`ptc` |
| identity-preserving 迁移 | 全部迁移头只改 `版本`/`代理预设` 字段，`标识`/`创建时间`/`工作目录`/`父会话`/`是种子` 保留（测试逐字段断言） |
| 未知必选事件尾部恢复保留 | `解码V3事件` 仅对已知事件类型做 payload 校验，未知类型**直通保留**（不静默丢弃、不抛错） |
| canonical envelope 归一 | `校验事件载荷`：必选键存在性 + 多余键拒绝（strict）；迁移链终态事件按 `重排序号` 归一为 0..n-1 连续 |
| 恢复策略 strict/recoverable | `读入会话`（strict）坏行抛错；`读入会话宽容`（recoverable）跳过坏行续读（坏行后的合法事件完整保留） |
| 继承前缀（inheritedEventCount） | `行对象` 头信息含 `继承数` 时写 `inheritedEventCount`；`读入会话带策略` 读取并保留（lightharness 会话当前无实际继承场景，语义落盘保留） |
| 旧格式兼容 | `解码V0头` 对 `version` 为整数（旧 1）或对象 `{major,minor}` 均容错；旧 V1 文件读回后重建为 V3 会话对象 |

## 4. 未移植项（登记缺口）

| 上游能力 | 理由 |
|---|---|
| 文件锁 / 写租约（session-persistence-write-lease #3362） | 宿主层并发控制，非纯逻辑。lightharness 持久化使用现有原子写 + 整盘快照，登记不移植 |
| 流式迁移（session-migration-streaming #3585） | 迁移为纯内存批量逐跳执行（`迁移会话`），无流式游标，语义等价（终态一致），登记简化 |
| createDecoder 分段流式解码（recovery 游标） | 读入为逐行解码 + strict/recoverable 两策略，未实现游标续读接口，登记简化 |
| `context.ts` 上下文聚合（引用解析上下文装配） | 非核心格式逻辑，lightharness 侧由调用方直接传已解析头/事件，登记 |
| 事件词汇表全量（RELEASED_V0_EVENT_DISPOSITIONS） | 复刻核心子集 + 关键必选键（21 类 V0 + 3 类 V2 增量 + system/message）；其余类别为未知直通（语义安全） |

## 5. 测试与验证

### 5.1 定向用例（rc==0）
- `examples/test_会话格式.light` —— **全部用例通过**
  - V3 编解码往返一致（编码→解码→编码 幂等）
  - canonical：必选键缺失抛错 / 多余键拒绝 / 未知事件类型直通保留
  - 紧凑 run 直通（打包行 → 单条 chunk → v1→v2 并入流）
  - 节点 0：append 拼接 / replace 覆盖 / 遮蔽后重投影清空
  - 内嵌助手流落盘往返（节点 0 + attempt + message，整理消息 2 条，流块并入 content）
  - strict 坏行抛错 / recoverable 跳过续读（坏行后事件完整）
- `examples/test_会话V3迁移.light` —— **全部用例通过**
  - v0→v1→v2→v3 全链迁移（终版本 3.0）
  - identity 五字段保留（标识/创建时间/工作目录/父会话/是种子）
  - 事件 1:1、序号重排 0..n-1 连续
  - v1→v2 chunk → message + 流
  - v2→v3 PTC 词汇重命名（codeMode→ptc、ptcEnabled、旧键移除、工具名重命名、代理预设 code→ptc）
  - 未知事件沿链直通保留
- 既有会话/持久化族回归全绿：`test_会话` / `test_会话深化` / `test_持久化` / `test_持久化增量` / `test_压缩` / `test_压缩自动` / `test_cli深化` / `test_L007b`

### 5.2 反跑判据（改反即红，机器验证 5/5）
| 改反点 | 反跑结果 |
|---|---|
| V3 编解码类型 `user/message`→`user/other` | rc=1（红）✓ |
| recoverable 事件数 2→99 | rc=1（红）✓ |
| 全链终版本 `3.0`→`2.0` | rc=1（红）✓ |
| 未知事件类型保留改反 | rc=1（红）✓ |
| PTC 工具名重命名改反 | rc=1（红）✓ |

验证脚本：`wt-S1/_antirun_sf.py`（改断言 → 运行 → 断言 rc!=0 → 恢复原文件）。

### 5.3 全量 CI
`python scripts/ci_test.py`（LIGHT_MERGE=light-merge）：
- **202 passed / 2 failed / 296s**（用例总数 204，较基线 200 新增 4 例＝本路新增测试）
- 2 个失败均为**既有失败**（非本路引入）：`test_agentE5钩子.light`、`test_压缩E5.light`（test_压缩E5 失败原因为 `slice indices must be integers` 类型错误，位于 `examples/test_压缩E5.light:27`，与 session-format V3 无关；main 分支基线同样失败）
- 结论：**无新增打红**，本路全部新增/改动用例 rc==0。

## 6. 移交清单（跨路接口）

| 接口 | 提供方 | 消费方（登记） |
|---|---|---|
| 节点 0 读取原语 `投影节点0()`（system/message 投影，append/replace） | `会话.light` | 路 3（agent-loop 系统提示提交语义）/ 路 5（llm 模型目录）若缺系统提示装配原语，从本路取 |
| PTC 词汇约定（request/header 工具模式 `ptc`/`ptcEnabled`、工具 `tool/ptc-dispatch-*`） | `会话格式.light` 迁移链 | 路 3 / 路 5 的提示词与工具清单侧 |
| 事件词汇表（`事件词汇表` 导出，canonical payload 规则） | `会话格式.light` | `会话查询过滤` 等消费侧如需按类型校验可引用 |
| 恢复策略两态（strict / recoverable） | `持久化.light`（`读入会话`/`读入会话宽容`） | 会话控制器 / 其他持久化消费方 |
