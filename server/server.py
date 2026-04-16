"""
WLED Cube Animation Server.

Startet mit: uvicorn server.server:app --host 0.0.0.0 --port 8000
             (aus dem Projektroot-Verzeichnis)

API:
  GET  /                          Status + aktuelle Animation
  GET  /animations                Verfügbare Animationen + Params-Schema
  POST /animation/{name}          Animation wechseln
  POST /animation/{name}/params   Parameter setzen (JSON body)
  POST /brightness/{value}        Helligkeit setzen (0–255)
  POST /stop                      Alles aus
  GET  /settings                  Einstellungen lesen
  POST /settings                  Einstellungen aktualisieren
  GET  /controllers/status        Controller-Onlinestatus
  POST /align/{face_id}           Ausrichtungs-Pattern für eine Fläche
  POST /align/stop                Ausrichtungs-Pattern stoppen
  WS   /ws                        Live-Frames (binary, 8640 Bytes @ 30fps)
"""
import asyncio
import inspect
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .cube import Cube
from .renderer import render
from .animations import REGISTRY
from .animations.base import Animation
from .config import FPS, LEDS_TOTAL
from . import settings
from . import discovery

log = logging.getLogger("wled-cube")
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

# --- Globaler Zustand ---
cube               = Cube()
cube.brightness    = 0.2  # Standard-Helligkeit auf 20% drosseln (Sicherheitswert für TOP)
current_animation: Animation | None = None
animation_name     = "none"
_loop_task         = None
_preview_mode      = False   # True → kein UDP, nur WebSocket-Preview

# WebSocket-Clients
_ws_clients: set[WebSocket] = set()
_last_frame: bytes = bytes(LEDS_TOTAL * 3 * 6)  # 8640 Bytes leer

# Ausrichtungsmodus
_align_face: int | None = None
_is_align_all: bool = False


# --- Animations-Loop ---
async def animation_loop() -> None:
    global _last_frame
    frame_time = 1.0 / FPS
    last_t     = time.monotonic()
    anim_start = last_t
    loop_count = 0

    while True:
        now = time.monotonic()
        dt  = now - last_t
        t   = now - anim_start
        last_t = now
        
        loop_count += 1
        if loop_count % (FPS * 10) == 0: # Alle 10 Sekunden
             log.info(f"Loop Heartbeat: anim={animation_name}, align={_align_face}, is_align_all={_is_align_all}")

        # Alle 60 Sekunden mDNS-Rediscovery im Hintergrund anstoßen
        if loop_count % (FPS * 60) == 0:
             asyncio.create_task(discovery.check_all())

        # Wenn eine Animation läuft ODER wir im Montage/Align-Modus sind:
        # Puffer rendern und senden.
        if current_animation is not None:
            try:
                current_animation.tick(cube, dt, t)
                face_buffers = render(cube, preview=_preview_mode)
                _broadcast_frame(face_buffers)
            except Exception as e:
                log.error(f"Animation-Fehler: {e}")
        elif _align_face is not None or _is_align_all:
            # Zurück auf 30 FPS für konsistentes Debugging
            face_buffers = render(cube, preview=_preview_mode)
            _broadcast_frame(face_buffers)

        sleep = frame_time - (time.monotonic() - now)
        if sleep > 0:
            await asyncio.sleep(sleep)


def _broadcast_frame(face_buffers: dict[int, bytes]) -> None:
    """Baut den WS-Frame (8640 Bytes) und sendet ihn an alle verbundenen Clients."""
    global _last_frame
    frame = b"".join(face_buffers[f] for f in range(6))
    _last_frame = frame
    dead: set[WebSocket] = set()
    for ws in list(_ws_clients):
        try:
            asyncio.ensure_future(ws.send_bytes(frame))
        except Exception:
            dead.add(ws)
    _ws_clients.difference_update(dead)


# --- FastAPI App ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _loop_task
    log.info(f"Animation-Loop startet @ {FPS} fps")
    _loop_task = asyncio.create_task(animation_loop())
    yield
    _loop_task.cancel()


app = FastAPI(title="WLED Cube Server", lifespan=lifespan)


# --- WebSocket ---
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    _ws_clients.add(ws)
    await ws.send_bytes(_last_frame)
    try:
        while True:
            await ws.receive_text()
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        _ws_clients.discard(ws)


