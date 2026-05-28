# Wizard Leaderboard – Backend

Central leaderboard server for the Wizard Score Tracker.
Runs as a FastAPI app with a SQLite database on an Oracle Cloud VM.

## Local development

```bash
cd wizard_backend
pip install -r requirements.txt

# Start the server (the SQLite file is created locally on first run)
# PowerShell:
$env:WIZARD_DB_PATH = "./leaderboard.db"
python -m uvicorn main:app --reload --port 8000

# Bash/Linux:
WIZARD_DB_PATH=./leaderboard.db uvicorn main:app --reload --port 8000
```

The server then listens at `http://localhost:8000`.

- Leaderboard web page: http://localhost:8000/
- Auto-generated API docs: http://localhost:8000/docs

## Production (Oracle Cloud)

The server runs on an Oracle Cloud Always Free VM (VM.Standard.E2.1.Micro).

- **Public IP:** `158.180.32.188`
- **URL:** `https://play-wizard.de`
- **Database:** `/data/leaderboard.db` (SQLite)
- **systemd service:** `wizard-leaderboard.service`

### Deploying (recommended)

Just run the deploy script from your workstation — it handles staging, the
upload, dependency install, and the service restart in one go:

```powershell
# Windows (double-click works too)
.\deploy.bat
```

Settings (SSH key path, host, etc.) are read from `deploy.config.json`. The
script's whitelist already includes every runtime file (`main.py`,
`database.py`, `elo.py`, `translations.py`, `requirements.txt`, `templates/`,
`ELO_SYSTEM.md`). The production DB at `/data/leaderboard.db` is **never**
touched — the deploy only writes to `~/wizard-leaderboard/` and `*.db` files
are explicitly stripped from the upload staging area. Schema migrations in
`init_db()` are idempotent, so existing data is preserved across restarts.

### SSH access

```bash
ssh -i PATH_TO_KEY ubuntu@158.180.32.188
```

### Common commands

```bash
# Check status
sudo systemctl status wizard-leaderboard

# Tail logs
sudo journalctl -u wizard-leaderboard -f

# Restart the server
sudo systemctl restart wizard-leaderboard
```

## API endpoints

### Games

| Method | Path           | Description                                                                 |
|--------|----------------|-----------------------------------------------------------------------------|
| POST   | `/api/games`   | Submit a finished game (optional: `group_code`). Returns per-player `elo`.  |

### Players

| Method | Path                   | Description                                  |
|--------|------------------------|----------------------------------------------|
| GET    | `/api/players/check`   | Check whether a player name exists (`?name=Alice`) |
| GET    | `/api/leaderboard`     | Global player leaderboard (`?mode=standard`) |

### Groups

| Method | Path                              | Description                                                       |
|--------|-----------------------------------|-------------------------------------------------------------------|
| POST   | `/api/groups`                     | Create a group (name, 4-digit code, visibility)                   |
| GET    | `/api/groups`                     | List public groups (optional: `?search=`)                         |
| GET    | `/api/groups/{code}`              | Get a group by code (works for hidden groups too)                 |
| GET    | `/api/leaderboard/groups`         | Global groups leaderboard (public groups only)                    |
| GET    | `/api/leaderboard/group/{code}`   | Per-group player leaderboard (`?mode=standard`), includes `elo`   |

### Web UI

| Method | Path                    | Description       |
|--------|-------------------------|-------------------|
| GET    | `/` or `/leaderboard`   | Leaderboard page  |

## Database schema

```sql
CREATE TABLE groups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    code        TEXT UNIQUE NOT NULL,   -- exactly 4 digits
    visibility  TEXT NOT NULL DEFAULT 'public'   -- 'public' | 'hidden'
);

CREATE TABLE games (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    game_hash   TEXT UNIQUE NOT NULL,
    game_mode   TEXT NOT NULL DEFAULT 'standard',
    num_players INTEGER NOT NULL,
    played_at   TEXT NOT NULL,
    group_id    INTEGER REFERENCES groups(id)   -- NULL = ungrouped game
);

CREATE TABLE results (
    game_id        INTEGER NOT NULL REFERENCES games(id),
    player_id      INTEGER NOT NULL REFERENCES players(id),
    final_score    INTEGER NOT NULL,
    rank           INTEGER NOT NULL,
    correct_bids   INTEGER NOT NULL,
    total_rounds   INTEGER NOT NULL,
    PRIMARY KEY (game_id, player_id)
);

-- ELO tables (created automatically by init_db)
CREATE TABLE elo_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    params TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL
);

CREATE TABLE player_ratings (
    player_id INTEGER NOT NULL REFERENCES players(id),
    group_id  INTEGER NOT NULL REFERENCES groups(id),
    game_mode TEXT NOT NULL,
    rating REAL NOT NULL,
    games INTEGER NOT NULL DEFAULT 0,
    streak INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (player_id, group_id, game_mode)
);

CREATE TABLE game_elo_deltas (
    game_id INTEGER NOT NULL REFERENCES games(id),
    player_id INTEGER NOT NULL REFERENCES players(id),
    rating_before REAL NOT NULL,
    rating_after  REAL NOT NULL,
    delta REAL NOT NULL,
    PRIMARY KEY (game_id, player_id)
);
```

The schema is migrated idempotently on startup — existing data is preserved.

## ELO system

Every player has an ELO rating per group and game mode (the headline
statistic on the leaderboards). The calculation happens server-side when a
game is submitted; the formula is fully tunable via the Admin Tool's **ELO**
tab.

- **Full documentation of the formula and implementation:** [`ELO_SYSTEM.md`](ELO_SYSTEM.md)
- `POST /api/games` additionally returns `elo` (per-player rating change).
- `GET /api/leaderboard/group/{code}` includes an `elo` field per player.
- New tables: `elo_config`, `player_ratings`, `game_elo_deltas` (migrated
  automatically on startup).

## Group semantics

- **Public groups** appear in the global groups leaderboard and in the search
  list.
- **Hidden groups** can only be reached via their code; they do not appear in
  search.
- Games may optionally be assigned to a group (via `group_code` in the POST
  body).
- Duplicate detection uses a SHA-256 hash — the same game can be re-sent
  multiple times, it is only stored once.
