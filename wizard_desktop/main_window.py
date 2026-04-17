"""
main_window.py – Haupt-Fenster des Wizard-GUI

Verwaltet:
  • QStackedWidget mit SetupView (Index 0) und GameView (Index 1)
  • Übergänge zwischen den Zuständen
  • Celebration-Overlay-Logik
  • Speichern / Laden via SaveManager
"""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from PyQt6 import QtCore, QtWidgets, QtGui

from game_control import GameControl, RoundEvents
from save_manager import SaveManager, SAVE_DIR
from style import ACCENT, BG_BASE, SUCCESS, DANGER, LEADER, PLAYER_COLORS, apply_titlebar_theme

from setup_view import SetupView
from game_view import GameView
from dialogs import (
    SaveGameDialog, LoadGameDialog,
    CelebrationOverlay, WarningDialog, PodiumDialog,
    MigrationDialog, MigrationProgressDialog, MigrationGroupDialog,
    PendingSyncAssignDialog,
)
from app_settings import t, get_theme, get_leaderboard_url, resolve_event_message

MIGRATION_MARKER = Path.home() / ".wizard_gui" / ".migration_done"


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(t("window_title"))
        self.setMinimumSize(1000, 650)

        self._save_manager = SaveManager()
        self._game: Optional[GameControl] = None
        self._game_view: Optional[GameView] = None
        self._active_group: Optional[dict] = None  # currently selected group

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
        self._submit_worker = None
        self._pending_sync_path: Optional[Path] = None

        self.showMaximized()

        # Check for old games that can be migrated (after UI is up)
        QtCore.QTimer.singleShot(500, self._check_migration)
        # Retry any games that were completed while offline.
        QtCore.QTimer.singleShot(1500, self._retry_pending_sync)

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
        apply_titlebar_theme(self)

    # ── State-Übergänge ───────────────────────────────────────────────────────

    def _on_start_game(self, player_data: list, game_mode: str, group: object) -> None:
        self._active_group = group  # may be None for load-game paths
        self._game = GameControl(player_data, game_mode=game_mode)
        self._show_game_view()

    def _show_game_view(self) -> None:
        assert self._game is not None

        if self._game_view is not None:
            self._stack.removeWidget(self._game_view)
            self._game_view.deleteLater()

        self._game_view = GameView(self._game)
        self._game_view.set_group(self._active_group)
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
        import random
        from app_settings import get_custom_rules

        # --- Evaluate Custom Rules (Highest Priority) ---
        custom_pool = []
        if self._game:
            deltas = self._game.last_deltas()
            for i, p in enumerate(self._game.players):
                delta = deltas[i]
                for rule in get_custom_rules():
                    matched = False
                    rtype = rule.get("type")
                    rval = rule.get("value", 0)
                    msg = rule.get("message", "")
                    if rtype == "points" and delta == rval:
                        matched = True
                    elif rtype == "win_streak" and p.consecutive_perfect == rval:
                        matched = True
                    elif rtype == "loss_streak" and p.consecutive_losses == rval:
                        matched = True
                        
                    if matched:
                        formatted_msg = msg.replace("{name}", p.name).replace("{value}", str(rval))
                        custom_pool.append(("✨", formatted_msg, "", "#d500f9"))
                        
        if custom_pool:
            emoji, title, subtitle, color = random.choice(custom_pool)
            self._overlay.show_event(emoji, title, subtitle, color=color)
            if events.game_over:
                self._submit_to_leaderboard()
                QtCore.QTimer.singleShot(0, self._show_podium)
            return

        # --- Priority 1: Check for special Tobi message at 60% rounds ---
        if self._game and self._check_tobi_message(events):
            # Tobi message was shown, skip other messages
            pass
        # --- Priority 2: huge loss → play XP sound ---
        elif events.huge_loss_player:
            try:
                from sounds import play_xp_shutdown
                play_xp_shutdown()
            except Exception:
                pass
            self._overlay.show_event(
                "💥",
                resolve_event_message(
                    "huge_loss",
                    name=events.huge_loss_player.name,
                    delta=events.huge_loss_delta,
                ),
                "",
                color=DANGER,
            )
        # --- Priority 3: Collect all possible messages and randomize ---
        else:
            possible_messages = []

            if events.fire_player:
                possible_messages.append((
                    "🔥",
                    resolve_event_message("fire", name=events.fire_player.name),
                    t("fire_subtitle"),
                    "#ff6b35",
                ))

            if events.new_leader:
                possible_messages.append((
                    "👑",
                    resolve_event_message("new_leader", name=events.new_leader.name),
                    t("new_leader_subtitle", score=events.new_leader.current_score),
                    LEADER,
                ))

            if events.big_scorer and events.big_score_delta >= 50:
                possible_messages.append((
                    "🎯",
                    resolve_event_message("big_scorer"),
                    t("big_scorer_subtitle",
                      delta=events.big_score_delta,
                      name=events.big_scorer.name),
                    SUCCESS,
                ))

            if events.bow_players:
                for player in events.bow_players:
                    possible_messages.append((
                        "🏹",
                        resolve_event_message("bow_stretched", name=player.name),
                        "",
                        DANGER,
                    ))

            if events.revenge_players:
                for player in events.revenge_players:
                    possible_messages.append((
                        "⚡",
                        resolve_event_message("revenge_lever", name=player.name),
                        "",
                        "#ff9900",
                    ))

            # Show one random message from all possibilities
            if possible_messages:
                emoji, title, subtitle, color = random.choice(possible_messages)
                self._overlay.show_event(emoji, title, subtitle, color=color)

        # --- Game over: submit to leaderboard & show podium ---
        if events.game_over:
            self._submit_to_leaderboard()
            QtCore.QTimer.singleShot(0, self._show_podium)

    def _check_tobi_message(self, events: RoundEvents) -> bool:
        """Check if we should show the special Tobi message. Returns True if shown."""
        if not self._game:
            return False

        # Check if we're at 60% of rounds
        total_rounds = self._game.total_rounds
        rounds_60_percent = int(total_rounds * 0.6)
        if self._game.round_number != rounds_60_percent:
            return False

        # Check if a player named "Tobi" exists and is last or second-last
        tobi_player = None
        for player in self._game.players:
            if player.name.lower() == "tobi":
                tobi_player = player
                break

        if not tobi_player:
            return False

        # Sort players by score (descending) to find position
        sorted_players = sorted(self._game.players, key=lambda p: p.current_score, reverse=True)
        tobi_position = sorted_players.index(tobi_player)

        # Check if last or second-last (index: len-1 or len-2)
        num_players = len(sorted_players)
        if tobi_position == num_players - 1 or tobi_position == num_players - 2:
            # Show special message
            self._overlay.show_event(
                "💪",
                resolve_event_message("tobi_message", name=tobi_player.name),
                "",
                color="#4fc3f7",
            )
            return True

        return False

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

    # ── Leaderboard: submit game after completion ──────────────────────────────

    def _submit_to_leaderboard(self) -> None:
        """Submit the current (completed) game to the leaderboard server.

        If no network is available or the server returns an error, persist the
        game locally with ``pending_sync=True`` so it can be uploaded later on
        the next successful launch.
        """
        url = get_leaderboard_url()
        if not url or not self._game or not self._game.is_game_over:
            return

        from leaderboard_client import (
            LeaderboardClient, GameSubmitWorker, build_game_submission,
        )

        game_data = self._game.to_dict()
        group_code = self._active_group["code"] if self._active_group else None

        # Always persist offline-first: if the submission fails, we keep the
        # pending-sync file; if it succeeds, we clear the flag.
        self._pending_sync_path = self._save_manager.save_game(
            game_data,
            game_name=None,
            pending_sync=True,
            group_code=group_code,
        )

        payload = build_game_submission(game_data, group_code=group_code)
        client = LeaderboardClient(url)
        self._submit_worker = GameSubmitWorker(client, payload)
        self._submit_worker.finished.connect(self._on_submit_result)
        self._submit_worker.start()

    def _on_submit_result(self, success: bool) -> None:
        path = getattr(self, "_pending_sync_path", None)
        if success:
            if path is not None:
                self._save_manager.mark_synced(path)
            self._show_status(t("leaderboard_submit_ok"))
        else:
            # Leave the file flagged as pending_sync — it will be retried on
            # the next launch by _retry_pending_sync().
            self._show_status(t("leaderboard_submit_fail_offline")
                              if path is not None
                              else t("leaderboard_submit_fail"))
        self._pending_sync_path = None

    # ── Pending-sync retry on launch ─────────────────────────────────────────

    def _retry_pending_sync(self) -> None:
        """Upload games that were queued offline.

        If any pending games have no group assigned, prompt the user to assign
        groups first (they can skip and the games go to the global leaderboard).
        """
        url = get_leaderboard_url()
        if not url:
            return
        pending = self._save_manager.list_pending_sync_games()
        if not pending:
            return

        from leaderboard_client import LeaderboardClient, build_game_submission

        client = LeaderboardClient(url)

        # Ask the user to assign groups for any games that went offline without
        # one. We reuse MigrationGroupDialog (allow_skip=True → empty group is
        # OK, it just uploads to the global leaderboard).
        unassigned = [p for p in pending if not p.get("group_code")]
        if unassigned:
            dlg = PendingSyncAssignDialog(self, unassigned, client)
            if dlg.exec():
                for item in unassigned:
                    fp = str(item["filepath"])
                    assigned = dlg.group_assignments.get(fp)
                    if assigned:
                        code = assigned.get("code")
                        item["group_code"] = code
                        self._save_manager.update_pending_group_code(item["filepath"], code)
            # If the user cancels the dialog entirely, we still sync below
            # (games just go to the global leaderboard without a group).

        synced = 0
        for item in pending:
            try:
                submission = build_game_submission(
                    item["game"],
                    played_at=item.get("saved_at") or None,
                    group_code=item.get("group_code"),
                )
                if client.submit_game(submission):
                    self._save_manager.mark_synced(item["filepath"])
                    synced += 1
            except Exception:
                continue
        if synced:
            self._show_status(t("pending_sync_success", n=synced))

    # ── Leaderboard: migrate old games ───────────────────────────────────────

    def _check_migration(self) -> None:
        """On first launch with a leaderboard URL, offer to upload old games."""
        url = get_leaderboard_url()
        if not url or MIGRATION_MARKER.exists():
            return

        # Scan for completed games
        completed: list[tuple[Path, dict]] = []
        for fp in sorted(SAVE_DIR.glob("*.json")):
            try:
                with open(fp, "r", encoding="utf-8") as fh:
                    payload = json.load(fh)
                game = payload.get("game", {})
                players = game.get("players", [])
                num_players = len(players)
                if num_players < 2:
                    continue
                total_rounds = 60 // num_players
                if game.get("round_number", 0) == total_rounds:
                    completed.append((fp, payload))
            except Exception:
                continue

        if not completed:
            # Nothing to migrate — mark as done so we don't keep re-scanning.
            MIGRATION_MARKER.parent.mkdir(parents=True, exist_ok=True)
            MIGRATION_MARKER.touch()
            return

        # Only mark migration as done when the user actually goes through with
        # it end-to-end. Skipping the prompt, closing the window, or canceling
        # mid-upload should leave the marker absent so the dialog re-appears
        # next launch.
        dlg = MigrationDialog(self, len(completed))
        if not dlg.exec():
            return

        from leaderboard_client import LeaderboardClient, build_game_submission

        client = LeaderboardClient(url)

        # Ask user to assign groups to each game
        saved_meta = [
            {"name": payload.get("meta", {}).get("name", fp.name), "filepath": str(fp)}
            for fp, payload in completed
        ]
        group_dlg = MigrationGroupDialog(self, saved_meta, client)
        if not group_dlg.exec():
            return

        success_count = 0
        was_canceled = False

        progress = MigrationProgressDialog(self, len(completed))
        progress.show()

        for i, (fp, payload) in enumerate(completed):
            if progress.wasCanceled():
                was_canceled = True
                break
            progress.update_progress(i + 1)
            QtWidgets.QApplication.processEvents()

            assigned_group = group_dlg.group_assignments.get(str(fp))
            group_code = assigned_group["code"] if assigned_group else None

            game_data = payload["game"]
            played_at = payload.get("meta", {}).get("saved_at", datetime.now().isoformat())
            submission = build_game_submission(game_data, played_at=played_at, group_code=group_code)
            if client.submit_game(submission):
                success_count += 1

        progress.close()

        if success_count > 0:
            self._show_status(t("migration_success", n=success_count))

        if was_canceled:
            return

        MIGRATION_MARKER.parent.mkdir(parents=True, exist_ok=True)
        MIGRATION_MARKER.touch()

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

