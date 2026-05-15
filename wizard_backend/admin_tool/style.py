"""
style.py - Design system for the Wizard Admin Tool.

Mirrors the color tokens and QSS building blocks of the desktop app
(`wizard_desktop/style.py`) with two additions:

  - Red "DEV ADMIN" accent on the header banner
  - Table styles (QTableWidget) on top of lists
"""

from __future__ import annotations

import sys

# -- Color tokens (dark mode) - identical to wizard_desktop --------------------
BG_DEEP = "#0d0d1a"
BG_BASE = "#12122b"
BG_PANEL = "#1a1a3a"
BG_CARD = "#20204a"
ACCENT = "#c9a84c"          # Gold
ACCENT_DIM = "#7a6230"
TEXT_MAIN = "#e8e8f0"
TEXT_DIM = "#888aaa"
SUCCESS = "#4ade80"
DANGER = "#f87171"
LEADER = "#ffd700"

# Admin-specific warning accent (red for destructive actions)
ADMIN_RED = "#e63946"

# -- QSS stylesheet ------------------------------------------------------------
STYLESHEET = f"""
/* -- Base -- */
QMainWindow, QWidget {{
    background-color: {BG_BASE};
    color: {TEXT_MAIN};
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}}

QLabel {{ background: transparent; }}

/* -- Sidebar -- */
QWidget#sidebar {{
    background-color: {BG_PANEL};
    border-right: 1px solid #2a2a4a;
}}
QPushButton#nav_btn {{
    background-color: transparent;
    border: none;
    border-left: 3px solid transparent;
    padding: 12px 18px;
    color: {TEXT_DIM};
    font-size: 14px;
    font-weight: 500;
    text-align: left;
}}
QPushButton#nav_btn:hover {{
    background-color: {BG_CARD};
    color: {TEXT_MAIN};
}}
QPushButton#nav_btn:checked {{
    background-color: {BG_CARD};
    color: {ACCENT};
    border-left: 3px solid {ACCENT};
}}

/* -- Banner / header -- */
QFrame#admin_banner {{
    background-color: #2a0f12;
    border: 1px solid {ADMIN_RED};
    border-radius: 6px;
}}
QLabel#admin_banner_text {{
    color: {ADMIN_RED};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
}}

/* -- Headings -- */
QLabel#title {{
    font-size: 26px;
    font-weight: 700;
    color: {ACCENT};
    letter-spacing: 2px;
}}
QLabel#subtitle {{
    font-size: 13px;
    color: {TEXT_DIM};
    letter-spacing: 1px;
}}
QLabel#section_header {{
    font-size: 11px;
    font-weight: 600;
    color: {ACCENT_DIM};
    letter-spacing: 2px;
    text-transform: uppercase;
}}
QLabel#status_bar {{
    color: {TEXT_DIM};
    font-size: 11px;
}}

/* -- Panels -- */
QFrame#panel {{
    background-color: {BG_PANEL};
    border: 1px solid #2a2a4a;
    border-radius: 10px;
}}
QFrame#card {{
    background-color: {BG_CARD};
    border: 1px solid #2f2f5a;
    border-radius: 8px;
}}

/* -- Inputs -- */
QLineEdit, QPlainTextEdit, QTextEdit {{
    background-color: {BG_CARD};
    border: 1px solid #3a3a6a;
    border-radius: 6px;
    padding: 6px 10px;
    color: {TEXT_MAIN};
    selection-background-color: {ACCENT_DIM};
    font-size: 13px;
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{
    border: 1px solid {ACCENT};
}}
QLineEdit:disabled {{
    color: {TEXT_DIM};
    border-color: #2a2a4a;
}}

QSpinBox {{
    background-color: {BG_CARD};
    border: 1px solid #3a3a6a;
    border-radius: 6px;
    padding: 5px 8px;
    color: {TEXT_MAIN};
    font-size: 14px;
    min-width: 60px;
}}
QSpinBox:focus {{
    border: 1px solid {ACCENT};
}}

QComboBox {{
    background-color: {BG_CARD};
    border: 1px solid #3a3a6a;
    border-radius: 6px;
    padding: 6px 10px;
    color: {TEXT_MAIN};
    font-size: 13px;
    min-height: 26px;
}}
QComboBox:focus {{ border: 1px solid {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background-color: {BG_CARD};
    border: 1px solid {ACCENT_DIM};
    selection-background-color: {ACCENT_DIM};
    color: {TEXT_MAIN};
    padding: 4px;
}}

/* -- Buttons -- */
QPushButton {{
    background-color: {BG_CARD};
    border: 1px solid #3a3a6a;
    border-radius: 7px;
    padding: 8px 18px;
    color: {TEXT_MAIN};
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: #2a2a5a;
    border-color: {ACCENT_DIM};
}}
QPushButton:pressed {{
    background-color: #1a1a3a;
}}
QPushButton:disabled {{
    color: {TEXT_DIM};
    border-color: #2a2a4a;
}}
QPushButton#primary {{
    background-color: {ACCENT_DIM};
    border: 1px solid {ACCENT};
    color: #fff8e0;
    font-weight: 700;
    font-size: 14px;
    padding: 9px 20px;
}}
QPushButton#primary:hover {{
    background-color: {ACCENT};
    color: {BG_DEEP};
}}
QPushButton#danger {{
    background-color: #3a1a1a;
    border: 1px solid {DANGER};
    color: {DANGER};
    font-weight: 600;
}}
QPushButton#danger:hover {{
    background-color: #5a2020;
}}
QPushButton#toolbar_btn {{
    background-color: transparent;
    border: none;
    color: {TEXT_DIM};
    font-size: 13px;
    padding: 6px 12px;
}}
QPushButton#toolbar_btn:hover {{
    color: {ACCENT};
    background-color: #1a1a3a;
    border-radius: 4px;
}}

/* -- Tables -- */
QTableWidget, QTableView {{
    background-color: {BG_PANEL};
    alternate-background-color: {BG_CARD};
    gridline-color: #2a2a4a;
    border: 1px solid #2a2a4a;
    border-radius: 8px;
    color: {TEXT_MAIN};
    selection-background-color: {ACCENT_DIM};
    selection-color: #fff8e0;
}}
QTableWidget::item, QTableView::item {{
    padding: 6px 8px;
}}
QHeaderView::section {{
    background-color: {BG_CARD};
    color: {ACCENT_DIM};
    border: none;
    border-right: 1px solid #2a2a4a;
    border-bottom: 1px solid #2a2a4a;
    padding: 6px 10px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
}}
QHeaderView::section:hover {{ color: {ACCENT}; }}
QTableCornerButton::section {{
    background-color: {BG_CARD};
    border: none;
    border-right: 1px solid #2a2a4a;
    border-bottom: 1px solid #2a2a4a;
}}

/* -- Lists -- */
QListWidget {{
    background-color: {BG_PANEL};
    border: 1px solid #2a2a4a;
    border-radius: 8px;
    padding: 4px;
    outline: none;
}}
QListWidget::item {{
    padding: 8px 12px;
    border-radius: 5px;
    color: {TEXT_MAIN};
}}
QListWidget::item:hover {{ background-color: {BG_CARD}; }}
QListWidget::item:selected {{
    background-color: {ACCENT_DIM};
    color: #fff8e0;
}}

/* -- Scrollbars -- */
QScrollBar:vertical {{
    background: {BG_BASE};
    width: 10px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: #3a3a6a;
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {ACCENT_DIM}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: {BG_BASE};
    height: 10px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background: #3a3a6a;
    border-radius: 5px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{ background: {ACCENT_DIM}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* -- Dialogs -- */
QDialog {{
    background-color: {BG_PANEL};
    border: 1px solid {ACCENT_DIM};
    border-radius: 12px;
}}
QDialogButtonBox QPushButton {{ min-width: 80px; }}

/* -- Separator -- */
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: #2a2a4a;
    border: none;
    background-color: #2a2a4a;
    max-height: 1px;
}}

/* -- Scroll area -- */
QScrollArea {{
    background: transparent;
    border: none;
}}

/* -- Tooltip -- */
QToolTip {{
    background-color: {BG_CARD};
    color: {TEXT_MAIN};
    border: 1px solid {ACCENT_DIM};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}}

/* -- RadioButton / CheckBox -- */
QRadioButton, QCheckBox {{
    color: {TEXT_MAIN};
    font-size: 13px;
    spacing: 6px;
    background: transparent;
}}
QRadioButton::indicator, QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {ACCENT_DIM};
    background: {BG_CARD};
}}
QRadioButton::indicator {{ border-radius: 8px; }}
QCheckBox::indicator {{ border-radius: 4px; }}
QRadioButton::indicator:checked {{
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
        stop:0 {ACCENT}, stop:0.5 {ACCENT}, stop:0.51 {BG_CARD}, stop:1 {BG_CARD});
    border: 2px solid {ACCENT};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border: 2px solid {ACCENT};
}}

/* -- ProgressBar -- */
QProgressBar {{
    background-color: {BG_CARD};
    border: 1px solid #3a3a6a;
    border-radius: 6px;
    text-align: center;
    color: {TEXT_MAIN};
    font-size: 11px;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 5px;
}}

/* -- Splitter -- */
QSplitter::handle {{
    background: #2a2a4a;
}}
QSplitter::handle:horizontal {{ width: 4px; }}
QSplitter::handle:vertical {{ height: 4px; }}
"""


