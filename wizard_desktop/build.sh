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

# Icon erzeugen (matched die Mobile-App)
echo "[+] Generiere icon.ico..."
python generate_icon.py || echo "[!] icon.ico konnte nicht erzeugt werden – Build läuft ohne eigenes Icon."

# Executable bauen
echo "[+] Baue Executable..."
ICON_FLAG=""
ICON_DATA_FLAG=""
if [ -f "icon.ico" ]; then
    ICON_FLAG="--icon=icon.ico"
    ICON_DATA_FLAG="--add-data=icon.ico;."
fi

# shellcheck disable=SC2086
pyinstaller \
    --onefile \
    --windowed \
    --name WizardGUI \
    $ICON_FLAG \
    $ICON_DATA_FLAG \
    --add-data "translations.py;." \
    --add-data "app_settings.py;." \
    --add-data "icons;icons" \
    --add-data "sounds;sounds" \
    --hidden-import matplotlib.backends.backend_qtagg \
    main.py

echo ""
echo "================================================"
echo "  Build abgeschlossen!"
echo "  Executable: dist/WizardGUI"
echo "================================================"
