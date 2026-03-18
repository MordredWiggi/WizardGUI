"""
main_window.py – Haupt-Fenster des Wizard-GUI

Verwaltet:
  • QStackedWidget mit SetupView (Index 0) und GameView (Index 1)
  • Übergänge zwischen den Zuständen
  • Celebration-Overlay-Logik
  • Speichern / Laden via SaveManager
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Optional

from PyQt6 import QtCore, QtWidgets, QtGui

from game_control import GameControl, RoundEvents
from save_manager import SaveManager
from style import ACCENT, BG_BASE, SUCCESS, DANGER, LEADER, PLAYER_COLORS

from setup_view import SetupView
from game_view import GameView
from dialogs import (
    SaveGameDialog, LoadGameDialog,
    CelebrationOverlay, WarningDialog, PodiumDialog,
)
from app_settings import t, get_theme


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(t("window_title"))
        self.setMinimumSize(1000, 650)

        self._save_manager = SaveManager()
        self._game: Optional[GameControl] = None
        self._game_view: Optional[GameView] = None

        # ── Stacked Widget ─────────────────────────────────────────────────
        self._stack = QtWidgets.QStackedWidget()
        self.setCentralWidget(self._stack)

        self._setup_view = SetupView(self._save_manager)
        self._setup_view.start_game.connect(self._on_start_game)
        self._setup_view.load_game.connect(self._on_load_game_from_path)
        self._setup_view.settings_changed.connect(self._on_settings_changed)
        self._stack.addWidget(self._setup_view)   # index 0

        # GameView wird erst beim ersten Spielstart erstellt (index 1+)

        # ── Celebration Overlay ────────────────────────────────────────────
        self._overlay = CelebrationOverlay(self)

        self.showMaximized()

    # ── Fenstergröße → Overlay anpassen ──────────────────────────────────────

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._overlay.setGeometry(self.rect())

    # ── Settings propagation ──────────────────────────────────────────────────

    def _on_settings_changed(self) -> None:
        """Called when settings change from any view – updates all views."""
        self._setup_view.retranslate_ui()
        if self._game_view is not None:
            self._game_view.retranslate_ui()
        self.setWindowTitle(t("window_title"))
        self._update_status_bar_style()

    # ── State-Übergänge ───────────────────────────────────────────────────────

    def _on_start_game(self, player_names: list) -> None:
        self._game = GameControl(player_names)
        self._show_game_view()

    def _show_game_view(self) -> None:
        assert self._game is not None

        if self._game_view is not None:
            self._stack.removeWidget(self._game_view)
            self._game_view.deleteLater()

        self._game_view = GameView(self._game)
        self._game_view.request_new_game.connect(self._on_new_game)
        self._game_view.request_save.connect(self._on_save_game)
        self._game_view.request_save_plot.connect(self._on_save_plot)
        self._game_view.round_submitted.connect(self._on_round_submitted)
        self._game_view.settings_changed.connect(self._on_settings_changed)
        self._stack.addWidget(self._game_view)
        self._stack.setCurrentWidget(self._game_view)

    def _on_new_game(self) -> None:
        """Zurück zur Setup-Ansicht."""
        self._setup_view.retranslate_ui()
        self._stack.setCurrentWidget(self._setup_view)

    # ── Spielrunden-Events → Celebration ─────────────────────────────────────

    def _on_round_submitted(self, events: RoundEvents) -> None:
        """Wählt den passenden Celebration-Effekt für die Runde."""
        # --- Priority 1: huge loss → play XP sound ---
        if events.huge_loss_player:
            try:
                from sounds import play_xp_shutdown
                play_xp_shutdown()
            except Exception:
                pass
            self._overlay.show_event(
                "💥",
                t("huge_loss", name=events.huge_loss_player.name, delta=events.huge_loss_delta),
                "",
                color=DANGER,
            )
        # --- Priority 2: fire / leading / big-score celebrations ---
        elif events.fire_player:
            self._overlay.show_event(
                "🔥", f"{events.fire_player.name} ist auf Feuer!",
                "3× perfekt in Folge!", color="#ff6b35",
            )
        elif events.new_leader:
            self._overlay.show_event(
                "👑", f"{events.new_leader.name} führt jetzt!",
                f"{events.new_leader.current_score} Punkte", color=LEADER,
            )
        elif events.big_scorer and events.big_score_delta >= 50:
            self._overlay.show_event(
                "🎯", f"Meisterschuss!",
                f"+{events.big_score_delta} für {events.big_scorer.name}", color=SUCCESS,
            )
        # --- Bow stretched: 3 consecutive losses ---
        elif events.bow_players:
            name = events.bow_players[0].name
            self._overlay.show_event(
                "🏹",
                t("bow_stretched", name=name),
                "",
                color=DANGER,
            )
        # --- Revenge: 2 gains after ≥2 losses ---
        elif events.revenge_players:
            name = events.revenge_players[0].name
            self._overlay.show_event(
                "⚡",
                t("revenge_lever", name=name),
                "",
                color="#ff9900",
            )

        # --- Game over: show podium (delayed so overlay can finish first) ---
        if events.game_over:
            QtCore.QTimer.singleShot(2800, self._show_podium)

    # ── Podium ────────────────────────────────────────────────────────────────

    def _show_podium(self) -> None:
        """Display the winner's podium dialog at the end of the game."""
        if not self._game:
            return
        players_sorted = sorted(
            [(p.name, p.current_score) for p in self._game.players],
            key=lambda x: x[1],
            reverse=True,
        )
        dlg = PodiumDialog(self, players_sorted)
        if dlg.exec():
            self._on_new_game()

    # ── Speichern ─────────────────────────────────────────────────────────────

    def _on_save_game(self) -> None:
        if not self._game:
            return
        players = "_".join(p.name for p in self._game.players)
        default = f"{datetime.now().strftime('%Y%m%d')}_{players}"
        dlg = SaveGameDialog(self, default_name=default)
        if dlg.exec():
            name = dlg.game_name or default
            path = self._save_manager.save_game(self._game.to_dict(), game_name=name)
            self._show_status(f"💾  Gespeichert: {path.name}")

    def _on_save_plot(self) -> None:
        if not self._game_view:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Plot speichern",
            str(Path.home() / "wizard_plot.png"),
            "PNG-Bild (*.png);;JPEG-Bild (*.jpg);;SVG-Vektorgrafik (*.svg)",
        )
        if path:
            self._save_manager.save_plot(self._game_view.canvas.fig, Path(path))
            self._show_status(f"🖼  Plot gespeichert: {Path(path).name}")

    # ── Laden ─────────────────────────────────────────────────────────────────

    def _on_load_game_from_path(self, filepath: Path) -> None:
        try:
            game_data = self._save_manager.load_game(filepath)
            self._game = GameControl.from_dict(game_data)
            self._show_game_view()
        except Exception as exc:
            QtWidgets.QMessageBox.critical(
                self, "Fehler beim Laden",
                f"Das Spiel konnte nicht geladen werden:\n{exc}",
            )

    # ── Statusleiste ──────────────────────────────────────────────────────────

    def _update_status_bar_style(self) -> None:
        if get_theme() == "light":
            self.statusBar().setStyleSheet(
                "QStatusBar { background: #e4e4ee; color: #9b7a1e; font-size: 12px; padding: 4px 12px; }"
            )
        else:
            self.statusBar().setStyleSheet(
                "QStatusBar { background: #1a1a3a; color: #c9a84c; font-size: 12px; padding: 4px 12px; }"
            )

    def _show_status(self, message: str, timeout_ms: int = 4000) -> None:
        self._update_status_bar_style()
        self.statusBar().showMessage(message, timeout_ms)

