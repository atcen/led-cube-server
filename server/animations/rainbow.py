"""
Rainbow-Animation: Kontinuierliche Farbwelle über den gesamten Würfel.

Jeder Block bekommt eine Farbe basierend auf (face + row + col + Zeit).
Fließt nahtlos über alle Flächen.
"""
import colorsys
import math
from ..cube import Cube
from .base import Animation


class RainbowAnimation(Animation):
    name = "rainbow"

    def __init__(self, speed: float = 0.3, wave_size: float = 1.5):
        self.speed     = speed      # Rotationsgeschwindigkeit (Zyklen/Sekunde)
        self.wave_size = wave_size  # Wie viele Farbzyklen über den Würfel

    def tick(self, cube: Cube, dt: float, t: float) -> None:
        for face in range(6):
            # Jede Fläche bekommt einen Basis-Hue-Offset (für 3D-Kontinuität)
            face_offset = face / 6.0
            for row in range(5):
                for col in range(5):
                    # Welle über row+col, verschoben durch Zeit
                    spatial = (row + col) / 8.0 * self.wave_size
                    hue     = (spatial + face_offset + t * self.speed) % 1.0
                    r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                    cube.set(face, row, col,
                             [round(r * 255), round(g * 255), round(b * 255)])
