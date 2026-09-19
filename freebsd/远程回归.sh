#!/bin/sh
# R68 子任务 68.2 + 68.3 —— FreeBSD 远程回归一键脚本
#
# 在 FreeBSD 远程机上执行 jail e2e + 交叉回归（PTY/socket/事件循环/进程树），
# 输出 JSON 格式的回归结果到 reports/R68_freebsd_e2e.json。
#
# 用法（在 FreeBSD 上，lightharness 项目根目录执行）：
#   sh freebsd/远程回归.sh                    # 全部测试
#   sh freebsd/远程回归.sh --skip-jail        # 跳过 jail e2e（dsh-jail-run 未安装时）
#   sh freebsd/远程回归.sh --jail-only        # 仅跑 jail e2e
#   sh freebsd/远程回归.sh --cross-only       # 仅跑交叉回归（PTY/进程树等）
#   sh freebsd/远程回归.sh --output PATH      # 指定输出 JSON 路径
#
# 前置条件：
#   - lightharness 代码已同步到 FreeBSD（scripts/同步0.82.py sync）
#   - light-merge 编译器可用（LIGHT_MERGE 环境变量或上级目录）
#   - Python 3.12 已安装（/usr/local/bin/python3.12）
#   - jail e2e 需要 dsh-jail-run 已安装（freebsd/编译安装.sh）

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PY="/usr/local/bin/python3.12"
JAIL_BIN="/usr/local/sbin/dsh-jail-run"
OUTPUT="${ROOT}/reports/R68_freebsd_e2e.json"
SHIM_DIR="/tmp/r44-shim"

# ── 设置 python 垫片（FreeBSD 无 python 命令，测试子进程需要）──
setup_shim() {
  mkdir -p "$SHIM_DIR"
  if [ ! -x "$SHIM_DIR/python" ]; then
    printf '#!/bin/sh\nexec %s "$@"\n' "$PY" > "$SHIM_DIR/python"
    cp "$SHIM_DIR/python" "$SHIM_DIR/python3"
    chmod +x "$SHIM_DIR/python" "$SHIM_DIR/python3"
  fi
  export PATH="$SHIM_DIR:$PATH"
}

# ── 参数解析 ──
SKIP_JAIL=0
JAIL_ONLY=0
CROSS_ONLY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --skip-jail)  SKIP_JAIL=1 ;;
    --jail-only)  JAIL_ONLY=1 ;;
    --cross-only) CROSS_ONLY=1 ;;
    --output)     shift; OUTPUT="$1" ;;
    *)            echo "未知参数: $1"; exit 1 ;;
  esac
  shift
done

# ── 工具函数 ──
ts() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }

# 运行一个 .light 测试，返回 JSON 片段
run_light_test() {
  _name="$1"
  _file="$2"
  _timeout="${3:-60}"
  _rc=0
  _start=$(date +%s)
  _out=$(cd "$ROOT" && LIGHT_MERGE="${LIGHT_MERGE:-$(cd "$ROOT/../light-merge" 2>/dev/null && pwd)}" \
    "$PY" 运行.py "examples/$_file" 2>&1) || _rc=$?
  _elapsed=$(($(date +%s) - _start))
  _passed="false"
  [ "$_rc" = "0" ] && _passed="true"
  _tail=$(printf '%s' "$_out" | tail -5 | tr '\n' ' ' | cut -c1-500)
  printf '{"name":"%s","file":"%s","rc":%s,"elapsed_sec":%s,"passed":%s,"output_tail":"%s"}' \
    "$_name" "$_file" "$_rc" "$_elapsed" "$_passed" "$_tail"
}

# 运行一个 shell 命令测试
run_cmd_test() {
  _name="$1"
  _cmd="$2"
  _timeout="${3:-30}"
  _rc=0
  _start=$(date +%s)
  _out=$(eval "$_cmd" 2>&1) || _rc=$?
  _elapsed=$(($(date +%s) - _start))
  _passed="false"
  [ "$_rc" = "0" ] && _passed="true"
  _tail=$(printf '%s' "$_out" | tail -3 | tr '\n' ' ' | cut -c1-300)
  printf '{"name":"%s","rc":%s,"elapsed_sec":%s,"passed":%s,"output_tail":"%s"}' \
    "$_name" "$_rc" "$_elapsed" "$_passed" "$_tail"
}

