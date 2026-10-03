# lightharness · 用光明复刻 DeepSeek Harness

> 版本：**v0.4.0-rc2**（与光明语言同家族，2026-10-03 R110 收口后维持）
> 状态：功能对标卡 **#1–#313 编号范围**（实存 307 条条目，含 6 处刻意跳号；截至 R108，R110 零新增），Web 服务与 CLI 已集成交付
> 一句话定位：**用「光明」这门自研中文语言，1:1 复刻 DeepSeek Harness 的 agent 智能体框架——复刻不是目的，检验光明这门语言才是目的。**

---

## 一、它是什么

`lightharness` 用「光明」（LightLang）重新实现 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)（agent 智能体框架），**功能等价 1:1**。

**复刻口径**：每个模块建一张**功能对标卡**——原版功能 → 光明实现 → 对齐度（done/partial/none）→ 证据 → 反跑判据。凡"写不出、写错、绕不过去"的地方，就是光明这门语言需要改进的清单，逐条登记到 `docs/功能对标/语言缺陷账.md`，再回喂光明语言本体（A9 泳道）。

**为什么做这件事**：用**真实大型工程**检验一门自研语言——比写 demo、跑 benchmark 更能暴露语言设计的真问题。

---

## 二、快速上手（5 分钟）

### 1. 启动 Web 服务

```bash
cd lightharness
python 运行.py examples/运行Web服务器.light
```

服务启动后**自动打开浏览器**，地址形如：

```
http://127.0.0.1:54321/?token=xxxxxxxxxxxxxxxx
```

> 首次启动默认 **mock 模式**（无需 API Key，内置模拟模型回复），可直接体验界面与流式对话。

### 2. 配置真实大模型

首次打开页面会自动弹出配置面板，填三项：

| 字段 | 示例 | 说明 |
|---|---|---|
| API Key | `sk-xxxxxxxx` | 大模型服务商密钥 |
| Base URL | `https://api.deepseek.com` | API 端点（自动拼接 `/chat/completions`） |
| 模型名 | `deepseek-chat` | 模型名称 |

点「保存并连接」后**立即热更新**，无需重启服务。也可手工编辑 `.env`：

```env
OPENAI_API_KEY=sk-xxxxxxxx
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
```

支持任何 OpenAI 兼容接口：DeepSeek、智谱、通义、Ollama（`http://localhost:11434/v1`）等。

### 3. 命令行

```bash
python 运行.py examples/冒烟.light       # 冒烟测试（验证环境）
python 运行.py examples/运行CLI.light    # CLI 交互模式
python 运行.py examples/运行Web服务器.light  # Web 服务（自动开浏览器）
```

---

## 三、项目定位与范围

| 项 | 值 |
|---|---|
| 对标对象 | DeepSeek Harness（`g:\github\deepseek-harness`，TypeScript monorepo，Cordis 插件驱动，50 packages + 2 apps） |
| 复刻语言 | 光明（`light-merge`） |
| 工作目录 | `lightharness/` |
| 对标粒度 | 每模块一张功能对标卡（#1 → #313） |

---

## 四、复刻进度

| 阶段 | 内容 | 状态 |
|---|---|---|
| **功能对标卡 #1–#70** | 全部 `done`（README 权威口径） | ✅ |
| **对标清单编号范围** | **#1–#313**（实存 307 条条目，含 6 处刻意跳号） | ✅ |
| **已落地区域** | core / session / llm / agent-loop / tools / compaction / hooks | ✅ |
| **运行层** | subprocess / terminal / shell / sandbox | ✅ |
| **生态** | mcp / 审批 / subagent / 遥测 / 代码运行时 / e2b | ✅ |
| **管理** | 工作区 / 存储域 / 路径规则 / 安全策略 / 类型注册 | ✅ |
| **扩展** | 语言服务器 / 推理工具 | ✅ |
| **多智能体团队** | agent-team：依赖图 / 看板 / 折叠 / 花名册 / 服务 / 日志 | ✅ |
| **Web UI** | 前端界面 + 登录认证 + 静态路由 + 一键启动开浏览器 + 大模型配置引导（网页面板 + `.env` 手工编辑 + 热更新） | ✅ |
| **对标清单.json 末位** | **#313**（R108 F 线：侧栏插件面板只读面） | ✅ |
| **R110（0.2.0-rc.2 对齐）** | 187 commits / 1022 真增量文件甄别，纯逻辑面待移植 4 组，本轮回基线修正 | ✅ |

