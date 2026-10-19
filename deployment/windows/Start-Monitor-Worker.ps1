param([switch]$TunnelDns)
$ErrorActionPreference='Stop'
$miniRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
Set-Location -LiteralPath $miniRoot
$env:PYTHONUTF8='1'
if ($TunnelDns) { $env:MINI_TUNNEL_DNS='1' }
& "$miniRoot\.venv\Scripts\python.exe" -m app.monitoring.scheduler
