# 第16轮路M收口说明

> 日期：2026-09-13 ｜ 上游：`G:\github\deepseek-harness`（本地 HEAD 9d9035b7c1，基线 0.1.5-rc.2）
> 编译器：`G:\dswork\duan-light-merge\light-merge` ｜ 工作区：`G:\dswork\duan-light-merge\lightharness`（branch main）
> 前置：第15轮收口 `3dae212`（对标103条 / 缺陷L-001~L-130 / pytest 286 passed）
> 本轮定位：**上游剩余纯逻辑面的最后清剿**——前15轮已覆盖 core/session/goal/fs/web/typert/context/storage/attachment/feedback/schedule/jobs/guard/preset/settings/skill/acp/hooks/workflow 等大域，本轮聚焦 subagent 子代理核心（13纯逻辑文件）+ api 域纯逻辑类型/协议（网关流协议/会话控制器类型/控制器类型）+ 小域类型合并（plan/todo/terminal）。**本轮后上游 packages/ 下可复刻的纯逻辑面基本清零**，剩余均为 Cordis 宿主装配面/Node IO 面/进程外执行面/工具定义面。

---

## 一、6路交付摘要

| 任务 | 域 | 光明模块 | 上游文件数 | 新增行数 | 测试断言 | 反跑 | 新缺陷 |
|---|---|---|---|---|---|---|---|
| 1 | subagent核心（上） | `src/子代理核心.light` | 6 | 1148 | ≥12 | 3/3 | L-131 |
| 2 | subagent核心（下）+model-selection | `src/子代理续传.light` | 6 | 825 | ≥12 | 3/3 | L-133 |
| 3 | api网关协议 | `src/网关协议.light` | 4 | 914 | ≥12 | 3/3 | L-135 |
| 4 | api会话控制器纯逻辑 | `src/会话控制类型.light` | 3 | 685 | ≥12 | 3/3 | L-137 |
| 5 | 小域类型合并(plan/todo/terminal) | `src/小域类型.light` | 5 | 556 | ≥10 | 3/3 | 无(L-139空缺) |
| 6 | api控制器类型合并(workspace/settings) | `src/控制器类型.light` | 3 | 1407 | ≥10 | 3/3 | 无(L-140空缺) |

**合计**：6个新src模块 + 6个新测试 + 4个repro + 6个反跑脚本 + 6份交付报告 = 5535行新增代码。

### 各路上游源与剔除清单

**任务1（子代理核心上）**：subagent/subagent/src/{catalog.ts,descriptor.ts,depth.ts,error.ts,assistant-output.ts,inbox.ts}（6文件纯逻辑）。剔除：index.ts(660行cordis+child_process装配面)/client.ts(纯类型重导出并入types)/child-agent.ts/continuation*.ts/control*.ts/invariant.ts/lifecycle.ts/list-children.ts/out-of-process.ts/projection*.ts/types.ts（全部宿主面或归任务2）。

**任务2（子代理续传+模型选择）**：subagent/subagent/src/{continuation-messages.ts,control-types.ts,internal.ts,run-settlement.ts} + tool-subagent/src/{model-selection.ts,model-selection-state.ts}（6文件纯逻辑）。剔除：tool-subagent/index.ts(707行cordis+defineTool)/invariant.ts/list-models.ts/model-selection-settings.ts（cordis宿主面）/tool-subagent-control（全部cordis+defineTool宿主面）。

**任务3（网关协议）**：api/gateway/src/{stream-protocol.ts(407行),remote-error-codes.ts} + api/remotes/src/{remote-events.ts,types.ts}（4文件纯逻辑）。剔除：gateway/index.ts(1204行cordis+node)/stream-server.ts(node)/types.ts(cordis宿主面)/remotes/index.ts(cordis+node宿主面)。

