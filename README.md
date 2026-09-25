# lightharness —— 用光明复刻 DeepSeek Harness

**用「光明」中文编程语言 1:1 复刻 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)（agent 智能体框架）。**

复刻的目的不是照抄代码，而是**在实践中检验光明这门语言**：把原版框架的每一个核心子系统用光明重新实现一遍，凡是"写不出来、写出来是错的、绕不过去"的地方，就是光明需要改进的清单。

---

## 快速上手（5 分钟）

### 1. 启动 Web 服务

```bash
cd G:\dswork\duan-light-merge\lightharness
python 运行.py examples/运行Web服务器.light
```

服务启动后会**自动打开浏览器**，地址类似：

```
http://127.0.0.1:54321/?token=xxxxxxxxxxxxxxxx
```

> 首次启动默认是 **mock 模式**（不需要 API Key，用内置模拟模型回复），可以直接体验界面和流式对话。

### 2. 配置真实大模型

首次打开页面（mock 模式或未配置时）会**自动弹出配置面板**，填入三项：

| 字段 | 示例 | 说明 |
|------|------|------|
| API Key | `sk-xxxxxxxx` | 大模型服务商的密钥 |
| Base URL | `https://api.deepseek.com` | API 端点（不需要加 `/chat/completions`，自动拼接） |
| 模型名 | `deepseek-chat` | 模型名称 |

点「保存并连接」后**立即热更新**，无需重启服务。

也可以**手工编辑 `.env`** 文件（参考 `.env.example` 模板）：

```env
OPENAI_API_KEY=sk-xxxxxxxx
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
```

支持任何 OpenAI 兼容接口：DeepSeek、智谱（`https://open.bigmodel.cn/api/paas/v4`）、通义、Ollama（`http://localhost:11434/v1`）等。

### 3. 开始聊天

在输入框输入消息，按 Enter 发送，agent 会**逐字流式回复**。支持多轮对话、停止生成、设置按钮随时重新配置模型。

---

## 命令行使用

```bash
# 冒烟测试（验证环境）
python 运行.py examples/冒烟.light

# CLI 交互模式
python 运行.py examples/运行CLI.light

# Web 服务（自动开浏览器）
python 运行.py examples/运行Web服务器.light
```

## 环境变量

启动 Web 服务时可用以下环境变量控制行为：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `HARNESS_WEB_MOCK` | 自动检测 | `1`=强制 mock（无需密钥）；缺省自动检测：`.env`/环境变量能读出大模型密钥则真实模式（不弹配置页），读不出则以 mock 占位启动并在页面自动弹出配置引导 |
| `HARNESS_WEB_TOKEN` | 自动生成 | 登录令牌（URL 里的 `?token=`） |
| `HARNESS_WEB_NO_OPEN` | 未设置 | 设置为 `1` 则不自动打开浏览器 |
| `HARNESS_WEB_LIFETIME` | — | 令牌有效期（秒） |
| `HARNESS_WEB_UI_DIR` | `webui/` | 前端静态文件目录 |
| `HARNESS_WEB_CORS` | 开 | CORS 跨域（默认 `Access-Control-Allow-Origin: *`） |
| `HARNESS_PORT_FILE` | — | 端口写入文件（供脚本读取） |
| `HARNESS_API_KEY` | — | 大模型密钥（优先级高于 `.env`） |
| `HARNESS_ENDPOINT` | — | API 端点（优先级高于 `.env`） |
| `HARNESS_MODEL` | — | 模型名（优先级高于 `.env`） |

示例：用真实模型启动且不自动开浏览器

```bash
$env:HARNESS_WEB_MOCK='0'; $env:HARNESS_WEB_NO_OPEN='1'; python 运行.py examples/运行Web服务器.light
```

## 常见问题

**Q: 发送消息后显示"服务端错误 500：HTTP 请求失败 [401]"？**
A: API Key 无效或已过期。点顶栏「⚙ 设置」重新填入正确的密钥。

**Q: 显示"该模型当前访问量过大"？**
A: 大模型服务商限流，稍后再试或换一个模型。

**Q: 页面显示"未授权"？**
A: URL 里缺少 `?token=` 或令牌已过期。重新启动服务，用终端输出的完整登录 URL 打开。

**Q: 怎么停止服务？**
A: 在启动服务的终端按 `Ctrl+C`。

**Q: 配置保存在哪里？**
A: 网页保存的配置写入项目根目录的 `.env` 文件，可随时手工编辑。

## 项目定位

- **对标对象**：DeepSeek Harness（`g:\github\deepseek-harness`，TypeScript monorepo，Cordis 插件驱动，50 个 packages + 2 个 apps）
- **复刻语言**：光明（LightLang，`G:\dswork\duan-light-merge\light-merge`）
- **工作目录**：`G:\dswork\duan-light-merge\lightharness`（本工程）
- **复刻口径**：功能等价 1:1 —— 每个模块建一张功能对标卡（原版功能 → 光明实现 → 对齐度 done/partial/none + 证据 + 反跑判据）

