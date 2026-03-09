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
from style import STYLESHEET
from main_window import MainWindow
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    app.setApplicationName("Wizard GUI")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
