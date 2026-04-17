# deploy.ps1 - Wizard Leaderboard Backend auf Oracle Cloud VM aktualisieren
#
# Was das Skript macht:
#   1. Sammelt die Backend-Dateien (main.py, database.py, requirements.txt, templates/)
#      und schliesst __pycache__, lokale *.db und das Deploy-Skript selbst aus.
#   2. Laedt sie per scp nach ~/wizard-leaderboard/ auf die VM.
#   3. Installiert/aktualisiert Python-Dependencies in einem venv.
#   4. Startet den systemd-Service wizard-leaderboard neu und enabled ihn
#      (damit er auch nach Reboot laeuft).
#   5. Prueft, ob der Server antwortet.
#
# Voraussetzungen (einmalig):
#   - OpenSSH Client unter Windows (bei Win10/11 standardmaessig dabei).
#   - Ein gueltiger SSH-Key, der auf der VM hinterlegt ist.
#   - Auf der VM muss der Dienst wizard-leaderboard.service bereits existieren.
#
# Benutzung (typisch):
#   .\deploy.ps1 -SshKey "C:\Users\JanCS\.ssh\wizard_oracle.key"
# Oder Einstellungen ueber deploy.config.json (siehe unten).

param(
    [string]$SshKey    = $null,
    [string]$SshUser   = "ubuntu",
    [string]$SshHost   = "158.180.32.188",
    [string]$RemoteDir = "~/wizard-leaderboard",
    [int]   $Port      = 8000,
    [switch]$SkipHealthCheck
)

$ErrorActionPreference = "Stop"
$scriptDir = $PSScriptRoot

# ------------------------------------------------------------------
# Konfig aus deploy.config.json laden, falls vorhanden (nicht versioniert)
# ------------------------------------------------------------------
$configPath = Join-Path $scriptDir "deploy.config.json"
if (Test-Path $configPath) {
    try {
        $cfg = Get-Content $configPath -Raw | ConvertFrom-Json
        if (-not $SshKey -and $cfg.SshKey)       { $SshKey    = $cfg.SshKey }
        if ($cfg.SshUser)                         { if (-not $PSBoundParameters.ContainsKey('SshUser'))   { $SshUser   = $cfg.SshUser   } }
        if ($cfg.SshHost)                         { if (-not $PSBoundParameters.ContainsKey('SshHost'))   { $SshHost   = $cfg.SshHost   } }
        if ($cfg.RemoteDir)                       { if (-not $PSBoundParameters.ContainsKey('RemoteDir')) { $RemoteDir = $cfg.RemoteDir } }
        if ($cfg.Port)                            { if (-not $PSBoundParameters.ContainsKey('Port'))      { $Port      = [int]$cfg.Port } }
    } catch {
        Write-Host "WARN: deploy.config.json konnte nicht gelesen werden: $_" -ForegroundColor Yellow
    }
}

# Fallback-Default fuer den SSH-Key
if (-not $SshKey) {
    $SshKey = Join-Path $env:USERPROFILE ".ssh\wizard_oracle.key"
}

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "    $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "    $msg" -ForegroundColor Red }

Write-Host "=== Wizard Leaderboard Deployment ===" -ForegroundColor Cyan
Write-Host "Ziel:         $SshUser@$SshHost" -ForegroundColor Gray
Write-Host "Remote-Dir:   $RemoteDir"        -ForegroundColor Gray
Write-Host "SSH-Key:      $SshKey"           -ForegroundColor Gray
Write-Host "Quelle:       $scriptDir"        -ForegroundColor Gray

# ------------------------------------------------------------------
# Voraussetzungen pruefen
# ------------------------------------------------------------------
if (-not (Test-Path $SshKey)) {
    Write-Err "SSH-Key nicht gefunden: $SshKey"
    Write-Host ""
    Write-Host "Moegliche Loesungen:" -ForegroundColor Yellow
    Write-Host "  1. Pfad per Parameter uebergeben:  .\deploy.ps1 -SshKey 'C:\Pfad\zum\key'" -ForegroundColor Yellow
    Write-Host "  2. Einstellungen dauerhaft in deploy.config.json hinterlegen (siehe deploy.config.example.json)" -ForegroundColor Yellow
    exit 1
}

foreach ($cmd in @("ssh", "scp")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Err "'$cmd' nicht gefunden. Bitte OpenSSH Client installieren (Einstellungen > Apps > Optionale Features)."
        exit 1
    }
}

# ------------------------------------------------------------------
# 1. Staging: saubere Kopie ohne Cache/DB
# ------------------------------------------------------------------
Write-Step "[1/4] Dateien sammeln (ohne __pycache__, *.db, *.pyc, deploy-*)"

$staging = Join-Path $env:TEMP ("wizard-deploy-" + [guid]::NewGuid().ToString("N").Substring(0,8))
New-Item -ItemType Directory -Path $staging -Force | Out-Null

