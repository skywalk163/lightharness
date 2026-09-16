# 第41轮任务3交付：CLI多平台 + 0.82接入

## 结论

任务3完成。Windows 本机与 0.82（FreeBSD）均通过 CLI 命令面验证；0.82 SSH 接入、临时副本同步和 light 运行时执行均成功。

## 交付物

- `scripts/跨平台CLI验证.ps1`：Windows PowerShell 验证入口。
- `scripts/跨平台CLI验证.sh`：POSIX sh 验证入口。
- `scripts/cli_platform_runner.py`：兼容 Windows PowerShell 5.1 编码限制的标准库辅助器。
- 本报告。

## 0.82接入实测

- SSH：从 Windows 本机连接成功；认证信息仅从工作区 `.env` 读取，未写入脚本、报告或命令参数。
- 平台：FreeBSD 15.1-STABLE amd64，默认 shell `/bin/sh`。
- Python：`python3.11`，版本 3.11.16；`python`/`python3` 命令不存在。
- 初始状态：远端无项目副本。
- 同步方式：本机打包 `lightharness` 与 `light-merge`，上传到远端 `/tmp/r41-<时间戳>`；远端只执行该临时副本，不编辑任何源文件。
- light 运行时：通过 `LIGHT_MERGE=<临时目录>/light-merge` 与 `python3.11 运行.py` 成功运行。

## CLI验证结果

Windows PowerShell：

- version：rc=0，输出 `0.1.5-lh`
- help：rc=0，含完整命令表
- dump-config：rc=0，环境变量模型值生效
- unknown：rc=1，含帮助提示
- `test_CLI命令面.light`：rc=0

0.82 POSIX：上述五项结果相同，脚本输出 `R41_CLI_POSIX PASS`。

## 平台差异与修正

1. Windows PowerShell 5.1 会把无 BOM UTF-8 脚本中的中文字符串/路径误按系统代码页解析，初版脚本出现解析错误和路径乱码。
2. 正式 `.ps1` 改为 ASCII 文本；由 `cli_platform_runner.py` 读取 UTF-8 源码并定位中文文件，避免依赖 PowerShell 的旧编码行为。
3. Windows 使用 `$env:HARNESS_CMD=...`，POSIX 使用 `HARNESS_CMD=...; export HARNESS_CMD`。
4. 远端 Python 可执行文件为 `python3.11`，POSIX脚本支持 `PYTHON` 覆盖并带回落。

## 约束核对

- 未修改 `src/`、总入口或 CLI 默认行为。
- 未把密码、token、API key 或内网认证值写入交付物。
- 0.82只运行上传的临时副本，未修改远端源仓库。
