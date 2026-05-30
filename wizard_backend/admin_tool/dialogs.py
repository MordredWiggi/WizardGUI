"""
dialogs.py - Shared dialogs for the admin tool.

Includes:
  - ConfirmDialog               generic confirmation with detail box
  - DangerConfirmDialog         destructive confirmation with required typed phrase
  - TextInputDialog             single text field (e.g. rename)
  - GroupEditDialog             create / edit a group
  - GameEditDialog              edit a game's metadata
  - ResultEditDialog            edit a single per-player result
  - GroupPlayerRenameDialog     rename a player inside a single group
  - GroupPlayerMergeDialog      merge two players inside a single group
  - PlayerEloHistoryDialog      per-player ELO timeline within one group
"""

from __future__ import annotations

from typing import Optional

from PyQt6 import QtCore, QtGui, QtWidgets

from style import (
    ACCENT,
    ADMIN_RED,
    DANGER,
    SUCCESS,
    TEXT_DIM,
    TEXT_MAIN,
    apply_titlebar_theme,
)


class _Themed(QtWidgets.QDialog):
    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        apply_titlebar_theme(self)


def _sep() -> QtWidgets.QFrame:
    line = QtWidgets.QFrame()
    line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    return line


def _header(text: str, color: str = ACCENT) -> QtWidgets.QLabel:
    lbl = QtWidgets.QLabel(text)
    lbl.setStyleSheet(
        f"font-size: 17px; font-weight: 700; color: {color}; background: transparent;"
    )
    return lbl


# ---------------------------------------------------------------------------
# ConfirmDialog
# ---------------------------------------------------------------------------


class ConfirmDialog(_Themed):
    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget],
        title: str,
        message: str,
        detail: str = "",
        ok_text: str = "OK",
        ok_role: str = "primary",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(420)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(14)

        layout.addWidget(_header(title))
        layout.addWidget(_sep())

        msg = QtWidgets.QLabel(message)
        msg.setWordWrap(True)
        msg.setStyleSheet(f"font-size: 13px; color: {TEXT_MAIN};")
        layout.addWidget(msg)

        if detail:
            box = QtWidgets.QPlainTextEdit()
            box.setPlainText(detail)
            box.setReadOnly(True)
            box.setMaximumHeight(150)
            layout.addWidget(box)

        layout.addWidget(_sep())

        row = QtWidgets.QHBoxLayout()
        row.addStretch()
        btn_cancel = QtWidgets.QPushButton("Cancel")
        btn_ok = QtWidgets.QPushButton(ok_text)
        btn_ok.setObjectName(ok_role)
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self.accept)
        row.addWidget(btn_cancel)
        row.addWidget(btn_ok)
        layout.addLayout(row)


# ---------------------------------------------------------------------------
# DangerConfirmDialog
# ---------------------------------------------------------------------------


class DangerConfirmDialog(_Themed):
    """Forces the user to type a confirmation phrase before destructive ops."""

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget],
        title: str,
        message: str,
        confirm_phrase: str = "DELETE",
        detail: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(460)
        self._phrase = confirm_phrase

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(12)

        layout.addWidget(_header(f"⚠  {title}", color=ADMIN_RED))
        layout.addWidget(_sep())

        msg = QtWidgets.QLabel(message)
        msg.setWordWrap(True)
        msg.setStyleSheet(f"font-size: 13px; color: {TEXT_MAIN};")
        layout.addWidget(msg)

        if detail:
            box = QtWidgets.QPlainTextEdit()
            box.setPlainText(detail)
            box.setReadOnly(True)
            box.setMaximumHeight(140)
            layout.addWidget(box)

        prompt = QtWidgets.QLabel(
            f"Type <b>{confirm_phrase}</b> to confirm:"
        )
        prompt.setStyleSheet(f"font-size: 12px; color: {TEXT_DIM};")
        layout.addWidget(prompt)

        self._edit = QtWidgets.QLineEdit()
        self._edit.textChanged.connect(self._on_changed)
        layout.addWidget(self._edit)

        layout.addWidget(_sep())
        row = QtWidgets.QHBoxLayout()
        row.addStretch()
        btn_cancel = QtWidgets.QPushButton("Cancel")
        self._btn_ok = QtWidgets.QPushButton("Delete")
        self._btn_ok.setObjectName("danger")
        self._btn_ok.setEnabled(False)
        btn_cancel.clicked.connect(self.reject)
        self._btn_ok.clicked.connect(self.accept)
        row.addWidget(btn_cancel)
        row.addWidget(self._btn_ok)
        layout.addLayout(row)

    def _on_changed(self, text: str) -> None:
        self._btn_ok.setEnabled(text.strip() == self._phrase)