# --- Helper ---
def _set_animation(name: str, params: dict | None = None, preview: bool = False) -> None:
    global current_animation, animation_name, _align_face, _is_align_all, _preview_mode
    if name not in REGISTRY:
        raise HTTPException(404, f"Animation '{name}' nicht gefunden")
    _align_face   = None
    _is_align_all = False
    _preview_mode = preview
    cls  = REGISTRY[name]
    anim = cls(**(params or {}))
    anim.start(cube)
    current_animation = anim
    animation_name    = name
    log.info(f"Animation: {name} {'[preview]' if preview else ''} {params or ''}")


# --- REST Endpoints ---
@app.get("/")
async def root():
    if not settings.get("setup_complete"):
        return RedirectResponse("/ui/index.html?wizard=true")
    return RedirectResponse("/ui/index.html")


@app.get("/status")
async def status():
    return {
        "animation":  animation_name,
        "brightness": round(cube.brightness * 255),
        "fps":        FPS,
        "preview":    _preview_mode,
    }


@app.get("/animations")
async def list_animations():
    result = {}
    for name, cls in REGISTRY.items():
        class_params = getattr(cls, "PARAMS", None)
        if class_params:
            result[name] = {"params": class_params}
        else:
            # Fallback: Introspection
            sig    = inspect.signature(cls.__init__)
            params = {}
            for p_name, p in sig.parameters.items():
                if p_name == "self":
                    continue
                default = p.default if p.default is not inspect.Parameter.empty else None
                params[p_name] = {"type": "float", "default": default, "label": p_name}
            result[name] = {"params": params}
    return result


@app.post("/animation/{name}")
async def set_animation(name: str):
    _set_animation(name, preview=False)
    return {"animation": name}


@app.post("/preview/{name}")
async def preview_animation(name: str):
    _set_animation(name, preview=True)
    return {"animation": name, "preview": True}


@app.post("/preview/{name}/params")
async def preview_animation_params(name: str, params: dict):
    _set_animation(name, params, preview=True)
    return {"animation": name, "params": params, "preview": True}


@app.post("/animation/{name}/params")
async def set_animation_params(name: str, params: dict):
    _set_animation(name, params)
    return {"animation": name, "params": params}


@app.post("/brightness/{value}")
async def set_brightness(value: int):
    if not 0 <= value <= 255:
        raise HTTPException(400, "Brightness muss 0–255 sein")
    cube.brightness = value / 255.0
    settings.update({"brightness": value})
    return {"brightness": value}


@app.post("/stop")
async def stop():
    global current_animation, animation_name, _align_face, _is_align_all
    current_animation = None
    animation_name    = "none"
    _align_face       = None
    _is_align_all     = False
    cube.fill([0, 0, 0])
    face_buffers = render(cube)
    _broadcast_frame(face_buffers)
    return {"status": "stopped"}


# --- Settings ---
@app.get("/settings")
async def get_settings():
    return settings.load()


@app.post("/settings")
async def post_settings(body: dict):
    return settings.update(body)


@app.get("/controllers/status")
async def controllers_status():
    return await discovery.check_all()


@app.post("/controllers/{face_id}/reset")
async def reset_controller(face_id: int):
    if face_id not in discovery.CONTROLLERS:
        raise HTTPException(404, "Controller nicht gefunden")
    ip = discovery.CONTROLLERS[face_id]
    log.info(f"Resetting controller {discovery.FACE_NAMES[face_id]} ({ip})")
    async with httpx.AsyncClient() as client:
        try:
            await client.post(f"http://{ip}/json/state", json={"rb": True}, timeout=2.0)
            return {"status": "reset command sent"}
        except Exception as e:
            raise HTTPException(500, f"Reset fehlgeschlagen: {e}")


@app.post("/animation/next")
async def next_animation():
    st = settings.load()
    enabled = st.get("enabled_animations", list(REGISTRY.keys()))
    if not enabled:
        return {"status": "no animations enabled"}
    
    try:
        current_idx = enabled.index(animation_name)
        next_idx = (current_idx + 1) % len(enabled)
    except ValueError:
        next_idx = 0
        
    next_name = enabled[next_idx]
    _set_animation(next_name)
    return {"animation": next_name}


