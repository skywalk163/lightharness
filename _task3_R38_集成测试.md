# 任务3 交付报告 —— 集成测试：上游8用例映射 + 端到端三模式对比（第 38 轮）

> 轮次：第 38 轮 ｜ 任务：3（P1）｜ 日期：2026-09-16
> 交付文件：`examples/test_R38_集成测试.light`（新增，rc=0，11 组全绿）
> 依赖基线：任务1 `src/工具展示.light`（已交付，其单元测试 14 组全绿）＋ src/工具.light ＋ src/代理循环.light ＋ src/代码运行时.light
> 上游：packages/core/agent-tool-presentation/tests/agent-tool-presentation.spec.ts（本地基线 0.1.5-rc.2，官方 7 用例 + 隐含 disposer = 8 契约）

## 一、上游 8 用例映射（逐条 → 光明测试组）

| # | 上游用例 | 光明映射（测试组） | 结果 |
|---|---|---|---|
| 1 | 声明使用的服务而不持有 codeRuntime（`inject=['tools']`） | `工具展示依赖 == ["tools"]` 且不含 codeRuntime；native 配置无运行时直接应用 | OK #1 |
| 2 | 给特定 agent PTC，其余保持 native（作用域隔离） | coded 作用域 ptc → 可见 `[run_code]`；plain 作用域 native → 全量；SDK 含 echo、3 条目 | OK #2 |
| 3 | both 模式两者都展示 | both 作用域 → `[echo, search, write_file, run_code]` | OK #3 |
| 4 | agent 卸载恢复部署默认（HMR 安全） | 注销后 `获取作用域展示` 回 native、可见工具回全量 | OK #4 |
| 5 | 等待部署未组合的 codeRuntime（pending，不应用） | ptc 无运行时 → `是否待代码运行时` 真、作用域回退部署默认、可见工具仍全量（**不静默降级**） | OK #5 |
| 6 | codeRuntime 到达后应用 | `等待代码运行时` 后 pending 解除、作用域转 ptc、可见 `[run_code]` | OK #6 |
| 7 | mode 必填，不设默认值 | 空/非法值抛错（2 次）、大小写敏感（`"PTC"` 拒绝，对齐 z.union）、校验矩阵 | OK #7 |
| 8 | （隐含）presentAs 返回 disposer | apply 返回配置句柄充当 disposer；重复注销幂等不抛；非法句柄返回假 | OK #8 |

## 二、端到端三模式对比（任务书 3.2，OK #9）

工具注册表（`src/工具.light` 的 `类 工具注册表`）注册 3 个工具：echo / search / write_file。

| 模式 | `获取可见工具` 结果 | SDK |
|---|---|---|
| native | `[echo, search, write_file]` | —（不适用） |
| ptc | `[run_code]`（schema 携带 parameters） | `生成工具SDK` 文本含 echo/search/write_file，3 条目 |
| both | `[echo, search, write_file, run_code]` | 同上 |

三模式差异明确、与任务书预期逐字一致；ptc 的唯一真工具 `run_code` 对齐上游 `RUN_CODE_NAME`。

## 三、代理循环联动（任务书 3.3，OK #10）

- 两个作用域经任务1 的零修改适配层 `造代理工具展示` 各得一个 `工具展示注册表代理`：coded（ptc，传 `新建 代码运行时(5)`）与 plain（native）。
- **真实状态机**：`建循环(3)` → `开始轮次` → `开始步骤(驱动, "llm")`（llm ∈ `步骤型表`）→ 步骤内取各代理 `描述表()`：coded 见 `[run_code]`、plain 见全量——**同一循环、同一注册表，不同作用域看到不同工具列表**，作用域隔离贯穿循环。
- **host-plane 不变语义**：代理 `名单()/有无()/执行策略()` 原样委托（注册表本体未过滤，只有展示层过滤）；`结束步骤/结束轮次` 后轮次终态正常。
- **卸载贯穿**：coded 注销后其代理 `描述表()` 回全量（HMR 安全在循环场景成立）。

## 四、执行说明

- 任务3 启动时任务1 尚未交付：先完成上游 spec 精读（8 契约）与任务4 反跑脚本/基线准备，轮询至任务1 交付后按**真实接口**编写本测试（含任务1 的 `工具展示注册表代理` 适配层），非按任务书建议签名盲写。
- 断言助手：`从 测试 导入 断言相等, 断言真`（stdlib，与 test_R34_集成测试 同惯例）；另带 #00 自检组（助手必须真能报错）。
- 全程不依赖真实大模型 API：工具执行函数传空（不调用），代码运行时仅作存在性判定（对齐上游 StubRuntime "presentation never dispatches"）。

## 五、结果与移交

- `python 运行.py examples/test_R38_集成测试.light` → **rc=0，11 组全绿**（#00 自检 + 8 用例映射 + 三模式对比 + 联动）。
- 移交任务4：本文件纳入全量回归与反跑语料；`从 工具展示 导入` 的引用方即本文件与 `test_R38_工具展示.light`（任务1 单元测试），无其他引用。
- 移交任务5：三模式过滤均为纯列表操作，性能差异预期可忽略（联动评估归任务5，本报告不重复）。
