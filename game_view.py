"""
game_view.py – Hauptbildschirm während eines laufenden Spiels

Zeigt:
  • Spieler-Karten mit aktuellem Punktestand und Rundeingabe
  • Matplotlib-Plot der Punkteverläufe
  • Toolbar-Aktionen (Undo, Speichern, Plot exportieren, Neues Spiel)
"""
from __future__ import annotations

from typing import Optional, List

import numpy as np
import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from PyQt6 import QtCore, QtWidgets, QtGui

from game_control import GameControl, RoundResult, RoundEvents
from style import (
    ACCENT, ACCENT_DIM, BG_BASE, BG_PANEL, BG_CARD, BG_DEEP,
    TEXT_MAIN, TEXT_DIM, SUCCESS, DANGER, LEADER, PLAYER_COLORS,
)


# ─────────────────────────────────────────────────────────────────────────────
# Matplotlib Canvas
# ─────────────────────────────────────────────────────────────────────────────

class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=7, height=5):
        self.fig, self.axes = plt.subplots(1, 1, figsize=(width, height))
        self._style_figure()
        super().__init__(self.fig)

    def _style_figure(self) -> None:
        self.fig.patch.set_facecolor("#0d0d1a")
        ax = self.axes
        ax.set_facecolor("#12122b")
        ax.tick_params(colors="#888aaa", labelsize=10)
        ax.spines[:].set_color("#2a2a4a")
        ax.xaxis.label.set_color(TEXT_DIM)
        ax.yaxis.label.set_color(TEXT_DIM)
        ax.set_xlabel("Runde", color=TEXT_DIM, fontsize=11)
        ax.set_ylabel("Punkte", color=TEXT_DIM, fontsize=11)
        ax.grid(True, color="#1e1e3a", linewidth=0.8, linestyle="--", alpha=0.6)

    def redraw(self, game: GameControl) -> None:
        self.axes.clear()
        self._style_figure()

        rounds = game.round_indices
        for i, player in enumerate(game.players):
            color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
            self.axes.plot(
                rounds, player.scores,
                color=color, marker="o", linewidth=2.2, markersize=6,
                label=player.name, zorder=3,
            )
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
            label="Ø Durchschnitt", zorder=2,
        )

        # Zero line
        self.axes.axhline(0, color="#3a3a5a", linewidth=1.0, linestyle=":", zorder=1)

        # Leader annotation
        leader = game.leader
        if leader and game.round_number > 0:
            self.axes.annotate(
                f"👑 {leader.name}",
                xy=(game.round_number, leader.current_score),
                xytext=(10, 10), textcoords="offset points",
                color=LEADER, fontsize=9, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=LEADER, lw=1.2),
            )

        legend = self.axes.legend(
            facecolor="#1a1a3a", edgecolor="#2a2a4a",
            labelcolor=TEXT_MAIN, fontsize=10, loc="upper left",
            framealpha=0.9,
        )
        self.fig.tight_layout(pad=1.5)
        self.draw()


# ─────────────────────────────────────────────────────────────────────────────
# Spieler-Karte (Eingabe-Widget pro Spieler)
# ─────────────────────────────────────────────────────────────────────────────

