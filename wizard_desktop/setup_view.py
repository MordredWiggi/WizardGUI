"""
setup_view.py – Spieler-Setup-Bildschirm

Zeigt:
  • Titelbereich mit Einstellungs-Button
  • Eingabefeld für Spielernamen
  • Liste gespeicherter Spiele zum Laden
  • „Spiel starten"-Button
"""
from __future__ import annotations

from typing import List, Optional

from PyQt6 import QtCore, QtWidgets, QtGui

from style import (
    ACCENT, ACCENT_DIM, BG_BASE, BG_PANEL, BG_CARD,
    TEXT_MAIN, TEXT_DIM, PLAYER_COLORS,
)
from save_manager import SaveManager
from app_settings import t
from game_control import GAME_MODE_STANDARD, GAME_MODE_MULTIPLICATIVE


AVATARS = ["🧙‍♂️", "🧙‍♀️", "🧚‍♂️", "🧚‍♀️", "🧞‍♂️", "🧞‍♀️", "🧝‍♂️", "🧝‍♀️", "🧛‍♂️", "🧛‍♀️"]


class PlayerChip(QtWidgets.QFrame):
    """Kleiner farbiger Chip für einen Spielernamen."""

    removed = QtCore.pyqtSignal(str)

    def __init__(self, name: str, color: str, parent: Optional[QtWidgets.QWidget] = None, display: Optional[str] = None):
        super().__init__(parent)
        self.name = name
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: transparent;
                border: 1px solid {color};
                border-radius: 14px;
                padding: 2px 10px;
            }}
            """
        )
        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(6, 3, 3, 3)
        row.setSpacing(4)

        lbl = QtWidgets.QLabel(display if display is not None else name)
        lbl.setStyleSheet(f"color: {color}; font-weight: 600; font-size: 12px; background: transparent; border: none;")

        btn_x = QtWidgets.QPushButton("✕")
        btn_x.setFixedSize(18, 18)
        btn_x.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                color: {color};
                border: none;
                font-size: 10px;
                font-weight: 700;
                padding: 0;
            }}
            QPushButton:hover {{ color: white; }}
            """
        )
        btn_x.clicked.connect(lambda: self.removed.emit(self.name))

        row.addWidget(lbl)
        row.addWidget(btn_x)


