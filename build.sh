#!/usr/bin/env bash
# build.sh – Erstellt eine eigenständige ausführbare Datei für Wizard GUI
# Verwendung: bash build.sh

set -euo pipefail

echo "================================================"
echo "  Wizard GUI – Build-Skript (PyInstaller)"
echo "================================================"

# PyInstaller installieren (falls nicht vorhanden)
if ! command -v pyinstaller &>/dev/null; then
    echo "[+] Installiere PyInstaller..."
    pip install pyinstaller
fi

# Altes Build-Verzeichnis bereinigen
echo "[+] Bereinige alte Build-Artefakte..."
rm -rf build dist WizardGUI.spec

# Executable bauen
echo "[+] Baue Executable..."
ICON_FLAG=""
if [ -f "icon.ico" ]; then
    ICON_FLAG="--icon=icon.ico"
fi

# shellcheck disable=SC2086
pyinstaller \
    --onefile \
    --windowed \
    --name WizardGUI \
    $ICON_FLAG \
    --add-data "translations.py:." \
    --add-data "app_settings.py:." \
    main.py

echo ""
echo "================================================"
echo "  Build abgeschlossen!"
echo "  Executable: dist/WizardGUI"
echo "================================================"
