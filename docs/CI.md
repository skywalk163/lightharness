# lightharness CI 说明

## 概述

lightharness CI 负责在每次推送和 PR 时自动运行全量测试，确保光明语言实现的各模块不回归。

## 测试架构

```
.github/workflows/ci.yml    # GitHub Actions / gitcode 兼容
.gitea/workflows/ci.yml     # Gitea Actions（内网）
scripts/ci_test.py           # 统一测试入口（不依赖 CI 平台）
requirements.txt             # Python 依赖（pytest）
tests/test_回归.py           # pytest 参数化回归套件（遍历 examples/*.light）
```

## CI 流程

1. **检出代码**：lightharness 仓库
2. **检出编译器**：light-merge（光明语言编译器），放到 `../light-merge`
3. **设置 Python**：3.13
4. **安装依赖**：`pip install -r requirements.txt`
5. **运行测试**：`python scripts/ci_test.py`
   - 检查 LIGHT_MERGE 环境变量
   - 运行 pytest 全量回归（80 个参数化用例）
   - 运行核心模块冒烟测试（会话/代理/工具/消息/流）
6. **上传日志**：失败时上传 tests/ 和 examples/ 为 artifact

## 关键依赖：light-merge 编译器

lightharness 本身不包含光明语言编译器，依赖外部 `light-merge` 仓库。CI 通过以下方式获取：

### GitHub Actions / gitcode

在仓库 Settings → Secrets and variables → Actions → Variables 中配置：

| 变量名 | 说明 | 示例 |
|---|---|---|
| `LIGHT_MERGE_REPO` | light-merge 仓库地址 | `https://gitcode.com/skywalk163/light.git` |

如果未配置，默认尝试 `https://gitcode.com/skywalk163/light.git`。

### Gitea Actions（内网）

默认从内网 `http://192.168.1.5:3000/skywalk/light.git` 检出，可通过 `LIGHT_MERGE_REPO` 变量覆盖。

## 本地运行 CI 测试

不需要 CI 平台，本地直接运行：

```bash
# Windows
set LIGHT_MERGE=G:\dswork\duan-light-merge\light-merge
python scripts\ci_test.py

# Linux / macOS
export LIGHT_MERGE=/path/to/light-merge
python scripts/ci_test.py
```

快速模式（仅 pytest，跳过冒烟测试）：

```bash
python scripts/ci_test.py --quick
```

## 单独运行测试

```bash
# 全量 pytest 回归
python -m pytest tests/ -q

# 按关键词过滤
python -m pytest tests/ -q -k 会话

# 单个光明用例
python 运行.py examples/test_代理.light
```

## 新增测试用例

1. 在 `examples/` 下创建 `test_模块名.light`
2. 用 `断言` 验证，最后打印 `--- xxx测试通过 ---`
3. 确保退出码为 0（pytest 回归套件会自动收集）
4. 如果是预期失败的用例（未修复缺陷），在 `tests/test_回归.py` 的 `EXPECT_RED` 中登记

## 平台说明

- CI 运行在 `ubuntu-latest`，光明编译器和 lightharness 均为跨平台 Python 实现
- 本地开发支持 Windows / Linux / macOS
- Windows 路径分隔符在 `运行.py` 中通过 `os.path` 自动处理
