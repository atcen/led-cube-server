#!/bin/bash -e
# Wird im Build-Environment ausgeführt (nicht im Chroot).
# Kopiert das Projekt (aus files/wled/) in das Image-Rootfs.
# Läuft im CWD des Sub-Stage-Verzeichnisses → relative Pfade funktionieren.

install -d -m 755 -o 1000 -g 1000 "${ROOTFS_DIR}/home/pi/wled"

rsync -a "files/wled/" "${ROOTFS_DIR}/home/pi/wled/"

chown -R 1000:1000 "${ROOTFS_DIR}/home/pi/wled"
