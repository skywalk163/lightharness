# scripts/fetch-deps.ps1 —— 一键拉齐 lightharness 的三个仓（light / lightplugin / lightharness）并平铺
#
# 为什么要有这个脚本：
#   lightharness 不是独立跑得起来的工程，它按「兄弟目录」查找两个外部依赖——
#     · light       光明编译器（判定标准：目录下有 src/）
#     · lightplugin 插件生态（含 集成/生产挂载.light —— 总入口 必需）
#   缺 lightplugin 时 src/总入口.light 的 `从 生产挂载 导入 挂载全部插件` 会报
#   `No module named '生产挂载'`，几十个 example 集体红，看着像代码坏了，
#   其实只是依赖仓没并排放。本脚本把三仓克隆到同一个目录下平铺，跑完即可冒烟。
#
# 本文件是 scripts/fetch-deps.sh 的 Windows 原生 PowerShell 版：不依赖 Git Bash，
# 参数与 sh 版一一对应（-Dir / -Mirror / -Depth / -Branch / -NoPull / -NoRun / -DryRun）。
#
# 用法（在仓库根目录或任意目录执行均可）：
#   powershell -File scripts/fetch-deps.ps1                 # 克隆到 ./lightharness-deps 并冒烟
#   powershell -File scripts/fetch-deps.ps1 -Dir C:\ws      # 指定目标目录
#   powershell -File scripts/fetch-deps.ps1 -Depth 1        # 浅克隆（快，但无历史）
#   powershell -File scripts/fetch-deps.ps1 -Mirror github  # 走 GitHub（默认 gitcode 国内直连）
#   powershell -File scripts/fetch-deps.ps1 -NoRun          # 只拉仓，不跑冒烟
#   powershell -File scripts/fetch-deps.ps1 -DryRun         # 只打印计划，不动磁盘
#
# 环境变量：LIGHTHARNESS_DEPS_DIR / LIGHT_REPO / LIGHTPLUGIN_REPO / LIGHTHARNESS_REPO
#           GIT / PYTHON（指定可执行文件）
#
# 退出码：0 成功；1 依赖缺失 / 克隆失败 / 冒烟失败；2 用法错误
#
# 只依赖 PowerShell 5.1+、git、python；不调用 bash / head / grep / awk。

param(
    [Parameter(Position = 0)]
    [string]$Dir,
    [string]$Mirror = 'gitcode',
    [string]$Depth,
    [string]$Branch,
    [switch]$NoPull,
    [switch]$NoRun,
    [switch]$DryRun,
    [Alias('h')]
    [switch]$Help
)

$ErrorActionPreference = 'Continue'
$script:DryRun = [bool]$DryRun
$script:NoPull = [bool]$NoPull
$script:Depth = $Depth
$script:Branch = $Branch

# ---------------------------------------------------------------------------
# 用法
# ---------------------------------------------------------------------------
function Show-Usage {
    Write-Host @'
用法: powershell -File scripts/fetch-deps.ps1 [选项] [目标目录]

把 light / lightplugin / lightharness 三个仓克隆到同一个目录下平铺，然后跑冒烟。
参数与 scripts/fetch-deps.sh 语义一致（sh 的 --dir 对应 -Dir，依此类推）。

  -Dir DIR        目标目录（默认 ./lightharness-deps，也可用 LIGHTHARNESS_DEPS_DIR）
  -Mirror NAME    仓库基址：gitcode（默认，国内直连）| github | 自定义基址 URL
  -Depth N        浅克隆深度（默认全量；CI 上建议 -Depth 1）
  -Branch NAME    克隆指定分支（三个仓共用；默认各仓默认分支）
  -NoPull         目标目录里已有仓时不执行 git pull --ff-only
  -NoRun          拉完仓不跑冒烟
  -DryRun         只打印将要执行的命令，不动磁盘
  -Help           显示本帮助

环境变量：
  LIGHTHARNESS_DEPS_DIR  同 -Dir
  LIGHT_REPO / LIGHTPLUGIN_REPO / LIGHTHARNESS_REPO
                         单独覆盖某个仓的 URL（优先级最高，便于内网 / 私有镜像）
  GIT / PYTHON           指定 git / python 可执行文件

示例：
  powershell -File scripts/fetch-deps.ps1
  cd lightharness-deps/lightharness; python 运行.py examples/冒烟.light
'@
}

function Die([string]$Message) {
    Write-Error ("错误: {0}" -f $Message)
    exit 1
}

function Usage-Error([string]$Message) {
    Write-Error ("错误: {0}" -f $Message)
    Show-Usage
    exit 2
}

if ($Help) {
    Show-Usage
    exit 0
}

# ---------------------------------------------------------------------------
# 参数收口（位置参数 / 环境变量 / 默认值）
# ---------------------------------------------------------------------------
if ([string]::IsNullOrWhiteSpace($Dir)) {
    $Dir = $env:LIGHTHARNESS_DEPS_DIR
}
if ([string]::IsNullOrWhiteSpace($Dir)) {
    $Dir = './lightharness-deps'
}

