"""Uhr-Animation: Je eine Ziffer (HH:MM) auf den 4 Seitenflächen, zentriert im 5×5-Grid."""
import datetime
from .base import Animation
from ..cube import Cube

# 3×5-Font (3 Spalten, 5 Zeilen) — zentriert auf 5×5 ergibt col-Offset 1
FONT = {
    0: [[1,1,1],[1,0,1],[1,0,1],[1,0,1],[1,1,1]],
    1: [[0,1,0],[1,1,0],[0,1,0],[0,1,0],[1,1,1]],
    2: [[1,1,1],[0,0,1],[0,1,1],[1,0,0],[1,1,1]],
    3: [[1,1,1],[0,0,1],[0,1,1],[0,0,1],[1,1,1]],
    4: [[1,0,1],[1,0,1],[1,1,1],[0,0,1],[0,0,1]],
    5: [[1,1,1],[1,0,0],[1,1,1],[0,0,1],[1,1,1]],
    6: [[1,1,1],[1,0,0],[1,1,1],[1,0,1],[1,1,1]],
    7: [[1,1,1],[0,0,1],[0,1,0],[0,1,0],[0,1,0]],
    8: [[1,1,1],[1,0,1],[1,1,1],[1,0,1],[1,1,1]],
    9: [[1,1,1],[1,0,1],[1,1,1],[0,0,1],[1,1,1]],
}

# Seitenflächen in Uhrzeigerrichtung: FRONT, RIGHT, BACK, LEFT
# Stellen: H-Zehner, H-Einer, M-Zehner, M-Einer
FACE_ORDER = [0, 3, 1, 2]

COLOR_HOURS   = [0, 100, 255]
COLOR_MINUTES = [0, 220, 80]
COLOR_PULSE_ON  = [180, 140, 0]
COLOR_PULSE_OFF = [15, 12, 0]


def _draw_digit(cube: Cube, face: int, digit: int, color: list) -> None:
    """Zeichnet eine Ziffer zentriert (col 1-3) auf eine 5×5-Fläche."""
    glyph = FONT[digit]
    for row in range(5):
        for gc in range(3):
            c = color if glyph[row][gc] else [0, 0, 0]
            cube.set(face, row, gc + 1, c)
        # Randkolumnen schwarz
        cube.set(face, row, 0, [0, 0, 0])
        cube.set(face, row, 4, [0, 0, 0])


class ClockAnimation(Animation):
    name = "clock"

    def start(self, cube: Cube) -> None:
        super().start(cube)

    def tick(self, cube: Cube, dt: float, t: float) -> None:
        now = datetime.datetime.now()
        h = now.hour   # 0–23
        m = now.minute
        s = now.second

        digits = [h // 10, h % 10, m // 10, m % 10]
        colors = [COLOR_HOURS, COLOR_HOURS, COLOR_MINUTES, COLOR_MINUTES]

        for i, face in enumerate(FACE_ORDER):
            _draw_digit(cube, face, digits[i], colors[i])

        # TOP/BOTTOM: Sekundenpuls
        pulse = COLOR_PULSE_ON if (s % 2 == 0) else COLOR_PULSE_OFF
        for row in range(5):
            for col in range(5):
                cube.set(4, row, col, pulse)
                cube.set(5, row, col, pulse)
