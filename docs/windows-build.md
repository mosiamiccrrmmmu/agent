# Windows Build

## Build machine requirements

- Windows 10/11 x64
- Python 3.11+ (build only)
- Optional: Rust/Node for Tauri installer

End users do **not** need Python, Node, Docker, or PostgreSQL.

## Build portable EXE

```powershell
.\scripts\build_exe.ps1
```

Output: `dist\PersonalAI.exe`

## Run

Double-click `PersonalAI.exe` or run from terminal.

## Code signing

```powershell
signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /a PersonalAI.exe
```
