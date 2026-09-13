$ErrorActionPreference='Stop'
$target='D:\MT5_Backtests\automation\Start-GuardianMonitor.cmd'
if(!(Test-Path -LiteralPath $target)){throw "Launcher not found: $target"}
$desktop=[Environment]::GetFolderPath('Desktop')
$link=Join-Path $desktop 'Guardian Monitor.lnk'
$w=New-Object -ComObject WScript.Shell
$s=$w.CreateShortcut($link)
$s.TargetPath=$target
$s.WorkingDirectory='D:\MT5_Backtests'
$s.Description='Guardian Monitor - read-only research dashboard'
$s.Save()
Write-Host "Created: $link"
