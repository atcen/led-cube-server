"""
Renderer: Cube-Zustand → UDP-Buffer pro Controller.

Für jeden Controller:
  1. Für jeden virtuellen LED-Index (0–479): Block-Farbe nachschlagen
  2. Brightness anwenden
  3. An physische LED-Position schreiben (via LED_MAP)
  4. Als DRGB-Buffer ausgeben
"""
from .config import CONTROLLERS, LED_MAP, VIRTUAL_TO_BLOCK, LEDS_TOTAL
from .cube import Cube
from .protocol import push_frame


def render(cube: Cube) -> None:
    """Rendert den aktuellen Cube-Zustand und schickt ihn via UDP."""
    bri = max(0.0, min(1.0, cube.brightness))
    face_buffers = {}

    for face in range(6):
        buf = bytearray(LEDS_TOTAL * 3)
        for vled in range(LEDS_TOTAL):
            row, col = VIRTUAL_TO_BLOCK[vled]
            r, g, b  = cube.blocks[(face, row, col)]
            phys     = LED_MAP[vled]
            buf[phys * 3]     = int(r * bri)
            buf[phys * 3 + 1] = int(g * bri)
            buf[phys * 3 + 2] = int(b * bri)
        face_buffers[face] = bytes(buf)

    push_frame(face_buffers)
