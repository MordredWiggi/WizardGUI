# Wizard Leaderboard – Backend

Zentraler Leaderboard-Server fuer den Wizard Score Tracker.
Laeuft als FastAPI-App mit SQLite-Datenbank auf einer Oracle Cloud VM.

## Lokale Entwicklung

```bash
cd wizard_backend
pip install -r requirements.txt

# Server starten (SQLite-Datei wird lokal erstellt)
# PowerShell:
$env:WIZARD_DB_PATH = "./leaderboard.db"
python -m uvicorn main:app --reload --port 8000

# Bash/Linux:
WIZARD_DB_PATH=./leaderboard.db uvicorn main:app --reload --port 8000
```

Der Server laeuft dann unter `http://localhost:8000`.

- Leaderboard-Webseite: http://localhost:8000/
- API-Docs (automatisch): http://localhost:8000/docs

## Produktion (Oracle Cloud)

Der Server laeuft auf einer Oracle Cloud Always Free VM (VM.Standard.E2.1.Micro).

- **Oeffentliche IP:** `158.180.32.188`
- **URL:** `http://158.180.32.188:8000`
- **Datenbank:** `/data/leaderboard.db` (SQLite)
- **Systemdienst:** `wizard-leaderboard.service`

### SSH-Zugang

```bash
ssh -i PFAD_ZUM_KEY ubuntu@158.180.32.188
```

### Haeufige Befehle

```bash
# Status pruefen
sudo systemctl status wizard-leaderboard

# Logs anzeigen
sudo journalctl -u wizard-leaderboard -f

# Server neustarten
sudo systemctl restart wizard-leaderboard
```

### Code updaten

```bash
# Dateien per SCP hochladen
scp -i PFAD_ZUM_KEY -r wizard_backend/* ubuntu@158.180.32.188:~/wizard-leaderboard/

# Dann auf der VM:
sudo systemctl restart wizard-leaderboard
```

## API-Endpunkte

### Spiele

| Methode | Pfad           | Beschreibung                                              |
|---------|----------------|-----------------------------------------------------------|
| POST    | `/api/games`   | Abgeschlossenes Spiel einreichen (optional: `group_code`) |

### Spieler

| Methode | Pfad                   | Beschreibung                         |
|---------|------------------------|--------------------------------------|
| GET     | `/api/players/check`   | Spielername pruefen (`?name=Alice`)  |
| GET     | `/api/leaderboard`     | Spieler-Leaderboard (`?mode=standard`) |

### Gruppen

| Methode | Pfad                           | Beschreibung                                              |
|---------|--------------------------------|-----------------------------------------------------------|
| POST    | `/api/groups`                  | Neue Gruppe erstellen (Name, 4-stelliger Code, Sichtbarkeit) |
| GET     | `/api/groups`                  | Oeffentliche Gruppen auflisten (optional: `?search=`) |
| GET     | `/api/groups/{code}`           | Gruppe per Code abrufen (auch versteckte Gruppen) |
| GET     | `/api/leaderboard/groups`      | Globales Gruppen-Leaderboard (nur oeffentliche Gruppen) |
| GET     | `/api/leaderboard/group/{code}`| Spieler-Leaderboard fuer eine Gruppe (`?mode=standard`) |

### Web-Oberflaeche

| Methode | Pfad                    | Beschreibung          |
|---------|-------------------------|-----------------------|
| GET     | `/` oder `/leaderboard` | Leaderboard-Webseite  |

## Datenbankschema

```sql
CREATE TABLE groups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    code        TEXT UNIQUE NOT NULL,  -- genau 4 Ziffern
    visibility  TEXT NOT NULL DEFAULT 'public'  -- 'public' | 'hidden'
);

CREATE TABLE games (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    game_hash   TEXT UNIQUE NOT NULL,
    game_mode   TEXT NOT NULL DEFAULT 'standard',
    num_players INTEGER NOT NULL,
    played_at   TEXT NOT NULL,
    group_id    INTEGER REFERENCES groups(id)  -- NULL = kein Gruppenspiel
);

CREATE TABLE player_results (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id        INTEGER NOT NULL REFERENCES games(id),
    name           TEXT NOT NULL,
    final_score    INTEGER NOT NULL,
    correct_bids   INTEGER NOT NULL DEFAULT 0,
    total_rounds   INTEGER NOT NULL DEFAULT 0,
    rank           INTEGER NOT NULL DEFAULT 1
);
```

Das Schema wird automatisch beim Start migriert — bestehende Daten gehen nicht verloren.

## Gruppen-Logik

- **Oeffentliche Gruppen** erscheinen im globalen Gruppen-Leaderboard und in der Suchlistge.
- **Versteckte Gruppen** sind nur per Code erreichbar; sie tauchen nicht in der Suche auf.
- Spiele koennen optional einer Gruppe zugeordnet werden (ueber `group_code` im POST-Body).
- Duplikat-Erkennung laeuft ueber SHA-256-Hash — dasselbe Spiel kann mehrfach gesendet werden, wird aber nur einmal gespeichert.
