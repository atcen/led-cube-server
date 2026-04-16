import math

from ..config import BLOCK_TO_VLEDS, BLOCK_WIDTHS, VLED_POS_IN_BLOCK
from ..cube import Cube, move
from .base import Animation

BLACK = [0, 0, 0]
PACMAN = [245, 210, 40]
PELLET = [220, 220, 220]
SIDE_FACES = [0, 1, 2, 3]


def _center_vled(row: int, col: int) -> int | None:
    for vled in BLOCK_TO_VLEDS[(row, col)]:
        if VLED_POS_IN_BLOCK[vled] == (1, 3):
            return vled
    return BLOCK_TO_VLEDS[(row, col)][len(BLOCK_TO_VLEDS[(row, col)]) // 2]


def _block_center(row: int, col: int) -> tuple[float, float]:
    x = sum(BLOCK_WIDTHS[:col]) + (BLOCK_WIDTHS[col] - 1) / 2.0
    y = row * 3 + 1.0
    return x, y


class PacmanAnimation(Animation):
    name = "pacman"
    PARAMS = {
        "speed": {"type": "float", "default": 0.28, "min": 0.05, "max": 2.0, "step": 0.05, "label": "Geschwindigkeit"},
    }

    def __init__(self, speed: float = 0.28):
        self.speed = speed

    def start(self, cube: Cube) -> None:
        super().start(cube)
        self._path = self._build_path()
        self._path_index = 0
        self._direction = "E"
        self._step_progress = 0.0
        self._mouth_open = True
        self._pellets = self._build_pellets()
        self._eat_current_pellet()
        self._render(cube)

    def _build_path(self) -> list[tuple[int, int, int]]:
        path = []
        face, row, col, direction = 0, 2, 0, "E"
        for _ in range(20):
            path.append((face, row, col))
            face, row, col, direction = move(face, row, col, direction)
        return path

    def _build_pellets(self) -> set[tuple[int, int, int]]:
        pellets = set()
        for face in SIDE_FACES:
            pellets.add((face, 2, 2))
        return pellets

    def _eat_current_pellet(self) -> None:
        self._pellets.discard(self._path[self._path_index])
        if not self._pellets:
            self._pellets = self._build_pellets()
            self._pellets.discard(self._path[self._path_index])

    def _step(self) -> None:
        current = self._path[self._path_index]
        next_index = (self._path_index + 1) % len(self._path)
        nxt = self._path[next_index]
        for candidate in ("E", "W", "N", "S"):
            nf, nr, nc, nd = move(*current, candidate)
            if (nf, nr, nc) == nxt:
                self._direction = nd
                break
        self._path_index = next_index
        self._mouth_open = not self._mouth_open
        self._eat_current_pellet()

    def _paint_pacman(self, cube: Cube, center: tuple[int, int, int], direction: str, mouth_open: bool) -> None:
        face, row, col = center
        center_x, center_y = _block_center(row, col)
        radius = 3.35

        if direction == "E":
            dir_x, dir_y = 1.0, 0.0
            eye_x, eye_y = -0.75, -1.05
        elif direction == "W":
            dir_x, dir_y = -1.0, 0.0
            eye_x, eye_y = 0.75, -1.05
        elif direction == "N":
            dir_x, dir_y = 0.0, -1.0
            eye_x, eye_y = 1.0, 0.65
        else:
            dir_x, dir_y = 0.0, 1.0
            eye_x, eye_y = 1.0, -0.65

        for grid_row in range(5):
            for block_col in range(5):
                for vled in BLOCK_TO_VLEDS[(grid_row, block_col)]:
                    sub_row, sub_col = VLED_POS_IN_BLOCK[vled]
                    px = sum(BLOCK_WIDTHS[:block_col]) + sub_col
                    py = grid_row * 3 + sub_row
                    dx = px - center_x
                    dy = py - center_y

                    inside = dx * dx + dy * dy <= radius * radius
                    if not inside:
                        continue

                    forward = dx * dir_x + dy * dir_y
                    side = -dx * dir_y + dy * dir_x
                    mouth_cut = mouth_open and forward > 0.2 and abs(side) < forward * 0.72
                    eye_cut = (dx - eye_x) ** 2 + (dy - eye_y) ** 2 <= 0.28

                    if not mouth_cut and not eye_cut:
                        cube.leds[(face, vled)] = PACMAN

    def _render(self, cube: Cube) -> None:
        cube.fill(BLACK)
        cube.leds.clear()

        for face in (4, 5):
            cube.fill_face(face, BLACK)

        pacman_pos = self._path[self._path_index]

        for pellet in self._pellets:
            face, row, col = pellet
            vled = _center_vled(row, col)
            cube.leds[(face, vled)] = PELLET

        self._paint_pacman(cube, pacman_pos, self._direction, self._mouth_open)

    def tick(self, cube: Cube, dt: float, t: float) -> None:
        self._step_progress += dt / self.speed
        if self._step_progress >= 1.0:
            self._step_progress = max(0.0, self._step_progress - 1.0)
            self._step()

        self._render(cube)