# ---------------------------------------------------------------------------
# TextInputDialog
# ---------------------------------------------------------------------------


class TextInputDialog(_Themed):
    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget],
        title: str,
        label: str,
        default: str = "",
        placeholder: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(380)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(12)

        layout.addWidget(_header(title))
        layout.addWidget(_sep())

        lbl = QtWidgets.QLabel(label)
        lbl.setStyleSheet(f"font-size: 12px; color: {TEXT_DIM};")
        layout.addWidget(lbl)

        self._edit = QtWidgets.QLineEdit(default)
        self._edit.setPlaceholderText(placeholder)
        self._edit.setMinimumHeight(34)
        layout.addWidget(self._edit)

        layout.addWidget(_sep())
        row = QtWidgets.QHBoxLayout()
        row.addStretch()
        btn_cancel = QtWidgets.QPushButton("Cancel")
        btn_ok = QtWidgets.QPushButton("OK")
        btn_ok.setObjectName("primary")
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self.accept)
        row.addWidget(btn_cancel)
        row.addWidget(btn_ok)
        layout.addLayout(row)

        self._edit.setFocus()
        self._edit.selectAll()

    @property
    def value(self) -> str:
        return self._edit.text().strip()


# ---------------------------------------------------------------------------
# GroupEditDialog
# ---------------------------------------------------------------------------


class GroupEditDialog(_Themed):
    """Create or edit a group."""

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget],
        group: Optional[dict] = None,
    ) -> None:
        super().__init__(parent)
        self._group = group or {}
        is_edit = bool(group)
        self.setWindowTitle("Edit group" if is_edit else "Create group")
        self.setMinimumWidth(420)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(12)

        layout.addWidget(_header(self.windowTitle()))
        layout.addWidget(_sep())

        # Name
        layout.addWidget(self._field_label("Name"))
        self._name_edit = QtWidgets.QLineEdit(self._group.get("name", ""))
        self._name_edit.setMinimumHeight(32)
        layout.addWidget(self._name_edit)

        # Code (exactly 4 digits)
        layout.addWidget(self._field_label("4-digit code"))
        self._code_edit = QtWidgets.QLineEdit(self._group.get("code", ""))
        self._code_edit.setMaxLength(4)
        self._code_edit.setMaximumWidth(120)
        self._code_edit.setMinimumHeight(32)
        validator = QtGui.QRegularExpressionValidator(
            QtCore.QRegularExpression(r"\d{0,4}")
        )
        self._code_edit.setValidator(validator)
        layout.addWidget(self._code_edit)

        # Visibility
        layout.addWidget(self._field_label("Visibility"))
        vis_row = QtWidgets.QHBoxLayout()
        self._radio_public = QtWidgets.QRadioButton("public")
        self._radio_hidden = QtWidgets.QRadioButton("hidden")
        if (self._group.get("visibility") or "public") == "hidden":
            self._radio_hidden.setChecked(True)
        else:
            self._radio_public.setChecked(True)
        vis_row.addWidget(self._radio_public)
        vis_row.addWidget(self._radio_hidden)
        vis_row.addStretch()
        layout.addLayout(vis_row)

        self._status = QtWidgets.QLabel(" ")
        self._status.setStyleSheet(f"color: {DANGER}; font-size: 12px;")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        layout.addWidget(_sep())
        row = QtWidgets.QHBoxLayout()
        row.addStretch()
        btn_cancel = QtWidgets.QPushButton("Cancel")
        btn_ok = QtWidgets.QPushButton("Save" if is_edit else "Create")
        btn_ok.setObjectName("primary")
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self._on_ok)
        row.addWidget(btn_cancel)
        row.addWidget(btn_ok)
        layout.addLayout(row)

    def _field_label(self, text: str) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(text)
        lbl.setStyleSheet(f"font-size: 11px; color: {TEXT_DIM}; font-weight: 600;")
        return lbl

    def _on_ok(self) -> None:
        name = self._name_edit.text().strip()
        code = self._code_edit.text().strip()
        if not name:
            self._status.setText("Name must not be empty.")
            return
        if len(code) != 4 or not code.isdigit():
            self._status.setText("Code must be exactly 4 digits.")
            return
        self.accept()

    @property
    def values(self) -> dict:
        return {
            "name": self._name_edit.text().strip(),
            "code": self._code_edit.text().strip(),
            "visibility": "hidden" if self._radio_hidden.isChecked() else "public",
        }


