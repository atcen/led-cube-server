import random

from ..cube import Cube, move
from .base import Animation

BLACK = [0, 0, 0]
ALIVE = [110, 210, 150]
NEWBORN = [180, 235, 200]


class GameOfLifeAnimation(Animation):
    name = "game_of_life"

    def __init__(self, speed: float = 0.35, density: float = 0.34, restart_delay: float = 1.0):
        self.speed = speed
        self.density = density
        self.restart_delay = restart_delay

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

        for pos, alive in self._grid.items():
            if not alive:
                continue
            face, row, col = pos
            color = NEWBORN if pos in self._newborns else ALIVE
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
