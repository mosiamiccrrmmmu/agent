#!/usr/bin/env bash
# Build PersonalAI binary with PyInstaller (current OS).
set -euo pipefail
cd "$(dirname "$0")/.."
python -m pip install -e ".[dev]" pyinstaller pywebview pystray pillow -q
python -m PyInstaller --noconfirm personal_ai.spec
echo "Artifact: dist/PersonalAI (or dist/PersonalAI.exe on Windows)"
ls -lh dist/ 2>/dev/null || true
