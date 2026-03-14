"""
main_window.py – Haupt-Fenster des Wizard-GUI

Verwaltet:
  • QStackedWidget mit SetupView (Index 0) und GameView (Index 1)
  • Übergänge zwischen den Zuständen
  • Celebration-Overlay-Logik
  • Speichern / Laden via SaveManager
"""
from __future__ import annotations

import os
import sys
import subprocess
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
    CelebrationOverlay, WarningDialog, WinnersPodiumDialog,
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
        showing_celebration = False

        # Huge loss always plays a sound; also takes overlay priority
        if events.huge_loss_player:
            self._play_xp_shutdown_sound()
            self._overlay.show_event(
                "💀",
                t("celeb_huge_loss"),
                t("celeb_huge_loss_sub",
                  player=events.huge_loss_player.name,
                  points=events.huge_loss_delta),
                color=DANGER,
            )
            showing_celebration = True
        elif events.fire_player:
            self._overlay.show_event(
                "🔥", f"{events.fire_player.name} ist auf Feuer!",
                "3× perfekt in Folge!", color="#ff6b35",
            )
            showing_celebration = True
        elif events.revenge_player:
            self._overlay.show_event(
                "⚡",
                t("celeb_revenge"),
                t("celeb_revenge_sub", player=events.revenge_player.name),
                color="#b44fff",
            )
            showing_celebration = True
        elif events.bow_player:
            self._overlay.show_event(
                "🏹",
                t("celeb_bow"),
                t("celeb_bow_sub", player=events.bow_player.name),
                color="#ff9900",
            )
            showing_celebration = True
        elif events.new_leader:
            self._overlay.show_event(
                "👑", f"{events.new_leader.name} führt jetzt!",
                f"{events.new_leader.current_score} Punkte", color=LEADER,
            )
            showing_celebration = True
        elif events.big_scorer and events.big_score_delta >= 50:
            self._overlay.show_event(
                "🎯", f"Meisterschuss!",
                f"+{events.big_score_delta} für {events.big_scorer.name}", color=SUCCESS,
            )
            showing_celebration = True

        # Check if the game is over and schedule the winner's podium
        if self._game and self._game.is_game_over:
            delay = 3000 if showing_celebration else 500
            QtCore.QTimer.singleShot(delay, self._show_winners_podium)

    def _play_xp_shutdown_sound(self) -> None:
        """Play a sound for the huge-loss event.

        Tries to play ``sounds/xp_shutdown.wav`` from the application directory
        (place the file there to enable it).  Falls back to a system beep.
        """
        sound_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "sounds", "xp_shutdown.wav",
        )
        if os.path.isfile(sound_path):
            try:
                if sys.platform == "win32":
                    import winsound  # type: ignore[import]
                    winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                elif sys.platform == "darwin":
                    subprocess.Popen(["afplay", sound_path])
                else:
                    subprocess.Popen(["aplay", sound_path], stderr=subprocess.DEVNULL)
                return
            except Exception:
                pass
        # Fallback: system beep
        try:
            if sys.platform == "win32":
                import winsound  # type: ignore[import]
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            else:
                QtWidgets.QApplication.beep()
        except Exception:
            pass

    def _show_winners_podium(self) -> None:
        """Display the end-of-game winner's podium dialog."""
        if self._game is None:
            return
        dlg = WinnersPodiumDialog(self, self._game.players)
        dlg.exec()

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