# ---------------------------------------------------------------------------
# GameEditDialog
# ---------------------------------------------------------------------------


class GameEditDialog(_Themed):
    """Edit a game's metadata (or create a new game row)."""

    GAME_MODES = ["standard", "multiplicative"]

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget],
        game: Optional[dict] = None,
        groups: Optional[list[dict]] = None,
    ) -> None:
        super().__init__(parent)
        self._game = game or {}
        self._groups = groups or []
        is_edit = bool(game and game.get("id"))
        self.setWindowTitle("Edit game" if is_edit else "Create game")
        self.setMinimumWidth(460)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(10)

        layout.addWidget(_header(self.windowTitle()))
        layout.addWidget(_sep())

        # Hash
        layout.addWidget(self._field_label("game_hash (unique)"))
        self._hash_edit = QtWidgets.QLineEdit(self._game.get("game_hash", ""))
        if is_edit:
            self._hash_edit.setReadOnly(True)
            self._hash_edit.setStyleSheet("color: #888aaa;")
        layout.addWidget(self._hash_edit)

        # Game mode
        layout.addWidget(self._field_label("Game mode"))
        self._mode_combo = QtWidgets.QComboBox()
        self._mode_combo.addItems(self.GAME_MODES)
        cur_mode = self._game.get("game_mode", "standard")
        if cur_mode not in self.GAME_MODES:
            self._mode_combo.addItem(cur_mode)
        self._mode_combo.setCurrentText(cur_mode)
        layout.addWidget(self._mode_combo)

        # Number of players
        layout.addWidget(self._field_label("Number of players"))
        self._np_spin = QtWidgets.QSpinBox()
        self._np_spin.setRange(2, 12)
        self._np_spin.setValue(int(self._game.get("num_players", 4)))
        layout.addWidget(self._np_spin)

        # Played at
        layout.addWidget(self._field_label("played_at (ISO-8601, e.g. 2026-05-10T18:30:00)"))
        self._when_edit = QtWidgets.QLineEdit(self._game.get("played_at", ""))
        layout.addWidget(self._when_edit)

        # Group
        layout.addWidget(self._field_label("Group"))
        self._group_combo = QtWidgets.QComboBox()
        self._group_combo.addItem("(no group)", None)
        cur_gid = self._game.get("group_id")
        cur_idx = 0
        for i, g in enumerate(self._groups, 1):
            self._group_combo.addItem(
                f"{g['name']}  ({g.get('code', '----')})", g["id"]
            )
            if cur_gid == g["id"]:
                cur_idx = i
        self._group_combo.setCurrentIndex(cur_idx)
        layout.addWidget(self._group_combo)

        self._status = QtWidgets.QLabel(" ")
        self._status.setStyleSheet(f"color: {DANGER}; font-size: 12px;")
        layout.addWidget(self._status)

        layout.addWidget(_sep())
        row = QtWidgets.QHBoxLayout()
        row.addStretch()
        btn_cancel = QtWidgets.QPushButton("Cancel")
        btn_ok = QtWidgets.QPushButton("Save" if is_edit else "Create")
        btn_ok.setObjectName("primary")
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self._on_ok)
        row.addWidget(btn_cancel)
        row.addWidget(btn_ok)
        layout.addLayout(row)

    def _field_label(self, text: str) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(text)
        lbl.setStyleSheet(f"font-size: 11px; color: {TEXT_DIM}; font-weight: 600;")
        return lbl

    def _on_ok(self) -> None:
        if not self._hash_edit.text().strip():
            self._status.setText("game_hash must not be empty.")
            return
        if not self._when_edit.text().strip():
            self._status.setText("played_at must not be empty.")
            return
        self.accept()

    @property
    def values(self) -> dict:
        return {
            "game_hash": self._hash_edit.text().strip(),
            "game_mode": self._mode_combo.currentText(),
            "num_players": int(self._np_spin.value()),
            "played_at": self._when_edit.text().strip(),
            "group_id": self._group_combo.currentData(),
        }


