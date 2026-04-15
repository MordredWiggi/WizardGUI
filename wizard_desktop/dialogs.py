"""
dialogs.py – Alle Dialog-Klassen des Wizard-GUI

• WarningDialog              – einfaches OK/Abbrechen
• SaveGameDialog             – Spiel benennen und speichern
• LoadGameDialog             – gespeicherte Spiele laden
• SavePlotDialog             – Plot als Bild speichern
• CelebrationOverlay         – animiertes Overlay für besondere Spielmomente
• SettingsDialog             – Einstellungen (Theme, Sprache, Regeln)
• GroupSelectDialog          – Join an existing group (searchable + code validation)
• GroupCreateDialog          – Create a new group (name + visibility)
• MigrationGroupDialog       – Assign groups to imported legacy games
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
    SUCCESS, DANGER, LEADER, apply_titlebar_theme,
)
from app_settings import t


# ── Hilfsfunktion ─────────────────────────────────────────────────────────────

def _sep() -> QtWidgets.QFrame:
    line = QtWidgets.QFrame()
    line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    # Styling is handled by QSS (QFrame[frameShape="4"]) for theme support
    return line


# ── Basis-Klasse für alle Dialoge mit Theme-Titelleiste ───────────────────────

class ThemedDialog(QtWidgets.QDialog):
    """Base dialog that applies the current theme to the OS title bar."""

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        apply_titlebar_theme(self)


# ─────────────────────────────────────────────────────────────────────────────
# WarningDialog
# ─────────────────────────────────────────────────────────────────────────────

class WarningDialog(ThemedDialog):
    def __init__(self, parent: QtWidgets.QWidget, message: str) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("warning_title"))
        self.setMinimumWidth(360)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 20)

        icon_row = QtWidgets.QHBoxLayout()
        icon_lbl = QtWidgets.QLabel("⚠️")
        icon_lbl.setStyleSheet("font-size: 32px; background: transparent;")
        msg_lbl = QtWidgets.QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(f"color: {TEXT_MAIN}; font-size: 15px; line-height: 1.5; background: transparent;")
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

class SaveGameDialog(ThemedDialog):
    def __init__(self, parent: QtWidgets.QWidget, default_name: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle(t("save_game_title"))
        self.setMinimumWidth(380)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 20)

        title = QtWidgets.QLabel(f"💾  {t('save_game_title')}")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {ACCENT}; background: transparent;")
        layout.addWidget(title)
        layout.addWidget(_sep())

        lbl = QtWidgets.QLabel(t("save_game_label"))
        lbl.setStyleSheet(f"font-size: 15px; background: transparent;")
        layout.addWidget(lbl)
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

class LoadGameDialog(ThemedDialog):
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
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {ACCENT}; background: transparent;")
        layout.addWidget(title)
        layout.addWidget(_sep())

        if not saved_games:
            empty = QtWidgets.QLabel(t("load_game_empty"))
            empty.setStyleSheet(f"color: {TEXT_DIM}; font-size: 15px; font-style: italic; padding: 20px; background: transparent;")
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


class SettingsDialog(ThemedDialog):
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
        title_lbl.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {ACCENT}; background: transparent;")
        layout.addWidget(title_lbl)
        layout.addWidget(_sep())

        # ── Theme ──────────────────────────────────────────────────────────
        theme_lbl = QtWidgets.QLabel(t("settings_theme"))
        theme_lbl.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {TEXT_DIM}; background: transparent;")
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
        lang_lbl.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {TEXT_DIM}; background: transparent;")
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
        try:
            webbrowser.open(_RULES_URL)
        except Exception:
            QtWidgets.QMessageBox.warning(
                self,
                t("warning_title"),
                "Der Browser konnte nicht geöffnet werden.\n\n" + _RULES_URL,
            )

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
# PodiumDialog
# ─────────────────────────────────────────────────────────────────────────────

class PodiumDialog(ThemedDialog):
    """
    Displays the winner's podium at the end of the game.
    Shows the top 3 players with their scores and places.
    Emits accepted() when the user clicks 'Start New Game'.
    """

    def __init__(self, parent: QtWidgets.QWidget, players_sorted: list) -> None:
        """
        Parameters
        ----------
        players_sorted : list of (name, score) tuples, sorted descending by score.
        """
        super().__init__(parent)
        self.setWindowTitle(t("podium_title"))
        self.setMinimumWidth(460)
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(18)
        layout.setContentsMargins(32, 28, 32, 24)

        # Title
        title = QtWidgets.QLabel(t("podium_title"))
        title.setStyleSheet(f"font-size: 24px; font-weight: 800; color: {ACCENT}; letter-spacing: 2px; background: transparent;")
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QtWidgets.QLabel(t("game_over_title"))
        subtitle.setStyleSheet(f"font-size: 15px; color: {TEXT_DIM}; letter-spacing: 1px; background: transparent;")
        subtitle.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addWidget(_sep())

        # Podium places
        place_keys = ["podium_1st", "podium_2nd", "podium_3rd"]
        place_colors = [LEADER, "#aaaacc", "#c9a84c"]  # gold, silver, bronze
        place_sizes = ["22px", "19px", "17px"]

        for rank, (place_key, color, size) in enumerate(zip(place_keys, place_colors, place_sizes)):
            if rank >= len(players_sorted):
                break
            name, score = players_sorted[rank]

            row = QtWidgets.QHBoxLayout()

            place_lbl = QtWidgets.QLabel(t(place_key))
            place_lbl.setStyleSheet(
                f"font-size: {size}; font-weight: 700; color: {color}; min-width: 120px; background: transparent;"
            )

            name_lbl = QtWidgets.QLabel(name)
            name_lbl.setStyleSheet(
                f"font-size: {size}; font-weight: 600; color: {TEXT_MAIN}; background: transparent;"
            )

            score_lbl = QtWidgets.QLabel(t("podium_points", pts=score))
            score_lbl.setStyleSheet(
                f"font-size: {size}; font-weight: 600; color: {color}; background: transparent;"
            )
            score_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)

            row.addWidget(place_lbl)
            row.addWidget(name_lbl, 1)
            row.addWidget(score_lbl)
            layout.addLayout(row)

            if rank < min(2, len(players_sorted) - 1):
                layout.addWidget(_sep())

        # Show remaining players if more than 3
        if len(players_sorted) > 3:
            layout.addWidget(_sep())
            others_lbl = QtWidgets.QLabel()
            lines = []
            for rank in range(3, len(players_sorted)):
                name, score = players_sorted[rank]
                lines.append(f"{rank + 1}. {name}  –  {t('podium_points', pts=score)}")
            others_lbl.setText("\n".join(lines))
            others_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 14px; background: transparent;")
            layout.addWidget(others_lbl)

        layout.addWidget(_sep())

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        btn_close = QtWidgets.QPushButton(t("podium_close"))
        btn_close.setObjectName("primary")
        btn_close.setMinimumHeight(40)
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)


# ─────────────────────────────────────────────────────────────────────────────
# MigrationDialog
# ─────────────────────────────────────────────────────────────────────────────

class MigrationDialog(ThemedDialog):
    """Asks the user whether to upload old games to the leaderboard."""

    def __init__(self, parent: QtWidgets.QWidget, count: int) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("migration_title"))
        self.setMinimumWidth(420)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(28, 24, 28, 20)

        # Title
        title = QtWidgets.QLabel(f"📊  {t('migration_title')}")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {ACCENT}; background: transparent;")
        layout.addWidget(title)
        layout.addWidget(_sep())

        # Message
        msg = QtWidgets.QLabel(t("migration_message", n=count))
        msg.setWordWrap(True)
        msg.setStyleSheet(f"font-size: 14px; color: {TEXT_MAIN}; line-height: 1.5; background: transparent;")
        layout.addWidget(msg)

        layout.addWidget(_sep())

        # Buttons
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        btn_skip = QtWidgets.QPushButton(t("migration_no"))
        btn_upload = QtWidgets.QPushButton(t("migration_yes"))
        btn_upload.setObjectName("primary")
        btn_skip.clicked.connect(self.reject)
        btn_upload.clicked.connect(self.accept)
        btn_row.addWidget(btn_skip)
        btn_row.addWidget(btn_upload)
        layout.addLayout(btn_row)


class MigrationProgressDialog(ThemedDialog):
    """Progress dialog for uploading old games to the leaderboard."""

    canceled = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget, total: int) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("migration_title"))
        self.setMinimumWidth(400)
        self.setModal(True)
        self._total = total
        self._was_canceled = False

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(28, 24, 28, 20)

        self._label = QtWidgets.QLabel(t("migration_progress", done=0, total=total))
        self._label.setStyleSheet(f"font-size: 14px; color: {TEXT_MAIN}; background: transparent;")
        layout.addWidget(self._label)

        self._progress = QtWidgets.QProgressBar()
        self._progress.setRange(0, total)
        self._progress.setValue(0)
        self._progress.setMinimumHeight(22)
        layout.addWidget(self._progress)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        self._btn_cancel = QtWidgets.QPushButton(t("cancel"))
        self._btn_cancel.clicked.connect(self._on_cancel)
        btn_row.addWidget(self._btn_cancel)
        layout.addLayout(btn_row)

    def update_progress(self, done: int) -> None:
        self._label.setText(t("migration_progress", done=done, total=self._total))
        self._progress.setValue(done)

    def _on_cancel(self) -> None:
        self._was_canceled = True
        self.canceled.emit()

    def wasCanceled(self) -> bool:
        return self._was_canceled


# ─────────────────────────────────────────────────────────────────────────────
# CelebrationOverlay
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# GroupSelectDialog  – join an existing group with code validation
# ─────────────────────────────────────────────────────────────────────────────

class GroupSelectDialog(ThemedDialog):
    """
    Shows a searchable list of public groups.
    The user must enter the 4-digit code to confirm joining.
    Emits accepted() with self.selected_group set to the validated group dict.
    """

    def __init__(self, parent: QtWidgets.QWidget, client) -> None:
        super().__init__(parent)
        self._client = client
        self.selected_group: Optional[Dict] = None
        self._validated_group: Optional[Dict] = None
        self._check_worker = None
        self._list_worker = None

        self.setWindowTitle(t("group_select_label"))
        self.setMinimumSize(500, 460)
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 20, 24, 18)

        title = QtWidgets.QLabel(f"👥  {t('group_select_label')}")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {ACCENT}; background: transparent;")
        layout.addWidget(title)
        layout.addWidget(_sep())

        # ── Search row ───────────────────────────────────────────────────────
        search_row = QtWidgets.QHBoxLayout()
        self._search_edit = QtWidgets.QLineEdit()
        self._search_edit.setPlaceholderText(t("group_search_placeholder"))
        self._search_edit.setMinimumHeight(34)
        self._search_edit.textChanged.connect(self._on_search_changed)
        search_row.addWidget(self._search_edit)
        layout.addLayout(search_row)

        # ── Group list ───────────────────────────────────────────────────────
        self._group_list = QtWidgets.QListWidget()
        self._group_list.setMinimumHeight(140)
        self._group_list.currentItemChanged.connect(self._on_group_selected)
        layout.addWidget(self._group_list)

        self._no_groups_lbl = QtWidgets.QLabel(t("no_groups"))
        self._no_groups_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-style: italic; font-size: 13px; background: transparent;")
        self._no_groups_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._no_groups_lbl.hide()
        layout.addWidget(self._no_groups_lbl)

        layout.addWidget(_sep())

        # ── Code validation ──────────────────────────────────────────────────
        code_lbl = QtWidgets.QLabel(t("group_code_label"))
        code_lbl.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {TEXT_DIM}; background: transparent;")
        layout.addWidget(code_lbl)

        code_row = QtWidgets.QHBoxLayout()
        self._code_edit = QtWidgets.QLineEdit()
        self._code_edit.setPlaceholderText(t("group_code_placeholder"))
        self._code_edit.setMaxLength(4)
        self._code_edit.setMinimumHeight(34)
        self._code_edit.setMaximumWidth(120)
        self._code_edit.textChanged.connect(self._on_code_changed)
        btn_validate = QtWidgets.QPushButton(t("group_code_validate"))
        btn_validate.setMinimumHeight(34)
        btn_validate.clicked.connect(self._validate_code)
        code_row.addWidget(self._code_edit)
        code_row.addWidget(btn_validate)
        code_row.addStretch()
        layout.addLayout(code_row)

        self._code_status = QtWidgets.QLabel()
        self._code_status.setStyleSheet(f"font-size: 12px; background: transparent;")
        layout.addWidget(self._code_status)

        # Remember-code checkbox
        self._chk_remember = QtWidgets.QCheckBox(t("group_remember_code"))
        self._chk_remember.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 12px; background: transparent;"
        )
        self._chk_remember.setChecked(True)
        layout.addWidget(self._chk_remember)

        layout.addWidget(_sep())

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QtWidgets.QPushButton(t("cancel"))
        self._btn_join = QtWidgets.QPushButton(t("load"))
        self._btn_join.setObjectName("primary")
        self._btn_join.setEnabled(False)
        btn_cancel.clicked.connect(self.reject)
        self._btn_join.clicked.connect(self._on_join)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(self._btn_join)
        layout.addLayout(btn_row)

        self._debounce = QtCore.QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(350)
        self._debounce.timeout.connect(self._do_search)

        self._do_search()

    def _on_search_changed(self, _: str) -> None:
        self._debounce.start()

    def _do_search(self) -> None:
        if not self._client:
            return
        from leaderboard_client import GroupsListWorker
        self._list_worker = GroupsListWorker(self._client, self._search_edit.text().strip())
        self._list_worker.result.connect(self._on_groups_received)
        self._list_worker.start()

    def _on_groups_received(self, groups: object) -> None:
        self._group_list.clear()
        if not groups:
            self._no_groups_lbl.show()
            self._group_list.hide()
            return
        self._no_groups_lbl.hide()
        self._group_list.show()
        for g in groups:
            n = g.get("player_count", 0)
            item = QtWidgets.QListWidgetItem(
                f"👥  {g['name']}  ({t('group_players_count', n=n)})"
            )
            item.setData(QtCore.Qt.ItemDataRole.UserRole, g)
            self._group_list.addItem(item)

    def _on_group_selected(self, current, _) -> None:
        # Auto-fill the code from the local cache if the user previously
        # opted in to remembering this group. Otherwise the user must type
        # it, since the code gates access.
        if current is None:
            return
        group = current.data(QtCore.Qt.ItemDataRole.UserRole)
        if not group:
            return
        from group_cache import lookup_code_by_name
        cached = lookup_code_by_name(group.get("name", ""))
        if cached:
            self._code_edit.setText(cached)
            self._validate_code()

    def _on_code_changed(self, text: str) -> None:
        # Reset validation if user edits code
        self._validated_group = None
        self._btn_join.setEnabled(False)
        self._code_status.clear()

    def _validate_code(self) -> None:
        code = self._code_edit.text().strip()
        if len(code) != 4 or not code.isdigit():
            self._code_status.setText(t("group_code_invalid"))
            self._code_status.setStyleSheet(f"font-size: 12px; color: {DANGER}; background: transparent;")
            return
        if not self._client:
            return
        from leaderboard_client import GroupCodeCheckWorker
        self._check_worker = GroupCodeCheckWorker(self._client, code)
        self._check_worker.result.connect(self._on_code_checked)
        self._check_worker.start()

    def _on_code_checked(self, group: object) -> None:
        if group is None:
            self._code_status.setText(t("group_code_invalid"))
            self._code_status.setStyleSheet(f"font-size: 12px; color: {DANGER}; background: transparent;")
            self._validated_group = None
            self._btn_join.setEnabled(False)
        else:
            self._validated_group = group
            self._code_status.setText(t("group_code_correct", name=group["name"]))
            self._code_status.setStyleSheet(f"font-size: 12px; color: {SUCCESS}; background: transparent;")
            self._btn_join.setEnabled(True)

    def _on_join(self) -> None:
        if self._validated_group:
            self.selected_group = self._validated_group
            if self._chk_remember.isChecked():
                from group_cache import remember_group
                remember_group(self._validated_group)
            self.accept()


# ─────────────────────────────────────────────────────────────────────────────
# GroupCreateDialog  – create a new group
# ─────────────────────────────────────────────────────────────────────────────

class GroupCreateDialog(ThemedDialog):
    """
    Dialog to create a new group with a name, a 4-digit code, and visibility.
    Emits accepted() with self.created_group set to the new group dict.
    """

    def __init__(self, parent: QtWidgets.QWidget, client) -> None:
        super().__init__(parent)
        self._client = client
        self.created_group: Optional[Dict] = None
        self._create_worker = None

        self.setWindowTitle(t("group_create_label"))
        self.setMinimumWidth(420)
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 20, 24, 18)

        title = QtWidgets.QLabel(f"✚  {t('group_create_label')}")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {ACCENT}; background: transparent;")
        layout.addWidget(title)
        layout.addWidget(_sep())

        # Name
        name_lbl = QtWidgets.QLabel(t("group_name_placeholder"))
        name_lbl.setStyleSheet(f"font-size: 13px; color: {TEXT_DIM}; background: transparent;")
        layout.addWidget(name_lbl)
        self._name_edit = QtWidgets.QLineEdit()
        self._name_edit.setPlaceholderText(t("group_name_placeholder"))
        self._name_edit.setMinimumHeight(34)
        layout.addWidget(self._name_edit)

        # Code
        code_lbl = QtWidgets.QLabel(t("group_code_label"))
        code_lbl.setStyleSheet(f"font-size: 13px; color: {TEXT_DIM}; background: transparent;")
        layout.addWidget(code_lbl)
        self._code_edit = QtWidgets.QLineEdit()
        self._code_edit.setPlaceholderText(t("group_code_placeholder"))
        self._code_edit.setMaxLength(4)
        self._code_edit.setMinimumHeight(34)
        self._code_edit.setMaximumWidth(120)
        layout.addWidget(self._code_edit)

        # Visibility
        vis_lbl = QtWidgets.QLabel()
        vis_lbl.setStyleSheet(f"font-size: 13px; color: {TEXT_DIM}; background: transparent;")
        layout.addWidget(vis_lbl)

        self._radio_public = QtWidgets.QRadioButton(t("group_visibility_public"))
        self._radio_hidden = QtWidgets.QRadioButton(t("group_visibility_hidden"))
        self._radio_public.setChecked(True)
        layout.addWidget(self._radio_public)
        layout.addWidget(self._radio_hidden)

        self._status_lbl = QtWidgets.QLabel()
        self._status_lbl.setStyleSheet(f"font-size: 12px; background: transparent;")
        self._status_lbl.setWordWrap(True)
        layout.addWidget(self._status_lbl)

        # Remember-code checkbox
        self._chk_remember = QtWidgets.QCheckBox(t("group_remember_code"))
        self._chk_remember.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 12px; background: transparent;"
        )
        self._chk_remember.setChecked(True)
        layout.addWidget(self._chk_remember)

        layout.addWidget(_sep())

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QtWidgets.QPushButton(t("cancel"))
        self._btn_create = QtWidgets.QPushButton(t("group_create_btn"))
        self._btn_create.setObjectName("primary")
        self._btn_create.setMinimumHeight(36)
        btn_cancel.clicked.connect(self.reject)
        self._btn_create.clicked.connect(self._on_create)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(self._btn_create)
        layout.addLayout(btn_row)

    def _on_create(self) -> None:
        name = self._name_edit.text().strip()
        code = self._code_edit.text().strip()
        if not name:
            self._status_lbl.setText(t("group_name_placeholder") + " – required")
            self._status_lbl.setStyleSheet(f"font-size: 12px; color: {DANGER}; background: transparent;")
            return
        if len(code) != 4 or not code.isdigit():
            self._status_lbl.setText(t("group_code_invalid"))
            self._status_lbl.setStyleSheet(f"font-size: 12px; color: {DANGER}; background: transparent;")
            return
        visibility = "hidden" if self._radio_hidden.isChecked() else "public"
        if not self._client:
            return
        from leaderboard_client import GroupCreateWorker
        self._btn_create.setEnabled(False)
        self._create_worker = GroupCreateWorker(self._client, name, code, visibility)
        self._create_worker.result.connect(self._on_created)
        self._create_worker.start()

    def _on_created(self, group: object) -> None:
        self._btn_create.setEnabled(True)
        if group is None:
            code = self._code_edit.text().strip()
            self._status_lbl.setText(t("group_code_taken", code=code))
            self._status_lbl.setStyleSheet(f"font-size: 12px; color: {DANGER}; background: transparent;")
        else:
            self.created_group = group
            if self._chk_remember.isChecked():
                from group_cache import remember_group
                remember_group(group)
            self._status_lbl.setText(t("group_created_ok", name=group["name"], code=group["code"]))
            self._status_lbl.setStyleSheet(f"font-size: 12px; color: {SUCCESS}; background: transparent;")
            QtCore.QTimer.singleShot(800, self.accept)


# ─────────────────────────────────────────────────────────────────────────────
# MigrationGroupDialog  – assign groups to imported legacy games
# ─────────────────────────────────────────────────────────────────────────────

class MigrationGroupDialog(ThemedDialog):
    """
    Shown before legacy migration: lets the user select/create a group and
    then assign each imported game to a group (can all go to the same group).

    self.group_assignments: dict[filepath_str, dict] = { fp: group_dict, ... }
    """

    def __init__(
        self,
        parent: QtWidgets.QWidget,
        saved_games: List[Dict],
        client,
    ) -> None:
        super().__init__(parent)
        self._client = client
        self._saved_games = saved_games
        self.group_assignments: Dict[str, Dict] = {}

        self.setWindowTitle(t("migration_group_header"))
        self.setMinimumSize(560, 520)
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(22, 18, 22, 16)

        title = QtWidgets.QLabel(f"📊  {t('migration_group_header')}")
        title.setStyleSheet(f"font-size: 17px; font-weight: 700; color: {ACCENT}; background: transparent;")
        layout.addWidget(title)

        info = QtWidgets.QLabel(t("migration_assign_group"))
        info.setStyleSheet(f"font-size: 13px; color: {TEXT_DIM}; background: transparent;")
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addWidget(_sep())

        # ── Quick-assign section ─────────────────────────────────────────────
        quick_row = QtWidgets.QHBoxLayout()
        quick_lbl = QtWidgets.QLabel(t("migration_assign_group") + " (all):")
        quick_lbl.setStyleSheet(f"font-size: 12px; color: {TEXT_DIM}; background: transparent;")
        quick_row.addWidget(quick_lbl)
        quick_row.addStretch()
        btn_join_all = QtWidgets.QPushButton(t("group_select_label"))
        btn_join_all.setMinimumHeight(30)
        btn_join_all.clicked.connect(lambda: self._pick_group_for_all(create=False))
        btn_create_all = QtWidgets.QPushButton(t("group_create_btn"))
        btn_create_all.setMinimumHeight(30)
        btn_create_all.clicked.connect(lambda: self._pick_group_for_all(create=True))
        quick_row.addWidget(btn_join_all)
        quick_row.addWidget(btn_create_all)
        layout.addLayout(quick_row)

        layout.addWidget(_sep())

        # ── Per-game list ────────────────────────────────────────────────────
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        container = QtWidgets.QWidget()
        self._games_layout = QtWidgets.QVBoxLayout(container)
        self._games_layout.setSpacing(8)
        self._games_layout.setContentsMargins(4, 4, 4, 4)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        self._game_rows: List[Dict] = []  # {game, label_widget, group_dict}
        for game in saved_games:
            row_frame = QtWidgets.QFrame()
            row_frame.setObjectName("panel")
            row_layout = QtWidgets.QHBoxLayout(row_frame)
            row_layout.setContentsMargins(10, 6, 10, 6)

            name_lbl = QtWidgets.QLabel(game.get("name", "?"))
            name_lbl.setStyleSheet(f"font-size: 13px; font-weight: 600; background: transparent;")
            group_lbl = QtWidgets.QLabel(t("migration_no_group"))
            group_lbl.setStyleSheet(f"font-size: 12px; color: {TEXT_DIM}; background: transparent;")

            btn_pick = QtWidgets.QPushButton(t("group_select_label"))
            btn_pick.setMinimumHeight(28)
            btn_create = QtWidgets.QPushButton(t("group_create_btn"))
            btn_create.setMinimumHeight(28)

            row_layout.addWidget(name_lbl, 1)
            row_layout.addWidget(group_lbl)
            row_layout.addWidget(btn_pick)
            row_layout.addWidget(btn_create)

            self._games_layout.addWidget(row_frame)

            entry = {"game": game, "label": group_lbl, "group": None}
            self._game_rows.append(entry)

            btn_pick.clicked.connect(lambda _, e=entry: self._pick_group_for_game(e, create=False))
            btn_create.clicked.connect(lambda _, e=entry: self._pick_group_for_game(e, create=True))

        self._games_layout.addStretch()

        layout.addWidget(_sep())

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QtWidgets.QPushButton(t("cancel"))
        self._btn_ok = QtWidgets.QPushButton(t("migration_yes"))
        self._btn_ok.setObjectName("primary")
        btn_cancel.clicked.connect(self.reject)
        self._btn_ok.clicked.connect(self._on_ok)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(self._btn_ok)
        layout.addLayout(btn_row)

    def _pick_group_for_all(self, create: bool) -> None:
        if create:
            dlg = GroupCreateDialog(self, self._client)
            if dlg.exec() and dlg.created_group:
                g = dlg.created_group
                for entry in self._game_rows:
                    self._assign_group(entry, g)
        else:
            dlg = GroupSelectDialog(self, self._client)
            if dlg.exec() and dlg.selected_group:
                g = dlg.selected_group
                for entry in self._game_rows:
                    self._assign_group(entry, g)

    def _pick_group_for_game(self, entry: Dict, create: bool) -> None:
        if create:
            dlg = GroupCreateDialog(self, self._client)
            if dlg.exec() and dlg.created_group:
                self._assign_group(entry, dlg.created_group)
        else:
            dlg = GroupSelectDialog(self, self._client)
            if dlg.exec() and dlg.selected_group:
                self._assign_group(entry, dlg.selected_group)

    def _assign_group(self, entry: Dict, group: Dict) -> None:
        entry["group"] = group
        entry["label"].setText(t("group_selected", name=group["name"], code=group["code"]))
        entry["label"].setStyleSheet(f"font-size: 12px; color: {SUCCESS}; background: transparent;")

    def _on_ok(self) -> None:
        # Require all games to have a group assignment
        unassigned = [e for e in self._game_rows if e["group"] is None]
        if unassigned:
            QtWidgets.QMessageBox.warning(
                self,
                t("warning_title"),
                t("migration_no_group") + f" ({len(unassigned)} games)",
            )
            return
        for entry in self._game_rows:
            fp = str(entry["game"].get("filepath", ""))
            self.group_assignments[fp] = entry["group"]
        self.accept()


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
