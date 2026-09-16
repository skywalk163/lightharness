# 任务2 交付报告 —— agent-default-model 模块复刻（第 37 轮）

> 轮次：第 37 轮 ｜ 任务：2（P0）｜ 日期：2026-09-16
> 上游基线：deepseek-harness 0.1.5-rc.2（本地 `G:\github\deepseek-harness`，已与 GitHub master blob `82e4e0d` 逐字比对一致，3791 字节）
> 交付文件：`src/代理默认模型.light`（新增）、`examples/test_R37_代理默认模型.light`（新增，rc=0，14 组全绿）

## 一、上游源码精读（packages/core/agent-default-model/src/index.ts，109 行）

| 上游元素 | 语义 | 行号 |
|----|----|----|
| `AGENT_DEFAULT_MODEL_SETTINGS_NAMESPACE` | settings 命名空间常量 `'agent-default-model'` | 21 |
| `AgentDefaultModelSettings` | 存储形态 `{provider, model, reasoningEffort?}`，缺省力度 = provider 默认行为 | 24-31 |
| `AGENT_DEFAULT_MODEL_SETTINGS_SCHEMA` | `z.object({provider: required, model: required, reasoningEffort: 可选})` | 34-38 |
| `Config` | 组合入口 `{provider, model}` 必填 | 41-46 |
| `selection(settings)` | 私有投影：存储形态 → `ModelSelection`；力度缺省时条件展开**省略键**；存在时经 `ReasoningEffortId(...)` | 49-57 |
| `AgentDefaultModelConfig` | Service：构造时 entry=组合入口、`source=()=>entry`；`ctx.inject(['settings'])` 挂载后 `setSource` 换为 settings 实时读取；`onChange: ()=>{}`（消费方全走 currentSelection，无需重建） | 64-84 |
| `currentSelection()` | 读 source 并投影，返回 **detached** 副本 | 90-92 |
| `saveSelection(next)` | `settings?.replace(ns, {...})` 整节替换写回；无 settings 时 no-op（注释明示 "keeps its composition entry"） | 100-106 |

**官方测试契约**（tests/agent-default-model.spec.ts，5 用例，本交付逐条映射）：
1. 用户层优先于组合入口（保存后 currentSelection 变更，含 `reasoningEffort: 'high'`）。
2. 保存无力度的选择 → 清除已存力度（replace 整节替换）。
3. 手写**部分 section**（仅 `{model}`）叠加在 entry 上（provider 仍来自入口）→ schema 校验作用于合并后生效设置，而非用户节本身。
4. settings 服务卸载 → 回退组合入口（可逆）。
5. 无 settings 挂载时 saveSelection 为 no-op，入口保持。

**关键佐证（packages/llm/llm/src/brand.ts）**：`ReasoningEffortId(id)` 仅做类型品牌化，注释明示 *"no validation is performed"*，原样返回同一字符串。光明无类型系统，等价语义为**推理力度原样保留**，不得发明枚举校验（如误加 `high/medium/low` 白名单即为臆造行为差异）。

## 二、光明适配要点

| 光明限制 | 适配 | 忠实性说明 |
|----|----|----|
| 无 cordis/Service | 配置实例 = 字典 `{"形态","入口","用户层","挂载"}` | entry/source/写回三态全部保留 |
| 一等函数为具名段落引用，**无法捕获局部状态**（无闭包） | 上游 `source` 闭包三态 → `挂载` 标志 + `用户层` 字典；`读当前设置` 分支读取 | 逐用例等价：未挂载=读入口；挂载=叠加(入口,用户层)；卸载=回退 |
| 无 schemastery | 手动谓词 `校验设置载荷`/`校验模型配置` | `.required()` 取「键存在且为字符串」最小确定口径；多余键宽容（上游未验证行为不擅自加严） |
| 无 settings 磁盘服务 | `挂载设置源`/`写用户层`/`卸载设置源` 内存化投影 | replace=整节替换用户层；校验作用于合并后生效设置（对齐官方用例 3 的部分节行为） |
| 分层合并 | 模块内 `叠加节(底, 上)` 浅层覆盖 | 本模块设置节全为标量键，与 mergeLayers 逐用例等价；不引入 src/设置.light 依赖（其 `设置命名空间` 段与本模块常量同名，内联 codegen 会重定义——常量改名为 `默认模型设置命名空间`） |

## 三、实现细节（src/代理默认模型.light，导出 11 项）