class SetupView(QtWidgets.QWidget):
    """
    Zeigt dem Benutzer die Möglichkeit, Spieler einzugeben oder ein
    gespeichertes Spiel zu laden.

    Signals
    -------
    start_game(player_names: list[str])
    load_game(filepath: Path)
    settings_changed()
    """

    start_game = QtCore.pyqtSignal(list, str)
    load_game = QtCore.pyqtSignal(object)   # Path
    settings_changed = QtCore.pyqtSignal()

    def __init__(self, save_manager: SaveManager, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self._save_manager = save_manager
        self._players: List[dict] = []
        self._build_ui()

    # ── UI-Aufbau ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Äußerer Scrollbereich
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root.addWidget(scroll)

        container = QtWidgets.QWidget()
        scroll.setWidget(container)

        main = QtWidgets.QVBoxLayout(container)
        main.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        main.setContentsMargins(60, 50, 60, 50)
        main.setSpacing(32)

        # ── Titel ──────────────────────────────────────────────────────────
        # Header row with title and settings button
        title_row = QtWidgets.QHBoxLayout()
        title_row.addStretch()

        title_lbl = QtWidgets.QLabel("🃏  WIZARD")
        title_lbl.setObjectName("title")
        title_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        title_lbl.setStyleSheet(
            "font-size: 40px; background: transparent;"
        )
        title_row.addWidget(title_lbl)
        title_row.addStretch()

        self._btn_settings = QtWidgets.QPushButton("⚙")
        self._btn_settings.setObjectName("toolbar_btn")
        self._btn_settings.setToolTip(t("tooltip_settings"))
        self._btn_settings.setFixedSize(44, 44)
        self._btn_settings.setStyleSheet(
            "QPushButton { font-size: 28px; padding: 0; background: transparent; border: none; }"
            "QPushButton:hover { background-color: #1a1a3a; border-radius: 4px; }"
        )
        self._btn_settings.clicked.connect(self._on_settings)
        title_row.addWidget(self._btn_settings)

        main.addLayout(title_row)

        self._sub_lbl = QtWidgets.QLabel(t("subtitle"))
        self._sub_lbl.setObjectName("subtitle")
        self._sub_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        main.addWidget(self._sub_lbl)

        # ── Spieler-Eingabe ────────────────────────────────────────────────
        setup_panel = self._make_panel()
        main.addWidget(setup_panel)

        sp_layout = QtWidgets.QVBoxLayout(setup_panel)
        sp_layout.setContentsMargins(24, 20, 24, 20)
        sp_layout.setSpacing(14)

        self._hdr1 = QtWidgets.QLabel(t("add_players_header"))
        self._hdr1.setObjectName("section_header")
        sp_layout.addWidget(self._hdr1)

        input_row = QtWidgets.QHBoxLayout()

        self._avatar_combo = QtWidgets.QComboBox()
        self._avatar_combo.addItems(AVATARS)
        self._avatar_combo.setMinimumHeight(38)
        self._avatar_combo.setStyleSheet("font-size: 18px;")

        self._name_edit = QtWidgets.QLineEdit()
        self._name_edit.setPlaceholderText(t("player_name_placeholder"))
        self._name_edit.setMinimumHeight(38)
        self._name_edit.returnPressed.connect(self._add_player)

        self._btn_add = QtWidgets.QPushButton(t("btn_add"))
        self._btn_add.clicked.connect(self._add_player)
        self._btn_add.setMinimumHeight(38)

        input_row.addWidget(self._avatar_combo)
        input_row.addWidget(self._name_edit, 1)
        input_row.addWidget(self._btn_add)
        sp_layout.addLayout(input_row)

        # Chip-Container
        self._chips_container = QtWidgets.QWidget()
        self._chips_container.setStyleSheet("background: transparent;")
        self._chips_layout = QtWidgets.QHBoxLayout(self._chips_container)
        self._chips_layout.setContentsMargins(0, 0, 0, 0)
        self._chips_layout.setSpacing(8)
        self._chips_layout.addStretch()
        sp_layout.addWidget(self._chips_container)

        # Hinweis
        self._hint_lbl = QtWidgets.QLabel(t("hint_min_players"))
        self._hint_lbl.setObjectName("input_label")
        self._hint_lbl.setStyleSheet(f"font-style: italic;")
        sp_layout.addWidget(self._hint_lbl)

        # ── Game Mode ─────────────────────────────────────────────────────
        mode_panel = self._make_panel()
        main.addWidget(mode_panel)

        mode_layout = QtWidgets.QVBoxLayout(mode_panel)
        mode_layout.setContentsMargins(24, 20, 24, 20)
        mode_layout.setSpacing(10)

        self._hdr_mode = QtWidgets.QLabel(t("game_mode_label"))
        self._hdr_mode.setObjectName("section_header")
        mode_layout.addWidget(self._hdr_mode)

        mode_row = QtWidgets.QHBoxLayout()
        self._radio_standard = QtWidgets.QRadioButton(t("game_mode_standard"))
        self._radio_standard.setChecked(True)
        self._radio_multi = QtWidgets.QRadioButton(t("game_mode_multiplicative"))
        mode_row.addWidget(self._radio_standard)
        mode_row.addWidget(self._radio_multi)
        mode_row.addStretch()
        mode_layout.addLayout(mode_row)

        # Start-Button
        self._btn_start = QtWidgets.QPushButton(t("start_game"))
        self._btn_start.setObjectName("primary")
        self._btn_start.setMinimumHeight(44)
        self._btn_start.setEnabled(False)
        self._btn_start.clicked.connect(self._on_start)
        mode_layout.addWidget(self._btn_start)

        # ── Gespeicherte Spiele ────────────────────────────────────────────
        saved_panel = self._make_panel()
        main.addWidget(saved_panel)

        sv_layout = QtWidgets.QVBoxLayout(saved_panel)
        sv_layout.setContentsMargins(24, 20, 24, 20)
        sv_layout.setSpacing(12)

        self._hdr2 = QtWidgets.QLabel(t("saved_games_header"))
        self._hdr2.setObjectName("section_header")
        self._hdr2.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        sv_layout.addWidget(self._hdr2)

        self._saved_list = QtWidgets.QListWidget()
        self._saved_list.itemDoubleClicked.connect(self._on_load_double)
        sv_layout.addWidget(self._saved_list, 1)

        btn_row2 = QtWidgets.QHBoxLayout()
        btn_row2.addStretch()
        self._btn_refresh = QtWidgets.QPushButton(t("btn_refresh"))
        self._btn_refresh.clicked.connect(self._refresh_saved)
        self._btn_load = QtWidgets.QPushButton(t("btn_load_game"))
        self._btn_load.setEnabled(False)
        self._btn_load.clicked.connect(self._on_load)
        btn_row2.addWidget(self._btn_refresh)
        btn_row2.addWidget(self._btn_load)
        sv_layout.addLayout(btn_row2)

        self._saved_list.currentItemChanged.connect(
            lambda cur, _: self._btn_load.setEnabled(cur is not None)
        )

        self._refresh_saved()

    # ── Hilfsmethoden ─────────────────────────────────────────────────────────

    @staticmethod
    def _make_panel() -> QtWidgets.QFrame:
        f = QtWidgets.QFrame()
        f.setObjectName("panel")
        return f

    def _add_player(self) -> None:
        name = self._name_edit.text().strip()
        avatar = self._avatar_combo.currentText()
        if not name or any(p["name"] == name for p in self._players):
            return
        if len(self._players) >= len(PLAYER_COLORS):
            return
        color = PLAYER_COLORS[len(self._players)]
        self._players.append({"name": name, "avatar": avatar})
        chip = PlayerChip(name, color, self._chips_container, display=f"{avatar}  {name}")
        chip.removed.connect(self._remove_player)
        # Insert before the stretch
        idx = self._chips_layout.count() - 1
        self._chips_layout.insertWidget(idx, chip)
        self._name_edit.clear()
        self._update_state()

    def _remove_player(self, name: str) -> None:
        self._players = [p for p in self._players if p["name"] != name]
        # Remove the chip widget
        for i in range(self._chips_layout.count()):
            item = self._chips_layout.itemAt(i)
            if item and isinstance(item.widget(), PlayerChip):
                if item.widget().name == name:
                    widget = item.widget()
                    self._chips_layout.removeWidget(widget)
                    widget.deleteLater()
                    break
        # Re-colour remaining chips to keep consistent colours
        for i, item_i in enumerate(
            [
                self._chips_layout.itemAt(j).widget()
                for j in range(self._chips_layout.count())
                if isinstance(self._chips_layout.itemAt(j).widget(), PlayerChip)
            ]
        ):
            color = PLAYER_COLORS[i]
            item_i.setStyleSheet(
                f"""
                QFrame {{
                    background-color: transparent;
                    border: 1px solid {color};
                    border-radius: 14px;
                    padding: 2px 10px;
                }}
                """
            )
        self._update_state()

    def _update_state(self) -> None:
        n = len(self._players)
        self._btn_start.setEnabled(n >= 2)
        if n == 0:
            self._hint_lbl.setText(t("hint_min_players"))
        else:
            self._hint_lbl.setText(t("hint_players_selected", n=n))

    def _refresh_saved(self) -> None:
        self._saved_list.clear()
        self._saved_games = self._save_manager.list_saved_games()
        if not self._saved_games:
            placeholder = QtWidgets.QListWidgetItem(t("no_saved_games"))
            placeholder.setForeground(QtGui.QColor(TEXT_DIM))
            placeholder.setFlags(QtCore.Qt.ItemFlag.NoItemFlags)
            self._saved_list.addItem(placeholder)
        else:
            for game in self._saved_games:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(game.get("saved_at", ""))
                    date_str = dt.strftime("%d.%m.%Y %H:%M")
                except Exception:
                    date_str = "–"
                players = ", ".join(game.get("players", []))
                rounds = game.get("rounds", 0)
                item = QtWidgets.QListWidgetItem(
                    f"  {game['name']}   ·   {date_str}   ·   {players}   ·   {t('saved_round')} {rounds}"
                )
                item.setData(QtCore.Qt.ItemDataRole.UserRole, game)
                self._saved_list.addItem(item)

    # ── Settings ──────────────────────────────────────────────────────────────

    def _on_settings(self) -> None:
        """Öffnet den Einstellungen-Dialog."""
        from dialogs import SettingsDialog
        dlg = SettingsDialog(self)
        dlg.exec()
        self.retranslate_ui()
        self.settings_changed.emit()

    # ── Übersetzung aktualisieren ──────────────────────────────────────────────

    def retranslate_ui(self) -> None:
        """Aktualisiert alle übersetzbaren UI-Texte nach Sprach-/Themenwechsel."""
        self._sub_lbl.setText(t("subtitle"))
        self._hdr1.setText(t("add_players_header"))
        self._hdr2.setText(t("saved_games_header"))
        self._hdr_mode.setText(t("game_mode_label"))
        self._radio_standard.setText(t("game_mode_standard"))
        self._radio_multi.setText(t("game_mode_multiplicative"))
        self._name_edit.setPlaceholderText(t("player_name_placeholder"))
        self._btn_add.setText(t("btn_add"))
        self._btn_refresh.setText(t("btn_refresh"))
        self._btn_load.setText(t("btn_load_game"))
        self._btn_start.setText(t("start_game"))
        self._btn_settings.setToolTip(t("tooltip_settings"))
        # Update hint based on current player count
        n = len(self._players)
        if n == 0:
            self._hint_lbl.setText(t("hint_min_players"))
        else:
            self._hint_lbl.setText(t("hint_players_selected", n=n))
        # Refresh saved games list to update "Round" label
        self._refresh_saved()

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        if len(self._players) >= 2:
            game_mode = GAME_MODE_MULTIPLICATIVE if self._radio_multi.isChecked() else GAME_MODE_STANDARD
            self.start_game.emit(list(self._players), game_mode)

    def _on_load(self) -> None:
        current = self._saved_list.currentItem()
        if current:
            game_meta = current.data(QtCore.Qt.ItemDataRole.UserRole)
            if game_meta:
                self.load_game.emit(game_meta["filepath"])

    def _on_load_double(self, item: QtWidgets.QListWidgetItem) -> None:
        game_meta = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if game_meta:
            self.load_game.emit(game_meta["filepath"])

