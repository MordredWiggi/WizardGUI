"""
dashboard_view.py - Database statistics overview.
"""

from __future__ import annotations

from PyQt6 import QtCore, QtWidgets

from db_backend import DbBackend
from style import ACCENT, ACCENT_DIM, BG_CARD, BG_PANEL, TEXT_DIM, TEXT_MAIN
from views_base import BaseView, push_button


class DashboardView(BaseView):
    def __init__(self, backend: DbBackend) -> None:
        super().__init__(backend)
        self.set_title("Dashboard", "Database statistics at a glance.")

        btn_refresh = push_button("⟳  Refresh", role="toolbar_btn")
        btn_refresh.clicked.connect(self.refresh)
        self.add_toolbar_widget(btn_refresh)
        self.add_toolbar_stretch()

        self._cards_grid = QtWidgets.QGridLayout()
        self._cards_grid.setSpacing(12)
        wrap = QtWidgets.QWidget()
        wrap.setLayout(self._cards_grid)
        self.add_to_body(wrap)

        # Top groups list
        list_label = QtWidgets.QLabel("Most active groups")
        list_label.setObjectName("section_header")
        self.add_to_body(list_label)

        self._top_groups = QtWidgets.QListWidget()
        self._top_groups.setMaximumHeight(220)
        self.add_to_body(self._top_groups)

        # Top players list
        plyr_label = QtWidgets.QLabel("Most active players")
        plyr_label.setObjectName("section_header")
        self.add_to_body(plyr_label)

        self._top_players = QtWidgets.QListWidget()
        self.add_to_body(self._top_players, stretch=1)

    # -- Data ---------------------------------------------------------------

    def refresh(self) -> None:
        # Counts
        counts = {
            "Groups": self._scalar("SELECT COUNT(*) AS n FROM groups"),
            "Games": self._scalar("SELECT COUNT(*) AS n FROM games"),
            "Players": self._scalar("SELECT COUNT(*) AS n FROM players"),
            "Results": self._scalar("SELECT COUNT(*) AS n FROM results"),
            "Feedback": self._scalar("SELECT COUNT(*) AS n FROM feedback"),
        }
        self._render_cards(counts)
        self._fill_top_groups()
        self._fill_top_players()
        self.set_status("Refreshed.", success=True)

    def _scalar(self, sql: str) -> int:
        rows = self.safe(self.backend.query, sql)
        if not rows:
            return 0
        try:
            return int(list(rows[0].values())[0] or 0)
        except (ValueError, TypeError):
            return 0

    def _render_cards(self, counts: dict[str, int]) -> None:
        # Clear grid
        while self._cards_grid.count():
            it = self._cards_grid.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()
        for col, (label, value) in enumerate(counts.items()):
            card = QtWidgets.QFrame()
            card.setObjectName("card")
            card.setMinimumHeight(90)
            cl = QtWidgets.QVBoxLayout(card)
            cl.setContentsMargins(16, 12, 16, 12)
            l_top = QtWidgets.QLabel(label.upper())
            l_top.setStyleSheet(
                f"color: {ACCENT_DIM}; font-size: 11px; font-weight: 700; "
                f"letter-spacing: 1px;"
            )
            l_val = QtWidgets.QLabel(str(value))
            l_val.setStyleSheet(
                f"color: {ACCENT}; font-size: 26px; font-weight: 800;"
            )
            cl.addWidget(l_top)
            cl.addWidget(l_val)
            self._cards_grid.addWidget(card, 0, col)

    def _fill_top_groups(self) -> None:
        self._top_groups.clear()
        rows = self.safe(
            self.backend.query,
            """
            SELECT gr.name, gr.code,
                   COUNT(DISTINCT g.id)        AS games,
                   COUNT(DISTINCT r.player_id) AS players
              FROM groups gr
         LEFT JOIN games   g ON g.group_id = gr.id
         LEFT JOIN results r ON r.game_id  = g.id
          GROUP BY gr.id
          ORDER BY games DESC, players DESC
             LIMIT 10
            """,
        )
        if not rows:
            return
        for r in rows:
            item = QtWidgets.QListWidgetItem(
                f"  {r['name']:<24}  ·  Code {r['code']}  ·  "
                f"{r.get('games', 0)} games  ·  {r.get('players', 0)} players"
            )
            self._top_groups.addItem(item)

    def _fill_top_players(self) -> None:
        self._top_players.clear()
        rows = self.safe(
            self.backend.query,
            """
            SELECT p.name,
                   COUNT(r.game_id)                              AS games,
                   SUM(CASE WHEN r.rank = 1 THEN 1 ELSE 0 END)   AS wins,
                   ROUND(AVG(r.final_score), 1)                  AS avg_score
              FROM players p
         LEFT JOIN results r ON r.player_id = p.id
          GROUP BY p.id
          ORDER BY games DESC
             LIMIT 15
            """,
        )
        if not rows:
            return
        for r in rows:
            item = QtWidgets.QListWidgetItem(
                f"  {r['name']:<24}  ·  {r.get('games', 0)} games  ·  "
                f"{r.get('wins', 0) or 0} wins  ·  Avg {r.get('avg_score', 0) or 0}"
            )
            self._top_players.addItem(item)
