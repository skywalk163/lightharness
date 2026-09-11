# 任务1 交付报告：代理循环行为对照

## 任务概述

- **轮次**: 第8轮
- **任务**: Task 1 — 代理循环行为对照
- **分支**: `task-8-agentloop`
- **工作树**: `wt-R8T1`
- **基线**: main HEAD `547ad56`

## 交付物

| 文件 | 说明 |
|------|------|
| `examples/test_行为对照_代理循环.light` | 行为对照测试文件 (20 节, S1–S20) |
| `_antirun_agentloop_contrast.py` | 反跑判据脚本 (4 变异项, 字节级备份/还原) |
| `_task1_代理循环对照_交付报告.md` | 本交付报告 |

## 上游 spec 文件对照

共读取 13 个上游 spec 文件，提取可断言纯逻辑场景，对照已有光明测试，翻译为 20 节测试：

| 节 | 对标 spec | 场景 | 已有测试覆盖? |
|----|-----------|------|---------------|
| S1 | cancel.spec.ts | Cancel primitive 终止/是已终止 | 否 |
| S2 | cancel.spec.ts | 中断结算非空 → assistant/message 中断=真 | 否 |
| S3 | cancel.spec.ts | 中断结算空 → assistant/attempt | 否 |
| S4 | cancel.spec.ts | 预终止驱动 → aborted | 否 |
| S5 | loop.spec.ts | max-tokens 终止 | 否 |
| S6 | loop.spec.ts | max-tokens 丢弃工具调用 | 否 |
| S7 | loop.spec.ts | max-tokens 不跨轮泄漏 | 否 |
| S8 | loop.spec.ts | 客户端异常 → error | 否 |
| S9 | loop.spec.ts | 错误完成原因 → error | 否 |
| S10 | loop.spec.ts | 请求配置 | 否 |
| S11 | loop.spec.ts | 读后置提示能力 | 否 |
| S12 | loop.spec.ts | 渲染系统提示 | 否 |
| S13 | loop.spec.ts | 工具模式变化检测 | 否 |
| S14 | loop.spec.ts | 请求面世代变化 | 否 |
| S15 | loop.spec.ts | 溢出错误检测 | 否 |
| S16 | tool-calls.spec.ts | 并行工具执行 | 部分 (test_agent工具调用) |
| S17 | tool-calls.spec.ts | 独占工具屏障 | 否 |
| S18 | loop.spec.ts | 轮次事件序列 | 否 |
| S19 | tool-calls.spec.ts | 并发上限默认值 | 否 |
| S20 | request-error.spec.ts | 客户端异常错误结构 | 否 |

## 已有光明测试对照

| 已有测试文件 | 覆盖场景 |
|-------------|---------|
| `test_代理系统提示.light` | SystemPromptProjection 折叠 + 请求头准入 |
| `test_代理深化.light` | 代理循环 v2 深化 (工具调用端到端, max-steps) |
| `test_agent工具调用.light` | 工具调用端到端 |

## 未覆盖场景说明

以下上游场景因光明语言当前实现限制无法直接对照：

1. **concludesTurn** (tool-calls.spec.ts): `工具注册表.执行` 方法始终将 `concludesTurn` 设为 `假`，不传播工具函数返回值中的 `concludesTurn` 字段。S18 改为测试轮次事件序列。
2. **mid-stream cancellation** (cancel.spec.ts): 需要流式块级中断能力，当前光明测试框架不支持。
3. **resume/crash repair** (resume.spec.ts): 需要物理层撕裂模拟，超出纯逻辑对照范围。
4. **scope lifecycle** (scope-lifecycle.spec.ts): 需要并发 scope 创建/销毁，当前光明运行时无并发原语。
5. **steering/inject** (loop.spec.ts): 需要异步 inject() 在工具执行期间注入，当前光明驱动为同步。

## 测试结果

### 直接测试

```
S1通过：cancel primitive 终止/是已终止
S2通过：中断结算非空内容 → assistant/message 中断=真
S3通过：中断结算空内容 → assistant/attempt
S4通过：预终止驱动 → aborted
S5通过：max-tokens 终止
S6通过：max-tokens 丢弃工具调用
S7通过：max-tokens 不跨轮泄漏
S8通过：客户端异常 → error
S9通过：错误完成原因 → error
S10通过：请求配置
S11通过：读后置提示能力
S12通过：渲染系统提示
S13通过：工具模式变化检测
S14通过：请求面世代变化
S15通过：溢出错误检测
S16通过：并行工具执行
S17通过：独占工具屏障
S18通过：轮次事件序列
S19通过：并发上限默认值
S20通过：客户端异常错误结构
--- 代理循环行为对照测试全部通过 ---
```

**结果: 20/20 通过**

### 反跑判据

```
反跑判据: 代理循环行为对照
变异项数: 4

  [1] RED (rc=1) — S5: max-tokens 种类断言 max-tokens → completed
  [2] RED (rc=1) — S8: 客户端异常种类断言 error → completed
  [3] RED (rc=1) — S16: 并行工具调用数 2 → 99
  [4] RED (rc=1) — S18: 轮次开始事件数 1 → 99

结果: ALL RED — 反跑判据通过
```

**结果: 4/4 ALL RED**

## 约束遵守

- [x] `src/` 只读 — 未修改任何 src 文件
- [x] 新测试文件位于 `examples/` 目录
- [x] 多节结构，每节标注对标 spec 文件名
- [x] 未使用 Python 绕过语言缺陷 (除 antirun 脚本)
- [x] 反跑判据 ≥ 2 项 (实际 4 项)
- [x] 字节级备份/还原测试文件本身