### 近期外发任务

- **外发任务 A–N**（对标 #51–#64）：14 个纯逻辑核心已合并推送。
- **外发任务 O–S + 并行修复 R2 / 补强 S2**（对标 #65–#70，agent-team 多智能体团队纯逻辑）：已合并推送；#69 已同步上游 v0.1.2 升级新增的视图 / 变更结果 / 部署上限 / 远端路由纯逻辑。

### Web 启动四路

- W1 前端 / W2 认证 / W3 服务端 / W4 启动器 已集成交付，集成验收 **12 项 curl + 5 项浏览器全过**。

---

## 五、门禁与质量（硬基线）

### 全量回归

```bash
python -m pytest tests/test_回归.py   # 约 1400 用例
python -m pytest tests/               # 全量（pytest.ini 默认 --timeout=60 -n auto）
```

- **R87 三平台实测**：Windows / FreeBSD 0.82 / 0.86 Linux 全量 **≈1400 用例 0 失败**。
- **R110 本机 Windows 全量**：**2074 用例 / 0 failed / 0 error / 0 new_red**（`reports/R110_lh_windows_latest.json`）。
- 计数基线：以 `tests/ci_environment_reds.txt` 台账为权威，按「新增红」判据（本轮失败 − 基线失败）。

### O0 测试（光明编译器 C 后端）

- 部分用例依赖光明 O0（优化级别 0）C 后端，需本地 LLVM/clang 或 `zig`（推荐，单文件自带 libc 头文件）。
- gitea CI（192.168.1.5）已预装 LLVM 工具链，O0 用例在 CI 全量执行；本地未装时相关用例跳过或失败，不影响 Python 层全量回归。

### 回归门禁纪律

- **0.82 FreeBSD 门禁机**：`192.168.1.5`（家庭实验室），跑 `.gitea/workflows/ci.yml` 权威 CI。
- **反跑判据**：见 `docs/功能对标/反跑判据.md`，零 `/tmp`、单点破坏-还原、防假绿（"非法输入被放行"类变异务必实测 RED）。

---

## 六、语言缺陷反馈机制

复刻中发现光明"写不出 / 写错 / 绕不过"的地方：

1. 在对应模块功能对标卡的「语言缺陷」字段登记：现象 + 最小复现 + 期望能力。
2. 汇总到 `docs/功能对标/语言缺陷账.md`（编号续 L-066 之后）。
3. 移交光明开发团队（A9 泳道）修复。

**这本身就是 lightharness 的核心价值：它是光明语言的"实战试金石"。**

---

## 七、近期收口亮点

### R109（2026-10-01）：债清收口轮

- 闭合 4 条历史账：`_light_re` import hook（LH 最大红源，0 改动销账）/ 挂载集对话内切换接入总入口 / 临时脚本清理 / 地板门禁接 CI。
- 全量回归 **1171 passed / 1 skipped / EXITCODE=0**，引入 0 红。
- lightharness 三远端已推（gitea / gitcode / github）。

### R110（2026-10-03）：上游 0.2.0-rc.2 增量对齐

