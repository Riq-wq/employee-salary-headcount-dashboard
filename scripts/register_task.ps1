<#
.SYNOPSIS
    Register (or remove) the nightly Windows Task Scheduler job for the
    employee salary pipeline.

.DESCRIPTION
    Level 4 of the automation build: scheduling.

    A schedule created by clicking through the Task Scheduler GUI cannot be
    reviewed, diffed, or rebuilt on another machine. This script is the
    schedule expressed as code, so the task can be recreated identically at any
    time — and so the parameters (time, runner, working directory) are visible
    in the repository rather than buried in a system dialog.

    The task runs scripts\run_scheduled.py, which:
      * sets its own working directory (never relies on the caller's),
      * writes a timestamped log to logs\,
      * returns a distinct exit code (0 ok / 2 bad data / 3 db down / 4 bug),
      * so Task Scheduler's History tab records *why* a run failed.

.PARAMETER Time
    Daily start time, 24-hour HH:mm. Default 06:00.

.PARAMETER TaskName
    Name shown in Task Scheduler. Default "EmployeeSalaryPipeline".

.PARAMETER Remove
    Unregister the task instead of creating it.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\register_task.ps1
    powershell -ExecutionPolicy Bypass -File scripts\register_task.ps1 -Time 07:30
    powershell -ExecutionPolicy Bypass -File scripts\register_task.ps1 -Remove
#>

[CmdletBinding()]
param(
    [string]$Time = "06:00",
    [string]$TaskName = "EmployeeSalaryPipeline",
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

# Root = the project folder (this script lives in scripts\).
$Root     = Split-Path -Parent $PSScriptRoot
# PowerShell's -File only accepts .ps1, so the task launches a thin PowerShell
# wrapper which in turn calls the real Python runner. Pointing -File at the
# .py directly fails instantly with exit code -196608 and writes no log.
$Wrapper  = Join-Path $Root "scripts\run_scheduled.ps1"
$Python   = "C:\ProgramData\anaconda3\python.exe"

# --------------------------------------------------------------------------
# Remove mode
# --------------------------------------------------------------------------
if ($Remove) {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Removed scheduled task '$TaskName'."
    } else {
        Write-Host "No scheduled task named '$TaskName' exists. Nothing to remove."
    }
    return
}

# --------------------------------------------------------------------------
# Validate before touching the scheduler
# --------------------------------------------------------------------------
if (-not (Test-Path $Python)) {
    throw "Python not found at $Python. Edit `$Python in this script."
}
if (-not (Test-Path $Wrapper)) {
    throw "Wrapper not found at $Wrapper."
}
if (-not (Test-Path (Join-Path $Root "scripts\run_scheduled.py"))) {
    throw "Python runner not found at scripts\run_scheduled.py."
}
if ($Time -notmatch '^\d{2}:\d{2}$') {
    throw "Time must be HH:mm in 24-hour form, e.g. 06:00 (got '$Time')."
}

Write-Host "Registering scheduled task"
Write-Host "  name    : $TaskName"
Write-Host "  time    : $Time daily"
Write-Host "  entry   : $Wrapper"
Write-Host "  python  : $Python"
Write-Host "  workdir : $Root"
Write-Host ""

# --------------------------------------------------------------------------
# Build the task
#
# -WindowStyle Hidden  : no console window appears at 06:00.
# -ExecutionPolicy Bypass : a scheduler-spawned PowerShell may otherwise block
#                           script execution depending on machine policy.
# WorkingDirectory is set explicitly: Task Scheduler's default is
# C:\Windows\System32, which would make any relative path in the run resolve
# somewhere unexpected.
#
# Note -File must point at a .ps1. The Python runner is invoked by that wrapper.
# --------------------------------------------------------------------------
$argument = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$Wrapper`""

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument $argument `
    -WorkingDirectory $Root

$trigger = New-ScheduledTaskTrigger -Daily -At $Time

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopOnIdleEnd `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -MultipleInstances IgnoreNew

# StartWhenAvailable  : if the machine was asleep/off at 06:00, run on wake
#                       rather than silently skipping the day.
# ExecutionTimeLimit  : a hung run is killed rather than left wedged.
# MultipleInstances   : a slow run must not overlap its own next execution.

# Run as the current user, only when logged on.
# This deliberately avoids storing a password. The trade-off is that the job
# does not run while the user is signed out; see the README for the
# production alternative (run on a server under a service account).
$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Write-Host "A task named '$TaskName' already exists - replacing it."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Runs the employee salary pipeline daily: clean, validate, incremental load, log." | Out-Null

Write-Host ""
Write-Host "Registered. Current state:"
Get-ScheduledTask -TaskName $TaskName |
    Select-Object TaskName, State,
        @{n = 'NextRun'; e = { (Get-ScheduledTaskInfo -TaskName $TaskName).NextRunTime } } |
    Format-List
