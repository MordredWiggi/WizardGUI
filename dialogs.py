"""
dialogs.py – Alle Dialog-Klassen des Wizard-GUI

• WarningDialog        – einfaches OK/Abbrechen
• SaveGameDialog       – Spiel benennen und speichern
• LoadGameDialog       – gespeicherte Spiele laden
• SavePlotDialog       – Plot als Bild speichern
• CelebrationOverlay   – animiertes Overlay für besondere Spielmomente
• SettingsDialog       – Einstellungen (Theme, Sprache, Regeln)
"""
from __future__ import annotations

import webbrowser
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from PyQt6 import QtCore, QtWidgets, QtGui

from style import (
    BG_PANEL, BG_CARD, BG_DEEP,
    ACCENT, ACCENT_DIM, TEXT_MAIN, TEXT_DIM,
    SUCCESS, DANGER, LEADER,
)
from app_settings import t


# ── Hilfsfunktion ─────────────────────────────────────────────────────────────

def _sep() -> QtWidgets.QFrame:
    line = QtWidgets.QFrame()
    line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    line.setStyleSheet(f"background-color: #2a2a4a; border: none; max-height: 1px;")
    return line


# ─────────────────────────────────────────────────────────────────────────────
# WarningDialog
# ─────────────────────────────────────────────────────────────────────────────

class WarningDialog(QtWidgets.QDialog):
    def __init__(self, parent: QtWidgets.QWidget, message: str) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("warning_title"))
        self.setMinimumWidth(360)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 20)

        icon_row = QtWidgets.QHBoxLayout()
        icon_lbl = QtWidgets.QLabel("⚠️")
        icon_lbl.setStyleSheet("font-size: 28px;")
        msg_lbl = QtWidgets.QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(f"color: {TEXT_MAIN}; font-size: 13px; line-height: 1.5;")
        icon_row.addWidget(icon_lbl, 0, QtCore.Qt.AlignmentFlag.AlignTop)
        icon_row.addWidget(msg_lbl, 1)
        layout.addLayout(icon_row)

        layout.addWidget(_sep())

        btn_box = QtWidgets.QHBoxLayout()
        btn_box.addStretch()
        self.btn_cancel = QtWidgets.QPushButton(t("cancel"))
        self.btn_ok = QtWidgets.QPushButton(t("proceed"))
        self.btn_ok.setObjectName("danger")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.clicked.connect(self.accept)
        btn_box.addWidget(self.btn_cancel)
        btn_box.addWidget(self.btn_ok)
        layout.addLayout(btn_box)


# ─────────────────────────────────────────────────────────────────────────────
# SaveGameDialog
# ─────────────────────────────────────────────────────────────────────────────

class SaveGameDialog(QtWidgets.QDialog):
    def __init__(self, parent: QtWidgets.QWidget, default_name: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle(t("save_game_title"))
        self.setMinimumWidth(380)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 20)

        title = QtWidgets.QLabel(f"💾  {t('save_game_title')}")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {ACCENT};")
        layout.addWidget(title)
        layout.addWidget(_sep())

        layout.addWidget(QtWidgets.QLabel(t("save_game_label")))
        self.name_edit = QtWidgets.QLineEdit(default_name)
        self.name_edit.setPlaceholderText(t("save_game_placeholder"))
        layout.addWidget(self.name_edit)

        layout.addWidget(_sep())
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QtWidgets.QPushButton(t("cancel"))
        btn_save = QtWidgets.QPushButton(t("save"))
        btn_save.setObjectName("primary")
        btn_cancel.clicked.connect(self.reject)
        btn_save.clicked.connect(self.accept)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

    @property
    def game_name(self) -> str:
        return self.name_edit.text().strip()


# ─────────────────────────────────────────────────────────────────────────────
# LoadGameDialog
# ─────────────────────────────────────────────────────────────────────────────

