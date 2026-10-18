param([switch]$TunnelDns)
$ErrorActionPreference='Stop'
$projectRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
if ($TunnelDns) {
    New-Item -ItemType Directory -Force "$projectRoot\data" | Out-Null
    New-Item -ItemType File -Force "$projectRoot\data\tunnel-dns.enabled" | Out-Null
}
$tick=Join-Path $PSScriptRoot 'Scheduler-Tick.ps1'
$action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$tick`"" -WorkingDirectory $projectRoot
$trigger=New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 1)
$settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
Register-ScheduledTask -TaskName 'DeepInsightMini-LondonMarket' -Action $action -Trigger $trigger -Settings $settings -Description 'Poll London 08:00/18:00 slots with DST handling; independent of web server' -Force