# Whitelist - nur diese Dateien/Ordner werden hochgeladen
$items = @("main.py", "database.py", "requirements.txt", "templates", "translations.py")
foreach ($item in $items) {
    $src = Join-Path $scriptDir $item
    if (-not (Test-Path $src)) {
        Write-Warn "Uebersprungen (fehlt lokal): $item"
        continue
    }
    Copy-Item -Path $src -Destination $staging -Recurse -Force
}

# __pycache__ defensiv entfernen, falls doch reingerutscht
Get-ChildItem -Path $staging -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-Item $_.FullName -Recurse -Force }
Get-ChildItem -Path $staging -Recurse -File -Include "*.pyc","*.db" -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-Item $_.FullName -Force }

Write-OK "Dateien gestaged in $staging"
Get-ChildItem $staging -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($staging.Length).TrimStart('\','/')
    Write-Host "      $rel" -ForegroundColor DarkGray
}

# ------------------------------------------------------------------
# 2. Upload per scp
# ------------------------------------------------------------------
Write-Step "[2/4] Upload nach $SshHost"

# Remote-Verzeichnis sicherstellen
& ssh -i $SshKey -o StrictHostKeyChecking=accept-new "$SshUser@$SshHost" "mkdir -p $RemoteDir"
if ($LASTEXITCODE -ne 0) {
    Write-Err "ssh-Verbindung fehlgeschlagen."
    Remove-Item $staging -Recurse -Force -ErrorAction SilentlyContinue
    exit 1
}

# Inhalt von $staging (nicht den Ordner selbst) hochladen
Push-Location $staging
try {
    & scp -i $SshKey -o StrictHostKeyChecking=accept-new -r -q `
        "main.py" "database.py" "requirements.txt" "templates" "translations.py" `
        "${SshUser}@${SshHost}:${RemoteDir}/"
    if ($LASTEXITCODE -ne 0) {
        Write-Err "scp-Upload fehlgeschlagen."
        Pop-Location
        Remove-Item $staging -Recurse -Force -ErrorAction SilentlyContinue
        exit 1
    }
    Write-OK "Upload abgeschlossen."
} finally {
    Pop-Location
}

Remove-Item $staging -Recurse -Force -ErrorAction SilentlyContinue

# ------------------------------------------------------------------
# 3. Remote: venv/pip + Service neu starten
# ------------------------------------------------------------------
Write-Step "[3/4] Dependencies installieren und Dienst neu starten"

$remoteScript = @'
set -e
cd ~/wizard-leaderboard

if [ ! -d venv ]; then
    echo "   (kein venv gefunden - erstelle neues)"
    python3 -m venv venv
fi

# shellcheck disable=SC1091
. venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet --upgrade -r requirements.txt

sudo systemctl daemon-reload
sudo systemctl enable  wizard-leaderboard >/dev/null 2>&1 || true
sudo systemctl restart wizard-leaderboard

sleep 2
if sudo systemctl is-active --quiet wizard-leaderboard; then
    echo "   service: ACTIVE"
else
    echo "   service: INACTIVE - siehe: sudo journalctl -u wizard-leaderboard -n 50"
    exit 2
fi
'@

$scriptClean = ($remoteScript -replace "`r`n", "`n").TrimEnd() + "`n"
$b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($scriptClean))
& ssh -i $SshKey -o StrictHostKeyChecking=accept-new "$SshUser@$SshHost" "echo '$b64' | base64 -d | bash"
if ($LASTEXITCODE -ne 0) {
    Write-Err "Remote-Schritt fehlgeschlagen (Exit $LASTEXITCODE)."
    $target = $SshUser + "@" + $SshHost
    Write-Host "   Logs pruefen:" -ForegroundColor Yellow
    Write-Host ("   ssh -i " + $SshKey + " " + $target) -ForegroundColor Yellow
    Write-Host "   und remote: sudo journalctl -u wizard-leaderboard -n 50" -ForegroundColor Yellow
    exit 1
}
Write-OK "Dienst laeuft."

# ------------------------------------------------------------------
# 4. Health-Check
# ------------------------------------------------------------------
if (-not $SkipHealthCheck) {
    Write-Step "[4/4] Health-Check http://${SshHost}:${Port}/api/groups"
    try {
        $resp = Invoke-WebRequest -Uri "http://${SshHost}:${Port}/api/groups" -TimeoutSec 10 -UseBasicParsing
        Write-OK "HTTP $($resp.StatusCode) - Server antwortet."
    } catch {
        Write-Warn "Server nicht erreichbar: $_"
        Write-Warn "Ggf. Firewall / Oracle Security List fuer Port $Port pruefen."
    }
} else {
    Write-Step "[4/4] Health-Check uebersprungen (-SkipHealthCheck)"
}

Write-Host ""
Write-Host "=== Fertig ===" -ForegroundColor Green
Write-Host "URL:        http://${SshHost}:${Port}" -ForegroundColor Cyan
$target = $SshUser + "@" + $SshHost
Write-Host "Logs live:" -ForegroundColor Gray
Write-Host ("   ssh -i " + $SshKey + " " + $target) -ForegroundColor Gray
Write-Host "   und remote: sudo journalctl -u wizard-leaderboard -f" -ForegroundColor Gray