```
默认模型设置命名空间                  常量 "agent-default-model"
校验设置载荷(载荷)                    设置节 schema（真/假）
校验模型配置(配置)                    组合入口 schema（真/假）
投影选择(设置)                        selection() 等价；力度缺省省略键；分离副本
建默认模型配置(提供者, 模型, 推理力度=空)  构造；非法入参抛错（上游 schema 校验失败即抛）
取当前选择(配置)                      currentSelection()；detached
更新默认模型(配置, 提供者=空, 模型=空, 推理力度=空)   任务书 2.2 要求（上游无直接对应）
挂载设置源(配置) / 卸载设置源(配置)     installSection 可逆挂载/回退
写用户层(配置, 节)                    settings.replace 等价（整节替换，校验合并后生效设置）
保存选择(配置, 选择)                  saveSelection 等价（未挂载 no-op 返回假）
```

**两处实现期修正（均由测试驱出）**：
1. `写用户层` 初版对用户节直接跑 schema → 官方用例 3 的部分节 `{"模型": …}` 被误拒。修正为对**叠加后生效设置**校验（这才是上游 installSection 的真实分层语义）。
2. `更新默认模型` 的 `推理力度` 参数是二态（空/非空），无法同时表达「不动」与「清除」。定稿语义：**传空=清除**（对齐上游「缺省=provider 默认行为」）；调用方只想改提供者/模型而保留力度时须显式传当前力度。已在模块头注释与测试 §5 双向钉住。

**命名**：`src/代理默认模型.light` 命名预检查通过（src/ 下无同名/近名文件）；全段落名全仓库唯一性预检查通过；无单字别名（L-119）、无可被关键字序列完全切分的标识符（L-120）。

## 四、测试结果（examples/test_R37_代理默认模型.light，rc=0，14 组全绿）

| 组 | 覆盖 | 对应上游 |
|----|----|----|
| #00 | 判据自检（必等助手真能报错） | — |
| #01-02b | 建配置：形态/入口形状、缺省力度省略键 | Config |
| #03 | 建配置带力度 | Config |
| #04 | 三类非法入参抛错 | Config schema 校验失败即抛 |
| #05 | 设置节/组合入口 schema 矩阵（7 断言） | AGENT_DEFAULT_MODEL_SETTINGS_SCHEMA |
| #06 | 投影选择：缺省省略键、未知力度 `'ultra'` 原样保留 | selection() + ReasoningEffortId 无验证 |
| #07 | 取当前选择：读入口、detached（篡改返回值不影响本体） | currentSelection() |
| #08 | 更新默认模型：改值/跳过/清除/抛错（9 断言） | 任务书 2.2 |
| #09 | 挂载 + 部分 section 叠加 | 官方用例 3 |
| #10 | 保存选择：写回含力度、无力度整节替换清除 | 官方用例 1/2 |
| #11 | 挂载后更新入口不影响当前选择（差异钉住） | setSource 后 entry 不再被读 |
| #12 | 卸载回退组合入口 | 官方用例 4 |
| #13 | 无挂载保存 no-op、入口保持 | 官方用例 5 |
| #14 | 命名空间常量 | NAMESPACE |

回归：`test_代理循环`/`test_代理`/`test_代理团队`/`test_会话日志深化`/`test_设置`/`test_客户端` 全部 rc=0（新增模块不触碰任何既有文件，全量反跑归任务4）。

## 五、口径声明与移交

- **上游证据基础**：本地 `G:\github\deepseek-harness`（0.1.5-rc.2 基线）index.ts 与 GitHub master blob `82e4e0d` 逐字一致；spec 5 用例作为行为契约。schemastery 的空串/多余键细节未能从上游源码逐字验证，光明侧取最小确定口径并在 §二 标注。
- **settings 集成范围**：核心 + 内存化 settings 投影（挂载/写用户层/卸载）已完整交付；磁盘持久化属 settings 服务本身职责（上游亦仅依赖其接口），不属本模块范围。
- **移交任务3**：`取当前选择` 返回的 `{"提供者","模型"(,"推理力度")}` 即可传给大模型客户端做默认路由；`test_R37_集成测试.light` 可直接复用本测试的挂载/写回模式做端到端。
- **移交任务4**：本任务新增 2 文件，不触碰既有文件；全量反跑预期仅新增 2 文件的 token 记录。
- **语言缺陷**：未发现新缺陷，无 L-0xx 登记。
