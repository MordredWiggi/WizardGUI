"""
backup_view.py - Create + manage local backups of the active DB.

Backups are written to ``admin_tool/backups/`` (gitignored). The file name
includes the connection label and a timestamp.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6 import QtCore, QtWidgets

from db_backend import DbBackend
from dialogs import ConfirmDialog, DangerConfirmDialog
from style import ACCENT, TEXT_DIM
from views_base import BaseView, fill_table, make_table, push_button, selected_row_index

BACKUP_DIR = Path(__file__).resolve().parent / "backups"


class BackupView(BaseView):
    def __init__(self, backend: DbBackend) -> None:
        super().__init__(backend)
        self.set_title(
            "Backup",
            "Create and manage backups of the active database.",
        )

        btn_refresh = push_button("⟳", role="toolbar_btn")
        btn_refresh.clicked.connect(self.refresh)
        self.add_toolbar_widget(btn_refresh)

        self.add_toolbar_stretch()

        btn_open = push_button("Open folder", role="toolbar_btn")
        btn_open.clicked.connect(self._open_folder)
        self.add_toolbar_widget(btn_open)

        btn_del = push_button("🗑  Delete", role="danger")
        btn_del.clicked.connect(self._delete_backup)
        self.add_toolbar_widget(btn_del)

        btn_create = push_button("💾  Create backup", role="primary")
        btn_create.clicked.connect(self._create_backup)
        self.add_toolbar_widget(btn_create)

        info = QtWidgets.QLabel(f"Target folder: {BACKUP_DIR}")
        info.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        info.setWordWrap(True)
        self.add_to_body(info)

        self._table = make_table(["File", "Size", "Created"])
        self.add_to_body(self._table, stretch=1)

    def refresh(self) -> None:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        files = sorted(
            (p for p in BACKUP_DIR.iterdir() if p.is_file() and p.suffix == ".db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        rows = [
            {
                "file": p.name,
                "size": _human_bytes(p.stat().st_size),
                "created": datetime.fromtimestamp(p.stat().st_mtime).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            }
            for p in files
        ]
        fill_table(
            self._table,
            rows,
            [("file", "File"), ("size", "Size"), ("created", "Created")],
        )
        self.set_status(f"{len(rows)} backup(s) found.", success=True)

    def _selected_path(self) -> Optional[Path]:
        idx = selected_row_index(self._table)
        if idx is None:
            return None
        item = self._table.item(idx, 0)
        if item is None:
            return None
        return BACKUP_DIR / item.text()

    def _create_backup(self) -> None:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_label = "".join(c if c.isalnum() else "_" for c in self.backend.label)
        dest = BACKUP_DIR / f"{safe_label}_{ts}.db"
        self.set_status(
            "Backup running... (a few seconds for remote DBs)", success=True
        )
        QtWidgets.QApplication.processEvents()
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)
        try:
            ok = self.safe(self.backend.backup_to, dest)
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
        if ok is None:
            return
        size = _human_bytes(dest.stat().st_size) if dest.exists() else "?"
        self.set_status(f"Saved: {dest.name} ({size}).", success=True)
        self.refresh()

    def _delete_backup(self) -> None:
        path = self._selected_path()
        if not path or not path.is_file():
            self.set_status("No backup selected.", success=False)
            return
        dlg = DangerConfirmDialog(
            self,
            title="Delete backup?",
            message=f"Remove file <b>{path.name}</b> from the backups folder?",
            confirm_phrase=path.name,
        )
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        try:
            path.unlink()
        except OSError as exc:
            QtWidgets.QMessageBox.warning(self, "Error", str(exc))
            return
        self.set_status(f"{path.name} deleted.", success=True)
        self.refresh()

    def _open_folder(self) -> None:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        import os
        import subprocess
        import sys

        if sys.platform == "win32":
            os.startfile(str(BACKUP_DIR))
        elif sys.platform == "darwin":
            subprocess.run(["open", str(BACKUP_DIR)], check=False)
        else:
            subprocess.run(["xdg-open", str(BACKUP_DIR)], check=False)


def _human_bytes(n: int) -> str:
    for unit in ("B", "KiB", "MiB", "GiB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if isinstance(n, float) else f"{n} {unit}"
        n = n / 1024
    return f"{n:.1f} TiB"