**任务4（会话控制类型）**：api/session-controller/src/{types.ts(611行大文件),assistant-stream.ts,remote-events.ts}（3文件纯逻辑）。剔除：session-controller 其余12文件（agent/catalog/commands/control/file-references/history/index/list/media-references/model-selection-projection/skill-catalog，全部cordis/node宿主面）+ client/子目录。

**任务5（小域类型合并）**：plan/plan-mode/src/{types.ts,client.ts} + todo/tool-todo/src/{types.ts,client.ts} + terminal/terminal/src/types.ts（5文件纯逻辑，client.ts为纯类型重导出并入types）。剔除：plan/index.ts+invariant.ts/todo/index.ts+invariant.ts/terminal/index.ts/terminal-bash（全部cordis/node/defineTool宿主面）。

**任务6（控制器类型合并）**：api/workspace-files/src/types.ts + api/settings-controller/src/types.ts + api/workspace-controller/src/types.ts（3文件纯逻辑）。剔除：各控制器 index.ts/commands.ts/feed.ts/changes.ts/credentials.ts/directory-picker.ts（全部cordis/node宿主面）+ runtime-diagnostics（cordis不变量安装器宿主面）。

---

## 二、路M核验结果

### 2.1 6测试单独跑全 PASS rc=0

| 测试 | 结果 | rc |
|---|---|---|
| test_子代理核心 | PASS | 0 |
| test_子代理续传 | PASS | 0 |
| test_网关协议 | PASS | 0 |
| test_会话控制类型 | PASS | 0 |
| test_小域类型 | PASS | 0 |
| test_控制器类型 | PASS | 0 |

### 2.2 6反跑全 ALL OK（A/B/C三项判据全过）

| 反跑脚本 | A正常 | B边界 | C变异立红 | 字节级恢复 | 恢复后绿 |
|---|---|---|---|---|---|
| _antirun_t1_子代理核心.py | ✓ | ✓ | ✓(深度最大值反向 rc=1) | ✓(sha256 37a9bfcc) | ✓ |
| _antirun_t2_子代理续传.py | ✓ | ✓ | ✓(模型路由键改分隔符 rc=1) | ✓(sha256 a5300b7f) | ✓ |
| _antirun_t3_网关协议.py | ✓ | ✓ | ✓(网关错误码表首码改错 rc=1) | ✓(sha256 7f03413e) | ✓ |
| _antirun_t4_会话控制类型.py | ✓ | ✓ | ✓(会话状态枚举idle改错 rc=1) | ✓(sha256 665ecf75) | ✓ |
| _antirun_t5_小域类型.py | ✓ | ✓ | ✓(待办状态枚举in_progress改错 rc=1) | ✓(sha256 920c38b5) | ✓ |
| _antirun_t6_控制器类型.py | ✓ | ✓ | ✓(目录类型枚举改坏 rc=1) | ✓ | ✓ |

**反跑核验要点**：C判据均为真变异（修改源文件后测试立红 rc=1），恢复后字节级校验通过（sha256匹配），恢复后测试回归绿 rc=0。反跑输出未截断核验（第13轮教训已遵守）。

### 2.3 文件互斥零越界

`git diff --name-only -- src/` 确认：6路均只新增文件，**未修改任何既有 src/ 模块**。零越界。

### 2.4 4个repro全 rc=0

| repro | 缺陷 | 任务 | rc |
|---|---|---|---|
| examples/_repro_L131.light | L-131 除零抛错非Infinity | 任务1 | 0 |
| examples/_repro_L133.light | L-133 缺chr内置无法生成NUL分隔符 | 任务2 | 0 |
| examples/_repro_L135.light | L-135 字典缺失键抛KeyError非undefined短路 | 任务3 | 0 |
| examples/_repro_L137.light | L-137 变量名以关键字开头被断开 | 任务4 | 0 |

---

## 三、新缺陷留档（L-131/L-133/L-135/L-137）

### L-131（任务1 子代理核心域）：除零抛错非Infinity

