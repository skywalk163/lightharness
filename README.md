# lightharness —— 用光明复刻 DeepSeek Harness

**用「光明」中文编程语言 1:1 复刻 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)（agent 智能体框架）。**

复刻的目的不是照抄代码，而是**在实践中检验光明这门语言**：把原版框架的每一个核心子系统用光明重新实现一遍，凡是"写不出来、写出来是错的、绕不过去"的地方，就是光明需要改进的清单。每发现一处，登记进语言缺陷账，交给光明开发团队。

## 项目定位

- **对标对象**：DeepSeek Harness（`g:\github\deepseek-harness`，TypeScript monorepo，Cordis 插件驱动，50 个 packages + 2 个 apps）
- **复刻语言**：光明（LightLang，`G:\dswork\duan-light-merge\light-merge`）
- **工作目录**：`G:\dswork\duan-light-merge\lightharness`（本工程）
- **复刻口径**：功能等价 1:1 —— 每个模块建一张功能对标卡（原版功能 → 光明实现 → 对齐度 done/partial/none + 证据 + 反跑判据）

## 范围与进度

复刻范围覆盖 deepseek-harness 全部可提取纯逻辑的模块，以**功能对标卡**为唯一粒度。不再使用 P0/P1/P2 分层——早期规划表已随模块逐一落地而失效，当前进度以 `docs/功能对标/对标清单.json` 为准。截至目前：

- **功能对标卡 #1–#70 共 70 张**，全部 `done`。
- 已落地区域包括：core/session/llm/agent-loop/tools/compaction/hooks、运行层（subprocess/terminal/shell/sandbox）、生态（mcp/审批/subagent/遥测/代码运行时/e2b）、管理（工作区/存储域/路径规则/安全策略/类型注册）、扩展（语言服务器/推理工具）、多智能体团队（agent-team：依赖图/看板/折叠/花名册/服务/日志）。
- Web UI / Cordis 插件宿主耦合层 纯逻辑价值低，不再扩展。

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
│   ├── 工具/钩子/压缩       # 工具.light(注册/校验/执行)、钩子.light、压缩.light(上下文/v2自动触发:token计量+step前检查)
│   ├── 持久化/存储/文件     # JSONL 持久化 + 存储/文件（P1）
│   └── 运行层/             # 子进程/沙箱/终端(管道+PTY)/流/重试策略（P1）
├── 工具集/                 # 内置工具（fs/bash/...）
├── docs/
│   ├── 架构设计.md          # 光明版架构蓝图
│   └── 功能对标/           # 每模块功能对标卡
├── tests/                  # 测试（含反跑判据）
└── examples/               # 运行示例
```

## 运行方式

```bash
cd G:\dswork\duan-light-merge\lightharness
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

- 功能对标卡 **#1–#70 共 70 张**，全部 `done`。
- 外发任务 A–N（对标 #51–#64）14 个纯逻辑核心已合并推送。
- 外发任务 O–S 及并行修复 R2/补强 S2（对标 #65–#70，agent-team 多智能体团队纯逻辑）已合并推送；其中 #69 已同步 deepseek-harness v0.1.2 升级新增的视图/变更结果/部署上限/远端路由纯逻辑。
- 回归门禁 `python -m pytest tests/`：178 passed 全绿。
- 批次交付报告：`_任务A-N_对标51-64_交付报告.md`、`_任务O-S_对标65-70_交付报告.md`。

## 回归门禁

`python -m pytest tests/` 跑全量 examples 用例（含缺陷复现套件），任一带退出码断言
失败即红；反跑判据见 `docs/功能对标/反跑判据.md`。

`python 运行.py examples/test_终端PTY.light` 单独验证终端 PTY（真 tty，需 Win10 1809+）。
