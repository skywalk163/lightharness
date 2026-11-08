---
name: Bug 报告
about: lightharness 的行为不符合预期（移植问题 / 运行器 / 插件加载）
title: '[Bug] '
labels: bug
assignees: ''
---

## 环境

- lightharness 版本（`git describe --tags` 或 `CHANGELOG.md` 首条）：
- light 编译器版本（`python -m cli.light_unified --version`）：
- 操作系统：
- Python 版本：
- lightplugin 是否接线（有 / 无；若有用 `LIGHTPLUGIN` 指到哪里）：

## 复现

（最小 `.light` 片段 + 运行命令）

```光明
# 你的光明代码
```

```text
粘贴完整报错
```

## 期望 vs 实际

- 期望行为：
- 实际行为：

## 归因（重要）

- [ ] 是 lightharness 的移植问题（上游 dsh 有对应实现，光明版复刻出错）
- [ ] 是 light 语言本体的缺陷（→ 请附 LH 编号，或转 [light/issues](https://github.com/skywalk163/light/issues)）
- [ ] 不确定

## 附加上下文

- 相关日志 / 截图：
- 是否只在特定平台或特定目录布局下出现？
