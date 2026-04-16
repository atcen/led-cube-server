import colorsys

from ..cube import Cube
from .base import Animation


class CheckerboardAnimation(Animation):
    name = "checkerboard"
    PARAMS = {
        "speed": {"type": "float", "default": 1.0,  "min": 0.1, "max": 10.0, "step": 0.1,  "label": "Wechsel-Intervall", "description": "Sekunden pro Farbwechsel"},
        "hue1":  {"type": "hue",   "default": 0.0,  "label": "Farbe A"},
        "hue2":  {"type": "hue",   "default": 0.67, "label": "Farbe B"},
    }

    def __init__(self, speed: float = 1.0, hue1: float = 0.0, hue2: float = 0.67):
        self.speed = speed   # Sekunden pro Farbwechsel
        self.hue1  = hue1   # Farbe A (0=Rot, 0.08=Orange, 0.33=Grün, 0.66=Blau)
        self.hue2  = hue2   # Farbe B

    def tick(self, cube: Cube, dt: float, t: float) -> None:
        swap = int(t / self.speed) % 2
        r1, g1, b1 = colorsys.hsv_to_rgb(self.hue1, 1.0, 1.0)
        r2, g2, b2 = colorsys.hsv_to_rgb(self.hue2, 1.0, 1.0)
        c1 = [round(r1 * 255), round(g1 * 255), round(b1 * 255)]
        c2 = [round(r2 * 255), round(g2 * 255), round(b2 * 255)]

        for face in range(6):
            for row in range(5):
                for col in range(5):
                    is_even = (row + col) % 2 == 0
                    if swap:
                        is_even = not is_even
                    cube.set(face, row, col, c1 if is_even else c2)
