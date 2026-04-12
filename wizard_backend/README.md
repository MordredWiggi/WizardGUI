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

| Methode | Pfad                    | Beschreibung                          |
|---------|------------------------|---------------------------------------|
| POST    | `/api/games`           | Abgeschlossenes Spiel einreichen      |
| GET     | `/api/players/check`   | Spielername pruefen (`?name=Alice`)    |
| GET     | `/api/leaderboard`     | Leaderboard-Daten (`?mode=standard`)  |
| GET     | `/` oder `/leaderboard`| Leaderboard-Webseite                  |