# ---------------------------------------------------------------------------
# ResultEditDialog - a single row in the results table
# ---------------------------------------------------------------------------


class ResultEditDialog(_Themed):
    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget],
        result: Optional[dict] = None,
        players: Optional[list[dict]] = None,
        lock_player: bool = False,
    ) -> None:
        super().__init__(parent)
        self._result = result or {}
        self._players = players or []
        is_edit = bool(result and "player_id" in result)
        self.setWindowTitle(
            "Edit result" if is_edit else "Add result"
        )
        self.setMinimumWidth(440)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(10)

        layout.addWidget(_header(self.windowTitle()))
        layout.addWidget(_sep())

        # Player
        layout.addWidget(self._field_label("Player"))
        if lock_player and is_edit:
            self._player_lbl = QtWidgets.QLabel(self._result.get("name", ""))
            self._player_lbl.setStyleSheet(
                f"font-weight: 700; color: {ACCENT}; font-size: 14px;"
            )
            layout.addWidget(self._player_lbl)
            self._player_combo = None
            self._new_player_edit = None
        else:
            self._player_combo = QtWidgets.QComboBox()
            self._player_combo.addItem("(new player below)", None)
            cur_pid = self._result.get("player_id")
            cur_idx = 0
            for i, p in enumerate(self._players, 1):
                self._player_combo.addItem(p["name"], p["id"])
                if cur_pid == p["id"]:
                    cur_idx = i
            self._player_combo.setCurrentIndex(cur_idx)
            layout.addWidget(self._player_combo)

            layout.addWidget(self._field_label("or new player name"))
            self._new_player_edit = QtWidgets.QLineEdit()
            layout.addWidget(self._new_player_edit)

        # Numeric fields
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        self._final_score = QtWidgets.QSpinBox()
        self._final_score.setRange(-100000, 100000)
        self._final_score.setValue(int(self._result.get("final_score", 0)))

        self._rank = QtWidgets.QSpinBox()
        self._rank.setRange(1, 12)
        self._rank.setValue(int(self._result.get("rank", 1)))

        self._correct = QtWidgets.QSpinBox()
        self._correct.setRange(0, 200)
        self._correct.setValue(int(self._result.get("correct_bids", 0)))

        self._rounds = QtWidgets.QSpinBox()
        self._rounds.setRange(1, 200)
        self._rounds.setValue(int(self._result.get("total_rounds", 10)))

        for r, (lbl, w) in enumerate(
            [
                ("final_score", self._final_score),
                ("rank", self._rank),
                ("correct_bids", self._correct),
                ("total_rounds", self._rounds),
            ]
        ):
            grid.addWidget(self._field_label(lbl), r, 0)
            grid.addWidget(w, r, 1)
        layout.addLayout(grid)

        self._status = QtWidgets.QLabel(" ")
        self._status.setStyleSheet(f"color: {DANGER}; font-size: 12px;")
        layout.addWidget(self._status)

        layout.addWidget(_sep())
        row = QtWidgets.QHBoxLayout()
        row.addStretch()
        btn_cancel = QtWidgets.QPushButton("Cancel")
        btn_ok = QtWidgets.QPushButton("Save")
        btn_ok.setObjectName("primary")
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self._on_ok)
        row.addWidget(btn_cancel)
        row.addWidget(btn_ok)
        layout.addLayout(row)

    def _field_label(self, text: str) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(text)
        lbl.setStyleSheet(f"font-size: 11px; color: {TEXT_DIM}; font-weight: 600;")
        return lbl

    def _on_ok(self) -> None:
        if self._player_combo is not None:
            pid = self._player_combo.currentData()
            new_name = (self._new_player_edit.text() or "").strip()
            if pid is None and not new_name:
                self._status.setText(
                    "Please pick an existing player or enter a new name."
                )
                return
        self.accept()

    @property
    def values(self) -> dict:
        out = {
            "final_score": int(self._final_score.value()),
            "rank": int(self._rank.value()),
            "correct_bids": int(self._correct.value()),
            "total_rounds": int(self._rounds.value()),
        }
        if self._player_combo is None:
            out["player_id"] = self._result.get("player_id")
        else:
            pid = self._player_combo.currentData()
            new_name = (self._new_player_edit.text() or "").strip()
            if pid is not None:
                out["player_id"] = pid
            else:
                out["player_id"] = None
                out["new_player_name"] = new_name
        return out