class LoadGameDialog(QtWidgets.QDialog):
    def __init__(self, parent: QtWidgets.QWidget, saved_games: List[Dict]) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("load_game_title"))
        self.setMinimumSize(480, 400)
        self._saved_games = saved_games
        self._selected: Optional[Dict] = None

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 20)

        title = QtWidgets.QLabel(f"📂  {t('load_game_title')}")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {ACCENT};")
        layout.addWidget(title)
        layout.addWidget(_sep())

        if not saved_games:
            empty = QtWidgets.QLabel(t("load_game_empty"))
            empty.setStyleSheet(f"color: {TEXT_DIM}; font-style: italic; padding: 20px;")
            empty.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(empty)
        else:
            self.list_widget = QtWidgets.QListWidget()
            for game in saved_games:
                saved_at = game.get("saved_at", "")
                try:
                    dt = datetime.fromisoformat(saved_at)
                    date_str = dt.strftime("%d.%m.%Y  %H:%M")
                except Exception:
                    date_str = saved_at[:16] if saved_at else "–"

                players_str = ", ".join(game.get("players", []))
                rounds = game.get("rounds", 0)

                item = QtWidgets.QListWidgetItem()
                item.setData(QtCore.Qt.ItemDataRole.UserRole, game)
                item.setText(
                    f"{game['name']}\n"
                    f"{date_str}  ·  {players_str}  ·  {t('round')} {rounds}"
                )
                self.list_widget.addItem(item)

            self.list_widget.itemDoubleClicked.connect(self._on_double_click)
            layout.addWidget(self.list_widget)

        layout.addWidget(_sep())
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QtWidgets.QPushButton(t("cancel"))
        self.btn_load = QtWidgets.QPushButton(t("load"))
        self.btn_load.setObjectName("primary")
        self.btn_load.setEnabled(bool(saved_games))
        btn_cancel.clicked.connect(self.reject)
        self.btn_load.clicked.connect(self._on_load)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(self.btn_load)
        layout.addLayout(btn_row)

    def _on_double_click(self, _item: QtWidgets.QListWidgetItem) -> None:
        self._on_load()

    def _on_load(self) -> None:
        if hasattr(self, "list_widget"):
            current = self.list_widget.currentItem()
            if current:
                self._selected = current.data(QtCore.Qt.ItemDataRole.UserRole)
                self.accept()

    @property
    def selected_game(self) -> Optional[Dict]:
        return self._selected


# ─────────────────────────────────────────────────────────────────────────────
# SettingsDialog
# ─────────────────────────────────────────────────────────────────────────────

_RULES_URL = "https://www.brettspiele-report.de/images/wizard/Spielanleitung_Wizard.pdf"


class SettingsDialog(QtWidgets.QDialog):
    """
    Einstellungen-Popup mit:
      • Dark-/Light-Mode Umschalter
      • Sprach-Auswahl (DE/EN/FR/HI)
      • Regeln-Button (öffnet URL im Browser)
    """

    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        import app_settings as _as
        self._as = _as
        self.setWindowTitle(t("settings_title"))
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(28, 24, 28, 20)

        # ── Titel ──────────────────────────────────────────────────────────
        title_lbl = QtWidgets.QLabel(f"⚙  {t('settings_title')}")
        title_lbl.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {ACCENT};")
        layout.addWidget(title_lbl)
        layout.addWidget(_sep())

        # ── Theme ──────────────────────────────────────────────────────────
        theme_lbl = QtWidgets.QLabel(t("settings_theme"))
        theme_lbl.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {TEXT_DIM};")
        layout.addWidget(theme_lbl)

        theme_row = QtWidgets.QHBoxLayout()
        self._radio_dark = QtWidgets.QRadioButton(t("settings_theme_dark"))
        self._radio_light = QtWidgets.QRadioButton(t("settings_theme_light"))
        if _as.get_theme() == "light":
            self._radio_light.setChecked(True)
        else:
            self._radio_dark.setChecked(True)
        theme_row.addWidget(self._radio_dark)
        theme_row.addWidget(self._radio_light)
        theme_row.addStretch()
        layout.addLayout(theme_row)

        layout.addWidget(_sep())

        # ── Sprache ────────────────────────────────────────────────────────
        lang_lbl = QtWidgets.QLabel(t("settings_language"))
        lang_lbl.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {TEXT_DIM};")
        layout.addWidget(lang_lbl)

        from translations import LANGUAGE_NAMES
        self._lang_combo = QtWidgets.QComboBox()
        self._lang_code_map: list[str] = []
        current_lang = _as.get_language()
        current_idx = 0
        for idx, (code, name) in enumerate(LANGUAGE_NAMES.items()):
            self._lang_combo.addItem(name)
            self._lang_code_map.append(code)
            if code == current_lang:
                current_idx = idx
        self._lang_combo.setCurrentIndex(current_idx)
        layout.addWidget(self._lang_combo)

        layout.addWidget(_sep())

        # ── Regeln ─────────────────────────────────────────────────────────
        btn_rules = QtWidgets.QPushButton(t("settings_rules_btn"))
        btn_rules.setMinimumHeight(38)
        btn_rules.clicked.connect(self._open_rules)
        layout.addWidget(btn_rules)

        layout.addWidget(_sep())

        # ── Buttons ────────────────────────────────────────────────────────
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        btn_apply = QtWidgets.QPushButton(t("apply"))
        btn_apply.setObjectName("primary")
        btn_apply.setMinimumHeight(38)
        btn_apply.clicked.connect(self._apply_and_close)
        btn_row.addWidget(btn_apply)
        layout.addLayout(btn_row)

    # ── private ───────────────────────────────────────────────────────────────

    def _open_rules(self) -> None:
        """Öffnet die Regelseite im Standard-Browser."""
        webbrowser.open(_RULES_URL)

    def _apply_and_close(self) -> None:
        """Speichert Einstellungen, wendet Theme an und schließt den Dialog."""
        from PyQt6.QtWidgets import QApplication
        from style import STYLESHEET, STYLESHEET_LIGHT

        # Sprache setzen
        lang_idx = self._lang_combo.currentIndex()
        if 0 <= lang_idx < len(self._lang_code_map):
            self._as.set_language(self._lang_code_map[lang_idx])

        # Theme setzen und sofort anwenden
        if self._radio_light.isChecked():
            self._as.set_theme("light")
            app = QApplication.instance()
            if app:
                app.setStyleSheet(STYLESHEET_LIGHT)
        else:
            self._as.set_theme("dark")
            app = QApplication.instance()
            if app:
                app.setStyleSheet(STYLESHEET)

        self.accept()


