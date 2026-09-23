#!/bin/sh
# R87 任务F（运维债）—— FreeBSD 0.82 环境固化（重启后一键恢复）
#
# 作用：把 0.82 门禁在「重启后失效」的环境项幂等恢复，使其回到 R86 收口状态。
#   * sudo kldload nullfs（幂等：已加载则跳过）
#   * dsh-jail-run setuid 安装/校验（test -u，复用 编译安装.sh）
#   * python 垫片校验（/tmp/r44-shim、/tmp/r80b-shim → python3.12）
#   * python3.12 的 pytest 插件校验（xdist / pytest_timeout / psutil，pip --user 幂等补装）
#   * /tmp/test-sandbox 预建（1777，jail/sandbox 用例工作根）
#
# 幂等：重复执行结果一致，已就绪的项直接跳过，不报错、不改写。
#
# 用法（在 0.82 上执行；脚本位于 lightharness/freebsd/）：
#   sh freebsd/初始化.sh                 # 环境恢复（默认）
#   sh freebsd/初始化.sh --verify        # 仅校验，缺失项报错但不安装
#   sh freebsd/初始化.sh --jail-only     # 环境恢复后跑 jail e2e（须位于已 sync 的 lightharness 根）
#   sh freebsd/初始化.sh --help
#
# 前置条件：
#   - 当前用户有 sudo 免密权限（chown/chmod 4755、kldload、jail 创建）
#   - cc 已安装（FreeBSD base 自带 /usr/bin/cc）
#   - lightharness/freebsd/dsh-jail-run.c 与 编译安装.sh、远程回归.sh 同在源树
#
# ⚠️ 红线：本脚本仅恢复「重启后失效」的环境项；不修改系统 Python 主环境（插件走 --user），
#   不触碰 /tmp 副本外的源码仓库，不 commit/push。

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FREEBSD_DIR="$SCRIPT_DIR"
BIN="/usr/local/sbin/dsh-jail-run"
PY="/usr/local/bin/python3.12"
SHIM_R44="/tmp/r44-shim"
SHIM_R80="/tmp/r80b-shim"
TEST_SANDBOX="/tmp/test-sandbox"

# ── 颜色 ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
info() { printf "${GREEN}[初始化]${NC} %s\n" "$*"; }
warn() { printf "${YELLOW}[初始化]${NC} %s\n" "$*"; }
err()  { printf "${RED}[初始化]${NC} %s\n" "$*" >&2; }

# ── 模式 ──
ACTION="${1:-init}"
VERIFY_ONLY=0
JAIL_CHECK=0
case "$ACTION" in
  --verify)    VERIFY_ONLY=1 ;;
  --jail-only) JAIL_CHECK=1 ;;
  init|-i|"")  ;;
  --help|-h)   sed -n '1,22p' "$0"; exit 0 ;;
  *)           err "未知参数: $ACTION"; exit 1 ;;
esac

# ── 1) nullfs（jail 运行时依赖，重启后失效）──
ensure_nullfs() {
  if [ "$(sysctl -n vfs.nullfs 2>/dev/null)" = "1" ]; then
    info "nullfs: 已加载 ✅"
  else
    info "nullfs: 未加载，sudo kldload nullfs ..."
    if [ "$VERIFY_ONLY" = "1" ]; then
      err "nullfs 未加载（--verify 模式不加载）"; return 1
    fi
    sudo kldload nullfs || { err "kldload nullfs 失败"; return 1; }
    info "nullfs: 已加载 ✅"
  fi
}

# ── 2) dsh-jail-run setuid 二进制（重启后失效项：实际是文件持久，但校验其存在/权限）──
ensure_jail_run() {
  if [ -u "$BIN" ] && [ -x "$BIN" ]; then
    info "dsh-jail-run: 已安装且 setuid ✅ ($(ls -la "$BIN" | awk '{print $1, $3, $4}'))"
    return 0
  fi
  if [ "$VERIFY_ONLY" = "1" ]; then
    err "dsh-jail-run 未就绪（--verify 模式不安装）"; return 1
  fi
  info "dsh-jail-run: 缺失或未设 setuid，调用 编译安装.sh ..."
  sh "$FREEBSD_DIR/编译安装.sh" || { err "编译安装.sh 失败"; return 1; }
}

# ── 3) python 垫片（test 子进程硬编码 `python`/`python3`，0.82 无该命令）──
ensure_shim() {
  for d in "$SHIM_R44" "$SHIM_R80"; do
    mkdir -p "$d"
    if [ ! -x "$d/python" ]; then
      if [ "$VERIFY_ONLY" = "1" ]; then
        err "垫片缺失: $d/python（--verify 模式不创建）"; return 1
      fi
      printf '#!/bin/sh\nexec %s "$@"\n' "$PY" > "$d/python"
      cp "$d/python" "$d/python3"
      chmod +x "$d/python" "$d/python3"
      info "垫片就绪: $d/python -> $PY"
    else
      info "垫片已存在: $d/python -> $(grep -o "$PY" "$d/python" 2>/dev/null | head -1 || echo UNKNOWN)"
    fi
  done
}

