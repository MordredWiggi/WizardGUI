"""
main.py – Einstiegspunkt für den Wizard Punkte-Tracker.

Starten:
    python main.py
oder (wenn als Paket installiert):
    python -m wizard_gui
"""
import sys
import os
from PyQt6 import QtWidgets, QtGui, QtCore
from app_settings import load_settings, get_theme
from style import STYLESHEET, STYLESHEET_LIGHT, apply_titlebar_theme
from main_window import MainWindow
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _resource_path(name: str) -> str:
    """Return absolute path to a bundled resource, both in dev and PyInstaller."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def _build_app_icon() -> QtGui.QIcon:
    """Load icon.ico if present; otherwise draw a spade that matches the mobile
    launcher icon so the taskbar still shows the right image in dev runs."""
    ico_path = _resource_path("icon.ico")
    if os.path.isfile(ico_path):
        icon = QtGui.QIcon(ico_path)
        if not icon.isNull():
            return icon

    size = 256
    pixmap = QtGui.QPixmap(size, size)
    pixmap.fill(QtGui.QColor("#0D0D1A"))
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    painter.setBrush(QtGui.QColor("#C9A84C"))
    painter.setPen(QtCore.Qt.PenStyle.NoPen)
    path = QtGui.QPainterPath()
    def p(x, y):
        return QtCore.QPointF(x / 108.0 * size, y / 108.0 * size)
    path.moveTo(p(54, 22))
    path.cubicTo(p(54, 22), p(30, 44), p(30, 58))
    path.cubicTo(p(30, 67), p(37, 72), p(45, 70))
    path.cubicTo(p(42, 76), p(38, 80), p(32, 82))
    path.lineTo(p(76, 82))
    path.cubicTo(p(70, 80), p(66, 76), p(63, 70))
    path.cubicTo(p(71, 72), p(78, 67), p(78, 58))
    path.cubicTo(p(78, 44), p(54, 22), p(54, 22))
    path.closeSubpath()
    painter.drawPath(path)
    painter.end()
    return QtGui.QIcon(pixmap)


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

    # Taskbar / window icon – matches the mobile launcher icon.
    icon = _build_app_icon()
    app.setWindowIcon(icon)
    # On Windows, grouping the taskbar icon under a custom AppUserModelID
    # is required for a custom icon to appear in the taskbar for the .exe.
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "WizardGUI.Desktop"
            )
        except Exception:
            pass

    window = MainWindow()
    window.setWindowIcon(icon)
    window.show()

    # Apply title bar theme after the window is shown
    apply_titlebar_theme(window)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
