#!/usr/bin/env bash
# WLED Cube – Setup-Script für Raspberry Pi OS Lite (Bookworm, 64-bit)
# Idempotent: kann mehrfach ausgeführt werden.
#
# Verwendung (als root oder mit sudo):
#   curl -sSL https://raw.githubusercontent.com/atcen/led-cube-server/main/scripts/setup_raspi.sh | sudo bash
# oder nach manuellem Klonen:
#   sudo bash scripts/setup_raspi.sh

set -euo pipefail

PROJECT_DIR="/home/pi/wled"
REPO_URL="https://github.com/atcen/led-cube-server.git"
BRANCH="main"
SERVICE_USER="pi"

log()  { echo -e "\033[1;32m▶  $*\033[0m"; }
warn() { echo -e "\033[1;33m⚠  $*\033[0m"; }

# ---- System-Pakete ----
log "Pakete aktualisieren…"
apt-get update -qq
apt-get install -y --no-install-recommends \
    git python3-venv python3-pip \
    libevdev2 libudev1 \
    avahi-daemon avahi-utils \
    2>/dev/null

# ---- Projekt klonen / aktualisieren ----
if [ -d "$PROJECT_DIR/.git" ]; then
    log "Projekt aktualisieren ($PROJECT_DIR)…"
    sudo -u "$SERVICE_USER" git -C "$PROJECT_DIR" pull --ff-only
else
    log "Projekt klonen nach $PROJECT_DIR…"
    sudo -u "$SERVICE_USER" git clone --branch "$BRANCH" "$REPO_URL" "$PROJECT_DIR"
fi

# ---- Python-Virtualenv ----
log "Virtualenv einrichten…"
sudo -u "$SERVICE_USER" python3 -m venv "$PROJECT_DIR/.venv"
sudo -u "$SERVICE_USER" "$PROJECT_DIR/.venv/bin/pip" install --quiet --upgrade pip
sudo -u "$SERVICE_USER" "$PROJECT_DIR/.venv/bin/pip" install --quiet -r "$PROJECT_DIR/requirements.txt"

# ---- input-Gruppe für pynput (kein X11 nötig) ----
log "User '$SERVICE_USER' zur Gruppe 'input' hinzufügen…"
usermod -aG input "$SERVICE_USER"

# ---- systemd-Services installieren ----
log "Services installieren…"
cp "$PROJECT_DIR/scripts/wled-server.service"  /etc/systemd/system/
cp "$PROJECT_DIR/scripts/wled-hotkeys.service" /etc/systemd/system/

systemctl daemon-reload
systemctl enable --now wled-server
systemctl enable --now wled-hotkeys

# ---- Avahi / mDNS sicherstellen ----
systemctl enable --now avahi-daemon 2>/dev/null || true

# ---- Abschluss ----
log "Setup abgeschlossen."
echo ""
echo "  Server:  http://$(hostname).local:8000"
echo "  Logs:    journalctl -fu wled-server"
echo "           journalctl -fu wled-hotkeys"
echo ""
warn "Neustart empfohlen damit Gruppenmitgliedschaft (input) aktiv wird."
