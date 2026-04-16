# WLED Cube

Animationsserver für einen LED-Würfel aus 6 WLED-Panels (je 480 LEDs, 5×5 Blöcke).  
Der Server läuft auf einem Raspberry Pi, steuert alle 6 Controller via UDP und bietet eine Web-UI zur Steuerung und Vorschau.

---

## Hardware

| Controller | IP              | Seite  |
|------------|-----------------|--------|
| w1.local   | 192.168.10.241  | FRONT  |
| w2.local   | 192.168.10.233  | BACK   |
| w3.local   | 192.168.10.207  | LEFT   |
| w4.local   | 192.168.10.208  | RIGHT  |
| w5.local   | 192.168.10.215  | TOP    |
| w6.local   | 192.168.10.204  | BOTTOM |

- WLED 0.15.3 auf ESP32, max. 32 Segmente pro Controller
- Jedes Panel: 480 LEDs, 5×5 Grid, Snake-Verdrahtung (gerade Reihen l→r, ungerade r→l)
- Protokoll: UDP DRGB (Port 21324), 6 Pakete à 1442 Bytes pro Frame

---

## Schnellstart (lokale Entwicklung)

```bash
pip install -r requirements.txt
uvicorn server.server:app --host 0.0.0.0 --port 8000
```

Web-UI: `http://localhost:8000`

---

## API

| Endpoint                       | Beschreibung                                              |
|--------------------------------|-----------------------------------------------------------|
| `GET  /animations`             | Verfügbare Animationen + PARAMS-Schema                    |
| `GET  /status`                 | Aktueller Status (laufende Animation, preview-Flag, …)    |
| `POST /preview/{name}`         | Animation im Web-Preview starten (kein UDP)               |
| `POST /preview/{name}/params`  | Preview mit Parametern (JSON-Body)                        |
| `POST /animation/{name}`       | Animation auf Hardware starten (UDP)                      |
| `POST /animation/{name}/params`| Hardware mit Parametern (JSON-Body)                       |
| `POST /brightness/{0-255}`     | Helligkeit setzen                                         |
| `POST /stop`                   | Alles aus                                                 |
| `GET  /settings`               | Persistente Einstellungen lesen                           |
| `POST /settings`               | Persistente Einstellungen schreiben                       |
| `WS   /ws`                     | Live-Frames binär (8640 Bytes @ 30 fps)                   |

`/preview/*` → nur WebSocket an Browser, kein UDP.  
`/animation/*` → UDP an alle 6 Controller + WebSocket.

---

## Architektur

```
Animation.tick(cube, dt, t)
  → cube.blocks / cube.leds setzen
  → renderer.render(cube, preview=False)
      → face_buffers (6 × 480 × 3 Bytes)
      → [preview=False] protocol.push_frame() → UDP an 6 Controller
      → return face_buffers
  → _broadcast_frame() → WebSocket an Browser
```

**Kern-Komponenten:**

| Datei                      | Aufgabe                                                              |
|----------------------------|----------------------------------------------------------------------|
| `server/cube.py`           | Virtuelles 3D-Modell. `cube.set(face, row, col, rgb)`, `cube.leds`, `cube.move()` |
| `server/renderer.py`       | Wandelt `cube.blocks`/`cube.leds` in UDP-Buffer, wendet Helligkeit an |
| `server/config.py`         | Hardware-Konstanten: IPs, LED-Map, Segmente                          |
| `server/settings.py`       | Persistenz via `settings.json`                                       |
| `server/server.py`         | FastAPI-App, WebSocket-Broadcast, Animation-Lifecycle                |

---

## Animationen

Verfügbare Animationen:

| Key            | Beschreibung            |
|----------------|-------------------------|
| `snake`        | Snake (blockweise)      |
| `snake_smooth` | Snake (flüssig)         |
| `rainbow`      | Regenbogen-Welle        |
| `checkerboard` | Schachbrett             |
| `water_fill`   | Wasser füllt sich       |
| `emoji_face`   | Emoji-Gesichter         |
| `heart`        | Pulsierendes Herz       |
| `game_of_life` | Conway's Game of Life   |
| `text_scroll`  | Scrollender Text        |
| `rubik_solve`  | Rubik's Cube Lösung     |
| `watercolor`   | Aquarell-Effekt         |
| `clock`        | Uhr                     |
| `tetris`       | Tetris                  |
| `pacman`       | Pac-Man                 |

### Neue Animation erstellen

```python
# server/animations/meine_animation.py
from .base import Animation
from ..cube import Cube

class MeineAnimation(Animation):
    name = "meine"
    PARAMS = {
        "speed": {"type": "float", "default": 1.0, "min": 0.1, "max": 5.0, "step": 0.1, "label": "Geschwindigkeit"},
        "hue":   {"type": "hue",   "default": 0.5, "label": "Farbe"},
    }

    def __init__(self, speed: float = 1.0, hue: float = 0.5):
        self.speed = speed
        self.hue = hue

    def start(self, cube: Cube) -> None:
        cube.fill([0, 0, 0])

    def tick(self, cube: Cube, dt: float, t: float) -> None:
        pass
```

In `server/animations/__init__.py` registrieren:

```python
from .meine_animation import MeineAnimation
REGISTRY["meine"] = MeineAnimation
```

PARAMS-Typen: `"float"`, `"int"`, `"hue"` (0–1, Slider 0–360°), `"str"`.

