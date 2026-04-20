import colorsys
import math

from ..config import LEDS_TOTAL, VIRTUAL_TO_BLOCK, VLED_POS_IN_BLOCK
from ..cube import Cube
from .base import Animation, lerp_color

BLACK = [0, 0, 0]


def _hsv(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return [round(r * 255), round(g * 255), round(b * 255)]


class WaterFillAnimation(Animation):
    name = "water_fill"
    PARAMS = {
        "fill_duration":  {"type": "float", "default": 10.0, "min": 1.0, "max": 30.0, "step": 0.5, "label": "Füll-Dauer", "description": "Sekunden bis voll"},
        "hold_duration":  {"type": "float", "default": 1.5,  "min": 0.0, "max": 10.0, "step": 0.5, "label": "Halte-Dauer"},
        "hue":            {"type": "hue",   "default": 0.6,  "label": "Wasserfarbe"},
    }

    def __init__(self, fill_duration: float = 10.0, hold_duration: float = 1.5, hue: float = 0.6):
        self.fill_duration = fill_duration
        self.hold_duration = hold_duration
        self.hue           = hue   # 0=Rot, 0.33=Grün, 0.5=Cyan, 0.6=Blau (default), 0.75=Violett

    def start(self, cube: Cube) -> None:
        cube.fill(BLACK)
        cube.leds.clear()

    def _surface_color(self, face: int, row: int, col: int, t: float, depth: float) -> list:
        dark  = _hsv(self.hue, 0.90, 0.47)
        light = _hsv(self.hue, 0.50, 0.96)
        foam  = _hsv(self.hue, 0.12, 0.92)
        wave = (
            math.sin(t * 2.0 + face * 0.7 + col * 0.9)
            + math.sin(t * 1.3 + row * 1.1 - face * 0.4)
        ) * 0.5
        shimmer = 0.65 + 0.35 * ((wave + 1.0) / 2.0)
        base = lerp_color(dark, light, shimmer)
        return lerp_color(base, foam, max(0.0, 1.0 - depth * 4.0))

    def _deep_water_color(self, face: int, row: int, col: int, t: float, depth: float) -> list:
        dark  = _hsv(self.hue, 0.90, 0.47)
        light = _hsv(self.hue, 0.50, 0.96)
        drift = 0.35 + 0.15 * math.sin(t * 1.2 + face * 0.5 + row * 0.7 + col * 0.4)
        return lerp_color(dark, light, max(0.0, min(1.0, drift - depth * 0.15)))

    def _physical_position(self, vled: int) -> tuple[int, int]:
        grid_row, block_col = VIRTUAL_TO_BLOCK[vled]
        sub_row, sub_col = VLED_POS_IN_BLOCK[vled]
        phys_row = grid_row * 3 + sub_row

        width_before = 0
        for col in range(block_col):
            width_before += 6 if col % 2 == 0 else 7
        phys_col = width_before + sub_col
        return phys_row, phys_col

    def _surface_point(self, face: int, phys_row: int, phys_col: int) -> tuple[float, float, float]:
        x = (phys_col / 31.0) * 2.0 - 1.0
        y = 1.0 - (phys_row / 14.0) * 2.0

        if face == 0:   # front
            return x, y, 1.0
        if face == 1:   # back
            return -x, y, -1.0
        if face == 2:   # left
            return -1.0, y, x
        if face == 3:   # right
            return 1.0, y, -x
        if face == 4:   # top
            return x, 1.0, -y
        return x, -1.0, y  # bottom

    def _fill_height(self, face: int, phys_row: int, phys_col: int) -> float:
        px, py, pz = self._surface_point(face, phys_row, phys_col)
        # Blaue Ecke (Top): px=-1, py=-1, pz=1
        # Wir wollen, dass dieser Punkt den Wert 1.0 (voll) hat und die gegenüberliegende Ecke 0.0
        # Diagonale: -px - py + pz geht von (-1,-1,1) -> 3 bis (1,1,-1) -> -3
        return ((-px - py + pz) + 3.0) / 6.0

    def tick(self, cube: Cube, dt: float, t: float) -> None:
        cycle = self.fill_duration + self.hold_duration
        phase = t % cycle
        progress = 1.0 if phase >= self.fill_duration else phase / self.fill_duration
        surface_band = 0.045

        cube.fill(BLACK)
        cube.leds.clear()

        for face in range(6):
            for vled in range(LEDS_TOTAL):
                phys_row, phys_col = self._physical_position(vled)
                fill_height = self._fill_height(face, phys_row, phys_col)
                depth = progress - fill_height
                if depth <= 0.0:
                    continue

                if depth < surface_band:
                    color = self._surface_color(face, phys_row, phys_col, t, depth / surface_band)
                else:
                    color = self._deep_water_color(face, phys_row, phys_col, t, depth * 10.0)

                cube.leds[(face, vled)] = color