# ---------------------------------------------------------------------------
# 仓库基址 → 三个仓的 URL
# ---------------------------------------------------------------------------
if ($Mirror -eq 'gitcode') {
    $Base = 'https://gitcode.com/skywalk163'
} elseif ($Mirror -eq 'github') {
    $Base = 'https://github.com/skywalk163'
} elseif ($Mirror -match '://') {
    $Base = $Mirror
} else {
    Usage-Error ("-Mirror 只接受 github / gitcode / 以 :// 开头的基址，收到: {0}" -f $Mirror)
}
$Base = $Base.TrimEnd('/')

$LightRepo = if ($env:LIGHT_REPO) { $env:LIGHT_REPO } else { "$Base/light.git" }
$LightPluginRepo = if ($env:LIGHTPLUGIN_REPO) { $env:LIGHTPLUGIN_REPO } else { "$Base/lightplugin.git" }
$LightHarnessRepo = if ($env:LIGHTHARNESS_REPO) { $env:LIGHTHARNESS_REPO } else { "$Base/lightharness.git" }

# ---------------------------------------------------------------------------
# 依赖检查
# ---------------------------------------------------------------------------
$GitName = if ($env:GIT) { $env:GIT } else { 'git' }
$GitCmd = Get-Command -Name $GitName -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $GitCmd) {
    Die ("找不到 git（用 GIT 环境变量指定可执行文件路径）")
}
$script:GitExe = $GitCmd.Source

function Find-Python {
    foreach ($cand in @($env:PYTHON, 'python3', 'python')) {
        if ([string]::IsNullOrWhiteSpace($cand)) { continue }
        $cmd = Get-Command -Name $cand -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($cmd) { return $cmd.Source }
    }
    return $null
}

$PyExe = $null
if (-not $NoRun) {
    $PyExe = Find-Python
    if (-not $PyExe) {
        Die ("找不到 python3/python（用 PYTHON 环境变量指定，或加 -NoRun 跳过冒烟）")
    }
}

# ---------------------------------------------------------------------------
# 克隆 / 更新
# ---------------------------------------------------------------------------
function Resolve-AbsolutePath([string]$Path) {
    if (-not [System.IO.Path]::IsPathRooted($Path)) {
        $Path = Join-Path -Path $PWD.ProviderPath -ChildPath $Path
    }
    return [System.IO.Path]::GetFullPath($Path)
}

function Test-InsideDir([string]$Path, [string]$Root) {
    $sep = [System.IO.Path]::DirectorySeparatorChar
    $full = [System.IO.Path]::GetFullPath($Path)
    $rootFull = [System.IO.Path]::GetFullPath($Root).TrimEnd($sep, [System.IO.Path]::AltDirectorySeparatorChar)
    return $full.StartsWith($rootFull + $sep, [System.StringComparison]::OrdinalIgnoreCase)
}

function Clone-Repo([string]$Name, [string]$Url, [string]$Dest) {
    $gitPath = Join-Path -Path $Dest -ChildPath '.git'

    if (Test-Path -LiteralPath $gitPath) {
        if ($script:NoPull) {
            Write-Host ("跳过（已存在）: {0}" -f $Dest)
        } elseif ($script:DryRun) {
            Write-Host ("[dry-run] git -C {0} pull --ff-only" -f $Dest)
        } else {
            Write-Host ("更新: {0}" -f $Dest)
            # 更新失败不算致命：本地可能有未提交改动或无网络，保留现有内容继续走
            & $script:GitExe -C $Dest pull --ff-only
            if ($LASTEXITCODE -ne 0) {
                Write-Warning ("{0} 更新失败，保留现有内容继续" -f $Dest)
            }
        }
        return
    }

    if (Test-Path -LiteralPath $Dest) {
        Die ("{0} 已存在但不是 git 仓库（不是空目录？），请先移走再重跑" -f $Dest)
    }

    Write-Host ("克隆 {0}: {1} -> {2}" -f $Name, $Url, $Dest)
    if ($script:DryRun) {
        $argText = 'clone'
        if ($script:Depth) { $argText += " --depth $($script:Depth)" }
        if ($script:Branch) { $argText += " --branch $($script:Branch)" }
        Write-Host ("[dry-run] git {0} {1} {2}" -f $argText, $Url, $Dest)
        return
    }

    $cloneArgs = @('clone')
    if ($script:Depth) { $cloneArgs += @('--depth', $script:Depth) }
    if ($script:Branch) { $cloneArgs += @('--branch', $script:Branch) }
    $cloneArgs += @($Url, $Dest)

    & $script:GitExe @cloneArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Error ("错误: 克隆失败 {0}" -f $Url)
        Write-Host "  网络直连不通时换成可达的镜像重试："
        Write-Host ("    powershell -File scripts/fetch-deps.ps1 -Mirror github|gitcode -Dir {0}" -f $Dir)
        Write-Host "  或只覆盖某一个仓（内网 Gitea / 私有镜像）："
        Write-Host ("    `$env:LIGHT_REPO='<url>'; `$env:LIGHTPLUGIN_REPO='<url>'; `$env:LIGHTHARNESS_REPO='<url>'; powershell -File scripts/fetch-deps.ps1 -Dir {0}" -f $Dir)
        # 清掉 clone 留下的半成品目录，方便重跑（只删目标目录内的路径）
        if ((Test-Path -LiteralPath $Dest) -and (Test-InsideDir -Path $Dest -Root $script:AbsDir)) {
            Remove-Item -LiteralPath $Dest -Recurse -Force -ErrorAction SilentlyContinue
        }
        exit 1
    }
}

