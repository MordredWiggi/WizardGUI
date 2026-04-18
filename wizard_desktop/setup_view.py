"""
setup_view.py – Spieler-Setup-Bildschirm

Zeigt:
  • Titelbereich mit Einstellungs-Button
  • Gruppen-Auswahl / Erstellung (vor Spieler-Eingabe)
  • Eingabefeld für Spielernamen
  • Liste gespeicherter Spiele, globales Gruppen-Leaderboard, Gruppen-Leaderboard
  • „Spiel starten"-Button
"""
from __future__ import annotations

from typing import List, Optional, Dict

from PyQt6 import QtCore, QtWidgets, QtGui

from style import (
    ACCENT, ACCENT_DIM, BG_BASE, BG_PANEL, BG_CARD,
    TEXT_MAIN, TEXT_DIM, PLAYER_COLORS, SUCCESS, DANGER,
)
from save_manager import SaveManager
from app_settings import t, get_leaderboard_url
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
    start_game(player_names: list[str], game_mode: str, group: dict|None)
    load_game(filepath: Path)
    settings_changed()
    """

    start_game = QtCore.pyqtSignal(list, str, object)  # players, mode, group dict or None
    load_game = QtCore.pyqtSignal(object)              # Path
    settings_changed = QtCore.pyqtSignal()

    def __init__(self, save_manager: SaveManager, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self._save_manager = save_manager
        self._players: List[dict] = []
        self._check_worker = None
        self._debounce_timer = QtCore.QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(300)
        self._debounce_timer.timeout.connect(self._do_player_check)

        # Group state: the currently confirmed group (dict) or None.
        # No group = offline by default; the user can always start a game
        # without picking a group.
        self._selected_group: Optional[Dict] = None

        self._build_ui()

    # ── Leaderboard client helper ──────────────────────────────────────────────

    def _get_client(self):
        url = get_leaderboard_url()
        if not url:
            return None
        from leaderboard_client import LeaderboardClient
        return LeaderboardClient(url)

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
        title_row = QtWidgets.QHBoxLayout()
        title_row.addStretch()

        title_lbl = QtWidgets.QLabel("🃏  WIZARD")
        title_lbl.setObjectName("title")
        title_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        title_lbl.setStyleSheet("font-size: 40px; background: transparent;")
        title_row.addWidget(title_lbl)
        title_row.addStretch()

        self._btn_leaderboard_web = QtWidgets.QPushButton("🌐")
        self._btn_leaderboard_web.setObjectName("toolbar_btn")
        self._btn_leaderboard_web.setToolTip("Online Leaderboard")
        self._btn_leaderboard_web.setFixedSize(44, 44)
        self._btn_leaderboard_web.setStyleSheet(
            "QPushButton { font-size: 28px; padding: 0; background: transparent; border: none; }"
            "QPushButton:hover { background-color: #1a1a3a; border-radius: 4px; }"
        )
        self._btn_leaderboard_web.clicked.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://play-wizard.de")))
        title_row.addWidget(self._btn_leaderboard_web)

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

        # ── Kombiniertes Setup-Panel (Gruppe + Spieler + Modus) ───────────
        combined_panel = self._make_panel()
        main.addWidget(combined_panel)

        combined_layout = QtWidgets.QVBoxLayout(combined_panel)
        combined_layout.setContentsMargins(24, 20, 24, 20)
        combined_layout.setSpacing(18)

        # ── Group subsection ───────────────────────────────────────────────
        gp_layout = QtWidgets.QVBoxLayout()
        gp_layout.setSpacing(10)
        combined_layout.addLayout(gp_layout)

        self._hdr_group = QtWidgets.QLabel(t("group_header"))
        self._hdr_group.setObjectName("section_header")
        gp_layout.addWidget(self._hdr_group)

        # Current group status display – starts as "no group selected"
        self._group_status_lbl = QtWidgets.QLabel(t("group_not_selected"))
        self._group_status_lbl.setStyleSheet(
            f"font-size: 13px; color: {TEXT_DIM}; background: transparent; font-style: italic;"
        )
        self._group_status_lbl.setWordWrap(True)
        gp_layout.addWidget(self._group_status_lbl)

        # Buttons: Join existing / Create new
        group_btn_row = QtWidgets.QHBoxLayout()
        self._btn_join_group = QtWidgets.QPushButton(t("group_select_label"))
        self._btn_join_group.setMinimumHeight(36)
        self._btn_join_group.clicked.connect(self._on_join_group)

        self._btn_create_group = QtWidgets.QPushButton(t("group_create_btn"))
        self._btn_create_group.setMinimumHeight(36)
        self._btn_create_group.clicked.connect(self._on_create_group)

        self._btn_clear_group = QtWidgets.QPushButton("✕")
        self._btn_clear_group.setToolTip("Clear group selection")
        self._btn_clear_group.setFixedSize(36, 36)
        self._btn_clear_group.setStyleSheet(
            "QPushButton { padding: 0; font-size: 16px; font-weight: 700; }"
        )
        self._btn_clear_group.setVisible(False)
        self._btn_clear_group.clicked.connect(self._clear_group)

        group_btn_row.addWidget(self._btn_join_group)
        group_btn_row.addWidget(self._btn_create_group)
        group_btn_row.addStretch()
        group_btn_row.addWidget(self._btn_clear_group)
        gp_layout.addLayout(group_btn_row)

        # Divider between subsections
        sub_sep1 = QtWidgets.QFrame()
        sub_sep1.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sub_sep1.setStyleSheet("background: #3a3a6a; border: none; max-height: 1px;")
        combined_layout.addWidget(sub_sep1)

        # ── Spieler-Eingabe ────────────────────────────────────────────────
        sp_layout = QtWidgets.QVBoxLayout()
        sp_layout.setSpacing(12)
        combined_layout.addLayout(sp_layout)

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
        self._name_edit.textChanged.connect(self._on_name_text_changed)

        self._name_status = QtWidgets.QLabel()
        self._name_status.setFixedWidth(160)
        self._name_status.setStyleSheet("font-size: 11px; background: transparent; border: none;")

        self._btn_add = QtWidgets.QPushButton(t("btn_add"))
        self._btn_add.clicked.connect(self._add_player)
        self._btn_add.setMinimumHeight(38)

        input_row.addWidget(self._avatar_combo)
        input_row.addWidget(self._name_edit, 1)
        input_row.addWidget(self._name_status)
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
        self._hint_lbl.setStyleSheet("font-style: italic;")
        sp_layout.addWidget(self._hint_lbl)

        # Divider between subsections
        sub_sep2 = QtWidgets.QFrame()
        sub_sep2.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sub_sep2.setStyleSheet("background: #3a3a6a; border: none; max-height: 1px;")
        combined_layout.addWidget(sub_sep2)

        # ── Game Mode ─────────────────────────────────────────────────────
        mode_layout = QtWidgets.QVBoxLayout()
        mode_layout.setSpacing(10)
        combined_layout.addLayout(mode_layout)

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

        # ── Bottom: Saved Games | Groups LB | Group LB ─────────────────────
        saved_panel = self._make_panel()
        main.addWidget(saved_panel)

        sv_layout = QtWidgets.QVBoxLayout(saved_panel)
        sv_layout.setContentsMargins(24, 20, 24, 20)
        sv_layout.setSpacing(12)

        # Tabs: Saved Games | Groups | My Group
        tab_row = QtWidgets.QHBoxLayout()
        tab_row.setSpacing(4)
        self._btn_tab_saved = QtWidgets.QPushButton(t("tab_saved_games"))
        self._btn_tab_groups = QtWidgets.QPushButton(t("tab_groups_lb"))
        self._btn_tab_mygroup = QtWidgets.QPushButton(t("tab_group_lb"))
        for btn in (self._btn_tab_saved, self._btn_tab_groups, self._btn_tab_mygroup):
            btn.setMinimumHeight(32)
            btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self._btn_tab_saved.clicked.connect(lambda: self._switch_bottom_tab(0))
        self._btn_tab_groups.clicked.connect(lambda: self._switch_bottom_tab(1))
        self._btn_tab_mygroup.clicked.connect(lambda: self._switch_bottom_tab(2))
        # "My Group" tab is disabled until a group is selected
        self._btn_tab_mygroup.setEnabled(False)
        tab_row.addWidget(self._btn_tab_saved)
        tab_row.addWidget(self._btn_tab_groups)
        tab_row.addWidget(self._btn_tab_mygroup)
        tab_row.addStretch()
        sv_layout.addLayout(tab_row)

        # Stacked widget for switching content
        self._bottom_stack = QtWidgets.QStackedWidget()

        # Page 0: Saved games
        saved_page = QtWidgets.QWidget()
        saved_page_layout = QtWidgets.QVBoxLayout(saved_page)
        saved_page_layout.setContentsMargins(0, 0, 0, 0)
        saved_page_layout.setSpacing(8)

        self._saved_list = QtWidgets.QListWidget()
        self._saved_list.itemDoubleClicked.connect(self._on_load_double)
        saved_page_layout.addWidget(self._saved_list, 1)

        btn_row2 = QtWidgets.QHBoxLayout()
        btn_row2.addStretch()
        self._btn_refresh = QtWidgets.QPushButton(t("btn_refresh"))
        self._btn_refresh.clicked.connect(self._refresh_saved)
        self._btn_load = QtWidgets.QPushButton(t("btn_load_game"))
        self._btn_load.setEnabled(False)
        self._btn_load.clicked.connect(self._on_load)
        btn_row2.addWidget(self._btn_refresh)
        btn_row2.addWidget(self._btn_load)
        saved_page_layout.addLayout(btn_row2)

        self._saved_list.currentItemChanged.connect(
            lambda cur, _: self._btn_load.setEnabled(cur is not None)
        )

        self._bottom_stack.addWidget(saved_page)  # index 0

        # Page 1: Global groups ranking
        from leaderboard_widget import GroupsLeaderboardWidget, GroupPlayerLeaderboardWidget
        self._groups_lb_widget = GroupsLeaderboardWidget()
        self._bottom_stack.addWidget(self._groups_lb_widget)  # index 1

        # Page 2: Group-internal player leaderboard
        self._lb_widget = GroupPlayerLeaderboardWidget()
        self._bottom_stack.addWidget(self._lb_widget)  # index 2

        sv_layout.addWidget(self._bottom_stack, 1)

        self._current_bottom_tab = 0
        self._apply_tab_style()
        self._refresh_saved()

    # ── Group management ───────────────────────────────────────────────────────

    def _on_join_group(self) -> None:
        client = self._get_client()
        if client is None:
            QtWidgets.QMessageBox.information(
                self, t("warning_title"),
                "Please configure a leaderboard URL in Settings first."
            )
            return
        from dialogs import GroupSelectDialog
        dlg = GroupSelectDialog(self, client)
        if dlg.exec() and dlg.selected_group:
            self._set_group(dlg.selected_group)

    def _on_create_group(self) -> None:
        client = self._get_client()
        if client is None:
            QtWidgets.QMessageBox.information(
                self, t("warning_title"),
                "Please configure a leaderboard URL in Settings first."
            )
            return
        from dialogs import GroupCreateDialog
        dlg = GroupCreateDialog(self, client)
        if dlg.exec() and dlg.created_group:
            self._set_group(dlg.created_group)

    def _set_group(self, group: Dict) -> None:
        self._selected_group = group
        self._group_status_lbl.setText(
            t("group_selected", name=group["name"], code=group["code"])
        )
        self._group_status_lbl.setStyleSheet(
            f"font-size: 13px; color: {SUCCESS}; background: transparent; font-weight: 600;"
        )
        self._btn_clear_group.setVisible(True)
        self._btn_tab_mygroup.setEnabled(True)
        self._lb_widget.set_group(group["code"])
        self._update_state()

    def _clear_group(self) -> None:
        self._selected_group = None
        # Reset the name-presence indicator since it only applies to groups.
        self._name_status.clear()
        self._name_status.setStyleSheet(
            "font-size: 11px; background: transparent; border: none;"
        )
        self._group_status_lbl.setText(t("group_not_selected"))
        self._group_status_lbl.setStyleSheet(
            f"font-size: 13px; color: {TEXT_DIM}; background: transparent; font-style: italic;"
        )
        self._btn_clear_group.setVisible(False)
        self._btn_tab_mygroup.setEnabled(False)
        self._lb_widget.set_group(None)
        # If user was viewing group LB, bounce back to saved games tab.
        if self._current_bottom_tab == 2:
            self._switch_bottom_tab(0)
        self._update_state()

    # ── Hilfsmethoden ─────────────────────────────────────────────────────────

    @staticmethod
    def _make_panel() -> QtWidgets.QFrame:
        f = QtWidgets.QFrame()
        f.setObjectName("panel")
        return f

    def _switch_bottom_tab(self, index: int) -> None:
        self._current_bottom_tab = index
        self._bottom_stack.setCurrentIndex(index)
        self._apply_tab_style()

    def _apply_tab_style(self) -> None:
        from app_settings import get_theme
        dark = get_theme() != "light"
        tabs = [self._btn_tab_saved, self._btn_tab_groups, self._btn_tab_mygroup]
        for i, btn in enumerate(tabs):
            active = (i == self._current_bottom_tab)
            if dark:
                if active:
                    btn.setStyleSheet(
                        f"QPushButton {{ background: {ACCENT_DIM}; color: #fff8e0; "
                        f"border: 1px solid {ACCENT}; border-radius: 5px; font-weight: 700; "
                        f"font-size: 12px; padding: 5px 14px; }}"
                    )
                else:
                    btn.setStyleSheet(
                        f"QPushButton {{ background: {BG_CARD}; color: {TEXT_DIM}; "
                        f"border: 1px solid #3a3a6a; border-radius: 5px; "
                        f"font-size: 12px; padding: 5px 14px; }}"
                        f"QPushButton:hover {{ border-color: {ACCENT_DIM}; color: {TEXT_MAIN}; }}"
                    )
            else:
                if active:
                    btn.setStyleSheet(
                        "QPushButton { background: #9b7a1e; color: #ffffff; "
                        "border: 1px solid #c9a84c; border-radius: 5px; font-weight: 700; "
                        "font-size: 12px; padding: 5px 14px; }"
                    )
                else:
                    btn.setStyleSheet(
                        "QPushButton { background: #f8f8ff; color: #555577; "
                        "border: 1px solid #aaaacc; border-radius: 5px; "
                        "font-size: 12px; padding: 5px 14px; }"
                        "QPushButton:hover { border-color: #9b7a1e; color: #1a1a2e; }"
                    )

    # ── Live player name checking ──────────────────────────────────────────────

    def _on_name_text_changed(self, text: str) -> None:
        self._name_status.clear()
        name = text.strip()
        # Only check player presence when the user is actually playing into
        # a group — in offline mode there is no roster to compare against.
        if not name or self._selected_group is None or not get_leaderboard_url():
            return
        self._debounce_timer.start()

    def _do_player_check(self) -> None:
        name = self._name_edit.text().strip()
        url = get_leaderboard_url()
        if not name or self._selected_group is None or not url:
            return
        from leaderboard_client import LeaderboardClient, GroupPlayerCheckWorker

        client = LeaderboardClient(url)
        self._check_worker = GroupPlayerCheckWorker(
            client, self._selected_group["code"], name
        )
        self._check_worker.result.connect(self._on_player_check_result)
        self._check_worker.start()

    def _on_player_check_result(self, name: str, exists) -> None:
        if self._name_edit.text().strip() != name:
            return
        # If the group was cleared while the check was in flight, drop the result.
        if self._selected_group is None:
            self._name_status.clear()
            return
        if exists is None:
            self._name_status.clear()
        elif exists:
            self._name_status.setText(t("player_exists_hint"))
            self._name_status.setStyleSheet(
                f"font-size: 11px; color: {SUCCESS}; background: transparent; border: none;"
            )
        else:
            self._name_status.setText(t("player_new_hint"))
            self._name_status.setStyleSheet(
                f"font-size: 11px; color: {TEXT_DIM}; background: transparent; border: none;"
            )

    # ── Spieler-Verwaltung ────────────────────────────────────────────────────

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
        idx = self._chips_layout.count() - 1
        self._chips_layout.insertWidget(idx, chip)
        self._name_edit.clear()
        self._name_status.clear()
        self._update_state()

    def _remove_player(self, name: str) -> None:
        self._players = [p for p in self._players if p["name"] != name]
        for i in range(self._chips_layout.count()):
            item = self._chips_layout.itemAt(i)
            if item and isinstance(item.widget(), PlayerChip):
                if item.widget().name == name:
                    widget = item.widget()
                    self._chips_layout.removeWidget(widget)
                    widget.deleteLater()
                    break
        # Re-colour remaining chips
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
        # Offline (no group) is the default and a valid way to play.
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
        from dialogs import SettingsDialog
        dlg = SettingsDialog(self)
        dlg.exec()
        self.retranslate_ui()
        self.settings_changed.emit()

    # ── Übersetzung aktualisieren ──────────────────────────────────────────────

    def retranslate_ui(self) -> None:
        self._sub_lbl.setText(t("subtitle"))
        self._hdr_group.setText(t("group_header"))
        self._hdr1.setText(t("add_players_header"))
        self._hdr_mode.setText(t("game_mode_label"))
        self._radio_standard.setText(t("game_mode_standard"))
        self._radio_multi.setText(t("game_mode_multiplicative"))
        self._name_edit.setPlaceholderText(t("player_name_placeholder"))
        self._btn_add.setText(t("btn_add"))
        self._btn_refresh.setText(t("btn_refresh"))
        self._btn_load.setText(t("btn_load_game"))
        self._btn_start.setText(t("start_game"))
        self._btn_settings.setToolTip(t("tooltip_settings"))
        self._btn_tab_saved.setText(t("tab_saved_games"))
        self._btn_tab_groups.setText(t("tab_groups_lb"))
        self._btn_tab_mygroup.setText(t("tab_group_lb"))
        self._btn_join_group.setText(t("group_select_label"))
        self._btn_create_group.setText(t("group_create_btn"))
        if self._selected_group:
            self._group_status_lbl.setText(
                t("group_selected",
                  name=self._selected_group["name"],
                  code=self._selected_group["code"])
            )
        else:
            self._group_status_lbl.setText(t("group_not_selected"))
        self._apply_tab_style()
        self._lb_widget.retranslate_ui()
        self._groups_lb_widget.retranslate_ui()
        n = len(self._players)
        if n == 0:
            self._hint_lbl.setText(t("hint_min_players"))
        else:
            self._hint_lbl.setText(t("hint_players_selected", n=n))
        self._refresh_saved()

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        if len(self._players) < 2:
            return
        game_mode = GAME_MODE_MULTIPLICATIVE if self._radio_multi.isChecked() else GAME_MODE_STANDARD
        # With no group selected the game runs offline (emits None for the group).
        self.start_game.emit(list(self._players), game_mode, self._selected_group)

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

    # ── Public API ─────────────────────────────────────────────────────────────

    @property
    def selected_group(self) -> Optional[Dict]:
        """Returns the currently selected group dict, or None."""
        return self._selected_group
