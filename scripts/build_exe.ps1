# Build PersonalAI.exe for Windows (run on Windows)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "=== Building PersonalAI.exe ==="
python -m pip install -U pip
python -m pip install -e ".[dev]" pyinstaller pywebview pystray pillow

# Windowed EXE (no console)
$spec = Get-Content personal_ai.spec -Raw
$spec = $spec -replace 'console=True', 'console=False'
Set-Content -Path personal_ai_win.spec -Value $spec

python -m PyInstaller --noconfirm personal_ai_win.spec

$src = Join-Path $Root "dist\PersonalAI.exe"
if (Test-Path $src) {
  Copy-Item $src (Join-Path $Root "dist\PersonalAI-Setup-Portable.exe") -Force
  $size = [math]::Round((Get-Item $src).Length / 1MB, 1)
  Write-Host "OK: dist\PersonalAI.exe ($size MB)"
  Write-Host "Run: dist\PersonalAI.exe"
} else {
  Write-Error "EXE not found"
}
