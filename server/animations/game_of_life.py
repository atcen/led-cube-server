import colorsys
import random

from ..cube import Cube, move
from .base import Animation

BLACK = [0, 0, 0]


class GameOfLifeAnimation(Animation):
    name = "game_of_life"
    PARAMS = {
        "speed":         {"type": "float", "default": 0.35, "min": 0.05, "max": 2.0, "step": 0.05, "label": "Schrittgeschwindigkeit"},
        "density":       {"type": "float", "default": 0.34, "min": 0.05, "max": 0.9, "step": 0.05, "label": "Startdichte"},
        "restart_delay": {"type": "float", "default": 1.0,  "min": 0.0,  "max": 5.0, "step": 0.5,  "label": "Neustart-Pause"},
        "hue":           {"type": "hue",   "default": 0.36, "label": "Zellfarbe"},
    }

    def __init__(self, speed: float = 0.35, density: float = 0.34, restart_delay: float = 1.0, hue: float = 0.36):
        self.speed = speed
        self.density = density
        self.restart_delay = restart_delay
        self.hue = hue   # 0=Rot, 0.08=Orange, 0.33=Grün, 0.5=Cyan, 0.66=Blau

    def start(self, cube: Cube) -> None:
        super().start(cube)
        self._elapsed = 0.0
        self._restart_timer = 0.0
        self._newborns = set()
        self._grid = self._random_grid()
        self._render(cube)

    def _random_grid(self) -> dict[tuple[int, int, int], bool]:
        grid = {}
        for face in range(6):
            for row in range(5):
                for col in range(5):
                    grid[(face, row, col)] = random.random() < self.density
        return grid

    def _neighbors(self, face: int, row: int, col: int) -> list[tuple[int, int, int]]:
        neighbors = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue

                pos = (face, row, col)
                if dr != 0:
                    pos = move(*pos, 'N' if dr < 0 else 'S')[:3]
                if dc != 0:
                    pos = move(*pos, 'W' if dc < 0 else 'E')[:3]
                neighbors.append(pos)
        return neighbors

    def _step(self) -> bool:
        next_grid = {}
        newborns = set()

        for face in range(6):
            for row in range(5):
                for col in range(5):
                    pos = (face, row, col)
                    alive = self._grid[pos]
                    count = sum(1 for npos in self._neighbors(face, row, col) if self._grid[npos])

                    next_alive = count == 3 or (alive and count == 2)
                    next_grid[pos] = next_alive
                    if next_alive and not alive:
                        newborns.add(pos)

        changed = next_grid != self._grid
        self._grid = next_grid
        self._newborns = newborns
        return changed

    def _render(self, cube: Cube) -> None:
        cube.fill(BLACK)
        cube.leds.clear()

        r_a, g_a, b_a = colorsys.hsv_to_rgb(self.hue, 0.45, 0.82)
        r_n, g_n, b_n = colorsys.hsv_to_rgb(self.hue, 0.22, 0.94)
        alive_color   = [round(r_a * 255), round(g_a * 255), round(b_a * 255)]
        newborn_color = [round(r_n * 255), round(g_n * 255), round(b_n * 255)]

        for pos, alive in self._grid.items():
            if not alive:
                continue
            face, row, col = pos
            color = newborn_color if pos in self._newborns else alive_color
            cube.set(face, row, col, color)

    def tick(self, cube: Cube, dt: float, t: float) -> None:
        self._elapsed += dt

        if self._elapsed < self.speed:
            return

        self._elapsed = 0.0
        changed = self._step()
        alive_cells = sum(self._grid.values())

        if alive_cells == 0 or not changed:
            self._restart_timer += self.speed
            if self._restart_timer >= self.restart_delay:
                self.start(cube)
                return
        else:
            self._restart_timer = 0.0

        self._render(cube)
