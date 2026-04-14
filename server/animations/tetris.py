"""Tetris-Animation auf allen 4 Seitenflächen des LED-Würfels."""
import random
from .base import Animation
from ..cube import Cube

SIDE_FACES = [0, 1, 2, 3]  # FRONT, BACK, LEFT, RIGHT

COLORS = [
    [0, 240, 240],   # Cyan (I)
    [240, 240, 0],   # Gelb (O)
    [160, 0, 240],   # Lila (T)
    [0, 240, 0],     # Grün (S)
    [240, 0, 0],     # Rot (Z)
    [0, 0, 240],     # Blau (J)
    [240, 160, 0],   # Orange (L)
]

TETROMINOES = {
    "I": [(0, 0), (1, 0), (2, 0), (3, 0)],
    "O": [(0, 0), (0, 1), (1, 0), (1, 1)],
    "T": [(0, 0), (0, 1), (0, 2), (1, 1)],
    "S": [(0, 1), (0, 2), (1, 0), (1, 1)],
    "Z": [(0, 0), (0, 1), (1, 1), (1, 2)],
    "J": [(0, 0), (1, 0), (1, 1), (1, 2)],
    "L": [(0, 2), (1, 0), (1, 1), (1, 2)],
}

ROWS = 5
COLS = 5
SPAWN_COL = 1


