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

## 禁止裸文本批量替换 .light 源码（L-009）

**绝不**使用 PowerShell 的 `-replace`、sed、`string.Replace` 等「文本级」工具直接改写 `.light` 源码。
这类工具不感知光明词法，会把**注释行内嵌的 `导入 X` 等字样**也当作代码命中，插入换行后把注释尾巴劈成代码行，
产生「无法识别的语法元素」之类的**伪语法错误**，严重误导排查（缺陷账 L-009，工程层陷阱，非语言运行时缺陷）。

正确做法：批量改名 / 改串一律用工程层词法感知替换工具 `scripts/安全替换.py`。它会跳过整行注释与字符串字面量
（含三引号、跨行、f/r/b 前缀），只对真实代码区域做替换，并保留行首缩进：

```bash
# 1) 先 dry-run 看差异统计，确认命中/跳过符合预期（不写任何文件）
python scripts/安全替换.py examples/foo.light "旧串" "新串" --dry-run

# 2) 输出到副本（严禁 --out 覆盖输入源码；工具也会主动拒绝同路径写回）
python scripts/安全替换.py examples/foo.light "旧串" "新串" --out examples/foo_改.light

# 3) 内置自测（不依赖文件，验证「注释/字符串跳过、代码行替换并保留缩进」）
python scripts/安全替换.py --self-test
```

要点：
- 替换串可含换行；多行替换时续行会自动对齐到原行缩进，不会破坏代码块层级。
- 差异统计分别列出「命中替换」与「跳过（注释/字符串内）」次数，便于复核。
- 永远先输出到新文件，人工 review diff 后再决定是否替换原文件；`.light` 源码不得以任何文本工具原地改写。

## 新增测试用例

1. 在 `examples/` 下创建 `test_模块名.light`
2. 用 `断言` 验证，最后打印 `--- xxx测试通过 ---`
3. 确保退出码为 0（pytest 回归套件会自动收集）
4. 如果是预期失败的用例（未修复缺陷），在 `tests/test_回归.py` 的 `EXPECT_RED` 中登记

## 缺陷复现用例必须同时挂 `tests/`（R57 起的硬惯例）

> **只放 `examples/` 不算进全量门。**

背景（R54 的 test_L170.light 教训，G7）：light-merge 仓库的全量 pytest 只收集
`tests/`，`examples/*.light` 完全不被 pytest 收集——只把缺陷复现用例写到
examples/，门禁对它**零感知**，修复被回退/破坏时全量门不会红。

硬性要求（两个仓库同口径）：

1. 每个语言/编译器缺陷的复现用例，除了运行期自校验的 `.light`
   （examples/ 可留作人工复核载体），**必须同时**在 `tests/` 落一个 pytest 用例：
   - 编译器缺陷 → 挂 `light-merge/tests/`（被 0.82 全量门收集），
     参照 `tests/test_R57_L170回归.py`（源码内嵌 + run/product 双腿 + 运行时断言）；
   - 词法/切词行为 → token 层钉桩挂 `lightharness/tests/`，
     参照 `tests/test_R57_复现回归.py`（`Lexer(text, deterministic=True).tokenize()`
     直接断言 token 流）+ 运行层真跑 example 断 rc==0；
2. 用例必须能在**修复前**红、**修复后**绿（先取证报错原文，修复后作为钉桩）；
3. 钉桩需顺带断言修复不许破坏的既有语义（如 R26 的 21 个单字语句关键字
   词首必须切分、L-155 嵌入块吞并语义），红即报警。

## 平台说明

- CI 运行在 `ubuntu-latest`，光明编译器和 lightharness 均为跨平台 Python 实现
- 本地开发支持 Windows / Linux / macOS
- Windows 路径分隔符在 `运行.py` 中通过 `os.path` 自动处理

## Linux 0.86 远端门禁（R85 任务F，实测）

除 GitHub Actions（`ubuntu-latest`）外，本仓库还把 **0.86 内网 Linux 机（Ubuntu 24.04，Python 3.12.3，无 sudo）** 纳入跨平台实测门禁，用于发现 Windows / FreeBSD 0.82 之外的第三平台差异。相关脚本与基建：

| 脚本 | 作用 | 备注 |
|---|---|---|
| `scripts/同步0.86.py` | 0.86 接入：多账号探活、git tracked 树打包上传、`--with-git`、`probe` 环境探测、venv 建pytest 全家桶、`test-lm`/`test-lh` 远端门禁跑通 | 机器常量用 `--host` 参数化（默认 192.168.0.86），向后兼容 |
| `scripts/跨平台CLI验证_0.86.py` + `.sh` | 在 0.86 实测 CLI 命令面 version/help/dump-config/unknown | 复用 0.86 远端副本 |
| `scripts/多平台矩阵.py --host 192.168.0.86 --mode core` | 把核心用例矩阵门跑在 0.86（Linux）上，与 Windows 比对 rc 字典 | `--platform linux` / 推断：传了非 0.82 的 `--host` 即视为 Linux；0.82 行为不变 |

### 0.86 接入要点（踩坑固化，别踩回去）

- **无 sudo**：0.86 的 `ai` 账号无 sudo，因此**绝不装系统 Python**、不 `make install`、不碰全局配置；所有 pytest 依赖装在 `/tmp/r85-venv`（用户级 venv，`python3 -m venv` 已验证可用，无需 apt）。
- **没有 `python` 命令**：0.86 只有 `python3`。`同步0.86.py` 在 `/tmp/r85-shim` 建了 `python`/`python3` 垫片指向 venv，并把 venv/bin + shim 注入 `PATH`，因此即便用例内部裸调 `python` 也能命中。
- **凭据只在本机读 `.env`**（`SSH_USER_*`/`SSH_PASS_*`），按 AI→TRAE→WORKBUDDY→DUMATE 顺序探活首个连通账号；值不入档、不落日志、**不上传**（脚本不把 `.env` 打进 tarball）。
- **打包用 `git ls-files`**（tracked 树），天然不含 `.venv`/未跟踪 scratch；`--with-git` 时额外把 `.git` 一并带上，使依赖 `git archive HEAD` 的用例在 0.86 真正执行而非退化成 skip。
- **远端命令一律后台跑 + 轮询**（`nohup … &` + 定时 `tail`），全量 pytest 10~20 分钟不阻塞本机；切忌前台死等。

### 0.86 实测结论（数据见 `reports/R85_*` 与 `_taskF_R85_交付报告.md`）

- 0.86（Ubuntu 24.04 / Python 3.12.3）上 light-merge 与 lightharness 全量 pytest 均可跑通，venv 装 `pytest + pytest-xdist + pytest-timeout + psutil + antlr4-python3-runtime`。
- 与 Windows / FreeBSD 的差异主要在**平台语义**（如 socket 系列），纯编译/解释链路一致；具体对照表见 `docs/多平台差异清单.md` 的 R85 Linux 段。
- **沙箱**：0.86 未预装 `bwrap`/landlock 用户态工具且 ai 无 sudo，真后端不可用 → 按 fail-closed 记录（见交付报告批2）。
