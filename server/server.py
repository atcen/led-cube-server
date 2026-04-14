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
current_animation: Animation | None = None
animation_name     = "none"
_loop_task         = None

# WebSocket-Clients
_ws_clients: set[WebSocket] = set()
_last_frame: bytes = bytes(LEDS_TOTAL * 3 * 6)  # 8640 Bytes leer

# Ausrichtungsmodus
_align_face: int | None = None


# --- Animations-Loop ---
async def animation_loop() -> None:
    global _last_frame
    frame_time = 1.0 / FPS
    last_t     = time.monotonic()
    anim_start = last_t

    while True:
        now = time.monotonic()
        dt  = now - last_t
        t   = now - anim_start
        last_t = now

        if current_animation is not None:
            try:
                current_animation.tick(cube, dt, t)
                face_buffers = render(cube)
                _broadcast_frame(face_buffers)
            except Exception as e:
                log.error(f"Animation-Fehler: {e}")

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
    _ws_clients -= dead


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
def _set_animation(name: str, params: dict | None = None) -> None:
    global current_animation, animation_name, _align_face
    if name not in REGISTRY:
        raise HTTPException(404, f"Animation '{name}' nicht gefunden")
    _align_face = None
    cls  = REGISTRY[name]
    anim = cls(**(params or {}))
    anim.start(cube)
    current_animation = anim
    animation_name    = name
    log.info(f"Animation: {name} {params or ''}")


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
    }


@app.get("/animations")
async def list_animations():
    result = {}
    for name, cls in REGISTRY.items():
        sig    = inspect.signature(cls.__init__)
        params = {}
        for p_name, p in sig.parameters.items():
            if p_name == "self":
                continue
            params[p_name] = {
                "default": p.default if p.default is not inspect.Parameter.empty else None
            }
        result[name] = {"params": params}
    return result


@app.post("/animation/{name}")
async def set_animation(name: str):
    _set_animation(name)
    return {"animation": name}


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
    global current_animation, animation_name
    current_animation = None
    animation_name    = "none"
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


# --- Controller ---
@app.get("/controllers/status")
async def controllers_status():
    return await discovery.check_all()


# --- Ausrichtung ---
@app.post("/align/{face_id}")
async def align_face(face_id: int):
    global _align_face
    if face_id < 0 or face_id > 5:
        raise HTTPException(400, "face_id muss 0–5 sein")
    _align_face = face_id
    cube.fill([0, 0, 0])
    # Eckblöcke und Mittelblock leuchten, für visuelle Orientierung
    for r in range(5):
        for c in range(5):
            if (r == 0 or r == 4) and (c == 0 or c == 4):
                cube.set(face_id, r, c, [255, 0, 0])    # Ecken: Rot
            elif r == 2 and c == 2:
                cube.set(face_id, r, c, [0, 255, 0])    # Mitte: Grün
            elif r == 0 or r == 4 or c == 0 or c == 4:
                cube.set(face_id, r, c, [0, 0, 255])    # Rand: Blau
    face_buffers = render(cube)
    _broadcast_frame(face_buffers)
    return {"aligning": face_id}


@app.post("/align/stop")
async def align_stop():
    global _align_face
    _align_face = None
    cube.fill([0, 0, 0])
    face_buffers = render(cube)
    _broadcast_frame(face_buffers)
    return {"status": "stopped"}


# StaticFiles zuletzt mounten (nach allen anderen Endpoints)
app.mount("/ui", StaticFiles(directory="web", html=True), name="web")
