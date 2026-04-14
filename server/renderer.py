"""
Renderer: Cube-Zustand → UDP-Buffer pro Controller.

Für jeden Controller:
  1. Für jeden virtuellen LED-Index (0–479): Block-Farbe nachschlagen
  2. Brightness anwenden
  3. An virtuelle LED-Position schreiben (WLED wendet LED-Map selbst an)
  4. Als DRGB-Buffer ausgeben
"""
from .config import VIRTUAL_TO_BLOCK, LEDS_TOTAL
from .cube import Cube
from .protocol import push_frame


def render(cube: Cube) -> dict[int, bytes]:
    """Rendert den aktuellen Cube-Zustand, schickt ihn via UDP und gibt face_buffers zurück."""
    bri = max(0.0, min(1.0, cube.brightness))
    face_buffers = {}

    leds = cube.leds  # per-LED-Override (optional, gesetzt von Smooth-Animationen)
    for face in range(6):
        buf = bytearray(LEDS_TOTAL * 3)
        for vled in range(LEDS_TOTAL):
            override = leds.get((face, vled))
            if override is not None:
                r, g, b = override
            else:
                row, col = VIRTUAL_TO_BLOCK[vled]
                r, g, b  = cube.blocks[(face, row, col)]
            buf[vled * 3]     = int(r * bri)
            buf[vled * 3 + 1] = int(g * bri)
            buf[vled * 3 + 2] = int(b * bri)
        face_buffers[face] = bytes(buf)

    push_frame(face_buffers)
    return face_buffers
