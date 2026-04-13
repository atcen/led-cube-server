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
- Da Blöcke nicht-kontiguierlich im physischen Strip liegen, wird eine **LED-Map** (`ledmap.json`) auf jedem Controller verwendet

## Server starten

```bash
pip install -r requirements.txt
uvicorn server.server:app --host 0.0.0.0 --port 8000
```

### API

| Endpoint | Beschreibung |
|---|---|
| `GET /` | Status |
| `GET /animations` | Verfügbare Animationen |
| `POST /animation/{name}` | Animation starten |
| `POST /animation/{name}/params` | Mit Parametern starten (JSON body) |
| `POST /brightness/{0-255}` | Helligkeit |
| `POST /stop` | Alles aus |

Beispiel Snake mit eigenen Parametern:
```bash
curl -X POST http://localhost:8000/animation/snake/params \
  -H "Content-Type: application/json" \
  -d '{"length": 8, "speed": 0.3}'
```

## Projektstruktur

```
server/
  server.py        # FastAPI App + Animations-Loop (30 fps)
  cube.py          # Virtuelles 3D-Modell + Würfel-Topologie (TRANSITIONS, move())
  renderer.py      # Cube-State → UDP-Buffer pro Controller
  protocol.py      # UDP DRGB Sender (Port 21324, kein TCP)
  config.py        # IPs, Panel-Layout, LED_MAP, SEGMENTS, VIRTUAL_TO_BLOCK
  animations/
    base.py        # Animation-Basisklasse + lerp_color()
    snake.py       # Snake mit software-seitiger Fade-Interpolation
    rainbow.py     # Kontinuierliche Farbwelle
scripts/
  reset.sh         # Alle Controller rebooten
  white.sh         # Alle Controller auf weiß
  black.sh         # Alle Controller aus
  align.py         # Würfel-Ausrichtungshilfe (3-Block-Kantenmuster)
  setup_all.py     # Einmalig: LED-Map + Segmente auf alle Controller pushen
```

## Neue Animation schreiben

```python
# server/animations/meine_animation.py
from .base import Animation
from ..cube import Cube

class MeineAnimation(Animation):
    name = "meine"

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

## Setup nach Controller-Reset

LED-Map und Segmente müssen nach jedem Reset neu gepusht werden:
```bash
python scripts/setup_all.py
```

## Protokoll

Animationen werden via **UDP DRGB** (Port 21324) gesendet — kein TCP, kein JSON-Parsing auf dem ESP32. Pro Frame: 6 UDP-Pakete à 1442 Bytes (2 Header + 480 LEDs × 3 RGB-Bytes), nahezu gleichzeitig gesendet.
