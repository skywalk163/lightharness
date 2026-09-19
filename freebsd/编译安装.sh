#!/bin/sh
# R68 子任务 68.1 —— dsh-jail-run 编译安装脚本
#
# 在 FreeBSD 远程机上编译 setuid-root 的 dsh-jail-run 二进制，
# 安装到 /usr/local/sbin/dsh-jail-run，权限 root:wheel 4755。
#
# 用法（在 FreeBSD 上执行）：
#   sh freebsd/编译安装.sh              # 编译+安装+验证
#   sh freebsd/编译安装.sh --verify     # 仅验证已安装的二进制
#   sh freebsd/编译安装.sh --clean      # 卸载二进制
#
# 前置条件：
#   - 源码位于 lightharness/freebsd/dsh-jail-run.c（R67 从上游复制）
#   - 当前用户有 sudo 免密权限（用于 chown + chmod 4755 + 安装到 /usr/local/sbin）
#   - clang 已安装（FreeBSD base 自带 /usr/bin/cc）
#   - nullfs 内核模块可加载（sudo kldload nullfs）

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="${SCRIPT_DIR}/dsh-jail-run.c"
BIN="/usr/local/sbin/dsh-jail-run"
TMP_BIN="/tmp/dsh-jail-run.$$"

# ── 颜色 ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { printf "${GREEN}[编译安装]${NC} %s\n" "$*"; }
warn()  { printf "${YELLOW}[编译安装]${NC} %s\n" "$*"; }
error() { printf "${RED}[编译安装]${NC} %s\n" "$*" >&2; }

# ── 子命令 ──
ACTION="${1:-install}"

case "$ACTION" in
  --verify|-v)
    # 仅验证
    if [ ! -x "$BIN" ]; then
      error "$BIN 不存在或不可执行"
      exit 1
    fi
    info "二进制: $(ls -la "$BIN")"
    if [ -u "$BIN" ]; then
      info "setuid 位: 已设置 ✅"
    else
      error "setuid 位未设置"
      exit 1
    fi
    # 烟雾测试：read-only 模式跑 true
    if "$BIN" --workspace /tmp --mode read-only -- true 2>/dev/null; then
      info "烟雾测试 PASS: read-only + true 退出码 0"
    else
      rc=$?
      warn "烟雾测试退出码 $rc（若 jail 基础设施未就绪可能非0）"
    fi
    exit 0
    ;;

  --clean|-c)
    # 卸载
    if [ -f "$BIN" ]; then
      sudo rm -f "$BIN"
      info "已删除 $BIN"
    else
      warn "$BIN 不存在，无需清理"
    fi
    exit 0
    ;;

  --help|-h)
    sed -n '1,20p' "$0"
    exit 0
    ;;
esac

# ── install ──
info "=== dsh-jail-run 编译安装 ==="

# 1. 检查源码
if [ ! -f "$SRC" ]; then
  error "源码不存在: $SRC"
  error "R67 应从上游复制 freebsd/dsh-jail-run.c 到 lightharness/freebsd/"
  error "当前缺失，无法编译。请先完成 R67 子任务 67.1 的源码复制。"
  exit 1
fi
info "源码: $SRC ($(wc -c < "$SRC") bytes)"

# 2. 检查编译器
if ! command -v cc >/dev/null 2>&1; then
  error "找不到 C 编译器 (cc)，请安装 clang: pkg install clang"
  exit 1
fi
info "编译器: $(cc --version | head -1)"

# 3. 检查 sudo
if ! sudo -n true 2>/dev/null; then
  error "需要 sudo 免密权限（用于 chown root:wheel + chmod 4755 + 安装到 /usr/local/sbin）"
  exit 1
fi
info "sudo: 免密可用"

# 4. 加载 nullfs（jail 运行时需要）
if ! sysctl -n vfs.nullfs >/dev/null 2>&1; then
  info "加载 nullfs 内核模块..."
  sudo kldload nullfs
fi
info "nullfs: 已加载 (vfs.nullfs=$(sysctl -n vfs.nullfs 2>/dev/null || echo N/A))"

# 5. 编译（jailparam_* 函数在 libjail 中，必须 -ljail）
info "编译中..."
cc -O2 -Wall -Wextra -o "$TMP_BIN" "$SRC" -ljail
info "编译成功: $TMP_BIN ($(wc -c < "$TMP_BIN") bytes)"

# 6. 安装到 /usr/local/sbin
info "安装到 $BIN ..."
sudo install -o root -g wheel -m 4755 "$TMP_BIN" "$BIN"
rm -f "$TMP_BIN"

# 7. 验证
info "安装验证:"
ls -la "$BIN"
# FreeBSD stat %Lp 不包含 setuid 位，用 test -u 验证 setuid + 权限位
if [ ! -u "$BIN" ]; then
  error "setuid 位未设置（期望 -rwsr-xr-x）"
  exit 1
fi
PERMS="$(stat -f '%Lp' "$BIN")"
if [ "$PERMS" != "755" ]; then
  error "权限位错误: 期望 755（+setuid），实际 $PERMS"
  exit 1
fi
info "权限验证: setuid-root + rwxr-xr-x ✅"

# 8. 烟雾测试
info "烟雾测试: dsh-jail-run --workspace /tmp --mode read-only -- true"
if "$BIN" --workspace /tmp --mode read-only -- true; then
  info "烟雾测试 PASS ✅"
else
  rc=$?
  warn "烟雾测试退出码 $rc（jail 基础设施可能需要额外配置）"
fi

info "=== 编译安装完成 ==="
info "二进制: $BIN"
info "权限: root:wheel 4755 (setuid)"
