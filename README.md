# lightharness —— 用光明复刻 DeepSeek Harness

**用「光明」中文编程语言 1:1 复刻 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)（agent 智能体框架）。**

复刻的目的不是照抄代码，而是**在实践中检验光明这门语言**：把原版框架的每一个核心子系统用光明重新实现一遍，凡是"写不出来、写出来是错的、绕不过去"的地方，就是光明需要改进的清单。每发现一处，登记进语言缺陷账，交给光明开发团队。

## 项目定位

- **对标对象**：DeepSeek Harness（`g:\github\deepseek-harness`，TypeScript monorepo，Cordis 插件驱动，50 个 packages + 2 个 apps）
- **复刻语言**：光明（LightLang，`G:\dswork\duan-light-merge\light-merge`）
- **工作目录**：`G:\dswork\duan-light-merge\lightharness`（本工程）
- **复刻口径**：功能等价 1:1 —— 每个模块建一张功能对标卡（原版功能 → 光明实现 → 对齐度 done/partial/none + 证据 + 反跑判据）

## 范围（第一版：P0 全 + P1 部分）

| 层 | 模块 | 原版包 | 状态 |
|----|------|--------|------|
| **P0 核心运行时** | session 会话（append-only 事件日志 + JSONL 持久化） | `core/session` + `session/session-persistence-jsonl` | 待实现 |
| | llm 流式客户端（deepseek 适配器） | `llm/llm` + `llm/llm-deepseek` | 待实现 |
| | agent-loop 多轮循环（turn/step 流程） | `core/agent` + `core/agent-loop` | 待实现 |
| | tools 工具系统（注册/校验/执行） | `core/tools` | 待实现 |
| | context 上下文压缩（compaction） | `compaction/compaction` | 待实现 |
| | hooks 事件/插件机制 | `core/hooks` + `hook-protocol` | 待实现 |
| | cli 命令行入口 | `apps/cli` | 待实现 |
| **P1 运行层** | subprocess / terminal / shell 进程执行 | `sandbox` `subprocess` `terminal` `shell` | 待实现 |
| | sandbox 沙箱边界 | `sandbox` | 待实现 |
| | fs / storage 文件与存储 | `fs` `storage` | 待实现 |

P2 生态层（mcp 客户端、subagent、code-runtime、e2b、遥测、Web UI）押后。

## 目录结构

```
lightharness/
├── 运行.py                 # 运行器：自包含 stdlib + 光明编译器
├── stdlib/                 # 自包含标准库（复制自 light-merge，含 .light + .py）
├── src/                    # lightharness 光明源码（扁平布局，P0+P1）
│   ├── 总入口.light        # CLI 入口
│   ├── 会话/消息/事件       # 会话.light(事件日志)、消息.light、事件.light(事件总线)
│   ├── 代理/异步代理/中止   # agent-loop：代理.light(同步)+异步代理.light(异步)+中止.light
│   ├── 客户端.light        # llm 流式客户端（deepseek 适配器）
│   ├── 工具/钩子/压缩       # 工具.light(注册/校验/执行)、钩子.light、压缩.light(上下文)
│   ├── 持久化/存储/文件     # JSONL 持久化 + 存储/文件（P1）
│   └── 运行层/             # 子进程/沙箱/终端/流/重试策略（P1）
├── 工具集/                 # 内置工具（fs/bash/...）
├── docs/
│   ├── 架构设计.md          # 光明版架构蓝图
│   └── 功能对标/           # 每模块功能对标卡
├── tests/                  # 测试（含反跑判据）
└── examples/               # 运行示例
```

## 运行方式

```bash
cd G:\dsword\duan-light-merge\lightharness
python 运行.py examples/冒烟.light        # 自包含 stdlib 冒烟测试
python 运行.py src/总入口.light           # CLI 入口
```

## 语言缺陷反馈流程

复刻中发现光明"写不出 / 写错 / 绕不过"的地方：

1. 在对应模块的功能对标卡「语言缺陷」字段登记：现象 + 最小复现 + 期望能力
2. 汇总到 `docs/功能对标/语言缺陷账.md`
3. 移交光明开发团队（A9 泳道）修复

## 对齐进度

见 `docs/功能对标/对标清单.json`。当前进度以文件内状态为准。

## 回归门禁

`python -m pytest tests/` 跑全量 examples 用例（含缺陷复现套件），任一带退出码断言
失败即红；反跑判据见 `docs/功能对标/反跑判据.md`。
