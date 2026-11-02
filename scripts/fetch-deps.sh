#!/bin/sh
# scripts/fetch-deps.sh —— 一键拉齐 lightharness 的三个仓（light / lightplugin / lightharness）并平铺
#
# 为什么要有这个脚本：
#   lightharness 不是独立跑得起来的工程，它按「兄弟目录」查找两个外部依赖——
#     · light       光明编译器（判定标准：目录下有 src/）
#     · lightplugin 插件生态（含 集成/生产挂载.light —— 总入口 必需）
#   缺 lightplugin 时 src/总入口.light 的 `从 生产挂载 导入 挂载全部插件` 会报
#   `No module named '生产挂载'`，几十个 example 集体红，看着像代码坏了，
#   其实只是依赖仓没并排放。本脚本把三仓克隆到同一个目录下平铺，跑完即可冒烟。
#
# 用法：
#   bash scripts/fetch-deps.sh                       # 克隆到 ./lightharness-deps 并冒烟
#   bash scripts/fetch-deps.sh ~/ws                  # 指定目标目录
#   bash scripts/fetch-deps.sh --dir ~/ws --depth 1  # 浅克隆（快，但无历史）
#   bash scripts/fetch-deps.sh --mirror github       # 走 GitHub（默认 gitcode 国内直连）
#   bash scripts/fetch-deps.sh --no-run              # 只拉仓，不跑冒烟
#   bash scripts/fetch-deps.sh --dry-run             # 只打印计划，不动磁盘
#
# Windows：用 Git Bash 执行（cmd.exe / PowerShell 里没有 sh）：
#   & "C:\Program Files\Git\bin\bash.exe" scripts/fetch-deps.sh
#
# 退出码：0 成功；1 依赖缺失 / 克隆失败 / 冒烟失败；2 用法错误
#
# 只依赖 POSIX sh + git + python，不依赖 bash 扩展语法（FreeBSD /bin/sh、dash 均可跑）。

set -eu

# ---------------------------------------------------------------------------
# 用法
# ---------------------------------------------------------------------------
usage() {
  cat <<'EOF'
用法: fetch-deps.sh [选项] [目标目录]

把 light / lightplugin / lightharness 三个仓克隆到同一个目录下平铺，然后跑冒烟。

  -d, --dir DIR       目标目录（默认 ./lightharness-deps，也可用 LIGHTHARNESS_DEPS_DIR）
      --mirror NAME   仓库基址：gitcode（默认，国内直连）| github | 自定义基址 URL
      --depth N       浅克隆深度（默认全量；CI 上建议 --depth 1）
      --branch NAME   克隆指定分支（三个仓共用；默认各仓默认分支）
      --no-pull       目标目录里已有仓时不执行 git pull --ff-only
      --no-run        拉完仓不跑冒烟
      --dry-run       只打印将要执行的命令，不动磁盘
  -h, --help          显示本帮助

环境变量：
  LIGHTHARNESS_DEPS_DIR  同 --dir
  LIGHT_REPO / LIGHTPLUGIN_REPO / LIGHTHARNESS_REPO
                         单独覆盖某个仓的 URL（优先级最高，便于内网 / 私有镜像）
  GIT / PYTHON          指定 git / python 可执行文件

示例：
  bash scripts/fetch-deps.sh
  cd lightharness-deps/lightharness && python 运行.py examples/冒烟.light
EOF
}

die() {
  printf '错误: %s\n' "$*" >&2
  exit 1
}

usage_error() {
  printf '错误: %s\n' "$*" >&2
  usage >&2
  exit 2
}

# ---------------------------------------------------------------------------
# 解析参数
# ---------------------------------------------------------------------------
DIR=
MIRROR=gitcode
DEPTH=
BRANCH=
NO_PULL=0
NO_RUN=0
DRY_RUN=0

