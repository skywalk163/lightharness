#!/bin/sh
# R41 任务3：POSIX CLI 命令面验证。仅依赖 POSIX sh + Python。
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON=${PYTHON:-python3}
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  PYTHON=python3.11
fi
cd "$ROOT"
export PYTHONIOENCODING=utf-8
export HARNESS_MODEL=r41-cross-platform-model

run_cmd() {
  cmd=$1
  expected=$2
  HARNESS_CMD=$cmd; export HARNESS_CMD
  out=$($PYTHON 运行.py examples/运行CLI.light 2>&1)
  rc=$?
  printf '%s\n' "$out" | grep -F "$expected" >/dev/null
  printf 'PASS %-12s rc=%s\n' "$cmd" "$rc"
}

run_cmd version '0.1.5-lh'
run_cmd help 'lightharness CLI 用法'
run_cmd dump-config 'r41-cross-platform-model'
HARNESS_CMD=bogus; export HARNESS_CMD
set +e
out=$($PYTHON 运行.py examples/运行CLI.light 2>&1)
rc=$?
set -e
[ "$rc" -ne 0 ]
printf '%s\n' "$out" | grep -F '未知命令' >/dev/null
printf 'PASS %-12s rc=%s\n' unknown "$rc"

HARNESS_MSG='R41 CLI 环境变量传参'; export HARNESS_MSG
# run 会触发真实模型请求，因此用既有无网络命令面单测覆盖环境读取与调度。
unset HARNESS_CMD
$PYTHON 运行.py examples/test_CLI命令面.light >/dev/null
printf 'PASS %-12s rc=0\n' cli-test
printf 'R41_CLI_POSIX PASS\n'
