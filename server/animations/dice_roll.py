import random
import math
import colorsys
from .base import Animation
from ..cube import Cube
from ..config import BLOCK_TO_VLEDS, VLED_POS_IN_BLOCK, BLOCK_WIDTHS


class DiceRollAnimation(Animation):
    name = "dice_roll"
    PARAMS = {
        "roll_duration": {"type": "float", "default": 3.5, "min": 1.0, "max": 8.0, "step": 0.5, "label": "Rolldauer (s)"},
        "hue":           {"type": "hue",   "default": 0.05, "label": "Farbe"},
    }

    # Pip-Positionen im 5×5-Grid (row, col) — zentriert im 3×3-Bereich
    PIPS = {
        1: [(2, 2)],
        2: [(1, 3), (3, 1)],
        3: [(1, 3), (2, 2), (3, 1)],
        4: [(1, 1), (1, 3), (3, 1), (3, 3)],
        5: [(1, 1), (1, 3), (2, 2), (3, 1), (3, 3)],
        6: [(1, 1), (1, 2), (1, 3), (3, 1), (3, 2), (3, 3)],
    }

    # Reihenfolge in der Flächen einrasten (TOP kommt zuletzt)
    LOCK_ORDER = [2, 3, 0, 1, 5, 4]  # LEFT, RIGHT, FRONT, BACK, BOTTOM, TOP

    def __init__(self, roll_duration=3.5, hue=0.05):
        self.duration = roll_duration
        self.hue = hue
        self.start_t = -1.0
        self.result = 1
        self.face_vals = [1] * 6
        self.locked = [False] * 6
        self.flash_t = [-999.0] * 6

    def start(self, cube: Cube):
        self.start_t = -1.0
        self.result = random.randint(1, 6)
        opp = 7 - self.result
        sides = [v for v in range(1, 7) if v not in (self.result, opp)]
        random.shuffle(sides)
        self.face_vals = [
            sides[0],     # FRONT
            sides[1],     # BACK
            sides[2],     # LEFT
            sides[3],     # RIGHT
            self.result,  # TOP
            opp,          # BOTTOM
        ]
        self.locked = [False] * 6
        self.flash_t = [-999.0] * 6
        cube.fill([0, 0, 0])
        cube.leds.clear()

    def _pip_color(self, brightness=1.0):
        r, g, b = colorsys.hsv_to_rgb(self.hue, 0.9, brightness)
        return [int(r * 255), int(g * 255), int(b * 255)]

    def _bg_color(self, brightness=1.0):
        r, g, b = colorsys.hsv_to_rgb((self.hue + 0.5) % 1.0, 0.65, brightness)
        return [int(r * 255), int(g * 255), int(b * 255)]

    def _draw_face(self, cube, face, val, pip_v, bg_v, flash=0.0):
        if flash > 0.0:
            v = int(255 * flash)
            white = [v, v, v]
            for r in range(5):
                for c in range(5):
                    cube.set(face, r, c, white)
            return

        bg = self._bg_color(bg_v)
        pip = self._pip_color(pip_v)

        # Hintergrund auf alle Blöcke
        for r in range(5):
            for c in range(5):
                cube.set(face, r, c, bg)

        # Pip-Blöcke: kreisförmiger LED-Falloff innerhalb jedes Blocks
        for pr, pc in self.PIPS[val]:
            w = BLOCK_WIDTHS[pc]
            cx = 1.0           # sub_row-Mitte (bei 3 Reihen: Index 1)
            cy = (w - 1) / 2.0  # sub_col-Mitte
            radius = 1.5       # in Pixel-Einheiten (Reihenabstand = 1)

            for vled in BLOCK_TO_VLEDS.get((pr, pc), []):
                sr, sc = VLED_POS_IN_BLOCK[vled]
                dist = math.sqrt((sr - cx) ** 2 + (sc - cy) ** 2)
                alpha = max(0.0, 1.0 - dist / radius)
                alpha = alpha ** 0.6  # weicherer Abfall
                color = [int(bg[i] * (1.0 - alpha) + pip[i] * alpha) for i in range(3)]
                cube.leds[(face, vled)] = color

    def tick(self, cube: Cube, dt: float, t: float):
        if self.start_t < 0.0:
            self.start_t = t

        elapsed = t - self.start_t
        progress = min(1.0, elapsed / self.duration)
        roll_frac = 1.0 - progress  # 1 → 0

        # Wechselgeschwindigkeit: 20/s am Anfang → 2/s kurz vor Ende
        speed = 2.0 + (roll_frac ** 0.6) * 18.0
        tick_idx = int(elapsed * speed)

        # Flächen rasten nacheinander ein, ab 60% Fortschritt
        lock_start = 0.60
        n = len(self.LOCK_ORDER)
        for i, f in enumerate(self.LOCK_ORDER):
            threshold = lock_start + i * (0.38 / n)
            if progress >= threshold and not self.locked[f]:
                self.locked[f] = True
                self.flash_t[f] = t

        # LED-Overrides aus dem letzten Frame löschen
        cube.leds.clear()

        for f in range(6):
            if self.locked[f]:
                flash_age = t - self.flash_t[f]
                flash = max(0.0, 1.0 - flash_age * 5.0)
                if progress >= 1.0:
                    pulse = 0.75 + 0.25 * math.sin(t * 3.0)
                    self._draw_face(cube, f, self.face_vals[f], pulse, 0.18, flash)
                else:
                    self._draw_face(cube, f, self.face_vals[f], 0.9, 0.18, flash)
            else:
                roll_val = ((tick_idx + f * 7) % 6) + 1
                v = 0.25 + roll_frac * 0.55
                self._draw_face(cube, f, roll_val, v, v * 0.35)