- 真增量 **187 commits / 1022 文件 / +33253 / -6141**（三点基准 `rc.1...rc.2`，merge-base `4878cdabd8`）。
- **B 路核实为 0 移植**：4 组候选（schedule framing / user-questions 状态机 / tool-ask-user timed / shell 提示词文案）在 lightharness 无对应纯逻辑层承载，按"暂缓"登记。
- **C 路**：宿主面登记清单 44 → **59** 条（+15，Windows ACL 修复链 / web-desktop UI / whale perf / Cordis inspect / desktop installer / llm pi-ai 升级 / CI 等）。
- **D 路**：上游 rc.2 无 freebsd/ 目录，fork 侧零改动 → **零同步**。
- **E 路**：Windows 双全量 0 新增红；0.86 / 0.82 基线 JSON 列为遗留（逻辑上无新红风险）。
- **版本维持 v0.4.0-rc2 不动**（纯逻辑面 0 文件 < 10）。

---

## 八、目录结构

```
lightharness/
├── 运行.py                 # 运行器：自包含 stdlib + 光明编译器
├── .env.example            # 大模型配置模板
├── stdlib/                 # 自包含标准库（复制自 light-merge，含 .light + .py）
├── src/                    # lightharness 光明源码
│   ├── 总入口.light        # CLI 模块
│   ├── web服务器.light     # Web 服务端（路由/认证/SSE/配置 API）
│   ├── 会话/消息/事件       # 事件日志 / 消息 / 事件总线
│   ├── 代理/异步代理/中止   # agent-loop 同步 + 异步 + 中止
│   ├── 客户端.light        # llm 流式客户端（OpenAI 兼容适配器）
│   ├── 认证.light          # 登录认证（令牌签发/校验）
│   ├── 工具/钩子/压缩       # 注册/校验/执行 / 钩子 / 压缩
│   ├── 持久化/存储/文件     # JSONL 持久化 + 存储/文件
│   └── 运行层/             # 子进程/沙箱/终端(管道+PTY)/流/重试策略
├── webui/                  # 前端静态文件（index.html / app.js / style.css）
├── 工具集/                 # 内置工具（fs/bash/...）
├── docs/                   # 架构设计 / 功能对标 / 宿主面登记 / 多平台差异清单
├── tests/                  # 测试（含反跑判据）
├── freebsd/                # FreeBSD 门禁机脚本（jail / rcd / verify-sandbox）
└── examples/               # 运行示例
```

---

## 九、许可证与社区

- **许可证**：[MIT](LICENSE)
- **贡献**：[CONTRIBUTING.md](CONTRIBUTING.md) —— 本地环境、跑测试、`.light` 书写规范、提交规范与三条工程铁律
- **变更记录**：[CHANGELOG.md](CHANGELOG.md)（Keep a Changelog 格式）
- **行为准则**：[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- **安全漏洞**：[SECURITY.md](SECURITY.md) —— 请走私密渠道，勿公开 Issue 披露
- **远端布局**：内网 gitea（192.168.1.5，主仓）→ GitHub → GitCode 三远端同步

---

## 十、下一步

1. **R111 轮**：上游 0.2.0-rc.2 的 4 组候选移植项——待 lightharness 对应纯逻辑层补齐后回移植（schedule framing / user-questions / tool-ask-user timed / shell 提示词）。
2. **0.86 Linux / 0.82 FreeBSD 基线 JSON** 补生成（R110 遗留）。
3. **版本 bump**：随纯逻辑面实际改动量决定是否从 v0.4.0-rc2 走 patch。
4. **语言缺陷账回喂**：把 lightharness 复刻中登记的缺陷，持续回喂光明语言本体迭代。

---

## 十一、数据真实性声明

本文所有数字（对标卡数、用例数、commit/文件数、版本号、门禁基线）均取自本仓库内权威文档：

- `lightharness/README.md`、`lightharness/CHANGELOG.md`
- `lightharness/docs/功能对标/R110_交付报告.md`、`R110_任务分发书_上游0.2.0-rc.2对齐.md`
- `lightharness/docs/宿主面登记清单.md`、`docs/多平台差异清单.md`
- `lightharness/reports/R110_lh_windows_latest.json`
- `R109_交付报告.md`（工作区根）

未引用任何联网推测；如与本仓最新 `git log` / `reports/` 基线 JSON 不一致，以仓内数据为准。