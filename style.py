"""
style.py – Zentrales Design-System für Wizard GUI.

Farbpalette: dunkles Midnight-Navy mit Goldakzenten (Karten-Spieltisch-Ästhetik).
Enthält Dark Mode (Standard) und Light Mode Varianten.
"""

# ── Farb-Tokens (Dark Mode) ───────────────────────────────────────────────────
BG_DEEP    = "#0d0d1a"   # tiefstes Schwarz-Blau
BG_BASE    = "#12122b"   # Haupthintergrund
BG_PANEL   = "#1a1a3a"   # Karten / Panels
BG_CARD    = "#20204a"   # Input-Felder, Listenelemente
ACCENT     = "#c9a84c"   # Gold
ACCENT_DIM = "#7a6230"   # gedämpftes Gold
TEXT_MAIN  = "#e8e8f0"   # Haupttext
TEXT_DIM   = "#888aaa"   # Nebentext
SUCCESS    = "#4ade80"   # Grün
DANGER     = "#f87171"   # Rot
LEADER     = "#ffd700"   # Anführer-Highlight

# ── Farb-Tokens (Light Mode) ──────────────────────────────────────────────────
BG_DEEP_L    = "#ffffff"   # reines Weiß
BG_BASE_L    = "#f0f0f5"   # heller Hintergrund
BG_PANEL_L   = "#e4e4ee"   # Panels
BG_CARD_L    = "#f8f8ff"   # Karten / Eingabefelder
ACCENT_L     = "#9b7a1e"   # dunkles Gold (für helle Flächen)
ACCENT_DIM_L = "#c9a84c"   # helles Gold
TEXT_MAIN_L  = "#1a1a2e"   # dunkler Haupttext
TEXT_DIM_L   = "#555577"   # dunkler Nebentext

# ── Matplotlib-Farben für Spieler ────────────────────────────────────────────
PLAYER_COLORS = [
    "#4fc3f7",  # Hellblau
    "#ff7043",  # Orange-Rot
    "#81c784",  # Grün
    "#ce93d8",  # Lila
    "#fff176",  # Gelb
    "#f48fb1",  # Pink
]

# ── QSS Stylesheet ───────────────────────────────────────────────────────────
STYLESHEET = f"""
/* ── Basis ── */
QMainWindow, QWidget {{
    background-color: {BG_BASE};
    color: {TEXT_MAIN};
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}}

/* ── Überschriften (über objectName) ── */
QLabel#title {{
    font-size: 28px;
    font-weight: 700;
    color: {ACCENT};
    letter-spacing: 2px;
}}
QLabel#subtitle {{
    font-size: 14px;
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
QLabel#score_value {{
    font-size: 22px;
    font-weight: 700;
    color: {TEXT_MAIN};
}}
QLabel#leader_badge {{
    font-size: 11px;
    color: {LEADER};
    font-weight: 600;
}}

/* ── Panels ── */
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

/* ── Inputs ── */
QLineEdit {{
    background-color: {BG_CARD};
    border: 1px solid #3a3a6a;
    border-radius: 6px;
    padding: 6px 10px;
    color: {TEXT_MAIN};
    selection-background-color: {ACCENT_DIM};
    font-size: 14px;
}}
QLineEdit:focus {{
    border: 1px solid {ACCENT};
}}
QLineEdit:disabled {{
    color: {TEXT_DIM};
    border-color: #2a2a4a;
}}

/* ── SpinBox ── */
QSpinBox {{
    background-color: {BG_CARD};
    border: 1px solid #3a3a6a;
    border-radius: 6px;
    padding: 5px 8px;
    color: {TEXT_MAIN};
    font-size: 16px;
    min-width: 70px;
}}
QSpinBox:focus {{
    border: 1px solid {ACCENT};
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background-color: #2a2a4a;
    border-radius: 3px;
    width: 18px;
    height: 14px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {ACCENT_DIM};
}}
QSpinBox::up-arrow {{
    width: 8px;
    height: 8px;
}}
QSpinBox::down-arrow {{
    width: 8px;
    height: 8px;
}}

/* ── Buttons ── */
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
QPushButton#primary {{
    background-color: {ACCENT_DIM};
    border: 1px solid {ACCENT};
    color: #fff8e0;
    font-weight: 700;
    font-size: 14px;
    padding: 10px 28px;
}}
QPushButton#primary:hover {{
    background-color: {ACCENT};
    color: {BG_DEEP};
}}
QPushButton#danger {{
    background-color: #3a1a1a;
    border: 1px solid {DANGER};
    color: {DANGER};
}}
QPushButton#danger:hover {{
    background-color: #5a2020;
}}
QPushButton#toolbar_btn {{
    background-color: transparent;
    border: none;
    color: {TEXT_DIM};
    font-size: 11px;
    padding: 4px 8px;
}}
QPushButton#toolbar_btn:hover {{
    color: {ACCENT};
    background-color: #1a1a3a;
    border-radius: 4px;
}}

/* ── Scrollbars ── */
QScrollBar:vertical {{
    background: {BG_BASE};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: #3a3a6a;
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {ACCENT_DIM};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

/* ── Listen ── */
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
QListWidget::item:hover {{
    background-color: {BG_CARD};
}}
QListWidget::item:selected {{
    background-color: {ACCENT_DIM};
    color: #fff8e0;
}}

/* ── Dialoge ── */
QDialog {{
    background-color: {BG_PANEL};
    border: 1px solid {ACCENT_DIM};
    border-radius: 12px;
}}
QDialogButtonBox QPushButton {{
    min-width: 80px;
}}

/* ── Separator ── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: #2a2a4a;
    border: none;
    background-color: #2a2a4a;
    max-height: 1px;
}}

/* ── Scrollbereich ── */
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

/* ── Tooltip ── */
QToolTip {{
    background-color: {BG_CARD};
    color: {TEXT_MAIN};
    border: 1px solid {ACCENT_DIM};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}}
"""

