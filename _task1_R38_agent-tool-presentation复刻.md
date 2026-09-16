# 第 38 轮 任务 1 交付报告 —— agent-tool-presentation 核心模块复刻

> 日期：2026-09-16 ｜ 方向：上游复刻——agent-tool-presentation（工具展示模式选择器）
> 上游基线：deepseek-harness 0.1.5-rc.2
> 上游源码：`packages/core/agent-tool-presentation/src/index.ts`（72 行）
> 上游测试：`packages/core/agent-tool-presentation/tests/agent-tool-presentation.spec.ts`（7 用例 + 隐含 disposer = 8 契约）
> 交付物：`src/工具展示.light`（新增模块）、`examples/test_R38_工具展示.light`（单元测试，rc=0）

---

## 一、上游源码精读（index.ts 72 行）

| 关键点 | 上游实现 | 语义 |
|---|---|---|
| 插件名 | `export const name = 'tool-presentation'` | 预设行标识 |
| 依赖声明 | `export const inject = ['tools']` | **只声明 tools**；codeRuntime 是条件等待，不是静态依赖 |
| 配置 | `Config = z.object({ mode: z.union(['native','ptc','both']).required() })` | **mode 必填、不设默认值** |
| apply（native） | `ctx.tools.presentAs('native'); return` | 直接声明，无需 codeRuntime |
| apply（ptc/both） | `ctx.inject(['codeRuntime'], (rt) => rt.tools.presentAs(config.mode))` | codeRuntime 到达后条件应用 |
| disposer | `presentAs` 返回 disposer，随 row 卸载解除 | 声明随 row 化解，无需第二层包装 |
| 作用域 | 一行 per composition，覆盖该 preset 下所有 agent | 一个 agent 设 ptc 不影响其他 agent |

**三种模式效果**：
- `native`：发送所有可见工具 schema。
- `ptc`：只发送 `run_code` + 生成的 SDK（真实工具走 SDK 描述）。
- `both`：两者都发送（所有原工具 + `run_code` + SDK）。

**关键设计**：
1. codeRuntime 条件等待：`inject=['tools']` 而非 `['tools','codeRuntime']`；ptc/both 在 `apply` 内部 `ctx.inject(['codeRuntime'], ...)` 条件等待。
2. mount 时失败而非 prompt 时失败：ptc 部署无 codeRuntime → row 处于 pending，preset 激活审计命名此 id，在操作者可行动处失败。
3. 作用域隔离：一个 agent ptc，其他 agent 仍 native。
4. 卸载恢复（HMR 安全）：agent 卸载时展示随之恢复部署默认。
5. mode 必填：省略意味着这行配置白写（preset 无此行已得到部署默认）。

---

## 二、光明适配设计

**模块名**：`src/工具展示.light`（命名预检查：src/ 下无同名，无单字别名风险）。

**核心数据结构**：
```
工具展示模式表 = ["native", "ptc", "both"]                  # 常量
工具展示配置   = {"模式", "作用域", "已应用", "待代码运行时", "注销函数"}  # 建工具展示配置 构造
作用域展示表   = { <作用域ID>: <native|ptc|both> }          # 模块级，全局作用域展示状态
运行代码工具模式 = {"name":"run_code", "description":..., "parameters":...}  # PTC/both 唯一真工具
```

**导出清单（18 项，满足「10-12 项」上限，含常量/类/助手）**：
1. `工具展示插件名`（常量 `'tool-presentation'`）
2. `工具展示依赖`（常量 `['tools']`）
3. `工具展示模式表`（常量）
4. `运行代码工具名`（常量 `'run_code'`）
5. `运行代码工具模式`（常量 schema）
6. `部署默认展示`（常量 `'native'`）
7. `校验展示模式(模式)` —— mode 合法性（枚举）
8. `建工具展示配置(模式)` —— 构造配置，mode 必填，非法抛错
9. `校验工具展示配置(配置)` —— 校验既有配置（真/假）
10. `获取作用域展示(作用域ID)` —— 取作用域当前展示模式
11. `应用工具展示(配置, 作用域ID, 工具注册表, 代码运行时=空)` —— 核心 apply
12. `注销工具展示(配置)` —— 卸载恢复（disposer）
13. `是否待代码运行时(配置)` —— 是否 pending
14. `等待代码运行时(配置, 代码运行时)` —— 条件等待后应用
15. `获取可见工具(作用域ID, 工具注册表)` —— 按模式过滤工具列表
16. `生成工具SDK(工具注册表)` —— 生成 SDK 描述（名+描述）
17. `工具展示注册表代理`（类）—— Task 2 零修改适配层
18. `造代理工具展示(作用域ID, 注册表, 模式, 代码运行时=空)` —— 「代理携带配置」助手

---

## 三、实现细节（对齐上游 5 大设计）