# ---------------------------------------------------------------------------
# GroupPlayerRenameDialog - rename a player but only inside one group
# ---------------------------------------------------------------------------


class GroupPlayerRenameDialog(_Themed):
    """Pick a player who has results in this group and choose a new name.

    The rename is scoped to the current group: only the results belonging to
    games of this group will move to the new identity. Results of the same
    player in other groups are left untouched.
    """

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget],
        group: dict,
        players_in_group: list[dict],
        preselect_id: Optional[int] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Rename player in group")
        self.setMinimumWidth(460)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(12)

        layout.addWidget(_header("Rename player in group"))
        layout.addWidget(_sep())

        info = QtWidgets.QLabel(
            f"Renames apply only to games of <b>{group['name']}</b>. "
            "Results in other groups are not affected."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"font-size: 12px; color: {TEXT_DIM};")
        layout.addWidget(info)

        layout.addWidget(self._field_label("Player"))
        self._combo = QtWidgets.QComboBox()
        cur_idx = 0
        for i, p in enumerate(players_in_group):
            self._combo.addItem(
                f"{p['name']}  (id={p['id']}, {p.get('games', 0)} games)",
                p["id"],
            )
            if preselect_id is not None and p["id"] == preselect_id:
                cur_idx = i
        if players_in_group:
            self._combo.setCurrentIndex(cur_idx)
        self._combo.currentIndexChanged.connect(self._on_player_changed)
        layout.addWidget(self._combo)

        layout.addWidget(self._field_label("New name"))
        self._edit = QtWidgets.QLineEdit()
        self._edit.setMinimumHeight(32)
        layout.addWidget(self._edit)

        self._status = QtWidgets.QLabel(" ")
        self._status.setStyleSheet(f"color: {DANGER}; font-size: 12px;")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        layout.addWidget(_sep())
        row = QtWidgets.QHBoxLayout()
        row.addStretch()
        btn_cancel = QtWidgets.QPushButton("Cancel")
        btn_ok = QtWidgets.QPushButton("Rename")
        btn_ok.setObjectName("primary")
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self._on_ok)
        row.addWidget(btn_cancel)
        row.addWidget(btn_ok)
        layout.addLayout(row)

        self._players = players_in_group
        self._on_player_changed(self._combo.currentIndex())
        self._edit.setFocus()
        self._edit.selectAll()

    def _field_label(self, text: str) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(text)
        lbl.setStyleSheet(f"font-size: 11px; color: {TEXT_DIM}; font-weight: 600;")
        return lbl

    def _on_player_changed(self, idx: int) -> None:
        if 0 <= idx < len(self._players):
            self._edit.setText(self._players[idx]["name"])
            self._edit.selectAll()

    def _on_ok(self) -> None:
        pid = self._combo.currentData()
        if pid is None:
            self._status.setText("No player selected.")
            return
        new_name = self._edit.text().strip()
        if not new_name:
            self._status.setText("New name must not be empty.")
            return
        self.accept()

    @property
    def player_id(self) -> Optional[int]:
        return self._combo.currentData()

    @property
    def new_name(self) -> str:
        return self._edit.text().strip()


