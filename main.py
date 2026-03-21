"""
main.py – Einstiegspunkt für den Wizard Punkte-Tracker.

Starten:
    python main.py
oder (wenn als Paket installiert):
    python -m wizard_gui
"""
import sys
import os
from PyQt6 import QtWidgets, QtGui
from app_settings import load_settings, get_theme
from style import STYLESHEET, STYLESHEET_LIGHT
from main_window import MainWindow
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _apply_dark_titlebar_to_window(window: QtWidgets.QMainWindow) -> None:
    """Apply dark title bar to a specific top-level window (Windows only)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        hwnd = int(window.winId())
        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
    except Exception:
        pass


def main() -> None:
    # Einstellungen laden (Sprache, Theme)
    load_settings()

    app = QtWidgets.QApplication(sys.argv)

    # Force Fusion style so the app controls look consistent on all platforms.
    # On Windows this also prevents the OS from overriding widget colours.
    app.setStyle("Fusion")

    # Apply dark palette so that Qt's own widget style matches the dark theme
    # (this affects scrollbars, menus, etc. that are rendered natively).
    if get_theme() != "light":
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor("#12122b"))
        palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor("#e8e8f0"))
        palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor("#20204a"))
        palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor("#1a1a3a"))
        palette.setColor(QtGui.QPalette.ColorRole.ToolTipBase, QtGui.QColor("#20204a"))
        palette.setColor(QtGui.QPalette.ColorRole.ToolTipText, QtGui.QColor("#e8e8f0"))
        palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor("#e8e8f0"))
        palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor("#20204a"))
        palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor("#e8e8f0"))
        palette.setColor(QtGui.QPalette.ColorRole.BrightText, QtGui.QColor("#ffffff"))
        palette.setColor(QtGui.QPalette.ColorRole.Link, QtGui.QColor("#c9a84c"))
        palette.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor("#7a6230"))
        palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtGui.QColor("#ffffff"))
        app.setPalette(palette)

    app.setStyleSheet(STYLESHEET_LIGHT if get_theme() == "light" else STYLESHEET)
    app.setApplicationName("Wizard GUI")

    window = MainWindow()
    window.show()

    # Apply dark title bar on Windows after the window is shown
    _apply_dark_titlebar_to_window(window)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
