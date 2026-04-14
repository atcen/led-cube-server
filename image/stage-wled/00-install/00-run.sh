#!/bin/bash -e
# Wird im Build-Environment ausgeführt (nicht im Chroot).
# Kopiert das Projekt (aus files/wled/) in das Image-Rootfs.
# FILES_DIR ist eine pi-gen-Variable: zeigt auf diesen stage/files/-Ordner.

install -d -m 755 -o 1000 -g 1000 "${ROOTFS_DIR}/home/pi/wled"

rsync -a "${FILES_DIR}/wled/" "${ROOTFS_DIR}/home/pi/wled/"

chown -R 1000:1000 "${ROOTFS_DIR}/home/pi/wled"
