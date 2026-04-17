# setup_domain.ps1 - Automates Nginx, Firewall, and SSL setup on Oracle Cloud VM
#
# Was das Skript macht:
#   1. Loggt sich via SSH in die Oracle VM ein.
#   2. Oeffnet die lokalen Firewall-Ports (80 & 443).
#   3. Installiert Nginx und Certbot.
#   4. Schreibt eine Nginx Reverse-Proxy Konfiguration fuer Port 8000.
#   5. Fuehrt Certbot aus, um ein kostenloses Let's Encrypt SSL-Zertifikat zu holen.
#
# Voraussetzungen:
#   - Die DNS-Eintraege muessen bereits auf die IP ($SshHost) zeigen!
#   - In der Oracle Cloud Konsole (VCN) muessen Port 80 & 443 freigegeben sein.
#   - OpenSSH Client unter Windows.

param(
    [string]$Domain    = "wizardapp.net",
    [string]$Email     = "admin@wizardapp.net",
    [string]$SshKey    = $null,
    [string]$SshUser   = "ubuntu",
    [string]$SshHost   = "158.180.32.188"
)

$ErrorActionPreference = "Stop"
$scriptDir = $PSScriptRoot

# ------------------------------------------------------------------
# Konfig aus deploy.config.json laden (teilt sich Config mit deploy.ps1)
# ------------------------------------------------------------------
$configPath = Join-Path $scriptDir "deploy.config.json"
if (Test-Path $configPath) {
    try {
        $cfg = Get-Content $configPath -Raw | ConvertFrom-Json
        if (-not $SshKey -and $cfg.SshKey)       { $SshKey    = $cfg.SshKey }
        if ($cfg.SshUser)                         { if (-not $PSBoundParameters.ContainsKey('SshUser'))   { $SshUser   = $cfg.SshUser   } }
        if ($cfg.SshHost)                         { if (-not $PSBoundParameters.ContainsKey('SshHost'))   { $SshHost   = $cfg.SshHost   } }
        if ($cfg.Domain)                          { if (-not $PSBoundParameters.ContainsKey('Domain'))    { $Domain    = $cfg.Domain    } }
        if ($cfg.Email)                           { if (-not $PSBoundParameters.ContainsKey('Email'))     { $Email     = $cfg.Email     } }
    } catch {
        Write-Host "WARN: deploy.config.json konnte nicht gelesen werden: $_" -ForegroundColor Yellow
    }
}

if (-not $SshKey) {
    $SshKey = Join-Path $env:USERPROFILE ".ssh\wizard_oracle.key"
}

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "    $msg" -ForegroundColor Green }
function Write-Err($msg)  { Write-Host "    $msg" -ForegroundColor Red }

Write-Host "=== Wizard Custom Domain Setup ===" -ForegroundColor Cyan
Write-Host "Domain:       $Domain"           -ForegroundColor Yellow
Write-Host "Zertifikats-EMail: $Email"       -ForegroundColor Gray
Write-Host "Ziel:         $SshUser@$SshHost" -ForegroundColor Gray
Write-Host "SSH-Key:      $SshKey"           -ForegroundColor Gray

if (-not (Test-Path $SshKey)) {
    Write-Err "SSH-Key nicht gefunden: $SshKey"
    exit 1
}

# ------------------------------------------------------------------
# Remote-Skript generieren und via SSH ausfuehren
# ------------------------------------------------------------------
Write-Step "Sende Konfigurations-Skript an den Server..."

$remoteScript = @"
set -e

DOMAIN="$Domain"
EMAIL="$Email"

echo "   [1/4] Konfiguriere lokale VM Firewall (iptables & ufw)..."
sudo iptables -I INPUT -p tcp -m state --state NEW -m tcp --dport 80 -j ACCEPT || true
sudo iptables -I INPUT -p tcp -m state --state NEW -m tcp --dport 443 -j ACCEPT || true
sudo netfilter-persistent save || true
sudo ufw allow 80/tcp >/dev/null 2>&1 || true
sudo ufw allow 443/tcp >/dev/null 2>&1 || true

echo "   [2/4] Installiere Nginx und Certbot..."
sudo apt-get update -y -qq
sudo apt-get install -y -qq nginx python3-certbot-nginx

echo "   [3/4] Erstelle Nginx Reverse-Proxy Konfiguration fuer $DOMAIN..."
cat << 'EOF' | sudo tee /etc/nginx/sites-available/$DOMAIN >/dev/null
server {
    listen 80;
    server_name DOMAIN www.DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host `$host;
        proxy_set_header X-Real-IP `$remote_addr;
        proxy_set_header X-Forwarded-For `$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto `$scheme;
    }
}
EOF

sudo sed -i "s/DOMAIN/\$DOMAIN/g" /etc/nginx/sites-available/$DOMAIN

sudo ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl restart nginx

echo "   [4/4] Beantrage SSL Zertifikat via Certbot..."
echo "   (HINWEIS: Dies funktioniert nur, wenn die DNS-Eintraege fuer $DOMAIN bereits auf diese VM zeigen!)"
sudo certbot --nginx -d \$DOMAIN -d www.\$DOMAIN --non-interactive --agree-tos -m \$EMAIL --redirect || {
    echo "FEHLER beim Certbot-Durchlauf. Pruefen Sie die DNS-Einstellungen."
    exit 1
}

echo "   ==> Setup erfolgreich abgeschlossen! <=="
"@

$scriptClean = ($remoteScript -replace "`r`n", "`n").TrimEnd() + "`n"
$b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($scriptClean))

& ssh -i $SshKey -o StrictHostKeyChecking=accept-new "$SshUser@$SshHost" "echo '$b64' | base64 -d | bash"

if ($LASTEXITCODE -ne 0) {
    Write-Err "Domain-Setup fehlgeschlagen. Ueberpruefen Sie die Konsolenausgabe."
    exit 1
}

Write-OK "Nginx und SSL Zertifikate wurden erfolgreich konfiguriert."
Write-Host "`nURL: https://$Domain" -ForegroundColor Green
Write-Host "Vergessen Sie nicht, in der Oracle Cloud Konsole (VCN Security Lists) Port 80 und 443 freizugeben!" -ForegroundColor Yellow