# ─────────────────────────────────────────────────────────────────────────────
# CelebrationOverlay
# ─────────────────────────────────────────────────────────────────────────────

class CelebrationOverlay(QtWidgets.QWidget):
    """
    Transparentes Overlay-Widget, das über dem übergeordneten Fenster erscheint
    und nach einigen Sekunden wieder ausblendet.
    """

    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoSystemBackground)

        self._opacity = 0.0
        self._timer_fade_in: Optional[QtCore.QTimer] = None
        self._timer_hold: Optional[QtCore.QTimer] = None
        self._timer_fade_out: Optional[QtCore.QTimer] = None

        # Haupt-Label
        self._label = QtWidgets.QLabel(self)
        self._label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._label.setWordWrap(True)
        self._label.setStyleSheet(
            f"""
            QLabel {{
                color: white;
                font-size: 32px;
                font-weight: 800;
                letter-spacing: 1px;
                background: transparent;
            }}
            """
        )

        # Hintergrund-Rahmen
        self._bg = QtWidgets.QFrame(self)
        self._bg.setStyleSheet(
            f"""
            QFrame {{
                background-color: rgba(20, 18, 50, 210);
                border: 2px solid {ACCENT};
                border-radius: 18px;
            }}
            """
        )
        self._bg.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.hide()

    # ── public API ────────────────────────────────────────────────────────────

    def show_event(
        self,
        emoji: str,
        headline: str,
        subline: str = "",
        color: str = ACCENT,
        hold_ms: int = 2200,
    ) -> None:
        """Einblenden mit Text, dann nach hold_ms ms ausblenden."""
        text = f"{emoji}\n{headline}"
        if subline:
            text += f"\n{subline}"
        self._label.setText(text)
        self._label.setStyleSheet(
            f"""
            QLabel {{
                color: {color};
                font-size: 30px;
                font-weight: 800;
                letter-spacing: 1px;
                background: transparent;
            }}
            """
        )

        self._resize_to_parent()
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()

        self._fade(target=1.0, step=0.08, interval=20, callback=lambda: self._start_hold(hold_ms))

    # ── private helpers ───────────────────────────────────────────────────────

    def _resize_to_parent(self) -> None:
        if self.parent():
            self.setGeometry(self.parent().rect())
            # centre the background box
            w, h = 480, 200
            x = (self.width() - w) // 2
            y = (self.height() - h) // 2
            self._bg.setGeometry(x, y, w, h)
            self._label.setGeometry(x, y, w, h)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self._resize_to_parent()
        super().resizeEvent(event)

    def _start_hold(self, hold_ms: int) -> None:
        self._timer_hold = QtCore.QTimer(self)
        self._timer_hold.setSingleShot(True)
        self._timer_hold.timeout.connect(self._start_fade_out)
        self._timer_hold.start(hold_ms)

    def _start_fade_out(self) -> None:
        self._fade(target=0.0, step=-0.06, interval=25, callback=self.hide)

    def _fade(self, target: float, step: float, interval: int, callback) -> None:
        """Animate opacity from current value towards target."""
        self._opacity = self.windowOpacity()

        t = QtCore.QTimer(self)
        t.setInterval(interval)

        def _tick() -> None:
            self._opacity = max(0.0, min(1.0, self._opacity + step))
            self.setWindowOpacity(self._opacity)
            if (step > 0 and self._opacity >= target) or (step < 0 and self._opacity <= target):
                t.stop()
                callback()

        t.timeout.connect(_tick)
        t.start()