- **现象**：明亮除法 `x / 0` 直接抛「除零错误」，而非产生 `±Infinity` / `NaN`。
- **上游语义**：TS/JS `1/0 === Infinity`、`0/0 === NaN`，可被 `isFinite()`/`isNaN()` 判定。
- **影响面**：任何含「可能除零」的数值逻辑——子代理深度计算、模型选择评分归一化、几何尺寸计算等。
- **绕法**：调用点 `尝试/捕获` 兜底，除零场景返回默认值。
- **repro**：`examples/_repro_L131.light`（rc=0）

### L-133（任务2 子代理续传域）：缺chr内置无法生成NUL分隔符

- **现象**：明亮仅有「字符→码」方向的 `字符转ASCII`（对应 ord），**缺「码→字符」方向的 chr 内置**（对应 `String.fromCharCode`）。
- **上游触发面**：model-selection.ts 的 modelRouteKey 用 `provider+'\0'+model`（NUL分隔符）作稳定身份键。
- **影响面**：任何需要生成控制字符（NUL/SOH/STX等）作分隔符或标记的场景。
- **绕法**：改用 `序列化JSON([provider, model])` 作无碰撞唯一键。
- **repro**：`examples/_repro_L133.light`（rc=0；若明亮新增chr内置，本脚本会主动抛错告警）

### L-135（任务3 网关协议域）：字典缺失键抛KeyError非undefined短路

- **现象**：光明字典「缺失键」访问 `值["缺失键"]` 直接抛 `KeyError`，而 TS/JS 对象属性缺失访问返回 `undefined`（不抛、可安全短路）。
- **上游语义**：JS `value.type === 'x' && exactKeys(...)` 依赖「undefined 短路」，上游校验器大量使用此模式。
- **影响面**：任何依赖「可选字段安全访问」的校验器/协议解析器/类型守卫。
- **绕法**：所有可选字段访问改用 `字典获取(值, 键, 空)` 安全取值。
- **repro**：`examples/_repro_L135.light`（rc=0）

### L-137（任务4 会话控制类型域）：变量名以关键字开头被断开

- **现象**：局部变量名以关键字「尝试」开头时，后续下标赋值/读取在关键字边界被断开——`尝试["甲"] 为 1` 报「期望 '='、':' 或 '为'」。
- **同族缺陷**：与 L-120（标识符可被关键字序列完全切分）/ L-101（「回调」保留字）同族——光明词法分析器在标识符与关键字边界处理不严谨。
- **影响面**：任何变量名包含「尝试」「如果」「对于」「当」「设」「返回」等关键字字样的场景。
- **绕法**：变量名完全避开「尝试」等关键字字样（改「活动项」「运行项」「待办态」等）。
- **repro**：`examples/_repro_L137.light`（rc=0；被破坏原写法见注释不参与编译）

### 空缺编号

L-132（任务1仅L-131）、L-134（任务2仅L-133）、L-136（任务3仅L-135）、L-138（任务4仅L-137）、L-139（任务5无新缺陷）、L-140（任务6无新缺陷）。空缺编号顺延至后续轮次使用（参照第14/15轮空缺先例）。

---

## 四、行为差异 R16-D1~D6

| 编号 | 任务 | 核心差异 | 状态 |
|---|---|---|---|
| R16-D1 | 任务1 | 除零抛错非Infinity(L-131)，尝试/捕获兜底；宿主面剔除 | ⚪ 纯逻辑面可用 |
| R16-D2 | 任务2 | 缺chr内置无法生成NUL分隔符(L-133)，序列化JSON数组作唯一键绕法；宿主面剔除 | ⚪ 纯逻辑面可用 |
| R16-D3 | 任务3 | 字典缺失键抛KeyError非undefined短路(L-135)，字典获取安全取值绕法；宿主面剔除 | ⚪ 纯逻辑面可用 |
| R16-D4 | 任务4 | 变量名以关键字开头被断开(L-137)，变量名避开关键字绕法；宿主面剔除 | ⚪ 纯逻辑面可用 |
| R16-D5 | 任务5 | 小域纯逻辑文件少(每域1-2个)合并成任务；client.ts纯类型重导出并入types；宿主面剔除 | ✅ 纯逻辑面可用 |
| R16-D6 | 任务6 | 小域纯逻辑文件少(每域1个types)合并成任务；三域类型命名空间隔离；宿主面剔除 | ✅ 纯逻辑面可用 |

