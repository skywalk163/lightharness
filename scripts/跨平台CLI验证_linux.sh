#!/bin/sh
# R85 任务F 批1（4）—— 0.86 Linux 跨平台 CLI 命令面验证（version/help/dump-config/unknown）。
# 转发到 paramiko 版 Python 运行器（远端副本已在 /tmp/r85-*，由 同步0.86.py sync 准备好）。
# 用法：sh scripts/跨平台CLI验证_linux.sh [--host 192.168.0.86]
set -e
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
PYTHON=${PYTHON:-python3}
exec "$PYTHON" scripts/跨平台CLI验证_0.86.py "$@"
