$ErrorActionPreference='Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
Set-Location -LiteralPath $projectRoot
$env:PYTHONUTF8='1'
if (Test-Path -LiteralPath "$projectRoot\data\tunnel-dns.enabled") { $env:MINI_TUNNEL_DNS='1' }
New-Item -ItemType Directory -Force "$projectRoot\output\logs" | Out-Null
& "$projectRoot\.venv\Scripts\python.exe" -m deepinsight scheduler *>> "$projectRoot\output\logs\scheduler.log"
exit $LASTEXITCODE
