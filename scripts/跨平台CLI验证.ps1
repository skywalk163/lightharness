# R41 Task 3: Windows PowerShell CLI verification (ASCII for Windows PowerShell 5.1).
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = if ($env:PYTHON) { $env:PYTHON } else { 'python' }
Set-Location $Root
$env:PYTHONIOENCODING = 'utf-8'
$env:HARNESS_MODEL = 'r41-cross-platform-model'
$Helper = Join-Path $Root 'scripts/cli_platform_runner.py'

function Invoke-CliCheck([string]$Command, [string]$Expected) {
    $env:HARNESS_CMD = $Command
    $ErrorActionPreference = 'Continue'
    $Output = & $Python $Helper 'entry' 2>&1 | Out-String
    $ErrorActionPreference = 'Stop'
    $Code = $LASTEXITCODE
    if ($Code -ne 0) { throw "$Command returned $Code" }
    if (-not $Output.Contains($Expected)) { throw "$Command output missing expected marker" }
    Write-Host ("PASS {0,-12} rc={1}" -f $Command, $Code)
}

Invoke-CliCheck 'version' '0.1.5-lh'
Invoke-CliCheck 'help' 'HARNESS_CMD=run|dump-config|version|help'
Invoke-CliCheck 'dump-config' 'r41-cross-platform-model'
$env:HARNESS_CMD = 'bogus'
$ErrorActionPreference = 'Continue'
$Output = & $Python $Helper 'entry' 2>&1 | Out-String
$ErrorActionPreference = 'Stop'
$Code = $LASTEXITCODE
if ($Code -eq 0) { throw 'unknown command must return non-zero' }
if (-not $Output.Contains('HARNESS_CMD')) { throw 'unknown command output missing marker' }
Write-Host ("PASS {0,-12} rc={1}" -f 'unknown', $Code)

$env:HARNESS_MSG = 'R41-CLI-env-input'
Remove-Item Env:HARNESS_CMD -ErrorAction SilentlyContinue
& $Python $Helper 'test' *> $null
if ($LASTEXITCODE -ne 0) { throw 'CLI command test failed' }
Write-Host 'PASS cli-test     rc=0'
Write-Host 'R41_CLI_WINDOWS PASS'
