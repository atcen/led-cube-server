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
from . import settings


def render(cube: Cube, preview: bool = False) -> dict[int, bytes]:
    """Rendert den aktuellen Cube-Zustand und gibt face_buffers zurück.
    preview=True → kein UDP, nur WebSocket-Feed."""
    bri = max(0.0, min(1.0, cube.brightness))
    face_buffers = {}
    
    st = settings.load()
    orientations = st.get("face_orientations", [])

    leds = cube.leds  # per-LED-Override (optional, gesetzt von Smooth-Animationen)
    for face in range(6):
        buf = bytearray(LEDS_TOTAL * 3)
        
        # Orientierung für diese Fläche
        ori = orientations[face] if face < len(orientations) else {"rotate": 0, "flip": False}
        rot = ori.get("rotate", 0) % 4
        flip = ori.get("flip", False)

        for vled in range(LEDS_TOTAL):
            override = leds.get((face, vled))
            if override is not None:
                r, g, b = override
            else:
                row, col = VIRTUAL_TO_BLOCK[vled]
                
                # Orientierung anwenden: (phys_row, phys_col) → (logical_row, logical_col)
                # 1. Flip (horizontal)
                if flip:
                    col = 4 - col
                # 2. Rotate (clockwise)
                for _ in range(rot):
                    # (r, c) -> (c, 4-r)
                    row, col = col, 4 - row
                
                r, g, b  = cube.blocks[(face, row, col)]
            buf[vled * 3]     = int(r * bri)
            buf[vled * 3 + 1] = int(g * bri)
            buf[vled * 3 + 2] = int(b * bri)
        face_buffers[face] = bytes(buf)

    if not preview:
        push_frame(face_buffers)
    return face_buffers
