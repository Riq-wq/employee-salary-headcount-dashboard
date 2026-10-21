<#
.SYNOPSIS
    PowerShell entry point for the scheduled employee salary pipeline run.

.DESCRIPTION
    Task Scheduler launches PowerShell, and PowerShell's -File parameter only
    accepts .ps1 scripts -- not .py. This wrapper exists for that reason, and
    for two more:

      * It sets the working directory explicitly. Task Scheduler's default is
        C:\Windows\System32, so anything relying on a relative path would
        resolve in the wrong place.
      * It pins the interpreter. Task Scheduler has no notion of a "PATH as you
        know it in your terminal", and there may be several Pythons on the
        machine. Naming the interpreter removes that ambiguity.

    All real work, logging and exit codes live in run_scheduled.py. This file
    is deliberately thin: a scheduler wrapper should be boring.

.EXIT CODES
    Passed straight through from run_scheduled.py so Task Scheduler records
    them:
      0  success
      2  data-quality checks failed
      3  database connection failed
      4  unexpected error
#>

$ErrorActionPreference = "Stop"

# Project root is the parent of this script's folder (scripts\).
$Root   = Split-Path -Parent $PSScriptRoot
$Python = "C:\ProgramData\anaconda3\python.exe"
$Runner = Join-Path $Root "scripts\run_scheduled.py"

Set-Location -LiteralPath $Root

if (-not (Test-Path -LiteralPath $Python)) {
    Write-Error "Python not found at $Python"
    exit 4
}
if (-not (Test-Path -LiteralPath $Runner)) {
    Write-Error "Runner not found at $Runner"
    exit 4
}

& $Python $Runner
exit $LASTEXITCODE
