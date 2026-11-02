#!/bin/sh
# lightharness 一键冒烟（T-0238）
#
# 只验两件事，全程只读、不写仓内任何文件：
#
#   1) 三仓依赖齐：本仓 lightharness、光明编译器仓（light / light-merge，含 src/）、
#      lightplugin（含 集成/生产挂载.light）。缺哪个就直接说缺哪个。
#   2) python 运行.py examples/冒烟.light 退出码 0。
#
# 为什么要有「依赖预检」：
#   lightharness 按兄弟目录找两个外部仓。缺 lightplugin 时 src/总入口.light 的
#   `从 生产挂载 导入 挂载全部插件` 会报 `No module named '生产挂载'`，几十个
#   example 集体红——看着像代码坏了，其实只是依赖仓没并排放。本脚本在跑
#   运行.py 之前先把三仓标志物（src/、集成/生产挂载.light）逐一确认，缺了直接
#   点名，不再让这句迷惑性错误漏到用户眼前。
#
# 用法：
#   sh smoke.sh              # 全跑
#
# 环境变量（可选，覆盖默认兄弟目录探测）：
#   LIGHT_MERGE    光明编译器仓根目录（含 src/）
#   LIGHTPLUGIN    插件生态仓根目录（含 集成/生产挂载.light）
#
# 依赖：sh、Python 3.8+。不需要网络。
# 平台：FreeBSD/Linux/macOS 直接跑；Windows 用 Git Bash 的 sh 跑。

set -u

# Git Bash 里直接 `sh smoke.sh` 时 PATH 往往只有 Windows 那份，拿不到 mkdir/rm 等。
# 补上 /usr/bin 就够；FreeBSD 上这两个目录本来就在 PATH 里，重复一次无副作用。
PATH="/usr/bin:/bin:$PATH"

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || {
    echo "smoke: 定位不到脚本所在目录" >&2
    exit 2
}

FAIL=0

say() { printf '%s\n' "$*"; }
ok()  { printf '  ok   %s\n' "$*"; }
bad() { printf '  FAIL %s\n' "$*" >&2; FAIL=$((FAIL + 1)); }

# 子串判断用 shell 的 case，不走 grep —— Windows worker 上 grep 不在 PATH。
has() {
    case "$1" in
        *"$2"*) return 0 ;;
    esac
    return 1
}

# 把 MSYS 风格路径（/tmp/x）转成原生 Windows 形式（C:/.../x），否则原生 python.exe
# 会把它当成当前盘符下的 \tmp\x。非 Windows 原样返回。
native() {
    if command -v cygpath >/dev/null 2>&1; then
        cygpath -m -- "$1"
    else
        printf '%s\n' "$1"
    fi
}

# --------------------------------------------------------------------------- #
say "== 0/3 环境 =="

# 本仓标志：运行.py 必须在脚本隔壁
if [ ! -f "$DIR/运行.py" ]; then
    say "smoke: $DIR 下没有 运行.py —— smoke.sh 必须放在 lightharness 仓根目录" >&2
    exit 2
fi
ok "lightharness 仓根：$DIR"

# 优先 python3；Windows 上 python3 常是应用商店占位 stub，所以拿「版本 >= 3.8」当判据。
PY=""
for c in python3 python; do
    command -v "$c" >/dev/null 2>&1 || continue
    if "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' \
            >/dev/null 2>&1; then
        PY=$c
        break
    fi
done
if [ -z "$PY" ]; then
    say "smoke: 找不到 Python 3.8+（运行.py 需要）" >&2
    exit 2
fi
ok "python：$PY（$("$PY" -V 2>&1)）"

# --------------------------------------------------------------------------- #
say "== 1/3 三仓依赖预检 =="

# —— 1a) 光明编译器仓（light / light-merge）——
# 判定标准照抄 运行.py:_find_light_merge：目录下有 src/ 即命中。
# 候选顺序也照抄，唯一区别是显式 LIGHT_MERGE 永远最优先。
LM_FOUND=""
LM_CANDIDATES=""
if [ -n "${LIGHT_MERGE:-}" ]; then
    LM_CANDIDATES="$LIGHT_MERGE"
fi
# 兄弟目录候选（脚本所在目录的上一级）
LM_CANDIDATES="$LM_CANDIDATES $DIR/../light $DIR/../light-merge"
LM_CANDIDATES="$LM_CANDIDATES $DIR/../duan-light-merge/light-merge $DIR/../../light"

for cand in $LM_CANDIDATES; do
    [ -d "$cand/src" ] && { LM_FOUND=$cand; break; }
done