Write-Host ("== 目标目录: {0}（镜像: {1}）" -f $Dir, $Mirror)

if (-not $DryRun) {
    if (-not (Test-Path -LiteralPath $Dir)) {
        New-Item -ItemType Directory -Path $Dir -Force > $null
    }
    $script:AbsDir = Resolve-AbsolutePath $Dir
} else {
    # dry-run 不落盘，目录可能不存在，只按字面值展示
    $script:AbsDir = $Dir
}

Clone-Repo light $LightRepo (Join-Path $script:AbsDir 'light')
Clone-Repo lightplugin $LightPluginRepo (Join-Path $script:AbsDir 'lightplugin')
Clone-Repo lightharness $LightHarnessRepo (Join-Path $script:AbsDir 'lightharness')

# ---------------------------------------------------------------------------
# 布局校验：三仓必须平铺在同一层，且各仓的标志物在位
# ---------------------------------------------------------------------------
if (-not $DryRun) {
    Write-Host '== 校验布局'
    $lightSrc = Join-Path $script:AbsDir 'light/src'
    $pluginDir = Join-Path $script:AbsDir 'lightplugin/集成'
    $runner = Join-Path $script:AbsDir 'lightharness/运行.py'

    if (-not (Test-Path -LiteralPath $lightSrc -PathType Container)) {
        Die ("light 缺 src/（光明编译器没拉全）: {0}" -f (Join-Path $script:AbsDir 'light'))
    }
    if (-not (Test-Path -LiteralPath $pluginDir -PathType Container)) {
        Die ("lightplugin 缺 集成/（插件生态没拉全）: {0}" -f (Join-Path $script:AbsDir 'lightplugin'))
    }
    if (-not (Test-Path -LiteralPath $runner -PathType Leaf)) {
        Die ("lightharness 缺 运行.py: {0}" -f (Join-Path $script:AbsDir 'lightharness'))
    }
    Write-Host ("   ok  {0}/{{light,lightplugin,lightharness}}" -f $script:AbsDir)
}

# ---------------------------------------------------------------------------
# 冒烟：跑 examples/冒烟.light，退出码 0 才算三仓接线通了
# ---------------------------------------------------------------------------
$smokeRc = 0
if ($NoRun) {
    # 显式跳过
} elseif ($DryRun) {
    Write-Host ("[dry-run] (cd {0}/lightharness; {1} 运行.py examples/冒烟.light)" -f $script:AbsDir, $PyExe)
} else {
    Write-Host ("== 冒烟：{0} 运行.py examples/冒烟.light" -f $PyExe)
    # 显式导出两个依赖根：即使目录名不叫 light / light-merge，运行.py 也能命中
    Push-Location -LiteralPath (Join-Path $script:AbsDir 'lightharness')
    try {
        $env:LIGHT_MERGE = Join-Path $script:AbsDir 'light'
        $env:LIGHTPLUGIN = Join-Path $script:AbsDir 'lightplugin'
        & $PyExe '运行.py' 'examples/冒烟.light'
        $smokeRc = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    if ($smokeRc -ne 0) {
        Die ("冒烟失败（依赖已拉齐，但运行.py 没跑通；看上面的报错）")
    }
}

# ---------------------------------------------------------------------------
# 下一步提示
# ---------------------------------------------------------------------------
$abs = $script:AbsDir
Write-Host ''
Write-Host ("== 完成：三仓已平铺在 {0}" -f $abs)
Write-Host ("   {0}/light          光明编译器" -f $abs)
Write-Host ("   {0}/lightplugin    插件生态" -f $abs)
Write-Host ("   {0}/lightharness   本工程" -f $abs)
Write-Host ''
Write-Host '下一步：'
Write-Host ("  cd {0}/lightharness" -f $abs)
Write-Host '  python 运行.py examples/冒烟.light'
Write-Host '  python 运行.py examples/运行Web服务器.light'
Write-Host ''
Write-Host '目录不在默认位置时，运行.py 也能靠环境变量找到依赖：'
Write-Host ("  `$env:LIGHT_MERGE='{0}/light'; `$env:LIGHTPLUGIN='{0}/lightplugin'; python 运行.py ..." -f $abs)

exit 0
