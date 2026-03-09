"""
setup_view.py – Spieler-Setup-Bildschirm

Zeigt:
  • Titelbereich
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


class PlayerChip(QtWidgets.QFrame):
    """Kleiner farbiger Chip für einen Spielernamen."""

    removed = QtCore.pyqtSignal(str)

    def __init__(self, name: str, color: str, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.name = name
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {color}22;
                border: 1px solid {color};
                border-radius: 14px;
                padding: 2px 10px;
            }}
            """
        )
        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(6, 3, 3, 3)
        row.setSpacing(4)

        lbl = QtWidgets.QLabel(name)
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
    """

    start_game = QtCore.pyqtSignal(list)
    load_game = QtCore.pyqtSignal(object)   # Path

    def __init__(self, save_manager: SaveManager, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self._save_manager = save_manager
        self._player_names: List[str] = []
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
        title_lbl = QtWidgets.QLabel("🃏  WIZARD")
        title_lbl.setObjectName("title")
        title_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        sub_lbl = QtWidgets.QLabel("Punkte-Tracker")
        sub_lbl.setObjectName("subtitle")
        sub_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        main.addWidget(title_lbl)
        main.addWidget(sub_lbl)

        # ── Spieler-Eingabe ────────────────────────────────────────────────
        setup_panel = self._make_panel()
        main.addWidget(setup_panel)

        sp_layout = QtWidgets.QVBoxLayout(setup_panel)
        sp_layout.setContentsMargins(24, 20, 24, 20)
        sp_layout.setSpacing(14)

        hdr1 = QtWidgets.QLabel("SPIELER HINZUFÜGEN")
        hdr1.setObjectName("section_header")
        sp_layout.addWidget(hdr1)

        input_row = QtWidgets.QHBoxLayout()
        self._name_edit = QtWidgets.QLineEdit()
        self._name_edit.setPlaceholderText("Name eingeben und Enter drücken …")
        self._name_edit.setMinimumHeight(38)
        self._name_edit.returnPressed.connect(self._add_player)

        btn_add = QtWidgets.QPushButton("＋ Hinzufügen")
        btn_add.clicked.connect(self._add_player)
        btn_add.setMinimumHeight(38)

        input_row.addWidget(self._name_edit, 1)
        input_row.addWidget(btn_add)
        sp_layout.addLayout(input_row)

        # Chip-Container
        self._chips_container = QtWidgets.QWidget()
        self._chips_layout = QtWidgets.QHBoxLayout(self._chips_container)
        self._chips_layout.setContentsMargins(0, 0, 0, 0)
        self._chips_layout.setSpacing(8)
        self._chips_layout.addStretch()
        sp_layout.addWidget(self._chips_container)

        # Hinweis
        self._hint_lbl = QtWidgets.QLabel("Mindestens 2 Spieler erforderlich.")
        self._hint_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; font-style: italic;")
        sp_layout.addWidget(self._hint_lbl)

        # Start-Button
        self._btn_start = QtWidgets.QPushButton("🎮  Spiel starten")
        self._btn_start.setObjectName("primary")
        self._btn_start.setMinimumHeight(44)
        self._btn_start.setEnabled(False)
        self._btn_start.clicked.connect(self._on_start)
        sp_layout.addWidget(self._btn_start)

        # ── Gespeicherte Spiele ────────────────────────────────────────────
        saved_panel = self._make_panel()
        main.addWidget(saved_panel)

        sv_layout = QtWidgets.QVBoxLayout(saved_panel)
        sv_layout.setContentsMargins(24, 20, 24, 20)
        sv_layout.setSpacing(12)

        hdr2 = QtWidgets.QLabel("GESPEICHERTE SPIELE")
        hdr2.setObjectName("section_header")
        sv_layout.addWidget(hdr2)

        self._saved_list = QtWidgets.QListWidget()
        self._saved_list.setMaximumHeight(200)
        self._saved_list.itemDoubleClicked.connect(self._on_load_double)
        sv_layout.addWidget(self._saved_list)

        btn_row2 = QtWidgets.QHBoxLayout()
        btn_row2.addStretch()
        btn_refresh = QtWidgets.QPushButton("↻  Aktualisieren")
        btn_refresh.clicked.connect(self._refresh_saved)
        self._btn_load = QtWidgets.QPushButton("📂  Laden")
        self._btn_load.setEnabled(False)
        self._btn_load.clicked.connect(self._on_load)
        btn_row2.addWidget(btn_refresh)
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
        if not name or name in self._player_names:
            return
        if len(self._player_names) >= len(PLAYER_COLORS):
            return
        color = PLAYER_COLORS[len(self._player_names)]
        self._player_names.append(name)
        chip = PlayerChip(name, color, self._chips_container)
        chip.removed.connect(self._remove_player)
        # Insert before the stretch
        idx = self._chips_layout.count() - 1
        self._chips_layout.insertWidget(idx, chip)
        self._name_edit.clear()
        self._update_state()

    def _remove_player(self, name: str) -> None:
        self._player_names.remove(name)
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
                    background-color: {color}22;
                    border: 1px solid {color};
                    border-radius: 14px;
                    padding: 2px 10px;
                }}
                """
            )
        self._update_state()

    def _update_state(self) -> None:
        n = len(self._player_names)
        self._btn_start.setEnabled(n >= 2)
        if n == 0:
            self._hint_lbl.setText("Mindestens 2 Spieler erforderlich.")
        else:
            self._hint_lbl.setText(f"{n} Spieler ausgewählt.")

    def _refresh_saved(self) -> None:
        self._saved_list.clear()
        self._saved_games = self._save_manager.list_saved_games()
        if not self._saved_games:
            placeholder = QtWidgets.QListWidgetItem("– Keine gespeicherten Spiele –")
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
                    f"  {game['name']}   ·   {date_str}   ·   {players}   ·   Runde {rounds}"
                )
                item.setData(QtCore.Qt.ItemDataRole.UserRole, game)
                self._saved_list.addItem(item)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        if len(self._player_names) >= 2:
            self.start_game.emit(list(self._player_names))

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