---

## Web-UI

`web/` — reine HTML/JS/CSS-App, wird vom FastAPI-Server als Static Files ausgeliefert.

- **Sidebar:** Animationen auflisten, per Klick im Preview starten
- **3D-Preview:** Three.js-Würfel empfängt WebSocket-Frames (8640 Bytes = 6 × 480 × 3 RGB)
- **Parameter:** Schieberegler/Eingaben pro Animation, werden in `settings.animation_params` gespeichert und beim nächsten Start mitgeschickt
- **Einstellungen:** Hotkeys konfigurieren, Animationen aktivieren/deaktivieren

---

## Hotkey-Daemon

`scripts/hotkeys.py` — läuft auf dem Raspberry Pi, liest Konfiguration aus `settings.json` (`hotkey_shortcuts`).

Konfigurierbar über Web-UI → Einstellungen → Hotkeys.

Standard-Belegung:

| Taste  | Aktion                  |
|--------|-------------------------|
| F9     | Zufällige Animation     |
| F10    | Alles aus               |
| F11    | Zuletzt aktive Animation|
| F12    | Nächste Animation       |

Zusätzlich können einzelne Animationen direkt auf Tasten gelegt werden.

Der Daemon lädt `settings.json` alle 30 Sekunden neu — Änderungen im Web-UI werden automatisch übernommen.

Manuell starten:

```bash
python scripts/hotkeys.py --server http://localhost:8000
```

Benötigt Zugriff auf `/dev/input` → User muss in Gruppe `input` sein.

---

## Controller-Setup (nach Reset)

Lädt LED-Maps und Segmentkonfiguration auf alle 6 Controller:

```bash
python scripts/setup_all.py
```

---

## Raspberry Pi — Fertiges Image bauen

Das Image enthält ein vollständiges Raspberry Pi OS Lite mit vorinstalliertem Server, Hotkey-Daemon und allen Services. Basis: Debian Trixie (arm64), kein Desktop.

### Voraussetzungen

- Docker (läuft auf macOS und Linux)
- `git`

### Build

```bash
bash image/build.sh
```

Der erste Build dauert ca. 20–40 Minuten (lädt Basis-Image, kompiliert in QEMU-Chroot).  
Folge-Builds sind deutlich schneller, da Docker-Layer gecacht werden.

Output: `image/deploy/wled-cube-*.img.xz` (~300 MB)

### Was der Build macht

1. Klont `pi-gen` (arm64-Branch) nach `image/.pi-gen/` oder aktualisiert es
2. Kopiert das Projekt-Repository in `image/stage-wled/00-install/files/wled/` (ohne `.venv`, `__pycache__`, `.pi-gen`)
3. Kopiert den Stage-Ordner in pi-gen
4. Überspringt stage3–5 (kein Desktop)
5. Baut das Image via `build-docker.sh` (Docker-Container mit QEMU-ARM-Emulation)

Der Stage `stage-wled` macht im Chroot folgendes:
- Pakete installieren: `python3-venv`, `python3-pip`, `libevdev2`, `avahi-daemon`, `rsync`
- Python-Virtualenv unter `/home/pi/wled/.venv` einrichten und Dependencies installieren
- User `pi` zur Gruppe `input` hinzufügen (für Hotkey-Daemon)
- systemd-Services installieren und aktivieren: `wled-server`, `wled-hotkeys`, `wled-setup-controllers`

### Image flashen

**Mit rpi-imager** (empfohlen):
1. "Use custom image" auswählen
2. `image/deploy/wled-cube-*.img.xz` wählen
3. Auf SD-Karte flashen

**Manuell:**
```bash
xz -d image/deploy/wled-cube-*.img.xz
sudo dd if=image/deploy/wled-cube-*.img of=/dev/sdX bs=4M status=progress
```

### Konfiguration

`image/config` — wird vor dem Build in pi-gen kopiert:

| Variable          | Wert              |
|-------------------|-------------------|
| Hostname          | `wled-cube`       |
| User              | `pi`              |
| Passwort          | `wled2024`        |
| WLAN              | in `config` setzen|
| Locale/Timezone   | `de_DE`, Berlin   |
| SSH               | aktiviert         |

**Passwort nach erstem Login ändern.**  
WLAN-Zugangsdaten (`WPA_ESSID`, `WPA_PASSWORD`) in `image/config` anpassen.

### Nach dem ersten Boot

```
Web-UI:  http://wled-cube.local:8000
SSH:     ssh pi@wled-cube.local
```

Beim ersten Start richtet `wled-setup-controllers` automatisch alle 6 WLED-Controller ein (LED-Map + Segmente). Läuft einmalig, danach wird `/var/lib/wled-setup-done` gesetzt.

Logs:
```bash
journalctl -fu wled-server
journalctl -fu wled-hotkeys
journalctl -fu wled-setup-controllers
```

---

## Raspberry Pi — Manuelles Setup (bestehende Installation)

Alternativ zum vorgefertigten Image auf einem laufenden Raspberry Pi OS Lite:

```bash
sudo bash scripts/setup_raspi.sh
```

Das Script ist idempotent und kann mehrfach ausgeführt werden. Es klont/aktualisiert das Repository, richtet das Virtualenv ein, installiert die systemd-Services und aktiviert sie.

Nach dem Setup einen Neustart durchführen, damit die `input`-Gruppe aktiv wird.
