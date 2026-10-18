param([switch]$TunnelDns, [int]$Port=8766)
$ErrorActionPreference='Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
Set-Location -LiteralPath $projectRoot
if ($TunnelDns) { $env:MINI_TUNNEL_DNS='1' }
$env:PYTHONUTF8='1'
& "$projectRoot\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port $Port