class TetrisAnimation(Animation):
    name = "tetris"
    PARAMS = {
        "speed": {"type": "float", "default": 0.6, "min": 0.1, "max": 3.0, "step": 0.1, "label": "Fallgeschwindigkeit", "description": "Sekunden pro Fall-Schritt"},
    }

    def __init__(self, speed: float = 0.6):
        self.speed = speed   # Sekunden pro Fall-Schritt

    def start(self, cube: Cube) -> None:
        super().start(cube)
        self.fall_speed = self.speed
        self._reset_game()

    def _reset_game(self) -> None:
        self.grid: list[list] = [[None] * COLS for _ in range(ROWS)]
        self.piece_bag: list[str] = []
        self.score = 0
        self.flash_rows: list[int] = []
        self.flash_timer = 0.0
        self.flash_duration = 0.25
        self.game_over = False
        self.game_over_timer = 0.0
        self.game_over_duration = 1.2
        self.fall_timer = 0.0
        self._spawn_piece()

    def _spawn_piece(self) -> bool:
        if not self.piece_bag:
            self.piece_bag = list(TETROMINOES.keys())
            random.shuffle(self.piece_bag)
        name = self.piece_bag.pop()
        self.piece_name = name
        self.piece_offsets = TETROMINOES[name]
        self.piece_color = random.choice(COLORS)
        self.piece_row = 0
        self.piece_col = SPAWN_COL
        self.target_plan = self._choose_best_plan()
        if not self._fits(self.piece_row, self.piece_col, self.piece_offsets):
            return False
        return True

    def _fits(self, row: int, col: int, offsets: list) -> bool:
        for dr, dc in offsets:
            r, c = row + dr, col + dc
            if r < 0 or r >= ROWS or c < 0 or c >= COLS:
                return False
            if self.grid[r][c] is not None:
                return False
        return True

    def _lock_piece(self) -> None:
        for dr, dc in self.piece_offsets:
            r, c = self.piece_row + dr, self.piece_col + dc
            if 0 <= r < ROWS and 0 <= c < COLS:
                self.grid[r][c] = list(self.piece_color)

    def _find_full_rows(self) -> list[int]:
        return [r for r in range(ROWS) if all(self.grid[r][c] is not None for c in range(COLS))]

    def _clear_rows(self, rows: list[int]) -> None:
        for r in sorted(rows, reverse=True):
            del self.grid[r]
            self.grid.insert(0, [None] * COLS)
        self.score += len(rows)

    def _rotate(self, offsets: list) -> list:
        # 90° im Uhrzeigersinn: (dr, dc) → (dc, -dr), dann normalisieren
        rotated = [(dc, -dr) for dr, dc in offsets]
        min_r = min(r for r, _ in rotated)
        min_c = min(c for _, c in rotated)
        return [(r - min_r, c - min_c) for r, c in rotated]

    def _try_rotate(self) -> None:
        new_offsets = self._rotate(self.piece_offsets)
        if self._fits(self.piece_row, self.piece_col, new_offsets):
            self.piece_offsets = new_offsets
        elif self._fits(self.piece_row, self.piece_col - 1, new_offsets):
            self.piece_offsets = new_offsets
            self.piece_col -= 1
        elif self._fits(self.piece_row, self.piece_col + 1, new_offsets):
            self.piece_offsets = new_offsets
            self.piece_col += 1

    def _unique_rotations(self, offsets: list) -> list[list]:
        rotations = []
        seen = set()
        current = offsets
        for _ in range(4):
            normalized = tuple(sorted(current))
            if normalized not in seen:
                seen.add(normalized)
                rotations.append(list(current))
            current = self._rotate(current)
        return rotations

    def _drop_row(self, col: int, offsets: list) -> int | None:
        row = 0
        if not self._fits(row, col, offsets):
            return None
        while self._fits(row + 1, col, offsets):
            row += 1
        return row

    def _simulate_lock(self, row: int, col: int, offsets: list) -> list[list]:
        trial = [list(line) for line in self.grid]
        for dr, dc in offsets:
            trial[row + dr][col + dc] = 1
        return trial

    def _count_full_rows(self, grid: list[list]) -> int:
        return sum(1 for r in range(ROWS) if all(grid[r][c] is not None for c in range(COLS)))

    def _column_heights(self, grid: list[list]) -> list[int]:
        heights = []
        for c in range(COLS):
            height = 0
            for r in range(ROWS):
                if grid[r][c] is not None:
                    height = ROWS - r
                    break
            heights.append(height)
        return heights

    def _count_holes(self, grid: list[list]) -> int:
        holes = 0
        for c in range(COLS):
            seen_block = False
            for r in range(ROWS):
                if grid[r][c] is not None:
                    seen_block = True
                elif seen_block:
                    holes += 1
        return holes

    def _surface_bumpiness(self, heights: list[int]) -> int:
        return sum(abs(heights[i] - heights[i + 1]) for i in range(len(heights) - 1))

    def _evaluate_position(self, row: int, col: int, offsets: list) -> tuple[float, int]:
        trial = self._simulate_lock(row, col, offsets)
        cleared = self._count_full_rows(trial)
        heights = self._column_heights(trial)
        holes = self._count_holes(trial)
        bumpiness = self._surface_bumpiness(heights)
        aggregate_height = sum(heights)
        max_height = max(heights)

        score = (
            cleared * 9.0
            - holes * 7.5
            - aggregate_height * 1.2
            - bumpiness * 1.0
            - max_height * 1.8
        )
        return score, cleared

    def _choose_best_plan(self) -> dict | None:
        best = None
        for rotation_index, offsets in enumerate(self._unique_rotations(self.piece_offsets)):
            min_c = min(dc for _, dc in offsets)
            max_c = max(dc for _, dc in offsets)
            for col in range(-min_c, COLS - max_c):
                row = self._drop_row(col, offsets)
                if row is None:
                    continue
                score, cleared = self._evaluate_position(row, col, offsets)
                plan = {
                    "score": score,
                    "cleared": cleared,
                    "rotations": rotation_index,
                    "col": col,
                    "row": row,
                    "offsets": offsets,
                }
                if best is None or plan["score"] > best["score"]:
                    best = plan
        return best

    def _steer_piece(self) -> None:
        if not self.target_plan:
            return

        target_offsets = self.target_plan["offsets"]
        for _ in range(4):
            if tuple(sorted(self.piece_offsets)) == tuple(sorted(target_offsets)):
                break
            before = (self.piece_col, tuple(sorted(self.piece_offsets)))
            self._try_rotate()
            after = (self.piece_col, tuple(sorted(self.piece_offsets)))
            if after == before:
                break

        while self.piece_col < self.target_plan["col"]:
            if not self._fits(self.piece_row, self.piece_col + 1, self.piece_offsets):
                break
            self.piece_col += 1

        while self.piece_col > self.target_plan["col"]:
            if not self._fits(self.piece_row, self.piece_col - 1, self.piece_offsets):
                break
            self.piece_col -= 1

    def tick(self, cube: Cube, dt: float, t: float) -> None:
        if self.game_over:
            self.game_over_timer += dt
            # Roter Bildschirm
            for face in SIDE_FACES:
                for r in range(ROWS):
                    for c in range(COLS):
                        cube.set(face, r, c, [220, 0, 0])
            for r in range(ROWS):
                for c in range(COLS):
                    cube.set(4, r, c, [0, 0, 0])
                    cube.set(5, r, c, [0, 0, 0])
            if self.game_over_timer >= self.game_over_duration:
                self._reset_game()
            return

        # Flash voller Zeilen
        if self.flash_rows:
            self.flash_timer += dt
            if self.flash_timer >= self.flash_duration:
                self._clear_rows(self.flash_rows)
                self.flash_rows = []
                self.flash_timer = 0.0
                if not self._spawn_piece():
                    self.game_over = True
                    self.game_over_timer = 0.0
            self._draw(cube, flash=True)
            return

        # Fall-Logik: zufällige horizontale Bewegung beim Fallen
        self.fall_timer += dt
        if self.fall_timer >= self.fall_speed:
            self.fall_timer = 0.0

            # Zielorientierte Platzierung statt Zufallsdrift
            self._steer_piece()

            # Nach unten fallen
            if self._fits(self.piece_row + 1, self.piece_col, self.piece_offsets):
                self.piece_row += 1
            else:
                self._lock_piece()
                full = self._find_full_rows()
                if full:
                    self.flash_rows = full
                    self.flash_timer = 0.0
                else:
                    if not self._spawn_piece():
                        self.game_over = True
                        self.game_over_timer = 0.0

        self._draw(cube, flash=False)

    def _draw(self, cube: Cube, flash: bool) -> None:
        # Spielfeld + aktives Tetromino auf alle 4 Seitenflächen
        active_cells: dict[tuple, list] = {}
        if not self.game_over:
            for dr, dc in self.piece_offsets:
                r, c = self.piece_row + dr, self.piece_col + dc
                if 0 <= r < ROWS and 0 <= c < COLS:
                    active_cells[(r, c)] = self.piece_color

        for face in SIDE_FACES:
            for r in range(ROWS):
                for c in range(COLS):
                    if flash and r in self.flash_rows:
                        color = [255, 255, 255]
                    elif (r, c) in active_cells:
                        color = active_cells[(r, c)]
                    elif self.grid[r][c] is not None:
                        color = self.grid[r][c]
                    else:
                        color = [0, 0, 0]
                    cube.set(face, r, c, color)

        # TOP: Score als Helligkeit
        brightness = min(255, self.score * 25)
        for r in range(ROWS):
            for c in range(COLS):
                cube.set(4, r, c, [brightness, brightness, brightness])

        # BOTTOM: schwarz
        for r in range(ROWS):
            for c in range(COLS):
                cube.set(5, r, c, [0, 0, 0])