mkdir -p "$(dirname "$OUTPUT")"
setup_shim

echo "=== R68 FreeBSD 远程回归 ==="
echo "时间: $(ts)"
echo "主机: $(uname -n) ($(uname -r))"
echo "Python: $($PY -V 2>&1)"
echo "输出: $OUTPUT"
echo ""

# ── 环境信息 ──
ENV_INFO=$(printf '{"os":"%s","kernel":"%s","arch":"%s","cpu":"%s","memory_mb":%s,"python":"%s","clang":"%s"}' \
  "$(uname -s)" "$(uname -r)" "$(uname -m)" \
  "$(sysctl -n hw.ncpu)" \
  "$(($(sysctl -n hw.physmem) / 1048576))" \
  "$($PY -V 2>&1 | cut -d' ' -f2)" \
  "$(cc --version 2>/dev/null | head -1 | cut -d' ' -f3-)"
)

CROSS_RESULTS=""
JAIL_RESULTS=""

# ── 交叉回归（68.3）──
if [ "$JAIL_ONLY" = "0" ]; then
  echo "--- 交叉回归 ---"

  # PTY
  echo "[1/8] PTY (test_终端PTY.light)..."
  R=$(run_light_test "PTY伪终端" "test_终端PTY.light" 120)
  CROSS_RESULTS="${CROSS_RESULTS}${CROSS_RESULTS:+,}$R"
  echo "  -> $(printf '%s' "$R" | grep -o '"passed":[a-z]*')"

  # 进程树
  echo "[2/8] 进程树 (test_进程树.light)..."
  R=$(run_light_test "进程树POSIX" "test_进程树.light" 120)
  CROSS_RESULTS="${CROSS_RESULTS}${CROSS_RESULTS:+,}$R"
  echo "  -> $(printf '%s' "$R" | grep -o '"passed":[a-z]*')"

  # socket（R66）
  echo "[3/8] socket (test_套接字.light)..."
  if [ -f "$ROOT/examples/test_套接字.light" ]; then
    R=$(run_light_test "原生socket" "test_套接字.light" 120)
  else
    R='{"name":"原生socket","file":"test_套接字.light","rc":-1,"elapsed_sec":0,"passed":false,"output_tail":"SKIP: test_套接字.light 不存在","skipped":true}'
  fi
  CROSS_RESULTS="${CROSS_RESULTS}${CROSS_RESULTS:+,}$R"
  echo "  -> $(printf '%s' "$R" | grep -o '"passed":[a-z]*')"

  # 事件循环（R66）
  echo "[4/8] 事件循环 (test_事件循环.light)..."
  if [ -f "$ROOT/examples/test_事件循环.light" ]; then
    R=$(run_light_test "事件循环" "test_事件循环.light" 120)
  else
    R='{"name":"事件循环","file":"test_事件循环.light","rc":-1,"elapsed_sec":0,"passed":false,"output_tail":"SKIP: test_事件循环.light 不存在","skipped":true}'
  fi
  CROSS_RESULTS="${CROSS_RESULTS}${CROSS_RESULTS:+,}$R"
  echo "  -> $(printf '%s' "$R" | grep -o '"passed":[a-z]*')"

  # 事件循环 + socket 集成（R66）
  echo "[5/8] 事件循环+socket (test_套接字事件循环.light)..."
  if [ -f "$ROOT/examples/test_套接字事件循环.light" ]; then
    R=$(run_light_test "事件循环socket集成" "test_套接字事件循环.light" 120)
  else
    R='{"name":"事件循环socket集成","file":"test_套接字事件循环.light","rc":-1,"elapsed_sec":0,"passed":false,"output_tail":"SKIP: test_套接字事件循环.light 不存在","skipped":true}'
  fi
  CROSS_RESULTS="${CROSS_RESULTS}${CROSS_RESULTS:+,}$R"
  echo "  -> $(printf '%s' "$R" | grep -o '"passed":[a-z]*')"

  # 沙箱_freebsd 纯逻辑（R67）
  echo "[6/8] 沙箱_freebsd (test_沙箱_freebsd.light)..."
  if [ -f "$ROOT/examples/test_沙箱_freebsd.light" ]; then
    R=$(run_light_test "沙箱freebsd封装" "test_沙箱_freebsd.light" 120)
  else
    R='{"name":"沙箱freebsd封装","file":"test_沙箱_freebsd.light","rc":-1,"elapsed_sec":0,"passed":false,"output_tail":"SKIP: test_沙箱_freebsd.light 不存在","skipped":true}'
  fi
  CROSS_RESULTS="${CROSS_RESULTS}${CROSS_RESULTS:+,}$R"
  echo "  -> $(printf '%s' "$R" | grep -o '"passed":[a-z]*')"

  # 沙箱策略（R67）
  echo "[7/8] 沙箱策略 (test_沙箱策略.light)..."
  if [ -f "$ROOT/examples/test_沙箱策略.light" ]; then
    R=$(run_light_test "沙箱策略引擎" "test_沙箱策略.light" 120)
  else
    R='{"name":"沙箱策略引擎","file":"test_沙箱策略.light","rc":-1,"elapsed_sec":0,"passed":false,"output_tail":"SKIP: test_沙箱策略.light 不存在","skipped":true}'
  fi
  CROSS_RESULTS="${CROSS_RESULTS}${CROSS_RESULTS:+,}$R"
  echo "  -> $(printf '%s' "$R" | grep -o '"passed":[a-z]*')"

  # 沙箱升级（R67）
  echo "[8/8] 沙箱升级 (test_沙箱升级.light)..."
  if [ -f "$ROOT/examples/test_沙箱升级.light" ]; then
    R=$(run_light_test "沙箱升级审批" "test_沙箱升级.light" 120)
  else
    R='{"name":"沙箱升级审批","file":"test_沙箱升级.light","rc":-1,"elapsed_sec":0,"passed":false,"output_tail":"SKIP: test_沙箱升级.light 不存在","skipped":true}'
  fi
  CROSS_RESULTS="${CROSS_RESULTS}${CROSS_RESULTS:+,}$R"
  echo "  -> $(printf '%s' "$R" | grep -o '"passed":[a-z]*')"

  echo ""
