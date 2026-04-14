import colorsys
import math

from ..config import BLOCK_WIDTHS, LEDS_TOTAL, VIRTUAL_TO_BLOCK, VLED_POS_IN_BLOCK
from ..cube import Cube
from .base import Animation

BLACK = [0, 0, 0]
PANEL_W = sum(BLOCK_WIDTHS)
PANEL_H = 15
HEART_WIDTH = 5.0
HEART_LENGTH = 9.0
TIP_MARGIN = 0.8

# Richtung von der Herzspitze zu den oberen Rundungen in lokalen Panel-Koordinaten.
# Die Ausrichtungen sind so gewählt, dass die Spitze zu einer Würfel-Ecke zeigt und
# das Motiv entlang derselben Raumdiagonale wie die Wasserfüllung wirkt.
FACE_TOP_DIRECTION = {
    0: (1.0, 1.0),    # front  -> Spitze unten links
    1: (-1.0, 1.0),   # back   -> Spitze unten rechts
    2: (-1.0, 1.0),   # left   -> Spitze unten rechts
    3: (1.0, 1.0),    # right  -> Spitze unten links
    4: (1.0, 1.0),    # top    -> Spitze unten links
    5: (1.0, -1.0),   # bottom -> Spitze oben links
}


def _physical_position(vled: int) -> tuple[int, int]:
    grid_row, block_col = VIRTUAL_TO_BLOCK[vled]
    sub_row, sub_col = VLED_POS_IN_BLOCK[vled]
    phys_row = grid_row * 3 + sub_row

    width_before = 0
    for col in range(block_col):
        width_before += BLOCK_WIDTHS[col]
    phys_col = width_before + sub_col
    return phys_row, phys_col


def _heart_tip(face: int) -> tuple[float, float]:
    dx, dy = FACE_TOP_DIRECTION[face]
    tip_x = TIP_MARGIN if dx > 0 else PANEL_W - 1 - TIP_MARGIN
    tip_y = TIP_MARGIN if dy > 0 else PANEL_H - 1 - TIP_MARGIN
    return tip_x, tip_y


def _is_heart_pixel(face: int, phys_row: int, phys_col: int) -> bool:
    dx, dy = FACE_TOP_DIRECTION[face]
    length = math.sqrt(dx * dx + dy * dy)
    dx /= length
    dy /= length
    px = -dy
    py = dx

    tip_x, tip_y = _heart_tip(face)

    # Panel-Koordinaten mit Ursprung unten links, damit dy>0 wirklich "nach oben" bedeutet.
    x = phys_col
    y = PANEL_H - 1 - phys_row

    rel_x = x - tip_x
    rel_y = y - tip_y
    along = rel_x * dx + rel_y * dy
    side = rel_x * px + rel_y * py

    hx = side / HEART_WIDTH
    hy = along / HEART_LENGTH - 1.0
    shape = (hx * hx + hy * hy - 1.0) ** 3 - hx * hx * hy * hy * hy

    return shape <= 0.0 and along >= -0.35


class HeartAnimation(Animation):
    name = "heart"
    PARAMS = {
        "hue": {"type": "hue", "default": 0.96, "label": "Herzfarbe"},
    }

    def __init__(self, hue: float = 0.96):
        self.hue = hue   # 0.96=Rot-Rosa (default), 0.0=Rot, 0.33=Grün, 0.5=Cyan

    def start(self, cube: Cube) -> None:
        r, g, b = colorsys.hsv_to_rgb(self.hue, 0.82, 0.86)
        heart_color = [round(r * 255), round(g * 255), round(b * 255)]

        cube.fill(BLACK)
        cube.leds.clear()

        for face in range(6):
            for vled in range(LEDS_TOTAL):
                phys_row, phys_col = _physical_position(vled)
                if _is_heart_pixel(face, phys_row, phys_col):
                    cube.leds[(face, vled)] = heart_color

    def tick(self, cube: Cube, dt: float, t: float) -> None:
        pass