# --- Ausrichtung ---
@app.post("/align/all")
async def align_all():
    """Zeigt das 8-Ecken-Montagemuster: Gleiche Farbe an den Ecken = Korrekte Position."""
    global _align_face, _is_align_all, current_animation, animation_name
    log.info("Montage-Modus (8 Ecken) aktiviert")
    current_animation = None
    animation_name = "none"
    _align_face = None
    _is_align_all = True
    cube.fill([0, 0, 0])

    # 8 Ecken und ihre Farben (RGB)
    C1, C2, C3, C4 = [255,0,0], [0,255,0], [0,0,255], [255,255,0]   # Rot, Grün, Blau, Gelb
    C5, C6, C7, C8 = [255,0,255], [0,255,255], [255,128,0], [255,255,255] # Magenta, Cyan, Orange, Weiß

    # Zuordnung: Welche (Face, Row, Col) bilden welche Ecke?
    # Siehe TRANSITIONS in cube.py
    corners = [
        (C1, [(0,0,0), (2,0,4), (4,4,0)]), # A: Front-Top-Left
        (C2, [(0,0,4), (3,0,0), (4,4,4)]), # B: Front-Top-Right
        (C3, [(0,4,0), (2,4,4), (5,0,0)]), # C: Front-Bottom-Left
        (C4, [(0,4,4), (3,4,0), (5,0,4)]), # D: Front-Bottom-Right
        (C5, [(1,0,4), (2,0,0), (4,0,0)]), # E: Back-Top-Left (von außen)
        (C6, [(1,0,0), (3,0,4), (4,0,4)]), # F: Back-Top-Right
        (C7, [(1,4,4), (2,4,0), (5,4,0)]), # G: Back-Bottom-Left
        (C8, [(1,4,0), (3,4,4), (5,4,4)]), # H: Back-Bottom-Right
    ]

    for color, points in corners:
        for f, r, c in points:
            cube.set(f, r, c, color)
    
    face_buffers = render(cube)
    _broadcast_frame(face_buffers)
    return {"aligning": "all"}


@app.post("/align/stop")
async def align_stop():
    global _align_face, _is_align_all
    _align_face = None
    _is_align_all = False
    cube.fill([0, 0, 0])
    _broadcast_frame(render(cube))
    return {"status": "stopped"}


@app.post("/align/{face_id}")
async def align_face(face_id: int):
    global _align_face, _is_align_all, current_animation, animation_name
    if face_id < 0 or face_id > 5:
        raise HTTPException(400, "face_id muss 0–5 sein")
    
    current_animation = None
    animation_name = "none"
    _align_face = face_id
    _is_align_all = False

    # Besseres Pattern: 
    # (0,0) = Weißlich
    # Oberer Rand (row=0) = Rot
    # Linker Rand (col=0) = Grün
    # Restlicher Rand = Blau
    # Mitte = Dunkelgrau
    cube.fill([0, 0, 0])
    for r in range(5):
        for c in range(5):
            if r == 0 and c == 0:
                cube.set(face_id, r, c, [180, 180, 180]) # Top-Left: Weißlich
            elif r == 0:
                cube.set(face_id, r, c, [180, 0, 0])     # Top: Rot
            elif c == 0:
                cube.set(face_id, r, c, [0, 180, 0])     # Left: Grün
            elif r == 4 or c == 4:
                cube.set(face_id, r, c, [0, 0, 180])     # Bottom/Right: Blau
            elif r == 2 and c == 2:
                cube.set(face_id, r, c, [40, 40, 40])    # Mitte: Grau

    face_buffers = render(cube)
    _broadcast_frame(face_buffers)
    return {"aligning": face_id}


@app.post("/align/{face_id}/rotate")
async def align_rotate(face_id: int):
    st = settings.load()
    orientations = st.get("face_orientations", [])
    if face_id >= len(orientations):
        return {"error": "invalid face"}

    orientations[face_id]["rotate"] = (orientations[face_id]["rotate"] + 1) % 4
    settings.update({"face_orientations": orientations})

    # Pattern neu rendern (mit neuer Orientierung)
    await align_face(face_id)
    return orientations[face_id]


@app.post("/align/{face_id}/flip")
async def align_flip(face_id: int):
    st = settings.load()
    orientations = st.get("face_orientations", [])
    if face_id >= len(orientations):
        return {"error": "invalid face"}

    orientations[face_id]["flip"] = not orientations[face_id].get("flip", False)
    settings.update({"face_orientations": orientations})

    # Pattern neu rendern
    await align_face(face_id)
    return orientations[face_id]



# StaticFiles zuletzt mounten (nach allen anderen Endpoints)
app.mount("/ui", StaticFiles(directory="web", html=True), name="web")
