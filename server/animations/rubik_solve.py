import math
import random

from ..config import BLOCK_WIDTHS, LEDS_TOTAL, VIRTUAL_TO_BLOCK, VLED_POS_IN_BLOCK
from ..cube import Cube
from .base import Animation

BLACK = [0, 0, 0]
FACE_COLORS = {
    0: [210, 45, 45],    # front
    1: [235, 120, 30],   # back
    2: [35, 140, 70],    # left
    3: [35, 85, 205],    # right
    4: [245, 210, 55],   # top
    5: [204, 204, 204],  # bottom
}
PANEL_W = sum(BLOCK_WIDTHS)
PANEL_H = 15


def _scale_color(color: list[int], factor: float) -> list[int]:
    return [max(0, min(255, int(channel * factor))) for channel in color]


def _rotate_point(point: tuple[float, float, float], axis: str, angle: float) -> tuple[float, float, float]:
    x, y, z = point
    c = math.cos(angle)
    s = math.sin(angle)

    if axis == "x":
        return (x, y * c - z * s, y * s + z * c)
    if axis == "y":
        return (x * c + z * s, y, -x * s + z * c)
    return (x * c - y * s, x * s + y * c, z)


def _rotate_int(point: tuple[int, int, int], axis: str, sign: int) -> tuple[int, int, int]:
    x, y, z = point
    if axis == "x":
        return (x, -z, y) if sign > 0 else (x, z, -y)
    if axis == "y":
        return (z, y, -x) if sign > 0 else (-z, y, x)
    return (-y, x, z) if sign > 0 else (y, -x, z)


def _physical_position(vled: int) -> tuple[int, int]:
    grid_row, block_col = VIRTUAL_TO_BLOCK[vled]
    sub_row, sub_col = VLED_POS_IN_BLOCK[vled]
    phys_row = grid_row * 3 + sub_row
    phys_col = sum(BLOCK_WIDTHS[:block_col]) + sub_col
    return phys_row, phys_col


def _surface_point(face: int, phys_row: int, phys_col: int) -> tuple[float, float, float]:
    x = ((phys_col + 0.5) / PANEL_W) * 2.0 - 1.0
    y = 1.0 - ((phys_row + 0.5) / PANEL_H) * 2.0

    if face == 0:
        return x, y, 1.0
    if face == 1:
        return -x, y, -1.0
    if face == 2:
        return -1.0, y, x
    if face == 3:
        return 1.0, y, -x
    if face == 4:
        return x, 1.0, -y
    return x, -1.0, y


def _to_index(value: float) -> int:
    return max(0, min(4, int((value + 1.0) * 2.5)))


def _point_to_face_row_col(point: tuple[float, float, float]) -> tuple[int, int, int]:
    x, y, z = point
    axis = max(range(3), key=lambda i: abs(point[i]))
    coord = point[axis]

    if axis == 2 and coord > 0:
        return 0, _to_index(-y), _to_index(x)
    if axis == 2:
        return 1, _to_index(-y), _to_index(-x)
    if axis == 0 and coord < 0:
        return 2, _to_index(-y), _to_index(z)
    if axis == 0:
        return 3, _to_index(-y), _to_index(-z)
    if coord > 0:
        return 4, _to_index(z), _to_index(x)
    return 5, _to_index(-z), _to_index(x)


def _coord_from_index(index: int) -> int:
    return index - 2


def _index_from_coord(coord: int) -> int:
    return coord + 2


def _layer_from_point(point: tuple[float, float, float], axis: str) -> int:
    value = {"x": point[0], "y": point[1], "z": point[2]}[axis]
    return max(-2, min(2, int((value + 1.0) * 2.5) - 2))