# ── 4) python3.12 pytest 插件（E 路 §4 环境欠账：0.82 的 3.12 当前缺 xdist/timeout）──
#    LM 全量走 3.12 + addopts（-n auto --timeout=60），缺插件会 ARGERROR（rc=4）。
#    走 pip --user（用户侧，不碰系统 site-packages 主环境），幂等。
ensure_pytest_plugins() {
  for pair in "xdist:pytest-xdist" "pytest_timeout:pytest-timeout" "psutil:psutil"; do
    mod="${pair%%:*}"; pkg="${pair##*:}"
    if "$PY" -c "import $mod" >/dev/null 2>&1; then
      info "pytest 插件 $mod: 已装 ✅"
      continue
    fi
    if [ "$VERIFY_ONLY" = "1" ]; then
      err "pytest 插件缺失: $mod（--verify 模式不安装）"; return 1
    fi
    info "pytest 插件 $mod: 安装中 (pip install --user $pkg) ..."
    if ! "$PY" -m pip install --user --quiet "$pkg" 2>/dev/null; then
      # pip 本体可能缺失：先 ensurepip（--user）再重试一次
      "$PY" -m ensurepip --user >/dev/null 2>&1 || true
      "$PY" -m pip install --user --quiet "$pkg" 2>/dev/null \
        || { err "安装 $pkg 失败（检查 0.82 网络/PyPI 可达性或手动安装）"; return 1; }
    fi
    info "pytest 插件 $mod: 已装 ✅"
  done
}

# ── 5) /tmp/test-sandbox 预建（jail/sandbox 用例工作根；1777 = 粘性可写临时目录）──
ensure_test_sandbox() {
  if [ -d "$TEST_SANDBOX" ]; then
    info "测试沙箱目录: 已存在 $TEST_SANDBOX"
  else
    mkdir -p "$TEST_SANDBOX"
    chmod 1777 "$TEST_SANDBOX"
    info "测试沙箱目录: 已预建 $TEST_SANDBOX (mode 1777)"
  fi
}

# ── 6) 可选：jail e2e 5/5 验证（须位于已 sync 的 lightharness 根）──
run_jail_check() {
  OUT="$FREEBSD_DIR/../reports/R87_jail_e2e.json"
  info "运行 jail e2e 验证 (freebsd/远程回归.sh --jail-only -> $OUT) ..."
  sh "$FREEBSD_DIR/远程回归.sh" --jail-only --output "$OUT" || {
    err "远程回归.sh 执行异常"; return 1
  }
  # 解析 jail_e2e 列表，统计 passed / total（python3.12 可用；路径经 argv 传入，避免 heredoc 展开）
  "$PY" - "$OUT" <<'PYEOF'
import json, sys
out = sys.argv[1]
try:
    d = json.load(open(out))
except Exception as e:
    print("  [初始化] 无法解析 JSON:", e); sys.exit(2)
je = d.get("jail_e2e", [])
tests = [t for t in je if isinstance(t, dict)]
passed = sum(1 for t in tests if t.get("passed"))
total = len(tests)
print("  [初始化] jail e2e: %d / %d 通过" % (passed, total))
sys.exit(0 if (total == 5 and passed == 5) else 1)
PYEOF
  rc=$?
  if [ "$rc" = "0" ]; then
    info "jail e2e 5/5 全绿 ✅"
  else
    err "jail e2e 未达 5/5（passed/total 见上，或 JSON 解析失败）"; return 1
  fi
}

# ── 主流程 ──
main() {
  info "=== R87-F 0.82 环境固化（幂等）==="
  info "模式: $([ "$VERIFY_ONLY" = 1 ] && echo verify || echo init)$([ "$JAIL_CHECK" = 1 ] && echo ' + jail-check')"
  info "python: $PY | jail-bin: $BIN"

  fail=0
  ensure_nullfs        || fail=1
  ensure_jail_run      || fail=1
  ensure_shim          || fail=1
  ensure_pytest_plugins|| fail=1
  ensure_test_sandbox  || fail=1

  if [ "$fail" = "1" ]; then
    err "=== 环境恢复存在未就绪项（见上）==="
    [ "$VERIFY_ONLY" = "1" ] && exit 1 || exit 1
  fi

  info "=== 环境恢复完成（全部就绪）==="

  if [ "$JAIL_CHECK" = "1" ]; then
    run_jail_check || exit 1
  else
    info "提示：如需验证 jail e2e 5/5，于已 sync 的 lightharness 根执行：sh freebsd/初始化.sh --jail-only"
  fi
  exit 0
}

main "$@"