# ---------------------------------------------------------------------------
# GroupPlayerMergeDialog - merge two players but only inside one group
# ---------------------------------------------------------------------------


class GroupPlayerMergeDialog(_Themed):
    """Pick two players, choose an arbitrary new name for the survivor.

    The merge is scoped to the current group: only this group's results are
    consolidated onto the survivor. If either source player has results in
    other groups, those rows stay where they are.
    """

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget],
        group: dict,
        players_in_group: list[dict],
        preselect_a_id: Optional[int] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Merge players in group")
        self.setMinimumWidth(480)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(12)

        layout.addWidget(_header("Merge players in group", color=ADMIN_RED))
        layout.addWidget(_sep())

        info = QtWidgets.QLabel(
            f"Both players' results in <b>{group['name']}</b> will move "
            "onto the chosen target name. Results in other groups are not "
            "affected. If both players have a result for the same game, the "
            "first player's row wins."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"font-size: 12px; color: {TEXT_DIM};")
        layout.addWidget(info)

        self._players = players_in_group

        layout.addWidget(self._field_label("Player A"))
        self._combo_a = QtWidgets.QComboBox()
        layout.addWidget(self._combo_a)

        layout.addWidget(self._field_label("Player B"))
        self._combo_b = QtWidgets.QComboBox()
        layout.addWidget(self._combo_b)

        a_idx = 0
        for i, p in enumerate(players_in_group):
            label = f"{p['name']}  (id={p['id']}, {p.get('games', 0)} games)"
            self._combo_a.addItem(label, p["id"])
            self._combo_b.addItem(label, p["id"])
            if preselect_a_id is not None and p["id"] == preselect_a_id:
                a_idx = i
        if players_in_group:
            self._combo_a.setCurrentIndex(a_idx)
        # Default B to a different player than A whenever possible.
        if len(players_in_group) >= 2:
            self._combo_b.setCurrentIndex(0 if a_idx != 0 else 1)
        self._combo_a.currentIndexChanged.connect(self._on_a_changed)

        layout.addWidget(self._field_label("New name (the merged player's name)"))
        self._edit = QtWidgets.QLineEdit()
        self._edit.setMinimumHeight(32)
        layout.addWidget(self._edit)

        self._status = QtWidgets.QLabel(" ")
        self._status.setStyleSheet(f"color: {DANGER}; font-size: 12px;")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        layout.addWidget(_sep())
        row = QtWidgets.QHBoxLayout()
        row.addStretch()
        btn_cancel = QtWidgets.QPushButton("Cancel")
        btn_ok = QtWidgets.QPushButton("Merge")
        btn_ok.setObjectName("danger")
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self._on_ok)
        row.addWidget(btn_cancel)
        row.addWidget(btn_ok)
        layout.addLayout(row)

        self._on_a_changed(self._combo_a.currentIndex())
        self._edit.setFocus()
        self._edit.selectAll()

    def _field_label(self, text: str) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(text)
        lbl.setStyleSheet(f"font-size: 11px; color: {TEXT_DIM}; font-weight: 600;")
        return lbl

    def _on_a_changed(self, idx: int) -> None:
        if 0 <= idx < len(self._players):
            self._edit.setText(self._players[idx]["name"])
            self._edit.selectAll()

    def _on_ok(self) -> None:
        a = self._combo_a.currentData()
        b = self._combo_b.currentData()
        if a is None or b is None:
            self._status.setText("Pick two players to merge.")
            return
        if a == b:
            self._status.setText("Player A and Player B must differ.")
            return
        if not self._edit.text().strip():
            self._status.setText("New name must not be empty.")
            return
        self.accept()

    @property
    def player_a_id(self) -> Optional[int]:
        return self._combo_a.currentData()

    @property
    def player_b_id(self) -> Optional[int]:
        return self._combo_b.currentData()

    @property
    def new_name(self) -> str:
        return self._edit.text().strip()