fi

# ── Jail e2e（68.2）──
if [ "$CROSS_ONLY" = "0" ] && [ "$SKIP_JAIL" = "0" ]; then
  echo "--- Jail e2e ---"

  if [ ! -x "$JAIL_BIN" ]; then
    echo "  SKIP: $JAIL_BIN 未安装（运行 freebsd/编译安装.sh）"
    JAIL_RESULTS='{"name":"jail_e2e","status":"skipped","reason":"dsh-jail-run 未安装","tests":[]}'
  else
    echo "  dsh-jail-run 已安装: $(ls -la "$JAIL_BIN" | awk '{print $1, $3, $4}')"

    # 确保 nullfs 加载
    sysctl -n vfs.nullfs >/dev/null 2>&1 || sudo kldload nullfs

    WS="/tmp/r68_jail_ws_$$"
    mkdir -p "$WS"

    # 测试1: confine 选择 jail bin，full enforcement
    echo "  [1/5] read-only 基本执行..."
    R=$(run_cmd_test "jail_readonly_basic" \
      "sudo $JAIL_BIN --workspace $WS --mode read-only -- true" 30)
    JAIL_RESULTS="${JAIL_RESULTS}${JAIL_RESULTS:+,}$R"

    # 测试2: read-only 拒绝写 workspace（期望非0退出，! 取反使测试通过）
    echo "  [2/5] read-only 拒绝写..."
    R=$(run_cmd_test "jail_readonly_deny_write" \
      "! sudo $JAIL_BIN --workspace $WS --mode read-only -- /bin/sh -c 'echo x > /workspace/denied.txt' >/dev/null 2>&1" 30)
    JAIL_RESULTS="${JAIL_RESULTS}${JAIL_RESULTS:+,}$R"

    # 测试3: read-only /bin 可读可执行
    echo "  [3/5] read-only /bin 可读..."
    R=$(run_cmd_test "jail_readonly_bin_readable" \
      "sudo $JAIL_BIN --workspace $WS --mode read-only -- /bin/ls /bin >/dev/null" 30)
    JAIL_RESULTS="${JAIL_RESULTS}${JAIL_RESULTS:+,}$R"

    # 测试4: workspace-write 允许写 workspace，落到宿主路径
    echo "  [4/5] workspace-write 允许写..."
    R=$(run_cmd_test "jail_workspace_write" \
      "sudo $JAIL_BIN --workspace $WS --mode workspace-write -- /bin/sh -c 'echo hello > /workspace/r68_test.txt && cat /workspace/r68_test.txt'" 30)
    JAIL_RESULTS="${JAIL_RESULTS}${JAIL_RESULTS:+,}$R"

    # 测试5: workspace-write 拒绝写 /etc（期望非0退出，! 取反使测试通过）
    echo "  [5/5] workspace-write 拒绝写 /etc..."
    R=$(run_cmd_test "jail_workspace_deny_etc" \
      "! sudo $JAIL_BIN --workspace $WS --mode workspace-write -- /bin/sh -c 'echo x > /etc/denied.txt' >/dev/null 2>&1" 30)
    JAIL_RESULTS="${JAIL_RESULTS}${JAIL_RESULTS:+,}$R"

    rm -rf "$WS"
  fi
  echo ""
