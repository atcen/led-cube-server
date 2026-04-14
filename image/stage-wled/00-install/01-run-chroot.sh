#!/bin/bash -e
# Läuft im Chroot (ARM-Emulation via QEMU in Docker).

PROJECT_DIR="/home/pi/wled"

# ---- Pakete ----
apt-get update -qq
apt-get install -y --no-install-recommends \
    python3-venv python3-pip python3-dev \
    libevdev2 libevdev-dev libudev1 \
    avahi-daemon avahi-utils \
    rsync
apt-get clean
rm -rf /var/lib/apt/lists/*

# ---- Python-Virtualenv (als User pi) ----
# In pi-gen-chroot kein sudo verfügbar → su benutzen
su -s /bin/bash pi -c "python3 -m venv ${PROJECT_DIR}/.venv"
su -s /bin/bash pi -c "${PROJECT_DIR}/.venv/bin/pip install --quiet --upgrade pip"
su -s /bin/bash pi -c "${PROJECT_DIR}/.venv/bin/pip install --quiet -r ${PROJECT_DIR}/requirements.txt"

# ---- Gruppe input für pynput ----
usermod -aG input pi

# ---- systemd-Services ----
cp "${PROJECT_DIR}/scripts/wled-server.service"  /etc/systemd/system/
cp "${PROJECT_DIR}/scripts/wled-hotkeys.service" /etc/systemd/system/
systemctl enable wled-server
systemctl enable wled-hotkeys
systemctl enable avahi-daemon

# ---- Einmaliger Setup-Service (LED-Maps auf Controller pushen) ----
cat > /etc/systemd/system/wled-setup-controllers.service << 'EOF'
[Unit]
Description=WLED Cube – Controller einmalig einrichten
After=network-online.target wled-server.service
Wants=network-online.target
ConditionPathExists=!/var/lib/wled-setup-done

[Service]
Type=oneshot
User=pi
WorkingDirectory=/home/pi/wled
ExecStart=/home/pi/wled/.venv/bin/python scripts/setup_all.py
ExecStartPost=/usr/bin/touch /var/lib/wled-setup-done
RemainAfterExit=yes
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
systemctl enable wled-setup-controllers
