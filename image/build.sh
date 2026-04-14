#!/usr/bin/env bash
# WLED Cube – Custom Raspberry Pi Image bauen
#
# Voraussetzung: Docker läuft (funktioniert auf macOS + Linux)
#
# Verwendung:
#   bash image/build.sh
#
# Output: image/deploy/wled-cube-*.img.xz  (~300 MB)
# Flashen: xz -d wled-cube-*.img.xz && dd ...
#          oder: rpi-imager → "Use custom image"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PIGEN_DIR="${SCRIPT_DIR}/.pi-gen"
DEPLOY_DIR="${SCRIPT_DIR}/deploy"

log()  { echo -e "\033[1;32m▶  $*\033[0m"; }
error(){ echo -e "\033[1;31m✗  $*\033[0m"; exit 1; }

# ---- Voraussetzungen prüfen ----
command -v docker >/dev/null || error "Docker nicht gefunden. Bitte installieren: https://docs.docker.com/get-docker/"
command -v git    >/dev/null || error "git nicht gefunden."

# ---- pi-gen holen / aktualisieren ----
if [ -d "${PIGEN_DIR}/.git" ]; then
    log "pi-gen aktualisieren…"
    git -C "${PIGEN_DIR}" pull --ff-only -q
else
    log "pi-gen klonen…"
    git clone --depth 1 https://github.com/RPi-Distro/pi-gen.git "${PIGEN_DIR}"
fi

# ---- Projektdateien in Stage-files/ kopieren ----
# (pi-gen führt Skripte aus seinem eigenen Verzeichnis aus — relative Pfade
#  zum Repo funktionieren dort nicht; Dateien müssen im stage-Ordner liegen)
log "Projektdateien in Stage kopieren…"
STAGE_FILES="${SCRIPT_DIR}/stage-wled/00-install/files/wled"
rm -rf "${STAGE_FILES}"
rsync -a \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='image/.pi-gen' \
    --exclude='image/deploy' \
    --exclude='debug_screenshots' \
    "${REPO_ROOT}/" \
    "${STAGE_FILES}/"

# ---- Eigenen Stage verlinken ----
log "Stage vorbereiten…"
ln -sfn "${SCRIPT_DIR}/stage-wled" "${PIGEN_DIR}/stage-wled"
cp "${SCRIPT_DIR}/config" "${PIGEN_DIR}/config"

# stage3–5 überspringen (kein Desktop)
for s in stage3 stage4 stage5; do
    touch "${PIGEN_DIR}/${s}/SKIP" 2>/dev/null || true
    touch "${PIGEN_DIR}/${s}/SKIP_IMAGES" 2>/dev/null || true
done

# ---- Bauen ----
log "Image bauen (Docker, dauert ~20–40 Min beim ersten Mal)…"
cd "${PIGEN_DIR}"
PRESERVE_CONTAINER=0 ./build-docker.sh

# ---- Ergebnis ----
mkdir -p "${DEPLOY_DIR}"
BUILT=$(ls -t "${PIGEN_DIR}/deploy/"*.img.xz 2>/dev/null | head -1)
if [ -z "$BUILT" ]; then
    error "Kein Image gefunden. Build-Output prüfen."
fi

cp "$BUILT" "${DEPLOY_DIR}/"
OUTFILE="${DEPLOY_DIR}/$(basename "$BUILT")"

log "Fertig: ${OUTFILE}"
echo ""
echo "  Flashen mit rpi-imager: 'Use custom image' → Datei wählen"
echo "  oder:"
echo "    xz -d '${OUTFILE}'"
echo "    sudo dd if='${OUTFILE%.xz}' of=/dev/sdX bs=4M status=progress"
echo ""
echo "  Nach dem ersten Boot erreichbar unter:"
echo "    http://wled-cube.local:8000"
echo "    SSH: ssh pi@wled-cube.local  (Passwort: wled2024)"
