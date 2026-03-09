"""
main.py – Einstiegspunkt für den Wizard Punkte-Tracker.

Starten:
    python main.py
oder (wenn als Paket installiert):
    python -m wizard_gui
"""
import sys
import os
from PyQt6 import QtWidgets
from app_settings import load_settings, get_theme
from style import STYLESHEET, STYLESHEET_LIGHT
from main_window import MainWindow
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main() -> None:
    # Einstellungen laden (Sprache, Theme)
    load_settings()

    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET_LIGHT if get_theme() == "light" else STYLESHEET)
    app.setApplicationName("Wizard GUI")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