def _make_stickers() -> list[dict]:
    stickers = []
    for row in range(5):
        for col in range(5):
            x = _coord_from_index(col)
            y = _coord_from_index(4 - row)
            stickers.append({"pos": (x, y, 2), "normal": (0, 0, 1), "color": FACE_COLORS[0]})
            stickers.append({"pos": (2 - col, y, -2), "normal": (0, 0, -1), "color": FACE_COLORS[1]})
            stickers.append({"pos": (-2, y, _coord_from_index(col)), "normal": (-1, 0, 0), "color": FACE_COLORS[2]})
            stickers.append({"pos": (2, y, _coord_from_index(4 - col)), "normal": (1, 0, 0), "color": FACE_COLORS[3]})
            stickers.append({"pos": (_coord_from_index(col), 2, _coord_from_index(row)), "normal": (0, 1, 0), "color": FACE_COLORS[4]})
            stickers.append({"pos": (_coord_from_index(col), -2, _coord_from_index(4 - row)), "normal": (0, -1, 0), "color": FACE_COLORS[5]})
    return stickers


def _state_to_grid(stickers: list[dict]) -> dict[tuple[int, int, int], list[int]]:
    grid = {}
    for sticker in stickers:
        nx, ny, nz = sticker["normal"]
        x, y, z = sticker["pos"]

        if nz == 1:
            key = (0, _index_from_coord(-y), _index_from_coord(x))
        elif nz == -1:
            key = (1, _index_from_coord(-y), _index_from_coord(-x))
        elif nx == -1:
            key = (2, _index_from_coord(-y), _index_from_coord(z))
        elif nx == 1:
            key = (3, _index_from_coord(-y), _index_from_coord(-z))
        elif ny == 1:
            key = (4, _index_from_coord(z), _index_from_coord(x))
        else:
            key = (5, _index_from_coord(-z), _index_from_coord(x))

        grid[key] = list(sticker["color"])
    return grid


def _apply_move(stickers: list[dict], move: tuple[str, int, int]) -> list[dict]:
    axis, layer, sign = move
    axis_index = {"x": 0, "y": 1, "z": 2}[axis]
    next_stickers = []

    for sticker in stickers:
        pos = sticker["pos"]
        normal = sticker["normal"]
        if pos[axis_index] == layer:
            pos = _rotate_int(pos, axis, sign)
            normal = _rotate_int(normal, axis, sign)
        next_stickers.append({"pos": pos, "normal": normal, "color": list(sticker["color"])})

    return next_stickers