while [ $# -gt 0 ]; do
  case $1 in
    -h | --help)
      usage
      exit 0
      ;;
    -d | --dir)
      [ $# -ge 2 ] || usage_error "--dir 缺少目录参数"
      DIR=$2
      shift 2
      ;;
    --mirror)
      [ $# -ge 2 ] || usage_error "--mirror 缺少取值（github / gitcode / 基址 URL）"
      MIRROR=$2
      shift 2
      ;;
    --depth)
      [ $# -ge 2 ] || usage_error "--depth 缺少深度参数"
      DEPTH=$2
      shift 2
      ;;
    --branch)
      [ $# -ge 2 ] || usage_error "--branch 缺少分支名"
      BRANCH=$2
      shift 2
      ;;
    --no-pull) NO_PULL=1; shift ;;
    --no-run) NO_RUN=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --)
      shift
      break
      ;;
    -*)
      usage_error "未知选项: $1"
      ;;
    *)
      [ -z "$DIR" ] || usage_error "只能指定一个目标目录（已给: $DIR，又给了: $1）"
      DIR=$1
      shift
      ;;
  esac
done

[ $# -eq 0 ] || usage_error "多余的参数: $*"

DIR=${DIR:-${LIGHTHARNESS_DEPS_DIR:-./lightharness-deps}}

# ---------------------------------------------------------------------------
# 仓库基址 → 三个仓的 URL
# ---------------------------------------------------------------------------
case $MIRROR in
  gitcode) BASE=https://gitcode.com/skywalk163 ;;
  github) BASE=https://github.com/skywalk163 ;;
  *://*) BASE=$MIRROR ;;   # 自定义基址（内网 Gitea / 私有镜像）
  *) usage_error "--mirror 只接受 github / gitcode / 以 :// 开头的基址，收到: $MIRROR" ;;
esac
BASE=${BASE%/}

LIGHT_REPO=${LIGHT_REPO:-$BASE/light.git}
LIGHTPLUGIN_REPO=${LIGHTPLUGIN_REPO:-$BASE/lightplugin.git}
LIGHTHARNESS_REPO=${LIGHTHARNESS_REPO:-$BASE/lightharness.git}

# ---------------------------------------------------------------------------
# 依赖检查
# ---------------------------------------------------------------------------
GIT=${GIT:-git}
command -v "$GIT" >/dev/null 2>&1 || die "找不到 git（用 GIT=/path/to/git 指定）"

find_python() {
  for cand in "${PYTHON:-}" python3 python; do
    [ -n "$cand" ] || continue
    if command -v "$cand" >/dev/null 2>&1; then
      printf '%s\n' "$cand"
      return 0
    fi
  done
  return 1
}

PY=
if [ "$NO_RUN" -eq 0 ]; then
  PY=$(find_python) || die "找不到 python3/python（用 PYTHON=... 指定，或加 --no-run 跳过冒烟）"
fi

# ---------------------------------------------------------------------------
# 克隆 / 更新
# ---------------------------------------------------------------------------
clone_repo() {
  name=$1
  url=$2
  dest=$3

  if [ -d "$dest/.git" ]; then
    if [ "$NO_PULL" -eq 1 ]; then
      printf '跳过（已存在）: %s\n' "$dest"
    elif [ "$DRY_RUN" -eq 1 ]; then
      printf '[dry-run] git -C %s pull --ff-only\n' "$dest"
    else
      printf '更新: %s\n' "$dest"
      # 更新失败不算致命：本地可能有未提交改动或无网络，保留现有内容继续走
      "$GIT" -C "$dest" pull --ff-only || printf '警告: %s 更新失败，保留现有内容继续\n' "$dest" >&2
    fi
    return 0
  fi

  if [ -e "$dest" ]; then
    die "$dest 已存在但不是 git 仓库（不是空目录？），请先移走再重跑"
  fi

  printf '克隆 %s: %s -> %s\n' "$name" "$url" "$dest"
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '[dry-run] %s clone%s%s %s %s\n' "$GIT" \
      "${DEPTH:+ --depth $DEPTH}" "${BRANCH:+ --branch $BRANCH}" "$url" "$dest"
    return 0
  fi

  if [ -n "$DEPTH" ] && [ -n "$BRANCH" ]; then
    "$GIT" clone --depth "$DEPTH" --branch "$BRANCH" "$url" "$dest" || clone_failed "$url" "$dest"
  elif [ -n "$DEPTH" ]; then
    "$GIT" clone --depth "$DEPTH" "$url" "$dest" || clone_failed "$url" "$dest"
  elif [ -n "$BRANCH" ]; then
    "$GIT" clone --branch "$BRANCH" "$url" "$dest" || clone_failed "$url" "$dest"
  else
    "$GIT" clone "$url" "$dest" || clone_failed "$url" "$dest"
  fi
}