if [ -z "$LM_FOUND" ]; then
    bad "缺光明编译器仓（light / light-merge）"
    say "     期望：与本仓平铺在同一层的兄弟目录，且目录下有 src/。"
    say "     已探测："
    for cand in $LM_CANDIDATES; do
        say "       - $cand （无 src/）"
    done
    say "     修法："
    say "       export LIGHT_MERGE=/path/to/light   # 指向含 src/ 的编译器仓根"
    say "       # 或把 light 仓平铺到 $DIR/../light"
else
    ok "光明编译器：$LM_FOUND （有 src/）"
fi

# —— 1b) 插件生态仓 lightplugin ——
# 判定标准：含 集成/生产挂载.light（总入口 必需）。缺它时运行期会报
# `No module named 生产挂载`，极具迷惑性，所以这里单独点名。
LP_FOUND=""
LP_CANDIDATES=""
if [ -n "${LIGHTPLUGIN:-}" ]; then
    LP_CANDIDATES="$LIGHTPLUGIN"
fi
LP_CANDIDATES="$LP_CANDIDATES $DIR/../lightplugin"

for cand in $LP_CANDIDATES; do
    [ -f "$cand/集成/生产挂载.light" ] && { LP_FOUND=$cand; break; }
done

if [ -z "$LP_FOUND" ]; then
    bad "缺 lightplugin 仓（插件生态）"
    say "     期望：与本仓平铺在同一层的兄弟目录，且含 集成/生产挂载.light。"
    say "     已探测："
    for cand in $LP_CANDIDATES; do
        say "       - $cand （无 集成/生产挂载.light）"
    done
    say "     注意：缺这个仓时运行.py 不会立刻报错，而是在 examples 跑到总入口时"
    say "           抛 No module named '生产挂载' —— 看着像代码坏了，其实只是没并排放。"
    say "     修法："
    say "       export LIGHTPLUGIN=/path/to/lightplugin"
    say "       # 或把 lightplugin 仓平铺到 $DIR/../lightplugin"
else
    ok "lightplugin：$LP_FOUND （有 集成/生产挂载.light）"
fi

if [ "$FAIL" -gt 0 ]; then
    say ""
    say "smoke: ✗ $FAIL 项依赖未通过 —— 不跑 examples 了（跑了也只会报迷惑性错误）"
    say "smoke: 按上面的修法把缺的仓补齐，或用 LIGHT_MERGE / LIGHTPLUGIN 指过去再跑。"
    exit 1
fi

# 把命中的绝对路径导出，喂给子进程里的 运行.py（即使目录名不叫 light/lightplugin 也能命中）
LIGHT_MERGE=$(native "$LM_FOUND")
LIGHTPLUGIN=$(native "$LP_FOUND")
export LIGHT_MERGE LIGHTPLUGIN

# --------------------------------------------------------------------------- #
say "== 2/3 examples/冒烟.light =="

DIR_N=$(native "$DIR")
last_out=$(cd "$DIR_N" && "$PY" 运行.py examples/冒烟.light 2>&1)
rc=$?

if [ "$rc" -eq 0 ] && has "$last_out" "自包含 stdlib 冒烟测试通过"; then
    ok "examples/冒烟.light 退出码 0，输出含「自包含 stdlib 冒烟测试通过」"
    # 把 stdout 原样打出来当证据（一行行打，避免依赖 cat/echo 之外的工具）
    say "     ---- 脚本输出 ----"
    # shellcheck disable=SC2086
    oldIFS=$IFS; IFS='
'
    for line in $last_out; do
        say "       $line"
    done
    IFS=$oldIFS
else
    bad "examples/冒烟.light 没跑通（退出码 $rc）"
    say "     ---- 脚本输出 ----"
    oldIFS=$IFS; IFS='
'
    for line in $last_out; do
        say "       $line"
    done
    IFS=$oldIFS
    # 常见迷惑错误的对症提示（用 shell 的 case 判断，不走 grep/sed/head）
    if has "$last_out" "生产挂载"; then
        say "     提示：报的是 生产挂载 —— 这是 lightplugin 没接好的典型症状，"
        say "           但本脚本第 1 步已确认 lightplugin 目录在位，说明问题在仓的"
        say "           版本/接线，而不是目录没并排。看上面原始输出定位。"
    elif has "$last_out" "No module named"; then
        say "     提示：报的是 No module named —— 多半是某个 .light 模块没被导入钩子"
        say "           找到。本脚本第 1 步只校验了 light / lightplugin 两个仓的标志物，"
        say "           若它们版本不对，也会出现这种症状。"
    fi
fi

# --------------------------------------------------------------------------- #
say ""
if [ "$FAIL" -gt 0 ]; then
    say "smoke: ✗ $FAIL 项未通过"
    exit 1
fi
say "smoke: ✓ 全部通过（依赖齐 + 冒烟退出码 0）"
