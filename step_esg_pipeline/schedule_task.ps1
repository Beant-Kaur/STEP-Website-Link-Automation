# Windows Task Scheduler Setup for STEP ESG Link Pipeline
param (
    [string]$Action = "register", # "register", "run", "unregister", or "status"
    [string]$Frequency = "Weekly", # "Daily" or "Weekly"
    [string]$DaysOfWeek = "Monday",
    [string]$At = "2:00AM"
)

$TaskName = "STEP_ESG_Link_Monitor"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = (Get-Command python.exe -ErrorAction SilentlyContinue).Source

if (-not $PythonExe) {
    Write-Error "python.exe was not found in your PATH."
    exit 1
}

if ($Action -eq "register") {
    Write-Host "Registering scheduled task '$TaskName'..." -ForegroundColor Cyan
    Write-Host "Directory: $ScriptDir"
    Write-Host "Schedule:  $Frequency at $At ($DaysOfWeek)"
    
    $TaskAction = New-ScheduledTaskAction -Execute $PythonExe -Argument "main.py --kajabi --json report.json --csv report.csv" -WorkingDirectory $ScriptDir
    
    if ($Frequency -eq "Daily") {
        $Trigger = New-ScheduledTaskTrigger -Daily -At $At
    } else {
        $Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $DaysOfWeek -At $At
    }
    
    $Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive
    $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    
    Register-ScheduledTask -TaskName $TaskName -Action $TaskAction -Trigger $Trigger -Principal $Principal -Settings $Settings -Description "Automated STEP ESG Link Freshness and Replacement Audit" -Force
    Write-Host "Task '$TaskName' registered successfully!" -ForegroundColor Green
}
elseif ($Action -eq "run") {
    Write-Host "Triggering task '$TaskName' immediately..." -ForegroundColor Cyan
    Start-ScheduledTask -TaskName $TaskName
    Write-Host "Task started in background. Check report.json when complete." -ForegroundColor Green
}
elseif ($Action -eq "status") {
    Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue | Format-List TaskName, State, Date
}
elseif ($Action -eq "unregister") {
    Write-Host "Unregistering scheduled task '$TaskName'..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Task removed successfully." -ForegroundColor Green
}
else {
    Write-Host "Unknown action: $Action. Use: register, run, status, or unregister." -ForegroundColor Red
}
