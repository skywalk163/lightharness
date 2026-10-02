# e2e_demo.ps1 —— 轨道 B 一键端到端联调（copy-paste 可跑，零 API Key）
#
# 用法：
#   cd lightharness
#   powershell -ExecutionPolicy Bypass -File e2e_demo.ps1
#
# 两段：
#   1) CLI 闭环：examples/端到端demo.light 走完整 agent 循环（mock：系统提示→工具调用→回灌→流式最终文本）
#   2) Web UI 闭环：后台起 examples/运行Web服务器.light（mock），curl /api/config 与 SSE chat
#
# 退出码：任一段失败 → 1；全通 → 0。
# 依赖：本机 python（优先 C:\Python314\python.exe，否则 PATH 上的 python）。

$ErrorActionPreference = "Stop"
# 脚本所在目录即 lightharness 根
Set-Location $PSScriptRoot
$root = $PSScriptRoot

# ---- 环境（对齐 README 长跑纪律）----
$env:PYTHONUTF8 = "1"
$env:CODEBUDDY_SAFE_DELETE_ENABLED = "0"
$py = if (Test-Path "C:\Python314\python.exe") { "C:\Python314\python.exe" } else { "python" }

Write-Host "=================================================="
Write-Host "  lightharness 轨道 B 端到端联调（mock / 零 Key）"
Write-Host "  解释器: $py"
Write-Host "=================================================="

# ==================================================
# 第 1 段：CLI 端到端 demo
# ==================================================
Write-Host "`n[段 1/2] CLI 闭环：python 运行.py examples/端到端demo.light"
& $py 运行.py examples/端到端demo.light
if ($LASTEXITCODE -ne 0) {
  Write-Host "!! 段 1 失败（rc=$LASTEXITCODE）"
  exit 1
}
Write-Host "[段 1/2] OK rc=0`n"

# ==================================================
# 第 2 段：Web UI mock 服务 + curl
# ==================================================
Write-Host "[段 2/2] Web UI 闭环：起 mock Web 服务 + curl SSE"
$env:HARNESS_WEB_MOCK = "1"
$env:HARNESS_WEB_NO_OPEN = "1"
$env:HARNESS_WEB_TOKEN = "e2e-token-123"
$env:HARNESS_WEB_REPLY = "Web UI mock 流式回复：E2E 联调成功。"
$env:HARNESS_WEB_LIFETIME = "60"
$portFile = Join-Path $root ".e2e_port.txt"
if (Test-Path $portFile) { Remove-Item $portFile -Force }
$env:HARNESS_PORT_FILE = $portFile

$proc = Start-Process -FilePath $py `
  -ArgumentList "运行.py", "examples/运行Web服务器.light" `
  -WorkingDirectory $root -PassThru -NoNewWindow `
  -RedirectStandardOutput (Join-Path $root ".e2e_web.log") `
  -RedirectStandardError  (Join-Path $root ".e2e_web.err")

# 等端口文件（编译约 15s，最多等 40s）
$port = $null
for ($i = 0; $i -lt 80; $i++) {
  if (Test-Path $portFile) { $port = (Get-Content $portFile -Raw).Trim(); break }
  Start-Sleep -Milliseconds 500
}
if (-not $port) {
  Write-Host "!! 段 2 失败：端口文件未出现。服务日志："
  Get-Content (Join-Path $root ".e2e_web.log") -Raw -ErrorAction SilentlyContinue
  Stop-Process $proc -Force -ErrorAction SilentlyContinue
  exit 1
}
Write-Host "  mock Web 服务已起，端口=$port"

# curl 1：GET /api/config（免认证）
try {
  $cfg = Invoke-RestMethod "http://127.0.0.1:$port/api/config" -TimeoutSec 10
  Write-Host ("  GET /api/config -> " + ($cfg | ConvertTo-Json -Compress))
  if ($cfg.mock -ne 1) { Write-Host "!! 段 2 失败：config.mock 应为 1"; Stop-Process $proc -Force; exit 1 }
} catch {
  Write-Host "!! 段 2 失败：/api/config 异常: $_"; Stop-Process $proc -Force; exit 1
}

# curl 2：POST /v1/chat/completions（stream=true → SSE）
$body = '{"model":"deepseek-chat","messages":[{"role":"user","content":"用一句话介绍你自己"}],"stream":true,"session_id":"e2e-curl-1"}'
try {
  $resp = Invoke-WebRequest "http://127.0.0.1:$port/v1/chat/completions?token=e2e-token-123" `
    -Method POST -Body $body -ContentType "application/json; charset=utf-8" -TimeoutSec 30 -UseBasicParsing
  $ct = $resp.Headers["Content-Type"]
  Write-Host ("  POST /v1/chat/completions -> HTTP " + $resp.StatusCode + "  CT=" + $ct)
  if ($resp.StatusCode -ne 200 -or $ct -notlike "text/event-stream*") {
    Write-Host "!! 段 2 失败：期望 200 + text/event-stream"; Stop-Process $proc -Force; exit 1
  }
  if ($resp.Content -notmatch "data:" -or $resp.Content -notmatch "\[DONE\]") {
    Write-Host "!! 段 2 失败：SSE 体缺 data: 或 [DONE]"; Stop-Process $proc -Force; exit 1
  }
  Write-Host "  SSE 帧序列 OK（含 data: 帧与 [DONE]）"
} catch {
  Write-Host "!! 段 2 失败：chat 异常: $_"; Stop-Process $proc -Force; exit 1
}

# 清理：停服务 + 删端口/日志临时件
Stop-Process $proc -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 300
foreach ($f in @($portFile, (Join-Path $root ".e2e_web.log"), (Join-Path $root ".e2e_web.err"))) {
  if (Test-Path $f) { Remove-Item $f -Force -ErrorAction SilentlyContinue }
}

Write-Host "`n=================================================="
Write-Host "  轨道 B 端到端联调全通（CLI + Web UI）rc=0"
Write-Host "=================================================="
exit 0
