# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Netzwerk

6 WLED-Controller im lokalen Netz (192.168.10.x), erreichbar über mDNS oder direkt per IP:

| Name | IP | Würfelseite |
|---|---|---|
| w1.local | 192.168.10.241 | FRONT |
| w2.local | 192.168.10.233 | BACK |
| w3.local | 192.168.10.207 | LEFT |
| w4.local | 192.168.10.208 | RIGHT |
| w5.local | 192.168.10.215 | TOP |
| w6.local | 192.168.10.204 | BOTTOM |

WLED-Version: 0.15.3, ESP32, max. 32 Segmente pro Controller.

## Panel-Layout

Jedes Panel: 5×5 Grid aus Blöcken, 480 LEDs gesamt.

- Strip schlängelt sich durch **3 physische Reihen = 1 Grid-Zeile**
- LEDs pro Block je physischer Reihe: **6, 7, 6, 7, 6** (alternierend)
- Snake-Richtung: gerade Reihen links→rechts, ungerade rechts→links
- Blöcke liegen nicht-kontiguierlich im physischen Strip → `ledmap.json` auf jedem Controller

## Server starten

```bash
pip install -r requirements.txt
uvicorn server.server:app --host 0.0.0.0 --port 8000
```

Web UI: `http://localhost:8000` (statische Dateien aus `web/` werden direkt unter `/` gemountet)

## API

| Endpoint | Beschreibung |
|---|---|
| `POST /preview/{name}` | Animation in Web-Preview starten (kein UDP) |
| `POST /preview/{name}/params` | Preview mit Parametern (JSON body) |
| `POST /animation/{name}` | Animation auf Hardware starten (UDP) |
| `POST /animation/{name}/params` | Hardware mit Parametern |
| `GET /animations` | Verfügbare Animationen + PARAMS-Schema |
| `GET /status` | Aktueller Status inkl. `preview`-Flag |
| `POST /brightness/{0-255}` | Helligkeit |
| `POST /stop` | Alles aus |
| `GET /settings` / `POST /settings` | Persistente Einstellungen |
| `WS /ws` | Live-Frames binary (8640 Bytes @ 30 fps) |

**Preview vs. Hardware:** `/preview/*` führt die Animation aus und sendet sie ans Web UI (WebSocket), aber **kein UDP** an die Controller. `/animation/*` sendet UDP. Der Hotkey-Daemon verwendet immer `/animation/*`.

## Architektur

### Datenfluss

```
Animation.tick(cube, dt, t)
  → cube.blocks / cube.leds setzen
  → renderer.render(cube, preview=False)
      → face_buffers berechnen (6 × 480 × 3 Bytes)
      → [preview=False] protocol.push_frame() → UDP an 6 Controller
      → return face_buffers
  → _broadcast_frame() → WebSocket an Browser
```

### Kern-Komponenten

**`server/cube.py`** — Virtuelles 3D-Modell. `cube.set(face, row, col, [r,g,b])` setzt Blöcke (5×5 Grid). `cube.leds[(face, vled)]` für per-LED-Override (smooth-Animationen). `move(face, row, col, dir)` navigiert über Würfelkanten hinweg — die Topologie (TRANSITIONS) ist hier definiert.

**`server/renderer.py`** — Wandelt `cube.blocks`/`cube.leds` in 6 UDP-Buffer. `preview=True` überspringt `push_frame`. Wendet `cube.brightness` an.

**`server/config.py`** — Alle Hardware-Konstanten: IPs, `VIRTUAL_TO_BLOCK`, `BLOCK_TO_VLEDS`, `VLED_POS_IN_BLOCK`, `LED_MAP`, Segmente.

**`server/settings.py`** — Persistenz via `settings.json`. `animation_params` speichert pro-Animation die zuletzt gesetzten Parameter.

### Animation-System

Jede Animation hat:
- `name: str` — Registry-Key
- `PARAMS: dict` — Schema für Web-UI (type, default, min, max, step, label). Typen: `"float"`, `"int"`, `"hue"` (0–1, Slider 0–360°), `"str"`
- `__init__(**params)` — Parameter müssen mit PARAMS übereinstimmen
- `start(cube)` — Einmalig beim Aktivieren
- `tick(cube, dt, t)` — Jeden Frame (30 fps)

### Neue Animation

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
        self.hue   = hue

    def start(self, cube: Cube) -> None:
        cube.fill([0, 0, 0])

    def tick(self, cube: Cube, dt: float, t: float) -> None:
        # cube.set(face, row, col, [r, g, b])
        pass
```

Dann in `server/animations/__init__.py` registrieren:
```python
from .meine_animation import MeineAnimation
REGISTRY["meine"] = MeineAnimation
```

### Web UI

**`web/js/app.js`** — Haupt-App. Sidebar-Klicks nutzen `/preview/*`. `_onParamChange` speichert nur in `settings.animation_params`, kein Live-Start. `startAnimation` liest gespeicherte Params und schickt sie beim Start mit.

**`web/js/cube3d.js`** — Three.js 3D-Preview. Empfängt WebSocket-Frames (8640 Bytes = 6 Flächen × 480 LEDs × 3 RGB). Verwendet `setSize(..., false)` + ResizeObserver damit CSS die Canvas-Größe kontrolliert.

**`web/js/api.js`** — `api.startAnimation/startWithParams` → `/preview/*`. `api.hardwareStart` → `/animation/*` (für direkten Hardware-Zugriff aus dem UI, falls nötig).

### Hotkey-Daemon

`scripts/hotkeys.py` läuft auf dem Raspberry Pi, liest Konfiguration aus `settings.hotkey_shortcuts` (gespeichert via Web UI → Einstellungen). Ruft `/animation/{name}` auf (Hardware, kein Preview). Als systemd-Service betreibbar.

Verwendet **`evdev`** (direkt `/dev/input`) statt pynput — funktioniert auf Wayland, X11 und headless. User muss in Gruppe `input` sein (`sudo usermod -aG input pi`). Key-Strings im pynput-Format (`<f10>`, `<right>`, `a`) werden intern auf evdev-Keycodes gemappt.

## Raspberry Pi Deployment

Pi läuft auf `192.168.10.205` (pi:admin), Hostname `wled-cube`. Raspberry Pi OS mit Desktop (Wayland).

**Projekt deployen:**
```bash
rsync -av --exclude='.git' --exclude='.venv' --exclude='__pycache__' \
  --exclude='image/.pi-gen' --exclude='image/deploy' --exclude='settings.json' \
  -e "ssh -o PreferredAuthentications=password" \
  ./ pi@192.168.10.205:/home/pi/wled/
```

**Services nach Änderungen neu starten:**
```bash
ssh pi@192.168.10.205 "sudo systemctl restart wled-server wled-hotkeys"
ssh pi@192.168.10.205 "journalctl -fu wled-server"
```

**Logs:**
```bash
ssh pi@192.168.10.205 "journalctl -fu wled-hotkeys"
```

## Setup nach Controller-Reset

```bash
python scripts/setup_all.py
```

## Protokoll

UDP DRGB (Port 21324). Pro Frame: 6 Pakete à `2 Header + 480 × 3 RGB = 1442 Bytes`. WLED wendet die LED-Map selbst an — der Server sendet in virtueller Reihenfolge.
