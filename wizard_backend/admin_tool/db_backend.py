"""
db_backend.py - Database access for the Admin Tool.

Two backends, one interface:

  - LocalBackend     opens the SQLite file directly via sqlite3
  - RemoteSshBackend pipes SQL into 'ssh user@host sqlite3 <path>'

All methods accept ``?`` placeholders just like sqlite3 itself.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

# -- Common abstraction -------------------------------------------------------


class DbError(RuntimeError):
    """Raised when a backend operation fails."""


class DbBackend(ABC):
    """Common interface used by every view in the admin tool.

    Conventions:
      • All methods that read return ``list[dict]`` (column name -> value).
      • execute() returns the number of affected rows (or -1 if unknown).
      • Implementations must enforce ``PRAGMA foreign_keys=ON`` per connection.
    """

    label: str = "?"

    @abstractmethod
    def query(self, sql: str, params: Iterable[Any] = ()) -> list[dict]:
        ...

    @abstractmethod
    def execute(self, sql: str, params: Iterable[Any] = ()) -> int:
        ...

    @abstractmethod
    def executescript(self, sql: str) -> None:
        ...

    @abstractmethod
    def backup_to(self, dest_path: Path) -> None:
        """Copy the entire database to ``dest_path`` (local file)."""

    @abstractmethod
    def description(self) -> str:
        """Short human-readable description (used in title bar)."""

    def close(self) -> None:
        pass


# -- SQL escaping (used by RemoteSshBackend) ----------------------------------


def _sql_quote(value: Any) -> str:
    """Conservative SQL literal escape for use over SSH.

    We only inline scalars (None, bool, int, float, str). The remote sqlite3
    process parses the resulting statement directly.
    """
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, (bytes, bytearray)):
        return "X'" + bytes(value).hex() + "'"
    text = str(value).replace("'", "''")
    return f"'{text}'"


def _bind(sql: str, params: Iterable[Any]) -> str:
    """Replace each '?' in ``sql`` with a properly quoted literal."""
    parts = sql.split("?")
    params = list(params)
    if len(parts) - 1 != len(params):
        raise DbError(
            f"Parameter count mismatch: {len(parts) - 1} placeholders, "
            f"{len(params)} values"
        )
    out = [parts[0]]
    for i, p in enumerate(params):
        out.append(_sql_quote(p))
        out.append(parts[i + 1])
    return "".join(out)


# -- Local backend ------------------------------------------------------------


class LocalBackend(DbBackend):
    def __init__(self, db_path: str, label: str = "Local DB") -> None:
        self.label = label
        self._db_path = str(Path(db_path).expanduser().resolve())
        if not Path(self._db_path).is_file():
            raise DbError(f"Database file not found: {self._db_path}")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def query(self, sql: str, params: Iterable[Any] = ()) -> list[dict]:
        with self._connect() as conn:
            try:
                rows = conn.execute(sql, tuple(params)).fetchall()
            except sqlite3.Error as exc:
                raise DbError(str(exc)) from exc
        return [dict(r) for r in rows]

    def execute(self, sql: str, params: Iterable[Any] = ()) -> int:
        with self._connect() as conn:
            try:
                cur = conn.execute(sql, tuple(params))
                conn.commit()
                return cur.rowcount
            except sqlite3.Error as exc:
                conn.rollback()
                raise DbError(str(exc)) from exc

    def executescript(self, sql: str) -> None:
        with self._connect() as conn:
            try:
                conn.executescript(sql)
                conn.commit()
            except sqlite3.Error as exc:
                conn.rollback()
                raise DbError(str(exc)) from exc

    def backup_to(self, dest_path: Path) -> None:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as src:
            with sqlite3.connect(str(dest_path)) as dst:
                src.backup(dst)

    def description(self) -> str:
        return f"{self.label}  |  {self._db_path}"


# -- Remote backend (via SSH + sqlite3 CLI) -----------------------------------


class RemoteSshBackend(DbBackend):
    """Executes SQL against a remote SQLite DB via 'ssh ... sqlite3 ...'.

    The remote machine must have the ``sqlite3`` CLI installed (Ubuntu has
    it preinstalled). The connection is authenticated with a private key.
    """

    def __init__(
        self,
        ssh_host: str,
        ssh_user: str,
        ssh_key: str,
        remote_db_path: str,
        label: str = "Remote DB",
        ssh_options: Optional[list[str]] = None,
    ) -> None:
        self.label = label
        self._host = ssh_host
        self._user = ssh_user
        self._key = str(Path(ssh_key).expanduser())
        self._remote = remote_db_path
        self._extra = ssh_options or [
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            "ConnectTimeout=15",
        ]
        if shutil.which("ssh") is None:
            raise DbError(
                "OpenSSH client (ssh) not found. On Windows install it via "
                "Settings > Apps > Optional features."
            )
        if not Path(self._key).is_file():
            raise DbError(f"SSH key not found: {self._key}")
        # Quick reachability ping (optional; fails fast on first action).
        self._sanity_check()

    def _ssh_args(self) -> list[str]:
        return [
            "ssh",
            "-i",
            self._key,
            *self._extra,
            f"{self._user}@{self._host}",
        ]

    def _scp_args(self) -> list[str]:
        return [
            "scp",
            "-i",
            self._key,
            *self._extra,
        ]

    def _sanity_check(self) -> None:
        # `sqlite3 -version` returns instantly when the binary exists.
        cmd = self._ssh_args() + ["sqlite3 -version"]
        try:
            res = subprocess.run(
                cmd, capture_output=True, text=True, timeout=20
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise DbError(f"SSH connection failed: {exc}") from exc
        if res.returncode != 0:
            raise DbError(
                "SSH / sqlite3 sanity check failed.\n"
                f"stderr: {res.stderr.strip()}"
            )

    # -- Execution helpers ------------------------------------------------

    def _run_remote_sql(
        self,
        sql: str,
        *,
        json_mode: bool,
        timeout: int = 60,
    ) -> tuple[str, str]:
        """Pipe ``sql`` into sqlite3 on the remote side. Returns (stdout, stderr)."""
        # Force errors to bubble up via exit code; -bail aborts on first error.
        flags = "-bail "
        if json_mode:
            flags += "-json "
        # sqlite3 needs the file path as the first non-flag argument.
        remote_cmd = (
            f"sqlite3 {flags}{_sh_quote(self._remote)}"
        )
        cmd = self._ssh_args() + [remote_cmd]
        try:
            res = subprocess.run(
                cmd,
                input=sql,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise DbError(f"SSH call failed: {exc}") from exc
        if res.returncode != 0:
            raise DbError(
                f"Remote sqlite3 returned code {res.returncode}.\n"
                f"stderr: {res.stderr.strip()}"
            )
        return res.stdout, res.stderr

    # -- Interface --------------------------------------------------------

    def query(self, sql: str, params: Iterable[Any] = ()) -> list[dict]:
        bound = _bind(sql, params).rstrip().rstrip(";") + ";"
        # Wrap in a transaction so the read is consistent.
        script = "BEGIN;\n" + bound + "\nCOMMIT;\n"
        out, _ = self._run_remote_sql(script, json_mode=True)
        out = out.strip()
        if not out:
            return []
        # sqlite3 -json emits a JSON array per statement, concatenated.
        # Since we run a single SELECT, expect one array.
        try:
            data = json.loads(out)
        except json.JSONDecodeError as exc:
            raise DbError(f"Invalid JSON response: {exc}\n{out[:200]}") from exc
        return data if isinstance(data, list) else [data]

    def execute(self, sql: str, params: Iterable[Any] = ()) -> int:
        bound = _bind(sql, params).rstrip().rstrip(";") + ";"
        # We wrap in a transaction and ask for changes() back.
        script = (
            "BEGIN;\n"
            + bound
            + "\nSELECT changes() AS n;\n"
            + "COMMIT;\n"
        )
        out, _ = self._run_remote_sql(script, json_mode=True)
        out = out.strip()
        if not out:
            return -1
        try:
            data = json.loads(out)
            if isinstance(data, list) and data:
                return int(data[0].get("n", -1))
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
        return -1

    def executescript(self, sql: str) -> None:
        # Run as-is, wrapped in a transaction.
        script = "BEGIN;\n" + sql.strip().rstrip(";") + ";\nCOMMIT;\n"
        self._run_remote_sql(script, json_mode=False)

    def backup_to(self, dest_path: Path) -> None:
        """Use ``scp`` to download the remote DB."""
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = self._scp_args() + [
            f"{self._user}@{self._host}:{self._remote}",
            str(dest_path),
        ]
        try:
            res = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise DbError(f"scp failed: {exc}") from exc
        if res.returncode != 0:
            raise DbError(f"scp code {res.returncode}: {res.stderr.strip()}")

    def description(self) -> str:
        return f"{self.label}  |  {self._user}@{self._host}:{self._remote}"


# -- Helpers ------------------------------------------------------------------


def _sh_quote(value: str) -> str:
    """POSIX shell single-quote (used inside the remote sqlite3 invocation)."""
    return "'" + value.replace("'", "'\\''") + "'"


# -- Factory ------------------------------------------------------------------


def make_backend(name: str, conn_cfg: dict) -> DbBackend:
    """Build the right backend from a connection-config dict.

    Local connections must contain ``db_path``; remote ones must contain
    ``ssh_host``, ``ssh_user``, ``ssh_key``, ``remote_db_path``.
    """
    label = conn_cfg.get("label") or name
    if "ssh_host" in conn_cfg:
        return RemoteSshBackend(
            ssh_host=conn_cfg["ssh_host"],
            ssh_user=conn_cfg.get("ssh_user", "root"),
            ssh_key=conn_cfg["ssh_key"],
            remote_db_path=conn_cfg.get("remote_db_path", "/data/leaderboard.db"),
            label=label,
        )
    db_path = conn_cfg.get("db_path")
    if not db_path:
        raise DbError(
            f"Connection '{name}' has neither db_path nor ssh_host set."
        )
    # Allow paths relative to the admin_tool folder.
    p = Path(db_path)
    if not p.is_absolute():
        p = (Path(__file__).resolve().parent / p).resolve()
    return LocalBackend(str(p), label=label)


# -- Schema introspection helper (used by SQL console & migrations) ----------


def list_tables(backend: DbBackend) -> list[str]:
    rows = backend.query(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
    return [r["name"] for r in rows]


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")
