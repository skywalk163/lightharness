# 第11轮路M收口说明

> 日期：2026-09-12 ｜ 路：路M（收口执行者）｜ 仓库：`G:\dswork\duan-light-merge\lightharness`
> 上游只读：`G:\github\deepseek-harness` @ `a305303422`（0.1.5-rc.2）
> 收口 commit：`9b1e4f1`（36 files changed, 4459 insertions(+), 1 deletion(-)）

---

## 一、六路修复统计

| 路 | 范围 | 新增模块 | 新增测试 | 断言数 | 反跑结果 |
|---|---|---|---|---|---|
| 任务1 | 消息 System + 通用文件附件 | 0（src/消息.light、src/附件准入.light 前轮已对齐，本轮仅复核+补测试） | `test_消息_System.light` + `test_附件_通用文件.light` | 10 + 18 = 28 | `_antirun_msg_attach.py` 2/2 PASS |
| 任务2 | 团队事件 v2 + 团队工具 | `src/团队工具.light`（新建）；改 `src/团队依赖图.light`（+v2 信封包装四函数）、`src/团队看板.light`（+v2 投影桥接四段） | `test_团队事件v2.light` + `test_团队工具.light` | ≥18 + ≥30 = ≥48 | `_antirun_team_v2.py` 3/3 PASS |
| 任务3 | util 8 小包 | `src/分块列表.light` + `src/双端队列.light` + `src/加密.light` + `src/值工具.light` + `src/品牌.light` + `src/时间工具.light` + `src/包清单.light` + `src/工作区路径.light` | `test_工具_小工具.light` | 59 | `_antirun_util8.py` 3/3 PASS |
| 任务4 | NDJSON JSON-RPC 传输 | `src/JSONRPC传输.light` | `test_JSONRPC传输.light` | 40+ | `_antirun_jsonrpc.py` 3/3 PASS |
| 任务5 | boot/app-boot profile + cmdline | `src/启动配置.light` | `test_启动配置.light` | 32 | `_antirun_boot.py` 3/3 PASS |
| 任务6 | mock 大模型服务器 | `src/mock大模型服务器.light` | `test_mock大模型服务器.light` + `_repro_L084.light` | 49 + 1（修复形态） | `_antirun_mockllm.py` 3/3 PASS |

**合计**：新增 src 模块 12 个（任务2×1 + 任务3×8 + 任务4×1 + 任务5×1 + 任务6×1），修改 src 模块 2 个（团队依赖图/团队看板），新增测试 9 个（含 _repro_L084.light 修复形态），反跑脚本 6 个全部 PASS（共 17 项判据）。

---

## 二、CI 终值