## 范围与进度

复刻范围覆盖 deepseek-harness 全部可提取纯逻辑的模块，以**功能对标卡**为唯一粒度。截至目前：

- **功能对标卡 #1–#70 共 70 张**，全部 `done`。
- 已落地区域包括：core/session/llm/agent-loop/tools/compaction/hooks、运行层（subprocess/terminal/shell/sandbox）、生态（mcp/审批/subagent/遥测/代码运行时/e2b）、管理（工作区/存储域/路径规则/安全策略/类型注册）、扩展（语言服务器/推理工具）、多智能体团队（agent-team：依赖图/看板/折叠/花名册/服务/日志）。
- **Web UI**：前端界面 + 登录认证 + 静态路由 + 一键启动开浏览器 + 大模型配置引导（网页面板 + .env 手工编辑），已集成交付。

## 目录结构

```
lightharness/
├── 运行.py                 # 运行器：自包含 stdlib + 光明编译器
├── .env.example            # 大模型配置模板（复制为 .env 使用）
├── stdlib/                 # 自包含标准库（复制自 light-merge，含 .light + .py）
├── src/                    # lightharness 光明源码
│   ├── 总入口.light        # CLI 模块（可运行包装：examples/运行CLI.light）
│   ├── web服务器.light     # Web 服务端（路由/认证/SSE/大模型配置 API）
│   ├── 会话/消息/事件       # 会话.light(事件日志)、消息.light、事件.light(事件总线)
│   ├── 代理/异步代理/中止   # agent-loop：代理.light(同步)+异步代理.light(异步)+中止.light
│   ├── 客户端.light        # llm 流式客户端（OpenAI 兼容适配器）
│   ├── 认证.light          # 登录认证（令牌签发/校验）
│   ├── 工具/钩子/压缩       # 工具.light(注册/校验/执行)、钩子.light、压缩.light
│   ├── 持久化/存储/文件     # JSONL 持久化 + 存储/文件
│   └── 运行层/             # 子进程/沙箱/终端(管道+PTY)/流/重试策略
├── webui/                  # 前端静态文件（index.html / app.js / style.css）
├── 工具集/                 # 内置工具（fs/bash/...）
├── docs/
│   ├── 架构设计.md          # 光明版架构蓝图
│   └── 功能对标/           # 每模块功能对标卡
├── tests/                  # 测试（含反跑判据）
└── examples/               # 运行示例（运行Web服务器.light / 运行CLI.light / 冒烟.light）
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
- Web 启动四路（W1 前端 / W2 认证 / W3 服务端 / W4 启动器）已集成交付，集成验收 12 项 curl + 5 项浏览器全过。
- 大模型配置引导（网页面板 + .env 手工编辑 + 热更新）已交付。
- 回归门禁：三平台（Windows / FreeBSD 0.82 / 0.86）全量 **≈1400 用例 0 失败**（R87 实测，详见 `docs/功能对标/` 与 `docs/历史存档/`）。

## 回归门禁

`python -m pytest tests/test_回归.py` 跑全量回归用例（约 1400，含缺陷复现套件），任一带退出码断言失败即红；反跑判据见 `docs/功能对标/反跑判据.md`。

- 本机全量：`python -m pytest tests/`（pytest.ini 默认 `--timeout=60 -n auto`）；本机 Windows 固定 `-n 4` 时加 `-o "addopts="`（绕过 ini 的 `-n auto`）。
- 数量基线：以 `tests/ci_environment_reds.txt` 台账为权威，按「新增红」判据（本轮失败 − 基线失败）而非裸 passed 数。

`python 运行.py examples/test_终端PTY.light` 单独验证终端 PTY（真 tty，需 Win10 1809+）。

### O0 测试（光明编译器 C 后端）

lightharness 的部分测试用例依赖光明编译器的 O0（优化级别 0）C 后端，需本地具备 LLVM/clang 工具链（含 `stdio.h` 等 C 头文件）。

- **检查环境**：命令行执行 `clang --version` 或 `zig version`，有输出即已具备。
- **本地未安装时**：O0 相关用例会跳过或失败，不影响 Python 层全量回归（`python -m pytest tests/`）。
- **CI 默认执行**：gitea CI（192.168.1.5）已预装 LLVM 工具链，O0 测试在 CI 上全量执行。
- **如需本地安装**：推荐 `zig`（单文件、自带 libc 头文件、无系统级安装依赖），或 `clang`/`LLVM`。

## 许可证与社区

- **许可证**：[LICENSE](LICENSE)（MIT）
- **贡献**：[CONTRIBUTING.md](CONTRIBUTING.md) —— 本地环境、跑测试、`.light` 书写规范、提交规范与三条工程铁律
- **变更记录**：[CHANGELOG.md](CHANGELOG.md)
- **行为准则**：[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- **安全漏洞**：[SECURITY.md](SECURITY.md) —— 请走私密渠道，勿公开 Issue 披露
