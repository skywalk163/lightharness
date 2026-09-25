# 贡献指南

欢迎参与 **lightharness**（下称 LH）——用「光明/Light」中文编程语言 1:1 复刻 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) 的工程。

复刻的目的不是照抄代码，而是**在实践中检验光明这门语言**：凡是"写不出来、写出来是错的、绕不过去"的地方，都要登记成语言缺陷并回灌给光明。

动手之前，请先读一遍 [`README.md`](README.md)（项目定位、目录结构、环境变量）与 `docs/核心概念.md`（架构与术语）。

---

## 一、本地环境准备

### 前置依赖

| 依赖 | 说明 |
|------|------|
| Python 3.10+ | 光明编译器与 pytest 的运行基础 |
| 父仓 light-merge | 光明语言本体（编译器 + 标准库），LH **不包含**它，必须外部提供 |
| pytest / pytest-xdist / pytest-timeout | 跑测试用，`-n`（并行）依赖 xdist |
| LLVM/Clang 或 zig（可选） | 仅 O0（C 后端）用例需要，见 README「O0 测试」 |

### 环境变量三件套

LH 全部脚本都通过下面三个环境变量定位父仓，**不设就跑不起来**：

| 变量 | 作用 |
|------|------|
| `LIGHT_MERGE` | 指向 light-merge 父仓根目录 |
| `PYTHONPATH` | 指向 light-merge 的 `src/`（编译器导入路径） |
| `PATH` | 前置 `/tmp/r80b-shim`（FreeBSD 门禁机的工具链垫片目录） |

**Windows / PowerShell（本机布局：父仓与 LH 同级）**

```powershell
cd G:\dswork\duan-light-merge\lightharness
$env:LIGHT_MERGE = 'G:\dswork\duan-light-merge\light-merge'
$env:PYTHONPATH  = 'G:\dswork\duan-light-merge\light-merge\src'
```

**FreeBSD / Linux（远端门禁机，POSIX）**

```bash
cd /path/to/lightharness
export LIGHT_MERGE="$PWD/light-merge"
export PYTHONPATH="$PWD/light-merge/src"
export PATH="/tmp/r80b-shim:$PATH"
```

> 若你的机器上 light-merge 与 lightharness 是同级目录，把上面两行改成
> `export LIGHT_MERGE="$PWD/../light-merge"` 与 `export PYTHONPATH="$PWD/../light-merge/src"`。
> 判断标准始终只有一个：`$LIGHT_MERGE/src` 必须存在且里面有光明的编译器。

**Windows / bash（Git Bash）**

```bash
cd /g/dswork/duan-light-merge/lightharness
export LIGHT_MERGE='/g/dswork/duan-light-merge/light-merge'
export PYTHONPATH='/g/dswork/duan-light-merge/light-merge/src'
```

验证环境是否就绪：

```bash
python 运行.py examples/冒烟.light
```

---

## 二、跑测试

**全量回归（本机 Windows，固化 `-n 4`）**

```bash
python -m pytest tests/test_回归.py -n 4
```

**全量回归（按 `pytest.ini` 默认配置）**

```bash
python -m pytest tests/
```

`pytest.ini` 里固化了 `--timeout=60 -n auto`：单用例 60 秒硬超时（防 hang 死），默认按 CPU 核数并行。

**只跑某一小类**

```bash
python -m pytest tests/test_回归.py -k "会话"
python -m pytest tests/test_L177_括号式参数注解.py
```

**单独跑一个 `.light` 示例**

```bash
python 运行.py examples/冒烟.light
python 运行.py examples/运行CLI.light
python 运行.py examples/运行Web服务器.light
```

O0（C 后端）相关用例需要本地有 `clang` 或 `zig`；没有时会跳过或失败，**不影响 Python 层全量回归判定**。

提交前的最低标准：**本机全量 pytest 0 失败**。跨平台差异由远端 FreeBSD 门禁机把关，但不要把已知红留给自己以外的人。

---

## 三、写一个新模块（`.light` 书写规范）

新模块放在 `src/`，文件名用中文、与其暴露的主概念同名（例如 `src/消息.light`、`src/异步代理.light`）。

### 基本骨架

```
# 模块名.light —— 一句话说明对齐原版哪个文件

段落 主:
  设 结果 为 某某(1, 2)
  打印(结果)
  返回 结果

段落 某某(a: 整数, b: 整数) -> 整数:
  返回 a 加 b
```

### 语法速查

