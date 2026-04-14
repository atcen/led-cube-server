import math
import random

from ..config import BLOCK_WIDTHS, BLOCK_TO_VLEDS, VLED_POS_IN_BLOCK
from ..cube import Cube
from .base import Animation

BLACK = [0, 0, 0]
PANEL_W = sum(BLOCK_WIDTHS)
PANEL_H = 15
PALETTE = [
    [215, 70, 80],
    [240, 145, 65],
    [240, 205, 90],
    [70, 160, 110],
    [65, 125, 210],
    [165, 95, 185],
]


def _build_pixel_map() -> dict[tuple[int, int], int]:
    pixel_to_vled = {}
    col_offset = 0
    for block_col, width in enumerate(BLOCK_WIDTHS):
        for grid_row in range(5):
            for vled in BLOCK_TO_VLEDS[(grid_row, block_col)]:
                sub_row, sub_col = VLED_POS_IN_BLOCK[vled]
                y = grid_row * 3 + sub_row
                x = col_offset + sub_col
                pixel_to_vled[(y, x)] = vled
        col_offset += width
    return pixel_to_vled


PIXEL_TO_VLED = _build_pixel_map()


class WatercolorAnimation(Animation):
    name = "watercolor"

    def __init__(
        self,
        hit_interval: float = 0.9,
        diffusion: float = 0.22,
        fade: float = 0.12,
    ):
        self.hit_interval = hit_interval
        self.diffusion = diffusion
        self.fade = fade

    def start(self, cube: Cube) -> None:
        super().start(cube)
        self._fields = [
            [[[0.0, 0.0, 0.0] for _ in range(PANEL_W)] for _ in range(PANEL_H)]
            for _ in range(6)
        ]
        self._time_to_hit = 0.15
        for _ in range(4):
            self._spawn_hit()
        self._render(cube)

    def _spawn_hit(self) -> None:
        face = random.randrange(6)
        cx = random.uniform(3.0, PANEL_W - 4.0)
        cy = random.uniform(2.0, PANEL_H - 3.0)
        radius = random.uniform(2.8, 5.8)
        color = random.choice(PALETTE)
        strength = random.uniform(0.45, 0.95)
        oval = random.uniform(0.7, 1.4)
        angle = random.uniform(0.0, math.tau)
        ca = math.cos(angle)
        sa = math.sin(angle)
        field = self._fields[face]

        for y in range(PANEL_H):
            for x in range(PANEL_W):
                dx = x - cx
                dy = y - cy
                rx = (dx * ca - dy * sa) / radius
                ry = (dx * sa + dy * ca) / (radius * oval)
                dist = rx * rx + ry * ry
                if dist > 1.6:
                    continue

                edge_noise = 0.82 + 0.18 * math.sin(x * 0.9 + y * 1.3 + face * 1.7 + angle * 2.0)
                deposit = strength * math.exp(-dist * 2.2) * edge_noise
                pixel = field[y][x]
                for i in range(3):
                    pixel[i] += color[i] * deposit

    def _step_field(self, dt: float) -> None:
        mix = min(0.45, self.diffusion * dt * 8.0)
        fade = max(0.0, 1.0 - self.fade * dt)

        for face in range(6):
            src = self._fields[face]
            dst = [[[0.0, 0.0, 0.0] for _ in range(PANEL_W)] for _ in range(PANEL_H)]

            for y in range(PANEL_H):
                for x in range(PANEL_W):
                    pixel = src[y][x]
                    accum = [pixel[0] * 4.0, pixel[1] * 4.0, pixel[2] * 4.0]
                    weight = 4.0

                    for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                        if 0 <= ny < PANEL_H and 0 <= nx < PANEL_W:
                            neighbor = src[ny][nx]
                            accum[0] += neighbor[0]
                            accum[1] += neighbor[1]
                            accum[2] += neighbor[2]
                            weight += 1.0

                    bleed = 1.0 + 0.05 * math.sin(face * 11.0 + x * 0.7 + y * 0.4)
                    blurred = [channel / weight for channel in accum]
                    dst_pixel = dst[y][x]
                    for i in range(3):
                        dst_pixel[i] = (pixel[i] * (1.0 - mix) + blurred[i] * mix * bleed) * fade

            self._fields[face] = dst

    def _render(self, cube: Cube) -> None:
        cube.fill(BLACK)
        cube.leds.clear()

        for face in range(6):
            field = self._fields[face]
            for y in range(PANEL_H):
                for x in range(PANEL_W):
                    vled = PIXEL_TO_VLED[(y, x)]
                    pixel = field[y][x]
                    cube.leds[(face, vled)] = [
                        max(0, min(255, int(pixel[0]))),
                        max(0, min(255, int(pixel[1]))),
                        max(0, min(255, int(pixel[2]))),
                    ]

    def tick(self, cube: Cube, dt: float, t: float) -> None:
        self._time_to_hit -= dt
        while self._time_to_hit <= 0.0:
            self._spawn_hit()
            if random.random() < 0.25:
                self._spawn_hit()
            self._time_to_hit += random.uniform(self.hit_interval * 0.65, self.hit_interval * 1.35)

        self._step_field(dt)
        self._render(cube)
