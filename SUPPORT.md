# 获取支持（Support）

在求助前，先确认你的场景属于哪一类：**lightharness 是「用光明复刻 dsh」的移植工程，不是光明语言本体**。
归错仓会多绕一圈，下面这张表用来快速分流。

## 支持范围

| 类别 | 是否支持 | 优先渠道 |
|---|---|---|
| 移植问题（上游 dsh 版本对齐、行为差异） | ✅ | 本仓 Issues（bug_report 模板） |
| 插件加载 / lightplugin 集成 | ✅ | 本仓 Issues（bug_report 模板） |
| 运行器（`运行.py`）与三仓目录布局 | ✅ | 本仓 Issues 或 [`README.md`](README.md) / [`docs/快速开始.md`](docs/快速开始.md) |
| 光明语言本身的 bug（语法 / 编译 / 类型 / 标准库） | ❌ → 转 `light` 仓 | [light Issues](https://github.com/skywalk163/light/issues) |
| lightplugin 插件本体问题 | ❌ → 转 `lightplugin` 仓 | lightplugin 仓 Issues |
| 商业支持 / SLA / 一对一实时答疑 | ❌ | 社区开源项目，无商业支持承诺 |

## 怎么判断是「lightharness 的问题」还是「light 语言本体的问题」

这是本仓最容易被误归类的地方，判据只有一条——**能不能在 light 仓用最小 `.light` 片段直接复现**：

- 最小片段在 `light` 仓用 `light check` / `light run` 同样报错 → 是**语言本体**的问题，
  请带 LH 编号（本仓 `docs/` 下的对标报告与问题记录用的就是这套编号）或最小复现转 `light` 仓；
- 换个等价写法/换回上游 dsh 的对应 Python 实现就正常，只有光明版复刻出问题 → 是**移植问题**，
  留在本仓。

不确定时选「不确定」，维护者会帮你分流，不要因为怕归错而不敢提。

## 提问前自查

1. 已读过 [`README.md`](README.md) 的「环境准备（目录布局）」，三仓（`light` / `lightplugin` / `lightharness`）按兄弟目录摆好；
2. 已用最小 `.light` 片段复现，并附上完整报错（不是只贴一句 `xxx 失败`）；
3. 已搜索过本仓 Issues，确认不是重复问题；
4. 已准备好环境信息：lightharness 版本（`git describe --tags` 或 `CHANGELOG.md` 首条）、
   light 编译器版本（`python -m cli.light_unified --version`）、操作系统、Python 版本。

## 渠道清单

- 🐛 Bug / 功能请求 → 本仓 Issues（模板：bug_report / feature_request）
- 🛡️ 安全漏洞 → 见 [`SECURITY.md`](SECURITY.md)（走私密渠道，不要开公开 Issue）
- 🤝 贡献流程 → 见 [`CONTRIBUTING.md`](CONTRIBUTING.md)
- 📖 文档与架构 → 见 [`docs/`](docs/)（架构设计、插件开发指南、配置参考等）