def apply_titlebar_theme(widget) -> None:
    """Tint the OS title bar dark (Windows only)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        DWMWA_CAPTION_COLOR = 35
        hwnd = int(widget.winId())
        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
        # Match the BG_BASE color (#12122b).
        color = ctypes.c_uint32(0x002B1212)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_CAPTION_COLOR,
            ctypes.byref(color),
            ctypes.sizeof(color),
        )
    except Exception:
        pass


def apply_dark_palette(app) -> None:
    """Apply a Qt dark palette so native widgets match the QSS."""
    from PyQt6 import QtGui

    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(BG_BASE))
    palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor(TEXT_MAIN))
    palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(BG_CARD))
    palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor(BG_PANEL))
    palette.setColor(QtGui.QPalette.ColorRole.ToolTipBase, QtGui.QColor(BG_CARD))
    palette.setColor(QtGui.QPalette.ColorRole.ToolTipText, QtGui.QColor(TEXT_MAIN))
    palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor(TEXT_MAIN))
    palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor(BG_CARD))
    palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor(TEXT_MAIN))
    palette.setColor(QtGui.QPalette.ColorRole.BrightText, QtGui.QColor("#ffffff"))
    palette.setColor(QtGui.QPalette.ColorRole.Link, QtGui.QColor(ACCENT))
    palette.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor(ACCENT_DIM))
    palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtGui.QColor("#ffffff"))
    app.setPalette(palette)
