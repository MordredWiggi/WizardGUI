"""
game_view.py – Hauptbildschirm während eines laufenden Spiels

Zeigt:
  • Spieler-Karten mit aktuellem Punktestand und Rundeingabe
  • Matplotlib-Plot der Punkteverläufe mit Hover-Funktion
  • Toolbar-Aktionen (Undo, Speichern, Plot exportieren, Neues Spiel)
"""
from __future__ import annotations

from typing import Optional, List

import numpy as np
import matplotlib
import matplotlib.ticker
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as _fm
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from PyQt6 import QtCore, QtWidgets, QtGui

from game_control import GameControl, RoundResult, RoundEvents
from style import (
    ACCENT, ACCENT_DIM, BG_BASE, BG_PANEL, BG_CARD, BG_DEEP,
    TEXT_MAIN, TEXT_DIM, TEXT_MAIN_L, SUCCESS, DANGER, LEADER, PLAYER_COLORS,
)
from app_settings import t, get_theme


# ─────────────────────────────────────────────────────────────────────────────
# Matplotlib font setup for Unicode / Hindi support
# ─────────────────────────────────────────────────────────────────────────────

def _configure_matplotlib_font() -> None:
    """Configure matplotlib to support Unicode including Hindi/Devanagari."""
    _DEVANAGARI_FONTS = [
        "Noto Sans Devanagari", "Noto Serif Devanagari",
        "Lohit Devanagari", "Mangal", "Kohinoor Devanagari",
        "Arial Unicode MS", "FreeSans", "DejaVu Sans",
    ]
    available = {f.name for f in _fm.fontManager.ttflist}
    for font_name in _DEVANAGARI_FONTS:
        if font_name in available:
            matplotlib.rcParams["font.family"] = font_name
            return
    # Fallback: use DejaVu Sans which ships with matplotlib
    matplotlib.rcParams["font.family"] = "DejaVu Sans"


_configure_matplotlib_font()


# ─────────────────────────────────────────────────────────────────────────────
# NoScrollSpinBox – QSpinBox with mouse-wheel scrolling disabled
# ─────────────────────────────────────────────────────────────────────────────

class NoScrollSpinBox(QtWidgets.QSpinBox):
    """QSpinBox that ignores mouse wheel events so the value cannot be changed
    by scrolling, even when the widget has focus."""

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        event.ignore()


# ─────────────────────────────────────────────────────────────────────────────
# Matplotlib Canvas
# ─────────────────────────────────────────────────────────────────────────────

