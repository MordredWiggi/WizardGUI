# Wizard DB Admin Tool

Internal developer tool for managing the Wizard leaderboard database.
Pure PyQt6 desktop app, **Windows only**, styled to match the player app
(`wizard_desktop`).

> ⚠ **Do not ship to player machines.** Changes are written **directly** to
> the SQLite database, locally or via SSH on the production server.

---

## Two kinds of config

The tool keeps password and connection details in **two separate files**:

| File                  | Where it lives                | What it contains                                | Status     |
|-----------------------|-------------------------------|-------------------------------------------------|------------|
| `admin_password.json` | This folder, **committed**    | PBKDF2 hash of the shared developer password    | shared     |
| `admin_config.json`   | This folder, **gitignored**   | Per-developer connections (SSH key path, etc.)  | per-machine |

The shared password is the same for every developer. Only the maintainer
sets it (see below). Per-machine details (SSH key paths) stay on each
developer's box.

---

## 1. Requirements

- Python 3.10+
- Windows 10 / 11
- For remote access: OpenSSH client + `sqlite3` installed on the VM

```powershell
cd wizard_backend\admin_tool
pip install -r requirements.txt
```

---

## 2. Maintainer one-time tasks

### Set / rotate the shared password

```powershell
python set_shared_password.py
```

Then commit and push the resulting `admin_password.json`:

```powershell
git add admin_password.json
git commit -m "Update shared admin password"
git push
```

Distribute the plaintext password to your developers **out-of-band**
(Signal, password manager, in person — never in chat or email).

### Install sqlite3 on the production VM (one-off)

If the remote SSH connection fails with `sqlite3: command not found`:

```powershell
python setup_admin.py --install-sqlite3
```

This SSHs into the configured VM and runs
`sudo apt-get install -y sqlite3`. You can also do it manually:

```bash
ssh -i <key> ubuntu@158.180.32.188
sudo apt-get update && sudo apt-get install -y sqlite3
```

---

## 3. Each developer's setup

```powershell
git pull                    # picks up admin_password.json
cd wizard_backend\admin_tool
pip install -r requirements.txt
python setup_admin.py       # configure local + SSH connections
```

`setup_admin.py` asks for:
1. A **local DB connection** (default: `wizard_backend/leaderboard.db`).
2. A **remote DB via SSH** (default host = your Oracle Cloud VM, you fill
   in the path to *your* SSH private key).
3. Which connection should be preselected at startup.

The result is written to `admin_config.json` (gitignored).

---

## 4. Launch

```powershell
run.bat                     # silent: launches pythonw, no console window
run_debug.bat               # debug: visible console, shows Python errors
```

Or from a shell:

```powershell
pythonw main.py             # silent
python main.py              # with console (for debugging)
```

In the login dialog: pick a connection, type the shared password, hit Enter.

---

## 5. Features

| Section     | What you can do                                                                |
|-------------|--------------------------------------------------------------------------------|
| Dashboard   | Counts + top-10 groups + top-15 players                                        |
| Groups      | Create, edit, **cascade-delete**, search, double-click -> open games           |
| Games       | Per group: create, edit, move to another group, delete                         |
| Results     | Per game: per-player results (score / rank / bids / rounds) - add, edit, delete |
| Players     | Rename, **merge** (reassign all results), delete                               |
| Feedback    | Edit message, reset votes, delete                                              |
| SQL Console | Run any SQL; write mode must be enabled and confirmed                          |
| Backup      | One-click DB snapshot to `admin_tool/backups/` (local file or via scp)         |

### Safety mechanisms

- **Login**: PBKDF2-HMAC-SHA256, 600,000 iterations, max. 3 failed attempts.
- **Delete dialogs** require typing a confirmation phrase (group code, player
  name, ...) so misclicks cannot delete data.
- **SQL Console** rejects mutating statements while read-only mode is on.
- **Remote backend** pipes SQL into `sqlite3 -bail` over SSH - no DB
  download, no race condition with the running FastAPI process.
- **No console flash**: child processes (ssh, scp) are launched with
  `CREATE_NO_WINDOW` on Windows.

---

## 6. File layout

```
admin_tool/
|-- main.py                     # entry point
|-- setup_admin.py              # per-developer connection setup
|-- set_shared_password.py      # MAINTAINER: update shared password
|-- auth.py                     # PBKDF2 + config IO
|-- db_backend.py               # local + remote SSH backend
|-- login_dialog.py
|-- main_window.py              # sidebar + stack
|-- views_base.py               # shared widgets
|-- dashboard_view.py
|-- groups_view.py
|-- games_view.py
|-- players_view.py
|-- feedback_view.py
|-- sql_console.py
|-- backup_view.py
|-- dialogs.py                  # CRUD dialogs + confirmations
|-- style.py
|-- requirements.txt
|-- run.bat                     # launch silently (pythonw)
|-- run_debug.bat               # launch with visible console
|-- setup.bat / set_password.bat
|-- admin_password.json         # COMMITTED: shared hash
+-- admin_config.example.json   # template only
```

---

## 7. Troubleshooting

**Login dialog says "Shared password missing"**
-> Run `git pull` to receive `admin_password.json`. If you ARE the
   maintainer and never set one, run `python set_shared_password.py`.

**Login dialog says "Wrong password"**
-> The maintainer rotated the password; ask for the current one. (After
   3 wrong attempts the tool exits.)

**"sqlite3 is NOT installed on the remote VM"**
-> Run `python setup_admin.py --install-sqlite3` (uses sudo on the VM)
   or do it yourself: `sudo apt-get install -y sqlite3`.

**"SSH connection failed" / "SSH key not found"**
-> Verify the key path in `admin_config.json` matches a real file on
   your machine. Test from PowerShell:
   `ssh -i <key> ubuntu@158.180.32.188 "echo ok"`.

**Console window stays open behind the GUI**
-> You launched via `python main.py` instead of `run.bat`. Use
   `run.bat` (which uses `pythonw`) for the silent launch.
