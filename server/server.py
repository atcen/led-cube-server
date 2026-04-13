"""
WLED Cube Animation Server.

Startet mit: uvicorn server.server:app --host 0.0.0.0 --port 8000
             (aus dem Projektroot-Verzeichnis)

API:
  GET  /                       Status + aktuelle Animation
  GET  /animations             Verfügbare Animationen
  POST /animation/{name}       Animation wechseln
  POST /animation/{name}/params  Parameter setzen (JSON body)
  POST /brightness/{value}     Helligkeit setzen (0–255)
  POST /stop                   Alles aus
"""
import asyncio
import time
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .cube import Cube
from .renderer import render
from .animations import REGISTRY
from .animations.base import Animation
from .config import FPS

log = logging.getLogger("wled-cube")
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

# --- Globaler Zustand ---
cube              = Cube()
current_animation: Animation | None = None
animation_name    = "none"
_loop_task        = None


# --- Animations-Loop ---
async def animation_loop() -> None:
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
                render(cube)
            except Exception as e:
                log.error(f"Animation-Fehler: {e}")

        sleep = frame_time - (time.monotonic() - now)
        if sleep > 0:
            await asyncio.sleep(sleep)


# --- FastAPI App ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _loop_task
    log.info(f"Animation-Loop startet @ {FPS} fps")
    _loop_task = asyncio.create_task(animation_loop())
    yield
    _loop_task.cancel()


app = FastAPI(title="WLED Cube Server", lifespan=lifespan)


def _set_animation(name: str, params: dict | None = None) -> None:
    global current_animation, animation_name
    if name not in REGISTRY:
        raise HTTPException(404, f"Animation '{name}' nicht gefunden")
    cls = REGISTRY[name]
    anim = cls(**(params or {}))
    anim.start(cube)
    current_animation = anim
    animation_name    = name
    log.info(f"Animation: {name} {params or ''}")


@app.get("/")
async def status():
    return {
        "animation":  animation_name,
        "brightness": round(cube.brightness * 255),
        "fps":        FPS,
    }


@app.get("/animations")
async def list_animations():
    return {"animations": list(REGISTRY.keys())}


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
    return {"brightness": value}


@app.post("/stop")
async def stop():
    global current_animation, animation_name
    current_animation = None
    animation_name    = "none"
    cube.fill([0, 0, 0])
    render(cube)
    return {"status": "stopped"}