class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=8.5, height=6.5):
        self.fig, self.axes = plt.subplots(1, 1, figsize=(width, height))
        self._style_figure()
        super().__init__(self.fig)
        self._hover_lines: list[tuple] = []
        self._hover_annot = None
        self._cid_hover = self.fig.canvas.mpl_connect(
            "motion_notify_event", self._on_hover
        )

    def _style_figure(self) -> None:
        if get_theme() == "light":
            self._style_figure_light()
        else:
            self._style_figure_dark()

    def _style_figure_dark(self) -> None:
        self.fig.patch.set_facecolor("#0d0d1a")
        ax = self.axes
        ax.set_facecolor("#12122b")
        ax.tick_params(colors="#888aaa", labelsize=14)
        ax.spines[:].set_color("#3a3a6a")
        ax.xaxis.label.set_color(TEXT_DIM)
        ax.yaxis.label.set_color(TEXT_DIM)
        ax.set_xlabel(t("round"), color=TEXT_DIM, fontsize=15)
        ax.set_ylabel(t("points"), color=TEXT_DIM, fontsize=15)
        ax.yaxis.set_label_position("right")
        ax.yaxis.tick_right()
        # Minor grid at 100-pt intervals (y), drawn before major grid
        ax.yaxis.set_minor_locator(matplotlib.ticker.MultipleLocator(100))
        ax.grid(True, which="minor", axis="y", color="#3a3a6a", linewidth=0.8,
                linestyle="--", alpha=0.7)
        ax.grid(True, which="major", color="#4a4a7a", linewidth=0.8,
                linestyle="--", alpha=0.6)

    def _style_figure_light(self) -> None:
        self.fig.patch.set_facecolor("#f0f0f5")
        ax = self.axes
        ax.set_facecolor("#f8f8ff")
        ax.tick_params(colors="#555577", labelsize=14)
        ax.spines[:].set_color("#ccccdd")
        ax.xaxis.label.set_color("#555577")
        ax.yaxis.label.set_color("#555577")
        ax.set_xlabel(t("round"), color="#555577", fontsize=15)
        ax.set_ylabel(t("points"), color="#555577", fontsize=15)
        ax.yaxis.set_label_position("right")
        ax.yaxis.tick_right()
        # Minor grid at 100-pt intervals (y), drawn before major grid
        ax.yaxis.set_minor_locator(matplotlib.ticker.MultipleLocator(100))
        ax.grid(True, which="minor", axis="y", color="#dcdcec", linewidth=0.8,
                linestyle="--", alpha=0.8)
        ax.grid(True, which="major", color="#dcdcec", linewidth=0.6,
                linestyle="--", alpha=0.5)

    def redraw(self, game: GameControl) -> None:
        self.axes.clear()
        self._style_figure()
        self._hover_lines = []

        rounds = game.round_indices
        n_rounds = len(rounds)

        # ── Detect overlapping segments ────────────────────────────────────
        # overlap_rank[(player_i, round_r)] = rank of this player in the overlap
        # group for segment [r, r+1], used to pick different linestyles.
        overlap_rank: dict = {}
        for r in range(n_rounds - 1):
            groups: dict = {}
            for i, player in enumerate(game.players):
                key = (player.scores[r], player.scores[r + 1])
                groups.setdefault(key, []).append(i)
            for group in groups.values():
                if len(group) > 1:
                    for rank, idx in enumerate(sorted(group)):
                        overlap_rank[(idx, r)] = rank

        OVERLAP_STYLES = ["--", ":", "-."]

        for i, player in enumerate(game.players):
            color = PLAYER_COLORS[i % len(PLAYER_COLORS)]

            if n_rounds <= 1:
                # Only a single point – nothing to segment
                line, = self.axes.plot(
                    rounds, player.scores,
                    color=color, marker="o", markersize=6, linewidth=0,
                    label=player.name, zorder=4,
                )
                self._hover_lines.append((line, player.name, player.scores, rounds))
            else:
                # Build a style list for each segment
                seg_styles = [
                    OVERLAP_STYLES[overlap_rank[(i, r)] % len(OVERLAP_STYLES)]
                    if (i, r) in overlap_rank else "-"
                    for r in range(n_rounds - 1)
                ]

                # Plot consecutive segments that share the same style as one call
                legend_added = False
                r = 0
                while r < n_rounds - 1:
                    curr_style = seg_styles[r]
                    r_end = r
                    while r_end < n_rounds - 1 and seg_styles[r_end] == curr_style:
                        r_end += 1
                    x_seg = rounds[r:r_end + 1]
                    y_seg = player.scores[r:r_end + 1]
                    lbl = player.name if not legend_added else "_nolegend_"
                    seg_line, = self.axes.plot(
                        x_seg, y_seg,
                        color=color, marker="o", linewidth=2.2, markersize=6,
                        label=lbl, linestyle=curr_style, zorder=3,
                    )
                    if not legend_added:
                        legend_added = True
                    r = r_end

                # Ghost line spanning all data points for reliable hover detection
                ghost, = self.axes.plot(
                    rounds, player.scores,
                    color=color, linewidth=8, alpha=0.0, zorder=6,
                )
                self._hover_lines.append((ghost, player.name, player.scores, rounds))

            # Highlight maximum
            max_i = int(np.argmax(player.scores))
            self.axes.plot(
                rounds[max_i], player.scores[max_i],
                marker="D", color=color, markersize=10,
                markeredgecolor="white", markeredgewidth=1.2, zorder=5,
            )

        # Average line
        self.axes.plot(
            rounds, game.averages,
            color="#555577", linewidth=1.5, linestyle="--",
            label=t("average"), zorder=2,
        )

        # Zero line – more prominent than regular grid
        if get_theme() == "light":
            self.axes.axhline(
                0, color="#666688", linewidth=1.8, linestyle="-", zorder=2, alpha=0.85,
            )
        else:
            self.axes.axhline(
                0, color="#8888aa", linewidth=1.8, linestyle="-", zorder=2, alpha=0.9,
            )

        # Integer-only x-axis ticks; bold label for the current round
        self.axes.set_xticks(rounds)
        for tick, r in zip(self.axes.xaxis.get_major_ticks(), rounds):
            tick.label1.set_fontweight("bold" if r == game.round_number else "normal")
            if r == game.round_number:
                tick.label1.set_color(TEXT_MAIN if get_theme() == "dark" else TEXT_MAIN_L)

        # ── Sorted legend with scores at the bottom ───────────────────────
        handles, raw_labels = self.axes.get_legend_handles_labels()
        avg_label = t("average")

        # Separate player handles from the average line
        player_entries: list = []
        avg_entries: list = []
        for h, lbl in zip(handles, raw_labels):
            if lbl == avg_label:
                avg_entries.append((h, lbl))
            else:
                player_entries.append((h, lbl))

        # name → handle map (first occurrence = solid/primary segment)
        name_to_handle: dict = {lbl: h for h, lbl in player_entries}

        # Sort players by current score descending (ranking order)
        sorted_players = sorted(game.players, key=lambda p: p.current_score, reverse=True)

        new_handles: list = []
        new_labels: list = []
        for player in sorted_players:
            if player.name in name_to_handle:
                new_handles.append(name_to_handle[player.name])
                new_labels.append(f"{player.name}  {player.current_score}")

        for h, lbl in avg_entries:
            new_handles.append(h)
            new_labels.append(lbl)

        if get_theme() == "light":
            self.axes.legend(
                new_handles, new_labels,
                facecolor="#e4e4ee", edgecolor="#ccccdd",
                labelcolor="#1a1a2e", fontsize=13,
                loc="upper left", ncol=1, framealpha=0.9,
            )
        else:
            self.axes.legend(
                new_handles, new_labels,
                facecolor="#1a1a3a", edgecolor="#2a2a4a",
                labelcolor=TEXT_MAIN, fontsize=13,
                loc="upper left", ncol=1, framealpha=0.9,
            )

        # Set up hover annotation on the fresh axes
        self._setup_hover_annotation()

        self.fig.tight_layout(pad=1.5)
        self.draw()

    def _setup_hover_annotation(self) -> None:
        """Create the hover annotation on the current axes."""
        if get_theme() == "light":
            bbox_color = "#e4e4ee"
            text_color = "#1a1a2e"
            edge_color = "#9b7a1e"
        else:
            bbox_color = "#1a1a3a"
            text_color = "#e8e8f0"
            edge_color = ACCENT

        self._hover_annot = self.axes.annotate(
            "",
            xy=(0, 0),
            xytext=(15, 15),
            textcoords="offset points",
            fontsize=13,
            color=text_color,
            bbox=dict(
                boxstyle="round,pad=0.5",
                fc=bbox_color,
                ec=edge_color,
                alpha=0.95,
                linewidth=1.5,
            ),
            arrowprops=dict(
                arrowstyle="->",
                color=edge_color,
                lw=1.5,
            ),
            zorder=10,
        )
        self._hover_annot.set_visible(False)

    def _on_hover(self, event) -> None:
        """Handle mouse hover over plot lines."""
        if event.inaxes != self.axes or not self._hover_lines or self._hover_annot is None:
            if self._hover_annot is not None and self._hover_annot.get_visible():
                self._hover_annot.set_visible(False)
                self.draw_idle()
            return

        changed = False
        for line, name, scores, rounds in self._hover_lines:
            cont, ind = line.contains(event)
            if cont and len(ind["ind"]) > 0:
                idx = ind["ind"][0]
                x = rounds[idx]
                y = scores[idx]
                self._hover_annot.xy = (x, y)
                self._hover_annot.set_text(
                    f"{name}\n{t('round')}: {x}\n{t('points')}: {y}"
                )
                # Keep the annotation inside the axes – flip the offset
                # whenever the point is near the right or top edge, so the
                # tooltip never gets clipped off the figure.
                self._place_hover_annot(x, y)
                self._hover_annot.set_visible(True)
                changed = True
                break
        else:
            if self._hover_annot.get_visible():
                self._hover_annot.set_visible(False)
                changed = True

        if changed:
            self.draw_idle()

    def _place_hover_annot(self, x: float, y: float) -> None:
        """Pick an offset for the hover annotation so it stays on-canvas."""
        if self._hover_annot is None:
            return
        try:
            x_min, x_max = self.axes.get_xlim()
            y_min, y_max = self.axes.get_ylim()
        except Exception:
            self._hover_annot.set_position((15, 15))
            return
        x_span = (x_max - x_min) or 1.0
        y_span = (y_max - y_min) or 1.0
        # Near right edge → flip horizontally; near top → flip vertically.
        dx = -80 if (x_max - x) / x_span < 0.22 else 15
        dy = -30 if (y_max - y) / y_span < 0.18 else 15
        self._hover_annot.set_position((dx, dy))


