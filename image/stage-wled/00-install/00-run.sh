#!/bin/bash -e
# Wird im Build-Environment ausgeführt (nicht im Chroot).
# Kopiert das Projekt in das Image-Rootfs.

ROOTFS="${ROOTFS_DIR}"
PROJECT_SRC="$(cd "$(dirname "$0")/../../.." && pwd)"   # Repo-Root

install -d -m 755 -o 1000 -g 1000 "${ROOTFS}/home/pi/wled"

# Projektdateien ins Image kopieren (ohne .git, .venv, __pycache__)
rsync -a --delete \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='debug_screenshots' \
    --exclude='image' \
    "${PROJECT_SRC}/" \
    "${ROOTFS}/home/pi/wled/"

chown -R 1000:1000 "${ROOTFS}/home/pi/wled"