clone_failed() {
  url=$1
  dest=$2
  printf '错误: 克隆失败 %s\n' "$url" >&2
  printf '  网络直连不通时换成可达的镜像重试：\n' >&2
  printf '    bash %s --mirror github|gitcode --dir %s\n' "$0" "$DIR" >&2
  printf '  或只覆盖某一个仓（内网 Gitea / 私有镜像）：\n' >&2
  printf '    LIGHT_REPO=<url> LIGHTPLUGIN_REPO=<url> LIGHTHARNESS_REPO=<url> bash %s --dir %s\n' "$0" "$DIR" >&2
  # 清掉 clone 留下的半成品目录，方便重跑（只删目标目录内的路径）
  case $dest in
    "$ABS_DIR"/*) rm -rf -- "$dest" ;;
  esac
  exit 1
}

printf '== 目标目录: %s（镜像: %s）\n' "$DIR" "$MIRROR"
if [ "$DRY_RUN" -eq 0 ]; then
  mkdir -p -- "$DIR"
fi

# 相对路径在 cd 之后会失效，统一换成绝对路径
if [ "$DRY_RUN" -eq 1 ]; then
  ABS_DIR=$DIR
else
  ABS_DIR=$(CDPATH= cd -- "$DIR" && pwd) || die "进不去目标目录: $DIR"
fi

clone_repo light "$LIGHT_REPO" "$ABS_DIR/light"
clone_repo lightplugin "$LIGHTPLUGIN_REPO" "$ABS_DIR/lightplugin"
clone_repo lightharness "$LIGHTHARNESS_REPO" "$ABS_DIR/lightharness"

# ---------------------------------------------------------------------------
# 布局校验：三仓必须平铺在同一层，且各仓的标志物在位
# ---------------------------------------------------------------------------
if [ "$DRY_RUN" -eq 0 ]; then
  printf '== 校验布局\n'
  [ -d "$ABS_DIR/light/src" ] || die "light 缺 src/（光明编译器没拉全）: $ABS_DIR/light"
  [ -d "$ABS_DIR/lightplugin/集成" ] || die "lightplugin 缺 集成/（插件生态没拉全）: $ABS_DIR/lightplugin"
  [ -f "$ABS_DIR/lightharness/运行.py" ] || die "lightharness 缺 运行.py: $ABS_DIR/lightharness"
  printf '   ok  %s/{light,lightplugin,lightharness}\n' "$ABS_DIR"
fi

# ---------------------------------------------------------------------------
# 冒烟：跑 examples/冒烟.light，有输出即说明三仓接线通了
# ---------------------------------------------------------------------------
if [ "$NO_RUN" -eq 1 ]; then
  :
elif [ "$DRY_RUN" -eq 1 ]; then
  printf '[dry-run] (cd %s/lightharness && %s 运行.py examples/冒烟.light)\n' "$ABS_DIR" "$PY"
else
  printf '== 冒烟：%s 运行.py examples/冒烟.light\n' "$PY"
  # 显式导出两个依赖根：即使目录名不叫 light / light-merge，运行.py 也能命中
  (
    cd "$ABS_DIR/lightharness" || exit 1
    LIGHT_MERGE=$ABS_DIR/light
    LIGHTPLUGIN=$ABS_DIR/lightplugin
    export LIGHT_MERGE LIGHTPLUGIN
    exec "$PY" 运行.py examples/冒烟.light
  ) || die "冒烟失败（依赖已拉齐，但运行.py 没跑通；看上面的报错）"
fi

# ---------------------------------------------------------------------------
# 下一步提示
# ---------------------------------------------------------------------------
cat <<EOF

== 完成：三仓已平铺在 $ABS_DIR
   $ABS_DIR/light          光明编译器
   $ABS_DIR/lightplugin    插件生态
   $ABS_DIR/lightharness   本工程

下一步：
  cd "$ABS_DIR/lightharness"
  python 运行.py examples/冒烟.light
  python 运行.py examples/运行Web服务器.light

目录不在默认位置时，运行.py 也能靠环境变量找到依赖：
  LIGHT_MERGE="$ABS_DIR/light" LIGHTPLUGIN="$ABS_DIR/lightplugin" python 运行.py ...
EOF