---

## 五、docs三件回填

| 文档 | 追加内容 | 当前状态 |
|---|---|---|
| `docs/功能对标/对标清单.json` | #104~#109（6条） | 109条 |
| `docs/功能对标/语言缺陷账.md` | L-131/L-133/L-135/L-137（4条+空缺说明） | L-001~L-137（L-132/134/136/138/139/140空缺） |
| `docs/功能对标/行为差异清单.md` | R16-D1~D6（6条） | R11~R16 |

---

## 六、git 提交链

```
3dae212  收口(第15轮): 对标回填 #98~#103 / L-123/L-125/L-127/L-129 / R15-D1~D6 + 收口说明(pytest 286全绿)
198b04c  任务6: 控制器类型合并 (对标#109 workspace-files/settings-controller/workspace-controller)  [用户先行提交]
e1d4621  任务1(子代理核心域): subagent catalog/descriptor/depth/error/assistant-output/inbox纯逻辑面(L-131; R16-D1; 反跑3/3)
f28be36  任务2(子代理续传域): subagent continuation-messages/control-types/internal/run-settlement + model-selection/state纯逻辑面(L-133; R16-D2; 反跑3/3)
0243e05  任务3(网关协议域): api gateway stream-protocol/remote-error-codes + remotes remote-events/types纯逻辑面(L-135; R16-D3; 反跑3/3)
f43ef6e  任务4(会话控制类型域): api session-controller types(611行)/assistant-stream/remote-events纯逻辑面(L-137; R16-D4; 反跑3/3)
d8c3aeb  任务5(小域类型域): plan-mode/types+client + tool-todo/types+client + terminal/types纯逻辑面(R16-D5; L-139空缺; 反跑3/3)
[待提交]  收口(第16轮): docs三件回填 + 收口说明(CI全绿)
```

---

## 七、全量CI结果

**CI全绿**（2026-09-13，耗时 7分24秒）：

| 项目 | 结果 | 详情 |
|---|---|---|
| pytest | **296 passed** | 286基线 + 6新测试 + 4repro = 296，完全符合预期；rc=0 |
| smoke | **5/5 通过** | test_会话/test_代理/test_工具/test_消息/test_流 全通过 |
| 总耗时 | 444.53s (0:07:24) | pytest 414.0s + smoke ~30s |

**已知 flaky 未复现**：test_审批.light（第14轮发现偶发 rc=1）本轮未复现，全量CI一次通过。

---

## 八、未移植项汇总（本轮后上游纯逻辑面基本清零）

本轮6路覆盖后，上游 `packages/` 下可复刻的纯逻辑面（无 cordis/node/child_process/defineTool 依赖的类型/协议/状态机/计算逻辑）基本全部复刻完毕。剩余文件按类别汇总：

### 8.1 Cordis 宿主装配面（不可复刻，需宿主接线）
- 所有 `index.ts`（Cordis Context/Service 装配，如 subagent/index.ts 660行、gateway/index.ts 1204行、session-controller/index.ts 417行等）
- 所有 `invariant.ts`（Cordis 不变量安装器，如 plan/invariant.ts、todo/invariant.ts、runtime-diagnostics/invariants/index.ts 等）
- 所有 `client.ts`（Cordis 客户端/服务总线，大部分为纯类型重导出已并入types）
- Cordis Context/Service/插件体系相关代码

