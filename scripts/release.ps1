# Release entrypoint — version stamp + full installer build.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Version = (Get-Content VERSION -Raw).Trim()
Write-Host "Releasing Personal AI $Version"

& "$Root\scripts\build_exe.ps1"

Write-Host @"

Release checklist:
  [ ] Backend tests passed
  [ ] EXE built
  [ ] Code signed (if certificate available)
  [ ] Smoke test on clean Windows VM

Artifacts:
  dist\PersonalAI.exe
"@