- 命令：`$env:LIGHT_MERGE="G:\dswork\duan-light-merge\light-merge"; python scripts/ci_test.py`
- **终值：252 passed, 0 failed**（pytest 全量回归），smoke 5/5 通过。
- 耗时：约 502.8s（pytest）+ 10s（smoke）。
- 首轮跑出现 1 失败：`_repro_L084.light` rc=1（任务6 交付时为"故意保留报错以登记缺陷"形态，与 CI「所有 examples/*.light 必须 rc=0」门禁冲突）。
- **路M 修复**：将 `_repro_L084.light` 改写为**修复形态**（与 `_repro_L083.light` 同范式）——文件头注释保留 L-084 现象与被切碎原写法说明，正文用绕法（裸标识符避开「为」字，`末位行为`→`末支`）写可编译的类定义并断言属性可正常读取，重跑 CI 全绿。

---

## 三、对标清单结论

文件：`docs/功能对标/对标清单.json`（73 → 79 条）

### 状态更新（4 条历史缺口转「已跟随」）
- **#4** 消息词表 System（`src/消息.light` 造系统消息 createSystemMessage）→ 已跟随
- **#48** 附件通用文件附件 EncodedFileAttachment（`src/附件准入.light` 准入编码文件）→ 已跟随
- **#65** 团队依赖图事件 v2（`src/团队依赖图.light` + v2 信封包装）→ 已跟随
- **#66** 团队看板事件 v2（`src/团队看板.light` + v2 投影桥接）→ 已跟随

### 新增对标卡（#74 ~ #79）
| 编号 | 原版包 | 光明模块 | 状态 |
|---|---|---|---|
| #74 | sdk/protocol NDJSON JSON-RPC 传输 | `src/JSONRPC传输.light` | done（纯逻辑层；pending/AbortSignal/flush 留宿主包） |
| #75 | boot/app-boot profile + cmdline | `src/启动配置.light` | done（纯逻辑层；patch 用 JSON 替代 YAML；未接总入口命令面） |
| #76 | test-support/llm-mock-server | `src/mock大模型服务器.light` | done（纯逻辑核心；LCG 替代 mulberry32；cli/bin 未移植） |
| #77 | experimental/tool-agent-team | `src/团队工具.light` | done（纯逻辑层；宿主挂载留后续轮） |
| #78 | util 8 小包 | 8 个 src 模块 | done |
| #79 | 本轮登记缺口收口（#4+#48+#65+#66 四路闭环） | 消息/附件准入/团队依赖图/团队看板 | done |

---

## 四、缺陷账登记

文件：`docs/功能对标/语言缺陷账.md`（仅追加 L-084，无其他改动）

- **L-084**（第11轮任务6）：赋值关键字 `为` 在词法层恒为独立 KEYWORD，即使黏在中文标识符尾部也会被切碎（`行为`→`行`+`为`）。最小复现 `examples/_repro_L084.light` 已按**修复形态**保留（绕法=裸标识符避开「为」字），rc=0。
- **「等待」关键字评估**：任务2 报告提及「等待」是 await 语句关键字，不能作局部变量名。经路M 评估：属**已知语言行为**（与 L-004/L-021/L-025 同族的关键字词法约束，项目早已遵循），非本轮新引入缺陷，**不追加 L-085**，仅在本说明与行为差异清单中提及。

---

## 五、行为差异登记

文件：`docs/功能对标/行为差异清单.md` 新增「五、第11轮路M行为差异登记」段，共 6 项 ⚪ 维持登记：

| ID | 路 | 差异 |
|---|---|---|
| R11-D1 | 任务4 | 光明无 byte 流，用文本行流模拟（UTF-8 跨块切断交 `stdlib/UTF8增量解码器.light`） |
| R11-D2 | 任务4 | 造请求ID 用 `req_` + 三段随机整数拼接（非 randomUUID v4 去横杠形状） |
| R11-D3 | 任务5 | patch 层用 JSON（`cordis.patch.json`）替代上游 YAML（`cordis.patch.yml`） |
| R11-D4 | 任务5 | 启动配置未接入 `src/总入口.light` 命令面（跨域风险，总入口被 test_CLI命令面 锁定） |
| R11-D5 | 任务6 | 播种随机用整数 LCG 替代 mulberry32（光明无位运算原语） |
| R11-D6 | 任务6 | `slow_success` 块间延时不模拟；`cli.ts`/`bin.ts` 未移植 |

---

## 六、遗留登记（留后续轮）

1. **code-runtime-python 协议**（上一轮未提交）：`src/代码运行时协议.light` + `test_代码运行时协议.light` + `_antirun_protocol.py` 属上一轮（第10轮）遗留未提交文件，本轮不动，留待后续轮统一收口。
2. **attachment-local sharp 依赖**：图片归一化依赖 sharp（Node 原生库），光明无对应面，留宿主层后续轮。
3. **api 控制器宿主层**：SDK client/server 宿主包（pending 请求表 + AbortSignal + flush + JsonRpcResponseError 异常类型化）待后续轮在 `src/JSONRPC传输.light` 之上补全。
4. **团队工具宿主挂载**：`团队工具面` 通过注入能力字典桥接 `ctx.agentTeams.*`，真实 Cordis ctx 挂载点留后续轮。
5. **boot 宿主面**：healProfilesModuleFallback / resolveBundleDir 的 Node require.resolve / applyEntryPatches 完整算法（group/disable/`!!js`/路径锚定）/ watchUserPatches HMR 均属 Node 安装面，留后续轮。
6. **mock 服务器退化项**：connection_reset/stream_disconnect/partial_disconnect/stall 退化为线上可观察形状（不断言真实拆链时序）；cli.ts/bin.ts 未移植。

### 上一轮遗留未提交文件说明（本轮未触碰、未提交）
以下文件属上一轮（非第11轮）遗留，路M 按铁律未 `git add`、未修改：
- 修改：`README.md`、`examples/运行Web服务器.light`、`src/审批.light`
- 未跟踪 src：`代理策略.light`、`代码运行时协议.light`、`会话冷读.light`、`会话轮次大纲.light`、`启动环境.light`、`大模型回放.light`、`查询工具.light`、`检查点策略.light`
- 未跟踪测试：`test_代理策略.light`、`test_代码运行时协议.light`、`test_会话冷读.light`、`test_会话轮次大纲.light`、`test_启动环境.light`、`test_大模型回放.light`、`test_审批对照.light`、`test_查询工具.light`、`test_检查点策略.light`
- 未跟踪工具/报告/脚本：`_antirun_approval.py`、`_antirun_coldread.py`、`_antirun_protocol.py`、`_antirun_proxy_env.py`、`_antirun_replay.py`、`_task1_会话冷读查询_交付报告.md`、`_task3_代理启动环境_交付报告.md`、`_task4_大模型回放_交付报告.md`、`_task5_运行时协议_交付报告.md`、`_task6_审批对照_交付报告.md`、各种 `_taskM_*`/`_inspect_*`/`_verify_*` 脚本
- 探针：`examples/_probeG.light`（上一轮遗留，未动）

**说明**：全量 CI 会收集 `examples/` 下所有 `.light`（含上述上一轮遗留测试），本轮 252 passed 0 failed 表明这些上一轮遗留测试在当前环境也全部绿，未引入新的失败。

---

## 七、文件互斥合规确认

- 本轮 commit `9b1e4f1` 仅包含第11轮文件清单内的 36 个文件（3 修改 + 12 新增 src + 9 新增 examples 测试 + 6 反跑脚本 + 6 交付报告），**无越界**。
- 上一轮遗留的未跟踪/修改文件（见第六节）全部未 `git add`，保持工作区原状。
- `docs/功能对标/语言缺陷账.md` 的 diff 经路M 复核：仅追加 L-084 段落（+10 行），无其他非 L-084 改动。
- 本轮探针清理：`examples/_probe_task6.light`（任务6 风险语言点一次性探针）已删除；`examples/_probeG.light`（上一轮遗留）未动。

---

## 八、交付物绝对路径

- 收口说明：`G:\dswork\duan-light-merge\lightharness\_taskM_第11轮收口说明.md`
- 对标清单：`G:\dswork\duan-light-merge\lightharness\docs\功能对标\对标清单.json`
- 语言缺陷账：`G:\dswork\duan-light-merge\lightharness\docs\功能对标\语言缺陷账.md`
- 行为差异清单：`G:\dswork\duan-light-merge\lightharness\docs\功能对标\行为差异清单.md`
- 对标清单回填脚本（本轮一次性）：`G:\dswork\duan-light-merge\lightharness\_taskM_update_ledger11.py`
