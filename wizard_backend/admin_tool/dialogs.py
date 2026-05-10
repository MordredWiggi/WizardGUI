"""
dialogs.py - Shared dialogs for the admin tool.

Includes:
  - ConfirmDialog            generic confirmation with detail box
  - DangerConfirmDialog      destructive confirmation with required typed phrase
  - TextInputDialog          single text field (e.g. rename)
  - GroupEditDialog          create / edit a group
  - GameEditDialog           edit a game's metadata
  - ResultEditDialog         edit a single per-player result
  - PlayerMergeDialog        merge two players
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
# PlayerMergeDialog - merge two players
# ---------------------------------------------------------------------------


class PlayerMergeDialog(_Themed):
    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget],
        players: list[dict],
        source_player: dict,
    ) -> None:
        super().__init__(parent)
        self._source = source_player
        self.setWindowTitle("Merge players")
        self.setMinimumWidth(440)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(12)

        layout.addWidget(_header("Merge players", color=ADMIN_RED))
        layout.addWidget(_sep())

        info = QtWidgets.QLabel(
            f"All results of <b>{source_player['name']}</b> "
            f"(id={source_player['id']}) will be reassigned to the target "
            f"player. <b>{source_player['name']}</b> will then be deleted."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addWidget(self._field_label("Target player"))
        self._combo = QtWidgets.QComboBox()
        for p in players:
            if p["id"] == source_player["id"]:
                continue
            self._combo.addItem(f"{p['name']}  (id={p['id']})", p["id"])
        layout.addWidget(self._combo)

        layout.addWidget(_sep())
        row = QtWidgets.QHBoxLayout()
        row.addStretch()
        btn_cancel = QtWidgets.QPushButton("Cancel")
        btn_ok = QtWidgets.QPushButton("Merge")
        btn_ok.setObjectName("danger")
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self.accept)
        row.addWidget(btn_cancel)
        row.addWidget(btn_ok)
        layout.addLayout(row)

    def _field_label(self, text: str) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(text)
        lbl.setStyleSheet(f"font-size: 11px; color: {TEXT_DIM}; font-weight: 600;")
        return lbl

    @property
    def target_id(self) -> Optional[int]:
        return self._combo.currentData()