class RubikSolveAnimation(Animation):
    name = "rubik_solve"
    PARAMS = {
        "scramble_moves": {"type": "int",   "default": 18,  "min": 1,   "max": 40,  "step": 1,   "label": "Züge (Mischen)"},
        "turn_duration":  {"type": "float", "default": 0.7, "min": 0.1, "max": 3.0, "step": 0.1, "label": "Dreh-Dauer"},
        "turn_pause":     {"type": "float", "default": 0.22,"min": 0.0, "max": 1.0, "step": 0.05,"label": "Pause zwischen Zügen"},
        "solved_pause":   {"type": "float", "default": 3.0, "min": 0.5, "max": 10.0,"step": 0.5, "label": "Gelöst-Pause"},
    }

    def __init__(
        self,
        scramble_moves: int = 18,
        intro_duration: float = 1.1,
        turn_duration: float = 0.7,
        turn_pause: float = 0.22,
        start_pause: float = 2.0,
        solved_pause: float = 3.0,
    ):
        self.scramble_moves = scramble_moves
        self.intro_duration = intro_duration
        self.turn_duration = turn_duration
        self.turn_pause = turn_pause
        self.start_pause = start_pause
        self.solved_pause = solved_pause

    def start(self, cube: Cube) -> None:
        super().start(cube)
        self._led_points = {
            (face, vled): _surface_point(face, *_physical_position(vled))
            for face in range(6)
            for vled in range(LEDS_TOTAL)
        }
        self._reset_sequence()
        self._render_static(cube)

    def _reset_sequence(self) -> None:
        self._moves = self._build_scramble()
        self._base_grid = _state_to_grid(_make_stickers())
        stickers = _make_stickers()
        for move in self._moves:
            stickers = _apply_move(stickers, move)

        self._stickers = stickers
        self._grid = _state_to_grid(stickers)
        self._intro_order = list(self._grid.keys())
        random.shuffle(self._intro_order)
        self._solve_moves = [(axis, layer, -sign) for axis, layer, sign in reversed(self._moves)]
        self._move_index = 0
        self._phase = "intro"
        self._phase_elapsed = 0.0
        self._active_move = None
        self._move_grid = None

    def _build_scramble(self) -> list[tuple[str, int, int]]:
        moves = []
        last = None
        for _ in range(self.scramble_moves):
            while True:
                move = (
                    random.choice(["x", "y", "z"]),
                    random.randint(-2, 2),
                    random.choice([-1, 1]),
                )
                if last is None or move[:2] != last[:2]:
                    moves.append(move)
                    last = move
                    break
        return moves

    def _render_static(self, cube: Cube) -> None:
        cube.fill(BLACK)
        cube.leds.clear()
        for (face, row, col), color in self._grid.items():
            cube.set(face, row, col, color)

    def _render_solved_pulse(self, cube: Cube, progress: float) -> None:
        cube.fill(BLACK)
        cube.leds.clear()
        wave = 0.5 - 0.5 * math.cos(progress * math.tau * 2.0)
        pulse = 0.90 + 0.08 * wave
        for (face, row, col), color in self._grid.items():
            cube.set(face, row, col, _scale_color(color, pulse))

    def _render_intro(self, cube: Cube, progress: float) -> None:
        cube.fill(BLACK)
        cube.leds.clear()
        for (face, row, col), color in self._base_grid.items():
            cube.set(face, row, col, color)

        reveal_count = int(len(self._intro_order) * progress)

        for key in self._intro_order[:reveal_count]:
            cube.set(*key, self._grid[key])

    def _render_turn(self, cube: Cube, progress: float) -> None:
        cube.fill(BLACK)
        cube.leds.clear()

        eased = progress * progress * (3.0 - 2.0 * progress)
        axis, layer, sign = self._active_move
        angle = sign * eased * (math.pi / 2.0)

        for face in range(6):
            for vled in range(LEDS_TOTAL):
                point = self._led_points[(face, vled)]
                source = _rotate_point(point, axis, -angle)
                sample = source if _layer_from_point(source, axis) == layer else point
                sample_face, sample_row, sample_col = _point_to_face_row_col(sample)
                cube.leds[(face, vled)] = self._move_grid[(sample_face, sample_row, sample_col)]

    def tick(self, cube: Cube, dt: float, t: float) -> None:
        self._phase_elapsed += dt

        if self._phase == "intro":
            progress = min(1.0, self._phase_elapsed / self.intro_duration)
            self._render_intro(cube, progress)
            if progress >= 1.0:
                self._phase = "start_pause"
                self._phase_elapsed = 0.0
            return

        if self._phase == "start_pause":
            self._render_static(cube)
            if self._phase_elapsed >= self.start_pause:
                self._phase = "turn"
                self._phase_elapsed = 0.0
                self._active_move = self._solve_moves[self._move_index]
                self._move_grid = dict(self._grid)
            return

        if self._phase == "turn":
            progress = min(1.0, self._phase_elapsed / self.turn_duration)
            self._render_turn(cube, progress)
            if progress >= 1.0:
                self._stickers = _apply_move(self._stickers, self._active_move)
                self._grid = _state_to_grid(self._stickers)
                self._render_static(cube)
                self._move_index += 1
                self._phase = "pause"
                self._phase_elapsed = 0.0
            return

        if self._phase == "pause":
            done = self._move_index >= len(self._solve_moves)
            if done:
                progress = min(1.0, self._phase_elapsed / self.solved_pause) if self.solved_pause > 0 else 1.0
                self._render_solved_pulse(cube, progress)
            else:
                self._render_static(cube)
            pause_time = self.solved_pause if done else self.turn_pause
            if self._phase_elapsed >= pause_time:
                if done:
                    self._reset_sequence()
                    self._render_static(cube)
                else:
                    self._phase = "turn"
                    self._phase_elapsed = 0.0
                    self._active_move = self._solve_moves[self._move_index]
                    self._move_grid = dict(self._grid)