# ─────────────────────────────────────────────────────────────────────────────
# Spieler-Karte (Eingabe-Widget pro Spieler)
# ─────────────────────────────────────────────────────────────────────────────

class PlayerCard(QtWidgets.QFrame):
    bid_changed = QtCore.pyqtSignal()

    def __init__(self, player_name: str, color: str, parent=None, avatar: str = ""):
        super().__init__(parent)
        self.player_name = player_name
        self.color = color
        self.setObjectName("card")
        # Only set the dynamic border color; background comes from QSS (#card)
        self.setStyleSheet(
            f"""
            QFrame#card {{
                border: 1px solid {color};
                border-left: 4px solid {color};
                border-radius: 8px;
            }}
            """
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Name + Crown + Punkte
        top_row = QtWidgets.QHBoxLayout()
        if avatar:
            lbl_avatar = QtWidgets.QLabel(avatar)
            lbl_avatar.setStyleSheet(
                "font-size: 28px; background: transparent; border: none;"
            )
            top_row.addWidget(lbl_avatar)
            top_row.addSpacing(4)
        self.lbl_name = QtWidgets.QLabel(player_name)
        self.lbl_name.setStyleSheet(
            f"color: {color}; font-weight: 700; font-size: 20px; background: transparent; border: none;"
        )
        # Leader crown placed right after the player name
        self.lbl_leader = QtWidgets.QLabel("👑")
        self.lbl_leader.setObjectName("leader_badge")
        self.lbl_leader.setStyleSheet(
            f"color: {LEADER}; font-size: 20px; background: transparent; border: none;"
        )
        self.lbl_leader.setVisible(False)
        self.lbl_score = QtWidgets.QLabel("0")
        self.lbl_score.setObjectName("score_value")
        self.lbl_delta = QtWidgets.QLabel("")
        self.lbl_delta.setStyleSheet(
            "font-size: 13px; font-weight: 600; background: transparent; border: none;"
        )
        top_row.addWidget(self.lbl_name)
        top_row.addWidget(self.lbl_leader)
        top_row.addStretch()
        top_row.addWidget(self.lbl_delta)
        top_row.addWidget(self.lbl_score)
        layout.addLayout(top_row)

        # Trennlinie
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        line.setStyleSheet(f"background: {color}33; border: none; max-height: 1px;")
        layout.addWidget(line)

        # Eingabe-Zeile
        input_row = QtWidgets.QHBoxLayout()
        input_row.addStretch()

        def _make_spin_col(label_key: str) -> tuple:
            col = QtWidgets.QVBoxLayout()
            lbl = QtWidgets.QLabel(label_key)
            lbl.setObjectName("input_label")
            lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 15px; font-weight: 600; letter-spacing: 1px; background: transparent; border: none;")
            spin = NoScrollSpinBox()
            spin.setRange(0, 20)
            spin.setMaximumWidth(60)
            col.addWidget(lbl, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
            col.addWidget(spin, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
            return col, spin

        col_bid, self._spin_said = _make_spin_col(t("announced"))
        input_row.addLayout(col_bid)
        input_row.addSpacing(12)

        # Auto-fill button: sets made = bid for this player.
        # Large, prominent "=" glyph so it reads as "equal to the bid".
        self._btn_auto_fill = QtWidgets.QPushButton("=")
        self._btn_auto_fill.setToolTip(t("tooltip_auto_fill"))
        self._btn_auto_fill.setFixedSize(54, 54)
        self._btn_auto_fill.setFocusPolicy(QtCore.Qt.FocusPolicy.TabFocus)
        self._btn_auto_fill.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self._btn_auto_fill.setStyleSheet(
            f"QPushButton {{ color: {color}; background: transparent; "
            f"border: 2px solid {color}88; border-radius: 14px; "
            f"font-size: 34px; font-weight: 900; padding: 0 0 4px 0; }}"
            f"QPushButton:hover {{ background: {color}33; border-color: {color}; color: white; }}"
            f"QPushButton:pressed {{ background: {color}55; }}"
        )
        self._btn_auto_fill.clicked.connect(self._fill_made_from_bid)
        input_row.addWidget(self._btn_auto_fill, alignment=QtCore.Qt.AlignmentFlag.AlignVCenter)
        input_row.addSpacing(12)

        col_made, self._spin_achieved = _make_spin_col(t("achieved"))
        input_row.addLayout(col_made)

        input_row.addStretch()

        # Emit bid_changed whenever the announced (said) spinbox changes
        self._spin_said.valueChanged.connect(self.bid_changed)

        layout.addLayout(input_row)

        # Dealer badge – prominent, larger font with highlighted background
        self.lbl_dealer = QtWidgets.QLabel()
        self.lbl_dealer.setStyleSheet(
            f"color: {BG_DEEP}; background: {ACCENT}; font-size: 14px; font-weight: 700; "
            f"border-radius: 6px; padding: 3px 8px;"
        )
        self.lbl_dealer.setVisible(False)
        layout.addWidget(self.lbl_dealer, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)

    # ── public API ────────────────────────────────────────────────────────────

    def get_round_result(self) -> RoundResult:
        return RoundResult(said=self._spin_said.value(), achieved=self._spin_achieved.value())

    def get_current_bid(self) -> int:
        return self._spin_said.value()

    def _fill_made_from_bid(self) -> None:
        self._spin_achieved.setValue(self._spin_said.value())

    def set_made(self, value: int) -> None:
        self._spin_achieved.setValue(value)

    def reset_inputs(self) -> None:
        self._spin_said.setValue(0)
        self._spin_achieved.setValue(0)

    def set_dealer(self, is_dealer: bool, cards: int) -> None:
        """Show or hide the dealer badge for this card."""
        if is_dealer:
            self.lbl_dealer.setText(t("dealer_badge", n=cards))
            self.lbl_dealer.setVisible(True)
        else:
            self.lbl_dealer.setVisible(False)

    def update_score(self, score: int, delta: int, is_leader: bool) -> None:
        self.lbl_score.setText(str(score))
        if delta > 0:
            self.lbl_delta.setText(f"▲ +{delta}")
            self.lbl_delta.setStyleSheet(
                f"color: {SUCCESS}; font-size: 13px; font-weight: 600; background: transparent; border: none;"
            )
        elif delta < 0:
            self.lbl_delta.setText(f"▼ {delta}")
            self.lbl_delta.setStyleSheet(
                f"color: {DANGER}; font-size: 13px; font-weight: 600; background: transparent; border: none;"
            )
        else:
            self.lbl_delta.setText("")
        self.lbl_leader.setVisible(is_leader)

    def retranslate_ui(self) -> None:
        """Update translatable labels on this card."""
        # Dealer badge text is always re-rendered by GameView._refresh_scores(),
        # which calls set_dealer() for every card after retranslate_ui() returns.
        pass


# ─────────────────────────────────────────────────────────────────────────────
# GameView
# ─────────────────────────────────────────────────────────────────────────────
# Tab-wrap event filter
# ─────────────────────────────────────────────────────────────────────────────

class _TabWrapFilter(QtCore.QObject):
    """Installed on the last widget in the tab chain.
    Catches a forward Tab and redirects focus to *first_widget*, implementing
    cyclic tab navigation without calling setTabOrder for the wrap (which would
    move first_widget in the chain and break the first player's bid→made link).
    """

    def __init__(self, first_widget: QtWidgets.QWidget, parent=None):
        super().__init__(parent)
        self._first = first_widget

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QtCore.QEvent.Type.KeyPress:
            if (event.key() == QtCore.Qt.Key.Key_Tab
                    and not (event.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier)):
                self._first.setFocus(QtCore.Qt.FocusReason.TabFocusReason)
                return True
        return super().eventFilter(obj, event)


# ─────────────────────────────────────────────────────────────────────────────

class GameView(QtWidgets.QWidget):
    """
    Signals
    -------
    request_new_game()
    request_save()
    request_save_plot()
    settings_changed()
    """

    request_new_game  = QtCore.pyqtSignal()
    request_save      = QtCore.pyqtSignal()
    request_save_plot = QtCore.pyqtSignal()
    round_submitted   = QtCore.pyqtSignal(object)   # RoundEvents
    settings_changed  = QtCore.pyqtSignal()

    def __init__(self, game: GameControl, parent=None):
        super().__init__(parent)
        self.game = game
        self._player_cards: List[PlayerCard] = []
        self._build_ui()

    # ── UI-Aufbau ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Linke Sidebar ──────────────────────────────────────────────────
        sidebar = QtWidgets.QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(360)
        sidebar_layout = QtWidgets.QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(14, 14, 14, 14)
        sidebar_layout.setSpacing(10)

        # Header
        header_row = QtWidgets.QHBoxLayout()
        header_row.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)

        title = QtWidgets.QLabel(t("app_title"))
        title.setStyleSheet(f"color: {ACCENT}; font-size: 16px; font-weight: 800; letter-spacing: 2px; background: transparent;")
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)

        self.lbl_round_header = QtWidgets.QLabel(t("round_header", n=0, total=self.game.total_rounds))
        self.lbl_round_header.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 20px; font-weight: 700; background: transparent;"
        )
        self.lbl_round_header.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )

        # Settings-Button
        self.btn_settings = QtWidgets.QPushButton("⚙")
        self.btn_settings.setObjectName("toolbar_btn")
        self.btn_settings.setToolTip(t("tooltip_settings"))
        self.btn_settings.setFixedSize(36, 36)
        self.btn_settings.setStyleSheet(
            "QPushButton { font-size: 24px; padding: 0; background: transparent; border: none; }"
            "QPushButton:hover { background-color: #1a1a3a; border-radius: 4px; }"
        )
        self.btn_settings.clicked.connect(self._on_settings)

        header_row.addWidget(title)
        header_row.addStretch()
        header_row.addWidget(self.btn_settings)
        header_row.addWidget(self.lbl_round_header)
        sidebar_layout.addLayout(header_row)

        # Separator
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sidebar_layout.addWidget(sep)

        # Spieler-Karten (scrollbar)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")
        cards_widget = QtWidgets.QWidget()
        cards_widget.setStyleSheet("background: transparent;")
        self._cards_layout = QtWidgets.QVBoxLayout(cards_widget)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(8)

        for i, player in enumerate(self.game.players):
            color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
            card = PlayerCard(player.name, color, avatar=player.avatar)
            self._player_cards.append(card)
            self._cards_layout.addWidget(card)
        self._cards_layout.addStretch()

        scroll.setWidget(cards_widget)
        sidebar_layout.addWidget(scroll, 1)

        # Bid counter (total tricks bid vs. possible tricks in current round)
        self.lbl_bid_counter = QtWidgets.QLabel(
            t("bid_total", bid=0, total=self.game.cards_this_round)
        )
        self.lbl_bid_counter.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 22px; font-weight: 700; background: transparent;"
        )
        self.lbl_bid_counter.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(self.lbl_bid_counter)

        # Warning label shown when total bids == total possible tricks
        self.lbl_bid_warning = QtWidgets.QLabel(t("bid_warning"))
        self.lbl_bid_warning.setWordWrap(True)
        self.lbl_bid_warning.setStyleSheet(
            f"color: {DANGER}; font-size: 11px; font-weight: 600; background: transparent;"
        )
        self.lbl_bid_warning.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lbl_bid_warning.setVisible(False)
        sidebar_layout.addWidget(self.lbl_bid_warning)

        # Runde-beendet-Button (mit etwas Abstand nach oben)
        sidebar_layout.addSpacing(8)
        self.btn_round_done = QtWidgets.QPushButton(t("complete_round"))
        self.btn_round_done.setObjectName("primary")
        self.btn_round_done.setMinimumHeight(44)
        self.btn_round_done.clicked.connect(self._on_round_done)
        sidebar_layout.addWidget(self.btn_round_done)

        # Aktions-Buttons
        action_row = QtWidgets.QHBoxLayout()
        action_row.setSpacing(6)

        self.btn_undo = self._make_action_btn(t("undo"), tooltip=t("tooltip_undo"))
        self.btn_undo.setEnabled(False)
        self.btn_undo.clicked.connect(self._on_undo)

        self.btn_save = self._make_action_btn(t("save"), tooltip=t("tooltip_save"))
        self.btn_save.clicked.connect(self.request_save)

        self.btn_export = self._make_action_btn(t("plot"), tooltip=t("tooltip_plot"))
        self.btn_export.clicked.connect(self.request_save_plot)

        self.btn_new = self._make_action_btn(t("new"), tooltip=t("tooltip_new"))
        self.btn_new.clicked.connect(self._on_new_game)

        for btn in [self.btn_undo, self.btn_save, self.btn_export, self.btn_new]:
            action_row.addWidget(btn)
        sidebar_layout.addLayout(action_row)

        root.addWidget(sidebar)

        # ── Rechter Bereich (Chart / Leaderboard) ─────────────────────────
        right_wrapper = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_wrapper)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(8)

        # Toggle row: Chart | Leaderboard | Groups
        toggle_row = QtWidgets.QHBoxLayout()
        toggle_row.setSpacing(4)
        self._btn_tab_chart = QtWidgets.QPushButton(t("tab_chart"))
        self._btn_tab_lb = QtWidgets.QPushButton(t("tab_leaderboard"))
        self._btn_tab_groups = QtWidgets.QPushButton(t("tab_groups_lb"))
        for btn in (self._btn_tab_chart, self._btn_tab_lb, self._btn_tab_groups):
            btn.setMinimumHeight(30)
            btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self._btn_tab_chart.clicked.connect(lambda: self._switch_right_tab(0))
        self._btn_tab_lb.clicked.connect(lambda: self._switch_right_tab(1))
        self._btn_tab_groups.clicked.connect(lambda: self._switch_right_tab(2))
        toggle_row.addWidget(self._btn_tab_chart)
        toggle_row.addWidget(self._btn_tab_lb)
        toggle_row.addWidget(self._btn_tab_groups)
        toggle_row.addStretch()
        right_layout.addLayout(toggle_row)

        # Stacked widget
        self._right_stack = QtWidgets.QStackedWidget()

        # Page 0: Chart
        self.canvas = MplCanvas(self)
        self._right_stack.addWidget(self.canvas)  # index 0

        # Page 1: Player leaderboard (with Global/Group scope toggle inside)
        from leaderboard_widget import LeaderboardWidget
        self._leaderboard_widget = LeaderboardWidget()
        self._right_stack.addWidget(self._leaderboard_widget)  # index 1

        # Page 2: Global groups ranking
        from leaderboard_widget import GroupsLeaderboardWidget
        self._groups_lb_widget = GroupsLeaderboardWidget()
        self._right_stack.addWidget(self._groups_lb_widget)  # index 2

        right_layout.addWidget(self._right_stack, 1)
        self._current_right_tab = 0
        self._apply_right_tab_style()

        root.addWidget(right_wrapper, 1)

        # Initiale Darstellung
        self._connect_bid_signals()
        self._setup_tab_order()
        self._refresh_scores()
        self.canvas.redraw(self.game)

    def set_group(self, group: Optional[dict]) -> None:
        """Forward the active group's code to the unified leaderboard widget.

        The widget uses this to enable the Group scope toggle; when None, only
        Global is available.
        """
        code = group["code"] if group else None
        self._leaderboard_widget.set_group(code)

    def _switch_right_tab(self, index: int) -> None:
        self._current_right_tab = index
        self._right_stack.setCurrentIndex(index)
        self._apply_right_tab_style()

    def _apply_right_tab_style(self) -> None:
        dark = get_theme() != "light"
        tabs = [
            self._btn_tab_chart, self._btn_tab_lb, self._btn_tab_groups,
        ]
        for i, btn in enumerate(tabs):
            active = (i == self._current_right_tab)
            if dark:
                if active:
                    btn.setStyleSheet(
                        f"QPushButton {{ background: {ACCENT_DIM}; color: #fff8e0; "
                        f"border: 1px solid {ACCENT}; border-radius: 5px; font-weight: 700; "
                        f"font-size: 12px; padding: 4px 10px; }}"
                    )
                else:
                    btn.setStyleSheet(
                        f"QPushButton {{ background: {BG_CARD}; color: {TEXT_DIM}; "
                        f"border: 1px solid #3a3a6a; border-radius: 5px; "
                        f"font-size: 12px; padding: 4px 10px; }}"
                        f"QPushButton:hover {{ border-color: {ACCENT_DIM}; color: {TEXT_MAIN}; }}"
                    )
            else:
                if active:
                    btn.setStyleSheet(
                        "QPushButton { background: #9b7a1e; color: #ffffff; "
                        "border: 1px solid #c9a84c; border-radius: 5px; font-weight: 700; "
                        "font-size: 12px; padding: 4px 10px; }"
                    )
                else:
                    btn.setStyleSheet(
                        "QPushButton { background: #f8f8ff; color: #555577; "
                        "border: 1px solid #aaaacc; border-radius: 5px; "
                        "font-size: 12px; padding: 4px 10px; }"
                        "QPushButton:hover { border-color: #9b7a1e; color: #1a1a2e; }"
                    )

    @staticmethod
    def _make_action_btn(text: str, tooltip: str = "") -> QtWidgets.QPushButton:
        btn = QtWidgets.QPushButton(text)
        btn.setObjectName("toolbar_btn")
        btn.setMinimumHeight(36)
        btn.setFlat(True)
        if tooltip:
            btn.setToolTip(tooltip)
        return btn

    # ── Spiellogik ────────────────────────────────────────────────────────────

    def _on_round_done(self) -> None:
        total_possible = self.game.cards_this_round

        # Check if total bids equal total possible tricks (invalid game rule)
        total_bid = sum(card.get_current_bid() for card in self._player_cards)
        if total_bid == total_possible:
            # Show blocking warning dialog
            from dialogs import WarningDialog
            dlg = WarningDialog(self, t("bid_warning"))
            dlg.exec()
            return  # Don't proceed with submitting the round

        # Check if total made tricks equals total possible tricks (data validation)
        results = [card.get_round_result() for card in self._player_cards]
        total_made = sum(r.achieved for r in results)
        if total_made != total_possible:
            from dialogs import WarningDialog
            dlg = WarningDialog(self, t("made_tricks_warning", made=total_made, total=total_possible))
            dlg.exec()
            return  # Don't proceed until made tricks are corrected

        events = self.game.submit_round(results)
        for card in self._player_cards:
            card.reset_inputs()
        self._refresh_scores()
        self.canvas.redraw(self.game)
        self.btn_undo.setEnabled(True)
        self.round_submitted.emit(events)

    def _on_undo(self) -> None:
        from dialogs import WarningDialog
        dlg = WarningDialog(self, t("undo_confirm"))
        if dlg.exec():
            self.game.undo_round()
            self._refresh_scores()
            self.canvas.redraw(self.game)
            self.btn_undo.setEnabled(self.game.round_number > 0)

    def _on_new_game(self) -> None:
        from dialogs import WarningDialog
        dlg = WarningDialog(self, t("new_game_confirm"))
        if dlg.exec():
            self.request_new_game.emit()

    def _on_settings(self) -> None:
        """Öffnet den Einstellungen-Dialog."""
        from dialogs import SettingsDialog
        from app_settings import get_theme as _get_theme
        old_theme = _get_theme()
        dlg = SettingsDialog(self)
        dlg.exec()
        # Nach dem Schließen: UI aktualisieren
        self.retranslate_ui()
        if _get_theme() != old_theme:
            self.canvas.redraw(self.game)
        self.settings_changed.emit()

    def _refresh_scores(self) -> None:
        self.lbl_round_header.setText(
            t("round_header", n=self.game.round_number + 1, total=self.game.total_rounds)
        )
        leaders = list(self.game.leaders)
        deltas = self.game.last_deltas()
        dealer_idx = self.game.current_dealer_index
        cards = self.game.cards_this_round
        for i, (card, player) in enumerate(zip(self._player_cards, self.game.players)):
            card.update_score(
                score=player.current_score,
                delta=deltas[i],
                is_leader=(player in leaders),
            )
            card.set_dealer(is_dealer=(i == dealer_idx), cards=cards)
        self._update_bid_counter()

    def _update_bid_counter(self) -> None:
        """Recalculate and display total bids vs. total possible tricks."""
        total_bid = sum(card.get_current_bid() for card in self._player_cards)
        total_possible = self.game.cards_this_round
        self.lbl_bid_counter.setText(
            t("bid_total", bid=total_bid, total=total_possible)
        )
        equal = total_bid == total_possible
        color = DANGER if equal else SUCCESS
        self.lbl_bid_counter.setStyleSheet(
            f"color: {color}; font-size: 22px; font-weight: 700;"
        )
        # Remove the warning label display - warning will be shown as popup when trying to submit
        # self.lbl_bid_warning.setVisible(equal)

    def _connect_bid_signals(self) -> None:
        """Connect each player card's bid_changed signal to the counter."""
        for card in self._player_cards:
            card.bid_changed.connect(self._update_bid_counter)

    def _setup_tab_order(self) -> None:
        """Tab order: P1.bid → P1.= → P1.made → P2.bid → P2.= → P2.made → … (cyclic).

        Uses a strictly linear setTabOrder chain so Qt never moves the first
        widget (which would break its bid→made link).  The cyclic wrap is
        handled by an event filter on the last widget instead.
        """
        if not self._player_cards:
            return

        # Collect focusable widgets in the desired order
        focusable: list = []
        for card in self._player_cards:
            focusable.extend([card._spin_said, card._btn_auto_fill, card._spin_achieved])

        # Linear chain only – no wrap via setTabOrder
        for i in range(len(focusable) - 1):
            QtWidgets.QWidget.setTabOrder(focusable[i], focusable[i + 1])

        # Cyclic wrap via event filter (avoids breaking the first link)
        if hasattr(self, '_tab_wrap_filter'):
            focusable[-1].removeEventFilter(self._tab_wrap_filter)
        self._tab_wrap_filter = _TabWrapFilter(focusable[0], self)
        focusable[-1].installEventFilter(self._tab_wrap_filter)

    def retranslate_ui(self) -> None:
        """Aktualisiert alle übersetzbaren UI-Texte (nach Sprach-/Themenwechsel)."""
        self.btn_round_done.setText(t("complete_round"))
        self.btn_undo.setText(t("undo"))
        self.btn_undo.setToolTip(t("tooltip_undo"))
        self.btn_save.setText(t("save"))
        self.btn_save.setToolTip(t("tooltip_save"))
        self.btn_export.setText(t("plot"))
        self.btn_export.setToolTip(t("tooltip_plot"))
        self.btn_new.setText(t("new"))
        self.btn_new.setToolTip(t("tooltip_new"))
        self.btn_settings.setToolTip(t("tooltip_settings"))
        self.lbl_bid_warning.setText(t("bid_warning"))
        self._btn_tab_chart.setText(t("tab_chart"))
        self._btn_tab_lb.setText(t("tab_leaderboard"))
        self._btn_tab_groups.setText(t("tab_groups_lb"))
        self._apply_right_tab_style()
        self._leaderboard_widget.retranslate_ui()
        self._groups_lb_widget.retranslate_ui()
        for card in self._player_cards:
            card.retranslate_ui()
        # _refresh_scores re-renders dealer badges + round header + bid counter
        self._refresh_scores()
        self.canvas.redraw(self.game)

    # ── Zustand neu laden (für Load-Funktion) ─────────────────────────────────

    def replace_game(self, new_game: GameControl) -> None:
        """Ersetzt das aktuelle Spielobjekt und aktualisiert die UI."""
        self.game = new_game

        # Karten neu aufbauen
        for card in self._player_cards:
            self._cards_layout.removeWidget(card)
            card.deleteLater()
        self._player_cards.clear()

        stretch = self._cards_layout.takeAt(0)  # entferne den alten Stretch

        for i, player in enumerate(self.game.players):
            color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
            card = PlayerCard(player.name, color, avatar=player.avatar)
            self._player_cards.append(card)
            self._cards_layout.addWidget(card)
        self._cards_layout.addStretch()

        self._connect_bid_signals()
        self._setup_tab_order()
        self._refresh_scores()
        self.canvas.redraw(self.game)
        self.btn_undo.setEnabled(self.game.round_number > 0)