# ---------------------------------------------------------------------------
# PlayerEloHistoryDialog
# ---------------------------------------------------------------------------


class PlayerEloHistoryDialog(_Themed):
    """A timeline of one player's ELO inside one group.

    Layout: a Standard/Multiplicative mode toggle on top, then a table with
    one row per game in that pool, newest first, with each game's rank,
    rating before, signed delta, and rating after. The current rating in
    that mode is shown in the header for quick comparison.
    """

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget],
        *,
        backend,
        player: dict,
        group: dict,
        initial_mode: str = "standard",
    ) -> None:
        super().__init__(parent)
        self._backend = backend
        self._player = player
        self._group = group
        self._mode = initial_mode
        self.setWindowTitle("ELO history")
        self.setMinimumSize(640, 480)
        self.resize(720, 540)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(10)

        layout.addWidget(_header(player.get("name", "?")))
        self._subtitle = QtWidgets.QLabel("")
        self._subtitle.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 12px; background: transparent;"
        )
        layout.addWidget(self._subtitle)
        layout.addWidget(_sep())

        # Mode toggle
        mode_row = QtWidgets.QHBoxLayout()
        mode_row.setSpacing(6)
        self._btn_standard = QtWidgets.QPushButton("Standard")
        self._btn_multi = QtWidgets.QPushButton("Multiplicative")
        for btn in (self._btn_standard, self._btn_multi):
            btn.setCheckable(True)
            btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self._btn_standard.clicked.connect(lambda: self._set_mode("standard"))
        self._btn_multi.clicked.connect(lambda: self._set_mode("multiplicative"))
        mode_row.addWidget(self._btn_standard)
        mode_row.addWidget(self._btn_multi)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        # Table
        self._table = QtWidgets.QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["Played at", "Game ID", "Rank", "ELO before", "ELO progress"]
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setAlternatingRowColors(True)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Interactive
        )
        # We deliberately keep sorting OFF — the timeline is meant to be in
        # reverse-chronological order (newest first), which is the order the
        # SQL already gives us.
        self._table.setSortingEnabled(False)
        layout.addWidget(self._table, 1)

        self._status = QtWidgets.QLabel("")
        self._status.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 12px; background: transparent;"
        )
        layout.addWidget(self._status)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        btn_close = QtWidgets.QPushButton("Close")
        btn_close.setObjectName("primary")
        btn_close.setMinimumWidth(100)
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        self._apply_mode_style()
        self._reload()

    # ── Mode handling ──────────────────────────────────────────────────────

    def _set_mode(self, mode: str) -> None:
        if mode == self._mode:
            return
        self._mode = mode
        self._apply_mode_style()
        self._reload()

    def _apply_mode_style(self) -> None:
        for btn, mode in (
            (self._btn_standard, "standard"),
            (self._btn_multi, "multiplicative"),
        ):
            active = self._mode == mode
            btn.setChecked(active)
            if active:
                btn.setStyleSheet(
                    f"QPushButton {{ background: {ACCENT}; color: #1a1a2e; "
                    f"font-weight: 700; border: 1px solid {ACCENT}; "
                    f"border-radius: 5px; padding: 6px 16px; }}"
                )
            else:
                btn.setStyleSheet(
                    f"QPushButton {{ background: transparent; color: {TEXT_DIM}; "
                    f"border: 1px solid #3a3a6a; border-radius: 5px; "
                    f"padding: 6px 16px; }}"
                    f"QPushButton:hover {{ color: {TEXT_MAIN}; border-color: {ACCENT}; }}"
                )

    # ── Data loading ───────────────────────────────────────────────────────

    def _reload(self) -> None:
        try:
            current = self._backend.query(
                """
                SELECT CAST(ROUND(rating) AS INTEGER) AS rating,
                       games, streak
                  FROM player_ratings
                 WHERE player_id = ? AND group_id = ? AND game_mode = ?
                """,
                (self._player["id"], self._group["id"], self._mode),
            )
            rows = self._backend.query(
                """
                SELECT g.id          AS game_id,
                       g.played_at,
                       r.rank,
                       d.rating_before,
                       d.delta,
                       d.rating_after
                  FROM game_elo_deltas d
                  JOIN games   g ON g.id = d.game_id
                  JOIN results r ON r.game_id = d.game_id
                               AND r.player_id = d.player_id
                 WHERE d.player_id = ?
                   AND g.group_id  = ?
                   AND g.game_mode = ?
              ORDER BY g.played_at DESC, g.id DESC
                """,
                (self._player["id"], self._group["id"], self._mode),
            )
        except Exception as exc:  # pragma: no cover - surfaced to UI
            self._status.setText(f"Error: {exc}")
            self._render([])
            self._subtitle.setText(
                f"Group {self._group.get('name', '?')}  ·  Mode: {self._mode}"
            )
            return

        rating = current[0]["rating"] if current else None
        games = current[0]["games"] if current else 0
        streak = current[0]["streak"] if current else 0
        self._render(rows)
        self._subtitle.setText(
            f"Group {self._group['name']} (code {self._group['code']})  ·  "
            f"Mode: {self._mode}  ·  "
            f"Current ELO: {rating if rating is not None else '—'}  ·  "
            f"Games: {games}  ·  Streak: {streak}"
        )
        if not rows:
            self._status.setText(
                "No rated games yet for this player in this mode."
            )
        else:
            self._status.setText(f"{len(rows)} rated game(s).")

    def _render(self, rows: list[dict]) -> None:
        self._table.setRowCount(len(rows))
        for r_idx, row in enumerate(rows):
            played_at = str(row.get("played_at") or "")
            game_id = row.get("game_id")
            rank = row.get("rank")
            before = row.get("rating_before")
            after = row.get("rating_after")
            delta = row.get("delta")

            # Pre-formatted, signed delta string ("+12" / "−8") with colour.
            if delta is None:
                delta_text = "—"
                delta_color = TEXT_DIM
            else:
                rounded = round(float(delta))
                delta_text = (
                    f"+{rounded}" if rounded >= 0 else f"−{abs(rounded)}"
                )
                delta_color = SUCCESS if rounded >= 0 else DANGER

            def cell(text: str, color: Optional[str] = None, right: bool = False):
                item = QtWidgets.QTableWidgetItem(text)
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                if color:
                    item.setForeground(QtGui.QColor(color))
                if right:
                    item.setTextAlignment(
                        QtCore.Qt.AlignmentFlag.AlignRight
                        | QtCore.Qt.AlignmentFlag.AlignVCenter
                    )
                return item

            self._table.setItem(r_idx, 0, cell(played_at))
            self._table.setItem(
                r_idx, 1, cell(str(game_id) if game_id is not None else "", right=True)
            )
            self._table.setItem(
                r_idx, 2, cell(str(rank) if rank is not None else "", right=True)
            )
            self._table.setItem(
                r_idx,
                3,
                cell(
                    str(round(float(before))) if before is not None else "—",
                    right=True,
                ),
            )
            progress = (
                f"{round(float(before)) if before is not None else '?'}  →  "
                f"{round(float(after)) if after is not None else '?'}   {delta_text}"
            )
            self._table.setItem(r_idx, 4, cell(progress, color=delta_color))
        self._table.resizeColumnsToContents()