| 用途 | 写法 | 备注 |
|------|------|------|
| 入口段 | `段落 主:` | 可运行文件的固定入口 |
| 参数（括号式） | `段落 X(参数甲, 参数乙):` | **新代码一律用括号式**，不要再用旧式 `段落 X 接收 参数:` |
| 参数/返回类型标注 | `段落 X(a: 整数) -> 整数:` | 可空写 `可空 字符串`，联合写 `整数\|字符串`，容器写 `列表<整数>` |
| 变量绑定 | `设 x 为 1` | 不要用 `=` |
| 返回 | `返回 x` | 无值返回写 `返回 空` |
| 空值 | `空` | 等价于其它语言的 `None` |
| 打印 | `打印(x)` | 另有两个变体 `显示(x)` / `输出(x)`，新代码统一用 `打印` |
| 序列截取 | `截取(序列, 开始, 长度)` / `[开始:结束]` | 注意第二个参数是**长度**不是结束下标 |
| 异步定义 | `异步 段落 X(...)` | **类体内不支持 `异步 段落`**，异步段只能写在顶层 |
| 等待单个 | `等待 f` | |
| 等待全部 | `等待 并发等待(协程表)` | 表（列表）入参，返回结果表 |
| 等待首个 | `等待 首个完成(任务表)` | 返回「完成对」 |
| 异步睡眠 | `等待 睡眠异步(毫秒)` | 不阻塞事件循环 |

### 两个高频坑

1. **逗号是流水线组合符**，不是随便用的分隔符。参数表里用半角逗号是参数分隔，但在表达式上下文里写逗号会被解析成流水线组合——不要混写。
2. **旧式接收语法** `段落 X 接收 参数:` 已废弃，写新文件时统一括号式；迁移存量文件请走专门的改造流程，不要顺手在一个 commit 里改一大片。

---

## 四、提交规范

### Commit message

中文书写，前缀用小写的 Conventional Commits 类型：

| 前缀 | 用途 |
|------|------|
| `feat:` | 新功能、新模块、新对标卡 |
| `fix:` | 修复缺陷、修复红用例 |
| `docs:` | 文档、对标卡、交付报告 |
| `test:` | 测试用例与测试基建 |
| `ci:` | 工作流、门禁脚本、环境变量 |
| `refactor:` | 不改外部行为的重构 |

示例：

```
fix: 修 异步代理 超时分支吞掉取消异常
docs: 补 #70 对标卡的反跑判据
test: 加 会话 V3 迁移用例
```

### 三条工程铁律

这三条是本仓用事故换来的，**必须遵守**：

**1. 一轮只允许一条改动路径触碰 `src/`。**
`src/` 的 codegen（代码生成/重编译）是唯一的串行瓶颈。多条改动路径同时改 `src/`，后写的会把先写的冲掉，且冲突往往在几百行之外才暴露。一轮里要改 `src/`，就先把其它路的内容合完，再放这一条进去。

**2. 禁止 `git add .`，只能 `git add <显式文件>`。**
仓库里长期存在 `_*.log`、`_*.json`、`.e2e_*`、`tmp_*`、`编译产物/` 这类临时产物，一个 `git add .` 就把几千字节垃圾带进提交历史。逐个显式添加，顺手核对 `git status` 里没有预期外的文件。

**3. 幂等补丁必须用「哨兵串 guard」判定是否已应用。**
批量打补丁的脚本要用一段独一无二的哨兵串做存在性判断，例如：

```python
哨兵 = "# LH-PATCH-会话V3记账闸门 已插入"
if 哨兵 in 原文:
    print("已应用，跳过")
else:
    写文件(原文.replace(锚点, 锚点 + 补丁))
```

**不要**用 `new in text` 来判断：因为 `new`（替换后的文本）本来就是 `old` 的超集，第一次应用后 `new in text` 依然成立会误判成"已应用"，而反过来又会二次插入导致内容重复。哨兵串必须是补丁自己写进去的、仓库里原本没有的串。

---

## 五、语言缺陷反馈

复刻中遇到光明"写不出 / 写错 / 绕不过"的地方：

1. 在对应模块的**功能对标卡**「语言缺陷」字段登记：现象 + 最小复现 + 期望能力
2. 汇总到 `docs/功能对标/语言缺陷账.md`
3. 移交光明开发团队修复

见 README「语言缺陷反馈流程」。

---

## 六、行为准则

参与本项目默认接受 [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)。安全问题报告方式见 [`SECURITY.md`](SECURITY.md)，版本历史见 [`CHANGELOG.md`](CHANGELOG.md)。

本项目使用 MIT 许可证，详见 [`LICENSE`](LICENSE)。