### 8.2 Node IO 面（不可复刻，需宿主接线）
- `fs`/`path`/`child_process`/`net`/`http`/`crypto`/`buffer`/`stream` 等 Node 内置模块依赖
- 文件读写、进程管理、网络通信、加密哈希、流处理等
- 如 subagent/child-agent.ts、out-of-process.ts、gateway/stream-server.ts、terminal-bash/session.ts 等

### 8.3 进程外执行面（不可复刻，需宿主接线）
- subagent 子代理驱动（subagent-acp/claude-code/codex/dsh-sdk/fork-in-process/in-process-driver/spawn-in-process）
- 子进程 spawn/fork、进程间通信、子代理生命周期管理
- code-runtime 代码运行时（沙箱执行/进程隔离）

### 8.4 工具定义面（不可复刻，需宿主接线）
- 所有 `defineTool` 调用（工具注册/参数校验/执行回调）
- 如 tool-subagent/index.ts、tool-subagent-control/index.ts、tool-todo/index.ts、plan/index.ts 等
- 工具实际执行逻辑（网络请求/文件操作/进程调用等）

### 8.5 上游本地HEAD更新待处理
- 上游本地 HEAD 已从基线 a305303422（0.1.5-rc.2）更新至 9d9035b7c1
- 本轮复刻文件无变化（已核对），记录待后续轮次更新基线或做增量差异分析

---

## 九、教训与注意事项

1. **反跑脚本恢复必须放 finally/异常安全路径**：第13轮教训，本轮6个反跑脚本均遵守，C判据变异后恢复字节级校验通过。
2. **反跑输出不能截断核验**：第13轮教训，本轮路M核验反跑输出时查看完整输出（A/B/C三项+字节级恢复+恢复后绿），未截断。
3. **反跑脚本路径自定位**：第14轮教训，本轮6个反跑脚本均使用 `BASE = os.path.dirname(os.path.abspath(__file__))`，从 lightharness 根目录运行正常。
4. **小域类型合并任务的命名空间隔离**：任务5（plan/todo/terminal三域）和任务6（workspace/settings三域）均为多域类型合并成单模块，需注意三域类型命名空间隔离，避免类型名冲突。本轮两任务均通过测试验证无冲突。
5. **大文件类型复刻的完整性**：任务4的 session-controller/types.ts 611行大文件，需确保所有类型定义完整复刻（Session/会话状态/视图/列表/快照/事件类型/命令类型/投影类型/媒体引用/文件引用等），本轮测试覆盖≥12断言用例验证完整性。
6. **缺陷编号空缺顺延**：本轮任务5/6无新缺陷（L-139/L-140空缺），任务1-4各1个缺陷（L-131/L-133/L-135/L-137），L-132/L-134/L-136/L-138也空缺。空缺编号顺延至后续轮次使用，参照第14/15轮空缺先例。
7. **用户先行提交任务6**：与第15轮任务6一样，本轮任务6（控制器类型）由用户先行提交（198b04c），路M核验提交完整性后直接纳入提交链，不重复提交。

---

## 十、下一轮展望

本轮后上游 packages/ 下可复刻的纯逻辑面基本清零。后续轮次可选方向：

1. **上游增量差异分析**：上游本地 HEAD 已从 a305303422 更新至 9d9035b7c1，需做增量差异分析，确认是否有新增纯逻辑面需要复刻。
2. **宿主接线原型**：开始探索 Cordis 宿主装配面的接线原型（如 Context/Service 模拟、工具注册机制、Node IO 抽象层），为后续宿主面复刻做准备。
3. **缺陷修复轮**：集中修复语言缺陷账中的高频缺陷（如 L-129 真值语义、L-135 字典缺失键、L-137 词法边界等），提升语言层能力。
4. **已有模块深化**：对前16轮已复刻的模块做深化（补充边缘用例、优化性能、完善类型定义）。

具体方向由用户决定。