# ── Light-Mode Stylesheet ─────────────────────────────────────────────────────
STYLESHEET_LIGHT = f"""
/* ── Basis ── */
QMainWindow, QWidget {{
    background-color: {BG_BASE_L};
    color: {TEXT_MAIN_L};
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}}

/* ── Überschriften ── */
QLabel#title {{
    font-size: 28px;
    font-weight: 700;
    color: {ACCENT_L};
    letter-spacing: 2px;
}}
QLabel#subtitle {{
    font-size: 14px;
    color: {TEXT_DIM_L};
    letter-spacing: 1px;
}}
QLabel#section_header {{
    font-size: 11px;
    font-weight: 600;
    color: {ACCENT_L};
    letter-spacing: 2px;
    text-transform: uppercase;
}}
QLabel#score_value {{
    font-size: 22px;
    font-weight: 700;
    color: {TEXT_MAIN_L};
}}
QLabel#leader_badge {{
    font-size: 11px;
    color: #b8860b;
    font-weight: 600;
}}

/* ── Panels ── */
QFrame#panel {{
    background-color: {BG_PANEL_L};
    border: 1px solid #ccccdd;
    border-radius: 10px;
}}
QFrame#card {{
    background-color: {BG_CARD_L};
    border: 1px solid #ccccdd;
    border-radius: 8px;
}}

/* ── Inputs ── */
QLineEdit {{
    background-color: {BG_CARD_L};
    border: 1px solid #aaaacc;
    border-radius: 6px;
    padding: 6px 10px;
    color: {TEXT_MAIN_L};
    selection-background-color: {ACCENT_DIM_L};
    font-size: 14px;
}}
QLineEdit:focus {{
    border: 1px solid {ACCENT_L};
}}
QLineEdit:disabled {{
    color: {TEXT_DIM_L};
    border-color: #ccccdd;
}}

/* ── SpinBox ── */
QSpinBox {{
    background-color: {BG_CARD_L};
    border: 1px solid #aaaacc;
    border-radius: 6px;
    padding: 5px 8px;
    color: {TEXT_MAIN_L};
    font-size: 16px;
    min-width: 70px;
}}
QSpinBox:focus {{
    border: 1px solid {ACCENT_L};
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background-color: #ddddee;
    border-radius: 3px;
    width: 18px;
    height: 14px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {ACCENT_DIM_L};
}}
QSpinBox::up-arrow {{
    width: 8px;
    height: 8px;
}}
QSpinBox::down-arrow {{
    width: 8px;
    height: 8px;
}}

/* ── Buttons ── */
QPushButton {{
    background-color: {BG_CARD_L};
    border: 1px solid #aaaacc;
    border-radius: 7px;
    padding: 8px 18px;
    color: {TEXT_MAIN_L};
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: #e0e0f0;
    border-color: {ACCENT_L};
}}
QPushButton:pressed {{
    background-color: #ccccdd;
}}
QPushButton#primary {{
    background-color: {ACCENT_L};
    border: 1px solid {ACCENT_DIM_L};
    color: #ffffff;
    font-weight: 700;
    font-size: 14px;
    padding: 10px 28px;
}}
QPushButton#primary:hover {{
    background-color: {ACCENT_DIM_L};
    color: #fff8e0;
}}
QPushButton#danger {{
    background-color: #fdeaea;
    border: 1px solid #f87171;
    color: #c0392b;
}}
QPushButton#danger:hover {{
    background-color: #fbd5d5;
}}
QPushButton#toolbar_btn {{
    background-color: transparent;
    border: none;
    color: {TEXT_DIM_L};
    font-size: 11px;
    padding: 4px 8px;
}}
QPushButton#toolbar_btn:hover {{
    color: {ACCENT_L};
    background-color: #e0e0f0;
    border-radius: 4px;
}}

/* ── Scrollbars ── */
QScrollBar:vertical {{
    background: {BG_BASE_L};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: #aaaacc;
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {ACCENT_L};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

/* ── Listen ── */
QListWidget {{
    background-color: {BG_PANEL_L};
    border: 1px solid #ccccdd;
    border-radius: 8px;
    padding: 4px;
    outline: none;
}}
QListWidget::item {{
    padding: 8px 12px;
    border-radius: 5px;
    color: {TEXT_MAIN_L};
}}
QListWidget::item:hover {{
    background-color: #e8e8f8;
}}
QListWidget::item:selected {{
    background-color: {ACCENT_DIM_L};
    color: #ffffff;
}}

/* ── Dialoge ── */
QDialog {{
    background-color: {BG_PANEL_L};
    border: 1px solid {ACCENT_L};
    border-radius: 12px;
}}
QDialogButtonBox QPushButton {{
    min-width: 80px;
}}

/* ── Separator ── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: #ccccdd;
    border: none;
    background-color: #ccccdd;
    max-height: 1px;
}}

/* ── Scrollbereich ── */
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

/* ── Tooltip ── */
QToolTip {{
    background-color: {BG_CARD_L};
    color: {TEXT_MAIN_L};
    border: 1px solid {ACCENT_L};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}}
"""
