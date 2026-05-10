# Wizard DB Admin Tool

Internal developer tool for managing the Wizard leaderboard database.
Pure PyQt6 desktop app, **Windows only**, styled to match the player app
(`wizard_desktop`).

> ⚠ **Do not ship to player machines.** Changes are written **directly** to
> the SQLite database, locally or via SSH on the production server.

---

## 1. Requirements

- Python 3.10+ (tested with 3.13)
- Windows 10 / 11
- For remote access: OpenSSH client + `sqlite3` installed on the VM

```powershell
cd wizard_backend\admin_tool
pip install -r requirements.txt
```

## 2. First-time setup

Run the setup script once. It writes `admin_config.json` (gitignored).

```powershell
python setup_admin.py
```

It asks for:
1. **Developer password** (PBKDF2-HMAC-SHA256, hash + salt are stored in
   `admin_config.json`, which is excluded by `.gitignore`).
2. **Local DB connection** (default: `wizard_backend/leaderboard.db`).
3. **Remote DB via SSH** (optional, prefilled with the Oracle Cloud IP).

You can re-run later for partial updates:

```powershell
python setup_admin.py --password   # only change the password
python setup_admin.py --ssh        # only add/update an SSH connection
```

## 3. Launch

```powershell
python main.py
# or just
run.bat
```

On launch:
1. Login dialog (password + connection picker)
2. Connection sanity check (for SSH this runs `sqlite3 -version` over SSH)
3. Main window opens

## 4. Features

| Section     | What you can do                                                                   |
|-------------|------------------------------------------------------------------------------------|
| Dashboard   | Counts + top-10 groups + top-15 players                                            |
| Groups      | Create, edit, **cascade-delete**, search, double-click -> open games               |
| Games       | Per group: create, edit, move to another group, delete                             |
| Results     | Per game: per-player results (score / rank / bids / rounds) - add, edit, delete    |
| Players     | Rename, **merge** (reassign all results to a target player), delete                |
| Feedback    | Edit message, reset votes, delete                                                  |
| SQL Console | Run any SQL; write mode must be enabled and confirmed                              |
| Backup      | One-click DB snapshot to `admin_tool/backups/` (local file or via scp)             |

### Safety mechanisms

- **Login**: PBKDF2-HMAC-SHA256, 600,000 iterations, max. 3 failed attempts.
- **Delete dialogs** require typing a confirmation phrase (group code,
  player name, ...) so misclicks cannot delete data.
- **SQL Console** rejects mutating statements while read-only mode is on.
- **Remote backend** pipes SQL into `sqlite3 -bail` over SSH - no DB
  download, no race condition with the running FastAPI process.
- **admin_config.json** and `backups/` are gitignored.

## 5. File layout

```
admin_tool/
|-- main.py                 # entry point
|-- setup_admin.py          # password + connection setup
|-- auth.py                 # PBKDF2 + config IO
|-- db_backend.py           # local + remote SSH backend
|-- login_dialog.py
|-- main_window.py          # sidebar + stack
|-- views_base.py           # shared widgets
|-- dashboard_view.py
|-- groups_view.py
|-- games_view.py
|-- players_view.py
|-- feedback_view.py
|-- sql_console.py
|-- backup_view.py
|-- dialogs.py              # CRUD dialogs + confirmations
|-- style.py
|-- requirements.txt
|-- run.bat / setup.bat
+-- admin_config.example.json
```

## 6. Troubleshooting

**Launch shows "Setup required"**
-> Run `python setup_admin.py`.

**"SSH connection failed"**
-> Verify from PowerShell:
   `ssh -i <key-path> ubuntu@158.180.32.188 "sqlite3 -version"`.
   If that fails, the key path is wrong or the VM is unreachable.

**"sqlite3: command not found" (on the VM)**
-> Ubuntu: `sudo apt-get install -y sqlite3`.

**Wrong password 3 times**
-> Tool exits. If you forgot the password just rerun
   `python setup_admin.py --password` - you only need local file access,
   not the old hash.