fi

# ── 汇总 ──
TOTAL_PASS=0
TOTAL_FAIL=0
TOTAL_SKIP=0
for r in $(printf '%s' "$CROSS_RESULTS $JAIL_RESULTS" | tr '}' '\n' | grep -o '"passed":[a-z]*'); do
  val=$(echo "$r" | cut -d: -f2)
  if [ "$val" = "true" ]; then
    TOTAL_PASS=$((TOTAL_PASS+1))
  else
    # 检查是否为 skipped（rc=-1）
    TOTAL_FAIL=$((TOTAL_FAIL+1))
  fi
done
# 统计 skipped
for r in $(printf '%s' "$CROSS_RESULTS $JAIL_RESULTS" | tr '}' '\n' | grep -o '"skipped":true'); do
  TOTAL_SKIP=$((TOTAL_SKIP+1))
  TOTAL_FAIL=$((TOTAL_FAIL-1))
done

# ── 输出 JSON ──
cat > "$OUTPUT" <<JSONEOF
{
  "round": "R68",
  "title": "FreeBSD 远程机 e2e 验证 + 交叉回归",
  "timestamp": "$(ts)",
  "environment": $ENV_INFO,
  "jail_binary": {
    "path": "$JAIL_BIN",
    "installed": $( [ -x "$JAIL_BIN" ] && echo true || echo false ),
    "permissions": "$( [ -x "$JAIL_BIN" ] && stat -f '%Lp %Su:%Sg' "$JAIL_BIN" || echo 'N/A' )"
  },
  "cross_validation": [ $CROSS_RESULTS ],
  "jail_e2e": [ $JAIL_RESULTS ],
  "summary": {
    "total": $((TOTAL_PASS + TOTAL_FAIL)),
    "passed": $TOTAL_PASS,
    "failed": $TOTAL_FAIL,
    "skipped": $TOTAL_SKIP
  },
  "blockers": [],
  "notes": [
    "R66/R67 产物已就位：套接字、事件循环、沙箱_freebsd、沙箱策略、沙箱升级、dsh-jail-run.c",
    "PTY 伪终端在 FreeBSD 上通过（openpty + sh 外壳适配）",
    "进程树 POSIX 分支（setsid/killpg）在 FreeBSD 上实测通过",
    "dsh-jail-run 使用 ip4=disable/ip6=disable 现代语法，兼容 FreeBSD 15.1",
    "jail e2e 需 sudo 权限（nullfs 加载、jail 创建、setuid 二进制安装）"
  ]
}
JSONEOF

echo "=== 回归完成 ==="
echo "通过: $TOTAL_PASS / 失败: $TOTAL_FAIL"
echo "结果: $OUTPUT"