class PlayerCard(QtWidgets.QFrame):
    def __init__(self, player_name: str, color: str, parent=None):
        super().__init__(parent)
        self.player_name = player_name
        self.color = color
        self.setObjectName("card")
        self.setStyleSheet(
            f"""
            QFrame#card {{
                background-color: {BG_CARD};
                border: 1px solid {color}55;
                border-left: 4px solid {color};
                border-radius: 8px;
            }}
            """
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Name + Punkte
        top_row = QtWidgets.QHBoxLayout()
        self.lbl_name = QtWidgets.QLabel(player_name)
        self.lbl_name.setStyleSheet(
            f"color: {color}; font-weight: 700; font-size: 14px; background: transparent; border: none;"
        )
        self.lbl_score = QtWidgets.QLabel("0")
        self.lbl_score.setObjectName("score_value")
        self.lbl_score.setStyleSheet(
            f"color: {TEXT_MAIN}; font-size: 20px; font-weight: 700; background: transparent; border: none;"
        )
        self.lbl_delta = QtWidgets.QLabel("")
        self.lbl_delta.setStyleSheet(
            f"font-size: 11px; font-weight: 600; background: transparent; border: none;"
        )
        top_row.addWidget(self.lbl_name)
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

        for label, attr in [("Angesagt", "_spin_said"), ("Gemacht", "_spin_achieved")]:
            col = QtWidgets.QVBoxLayout()
            lbl = QtWidgets.QLabel(label)
            lbl.setStyleSheet(
                f"color: {TEXT_DIM}; font-size: 10px; letter-spacing: 1px; background: transparent; border: none;"
            )
            spin = QtWidgets.QSpinBox()
            spin.setRange(0, 20)
            spin.setMinimumWidth(72)
            col.addWidget(lbl, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
            col.addWidget(spin, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
            setattr(self, attr, spin)
            input_row.addLayout(col)
            input_row.addStretch()

        input_row.addStretch()
        layout.addLayout(input_row)

        # Leader badge
        self.lbl_leader = QtWidgets.QLabel("👑 Führend")
        self.lbl_leader.setObjectName("leader_badge")
        self.lbl_leader.setStyleSheet(
            f"color: {LEADER}; font-size: 11px; font-weight: 600; background: transparent; border: none;"
        )
        self.lbl_leader.setVisible(False)
        layout.addWidget(self.lbl_leader, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

    # ── public API ────────────────────────────────────────────────────────────

    def get_round_result(self) -> RoundResult:
        return RoundResult(said=self._spin_said.value(), achieved=self._spin_achieved.value())

    def reset_inputs(self) -> None:
        self._spin_said.setValue(0)
        self._spin_achieved.setValue(0)

    def update_score(self, score: int, delta: int, is_leader: bool) -> None:
        self.lbl_score.setText(str(score))
        if delta > 0:
            self.lbl_delta.setText(f"▲ +{delta}")
            self.lbl_delta.setStyleSheet(
                f"color: {SUCCESS}; font-size: 11px; font-weight: 600; background: transparent; border: none;"
            )
        elif delta < 0:
            self.lbl_delta.setText(f"▼ {delta}")
            self.lbl_delta.setStyleSheet(
                f"color: {DANGER}; font-size: 11px; font-weight: 600; background: transparent; border: none;"
            )
        else:
            self.lbl_delta.setText("")
        self.lbl_leader.setVisible(is_leader)


# ─────────────────────────────────────────────────────────────────────────────
# GameView
# ─────────────────────────────────────────────────────────────────────────────

class GameView(QtWidgets.QWidget):
    """
    Signals
    -------
    request_new_game()
    request_save()
    request_save_plot()
    """

    request_new_game  = QtCore.pyqtSignal()
    request_save      = QtCore.pyqtSignal()
    request_save_plot = QtCore.pyqtSignal()
    round_submitted   = QtCore.pyqtSignal(object)   # RoundEvents

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
        sidebar.setFixedWidth(300)
        sidebar.setStyleSheet(f"background-color: {BG_PANEL}; border-right: 1px solid #2a2a4a;")
        sidebar_layout = QtWidgets.QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(14, 14, 14, 14)
        sidebar_layout.setSpacing(10)

        # Header
        header_row = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("🃏 WIZARD")
        title.setStyleSheet(f"color: {ACCENT}; font-size: 16px; font-weight: 800; letter-spacing: 2px;")
        rnd_lbl_wrapper = QtWidgets.QWidget()
        rnd_layout = QtWidgets.QVBoxLayout(rnd_lbl_wrapper)
        rnd_layout.setContentsMargins(0, 0, 0, 0)
        rnd_layout.setSpacing(0)
        self.lbl_round_header = QtWidgets.QLabel("Runde 0")
        self.lbl_round_header.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 11px; font-weight: 600; text-align: right;"
        )
        self.lbl_round_header.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        rnd_layout.addWidget(self.lbl_round_header)
        header_row.addWidget(title)
        header_row.addStretch()
        header_row.addWidget(rnd_lbl_wrapper)
        sidebar_layout.addLayout(header_row)

        # Separator
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setStyleSheet("background: #2a2a4a; border: none; max-height: 1px;")
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
            card = PlayerCard(player.name, color)
            self._player_cards.append(card)
            self._cards_layout.addWidget(card)
        self._cards_layout.addStretch()

        scroll.setWidget(cards_widget)
        sidebar_layout.addWidget(scroll, 1)

        # Runde-beendet-Button
        self.btn_round_done = QtWidgets.QPushButton("✓  Runde abschließen")
        self.btn_round_done.setObjectName("primary")
        self.btn_round_done.setMinimumHeight(44)
        self.btn_round_done.clicked.connect(self._on_round_done)
        sidebar_layout.addWidget(self.btn_round_done)

        # Aktions-Buttons
        action_row = QtWidgets.QHBoxLayout()
        action_row.setSpacing(6)

        self.btn_undo = self._make_action_btn("↩  Undo", tooltip="Letzte Runde rückgängig")
        self.btn_undo.setEnabled(False)
        self.btn_undo.clicked.connect(self._on_undo)

        btn_save = self._make_action_btn("💾  Speichern", tooltip="Spielstand speichern")
        btn_save.clicked.connect(self.request_save)

        btn_export = self._make_action_btn("🖼  Plot", tooltip="Plot als Bild exportieren")
        btn_export.clicked.connect(self.request_save_plot)

        btn_new = self._make_action_btn("⟳  Neu", tooltip="Neues Spiel starten")
        btn_new.clicked.connect(self._on_new_game)

        for btn in [self.btn_undo, btn_save, btn_export, btn_new]:
            action_row.addWidget(btn)
        sidebar_layout.addLayout(action_row)

        root.addWidget(sidebar)

        # ── Rechter Plot-Bereich ───────────────────────────────────────────
        plot_wrapper = QtWidgets.QWidget()
        plot_layout = QtWidgets.QVBoxLayout(plot_wrapper)
        plot_layout.setContentsMargins(16, 16, 16, 16)
        plot_layout.setSpacing(0)

        self.canvas = MplCanvas(self)
        plot_layout.addWidget(self.canvas)

        root.addWidget(plot_wrapper, 1)

        # Initiale Darstellung
        self._refresh_scores()
        self.canvas.redraw(self.game)

    @staticmethod
    def _make_action_btn(text: str, tooltip: str = "") -> QtWidgets.QPushButton:
        btn = QtWidgets.QPushButton(text)
        btn.setObjectName("toolbar_btn")
        btn.setMinimumHeight(32)
        if tooltip:
            btn.setToolTip(tooltip)
        return btn

    # ── Spiellogik ────────────────────────────────────────────────────────────

    def _on_round_done(self) -> None:
        results = [card.get_round_result() for card in self._player_cards]
        events = self.game.submit_round(results)
        for card in self._player_cards:
            card.reset_inputs()
        self._refresh_scores()
        self.canvas.redraw(self.game)
        self.btn_undo.setEnabled(True)
        self.round_submitted.emit(events)

    def _on_undo(self) -> None:
        from dialogs import WarningDialog
        dlg = WarningDialog(self, "Letzte Runde wirklich rückgängig machen?")
        if dlg.exec():
            self.game.undo_round()
            self._refresh_scores()
            self.canvas.redraw(self.game)
            self.btn_undo.setEnabled(self.game.round_number > 0)

    def _on_new_game(self) -> None:
        from dialogs import WarningDialog
        dlg = WarningDialog(
            self,
            "Aktuelles Spiel beenden und ein neues starten?\n\nUngespeicherte Daten gehen verloren."
        )
        if dlg.exec():
            self.request_new_game.emit()

    def _refresh_scores(self) -> None:
        self.lbl_round_header.setText(f"Runde {self.game.round_number}")
        leader = self.game.leader
        deltas = self.game.last_deltas()
        for i, (card, player) in enumerate(zip(self._player_cards, self.game.players)):
            card.update_score(
                score=player.current_score,
                delta=deltas[i],
                is_leader=(player is leader),
            )

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
            card = PlayerCard(player.name, color)
            self._player_cards.append(card)
            self._cards_layout.addWidget(card)
        self._cards_layout.addStretch()

        self._refresh_scores()
        self.canvas.redraw(self.game)
        self.btn_undo.setEnabled(self.game.round_number > 0)