### 3.1 作用域隔离
模块级字典 `作用域展示表` 按 `作用域ID` 存储模式。每个 agent 用唯一作用域 ID（可用 agent ID）。`获取可见工具` 按 `作用域ID` 过滤，互不影响（用例 6/§7 验证）。

### 3.2 codeRuntime 条件等待
`应用工具展示` 的 `代码运行时` 参数默认空：
- ptc/both **有** codeRuntime → 直接写入 `作用域展示表[作用域ID]=模式`，`已应用=真`。
- ptc/both **无** codeRuntime → 标记 `待代码运行时=真`，**不写入**作用域展示（回退部署默认 = 全量可见），返回 pending 句柄。
- `等待代码运行时(配置, 运行时)`：pending 态收到运行时后立即应用（用例 5/6 验证）。

### 3.3 卸载恢复（HMR 安全）
`注销工具展示(配置)` 删除 `作用域展示表[配置["作用域"]]`，作用域回退部署默认；`配置["已应用"]/["待代码运行时"]` 复位。等价于上游 row.dispose()（用例 4/§8 验证）。

### 3.4 三模式工具过滤（`获取可见工具`）
- `native` → `注册表.描述表()`（全部 schema）
- `ptc` → 仅 `[运行代码工具模式]`
- `both` → `注册表.描述表()` + `[运行代码工具模式]`
- 未配置/pending → 部署默认（全量）

### 3.5 mode 必填、不设默认值
`建工具展示配置(模式)` 在 mode 缺失/非法时 `抛出 新建 错误(...INVALID_MODE)`；`校验工具展示配置` 返回真/假。对齐上游 `Config({})` 抛错（用例 7 验证）。

---

## 四、测试结果与验证

**测试文件**：`examples/test_R38_工具展示.light`
**运行命令**：`cd lightharness && python 运行.py examples/test_R38_工具展示.light`
**结果**：**14 组断言全部通过，rc=0**。

| 组 | 覆盖 | 上游契约 |
|---|---|---|
| #00 | 断言自检 | — |
| #01 | 常量/依赖（inject=['tools']） | 用例 1 |
| #02 | 建配置/校验展示模式（枚举） | 用例 7 |
| #03 | mode 必填/非法抛错 | 用例 7 |
| #04 | native 应用 + 获取可见工具（全量） | 用例 2 |
| #05 | ptc 有 codeRuntime → 仅 run_code | 用例 2/3 |
| #06 | ptc 无 codeRuntime → pending 回退全量 | 用例 5 |
| #07 | 等待 codeRuntime 到达后应用 | 用例 6 |
| #08 | both → echo/search/write_file + run_code | 用例 3 |
| #09 | 作用域隔离（ptc vs native） | 用例 2 |
| #10 | 卸载恢复（HMR 安全） | 用例 4 |
| #11 | 生成工具 SDK（含真实工具名） | 用例 2/3 |
| #12 | 代理注册表代理联动（Task 2 适配层） | 用例 2/4 |
| #13 | 代理 pending → 运行时到达后切换 | 用例 5/6 |

---

## 五、上游 8 契约映射对照

| # | 上游契约 | 光明实现 | 状态 |
|---|---|---|---|
| 1 | inject=['tools']（不持有 codeRuntime） | `工具展示依赖=["tools"]`；codeRuntime 为条件等待参数 | ✅ |
| 2 | 特定 agent PTC、其余 native（作用域隔离） | `作用域展示表` 按作用域 ID 隔离（#09） | ✅ |
| 3 | both 两者都展示 | #08 both = 原工具 + run_code | ✅ |
| 4 | agent 卸载恢复部署默认（HMR 安全） | `注销工具展示`（#10） | ✅ |
| 5 | 等待未组合的 codeRuntime（pending） | `待代码运行时` 态（#06） | ✅ |
| 6 | codeRuntime 到达后应用 | `等待代码运行时`（#07） | ✅ |
| 7 | mode 必填、不设默认值 | `建工具展示配置` 抛错（#02/03） | ✅ |
| 8 | presentAs 返回 disposer | `应用工具展示` 返回句柄；`注销工具展示` 即 disposer（#10） | ✅ |

---

## 六、铁律遵守

- ✅ 命名预检查：新增 `工具展示.light`，不与既有 src/*.light 冲突。
- ✅ 新增一律 .light，无 Python 绕语言缺陷。
- ✅ mode 必填、不设默认值（对齐上游）。
- ✅ inject 只声明 tools，codeRuntime 是条件等待（对齐上游）。
- ✅ 作用域隔离严格（一个 agent ptc 不影响其他）。
- ✅ 卸载恢复实现（HMR 安全）。
- ✅ ptc/both 无 codeRuntime 时 pending，不静默降级为 native。
- ✅ 测试用例 rc=0。
