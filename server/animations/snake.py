"""
Snake-Animation über alle 6 Würfelflächen.

Smooth: Kopf faded pro Frame rein, Schwanz faded raus.
Der Übergang läuft software-seitig über die step_progress (0→1).
"""
import colorsys
from ..cube import Cube, move, TURN_LEFT, TURN_RIGHT, OPPOSITE
from .base import Animation, lerp_color

BLACK = [0, 0, 0]


class SnakeAnimation(Animation):
    name = "snake"

    def __init__(self, length: int = 12, speed: float = 0.5):
        self.length = length
        self.speed  = speed          # Sekunden pro Schritt

    def start(self, cube: Cube) -> None:
        cube.fill(BLACK)
        self.body         = [(0, 2, 2)]
        self.face         = 0
        self.row          = 2
        self.col          = 2
        self.direction    = 'E'
        self.step_progress = 0.0     # 0.0 → 1.0 innerhalb eines Schritts
        self.old_tail     = None
        self.old_tail_color = BLACK

    def _body_color(self, i: int) -> list:
        """Farbgradient: Kopf=weiß, Körper gelb→rot→dunkel."""
        if i == 0:
            return [255, 255, 255]
        t   = (i - 1) / max(self.length - 2, 1)
        hue = 0.08 * (1.0 - t)
        val = 1.0 - t * 0.8
        r, g, b = colorsys.hsv_to_rgb(hue, 1.0, val)
        return [round(r * 255), round(g * 255), round(b * 255)]

    def _advance(self) -> None:
        """Snake einen Schritt weiterrücken."""
        dirs = [self.direction,
                TURN_LEFT[self.direction],
                TURN_RIGHT[self.direction],
                OPPOSITE[self.direction]]

        for d in dirs:
            nf, nr, nc, nd = move(self.face, self.row, self.col, d)
            if (nf, nr, nc) not in self.body:
                self.face, self.row, self.col, self.direction = nf, nr, nc, nd
                break
        else:
            self.face, self.row, self.col, self.direction = move(
                self.face, self.row, self.col, dirs[0])[:4]

        self.body.insert(0, (self.face, self.row, self.col))
        if len(self.body) > self.length:
            self.old_tail       = self.body.pop()
            self.old_tail_color = self._body_color(self.length - 1)
        else:
            self.old_tail = None

    def tick(self, cube: Cube, dt: float, t: float) -> None:
        self.step_progress += dt / self.speed
        if self.step_progress >= 1.0:
            self._advance()
            self.step_progress = max(0.0, self.step_progress - 1.0)

        p = self.step_progress  # 0=Schrittbeginn, 1=Schrittende

        # Alle Körperteile setzen
        for i, (f, r, c) in enumerate(self.body):
            color = self._body_color(i)
            if i == 0:
                # Kopf faded rein
                color = lerp_color(BLACK, color, p)
            cube.set(f, r, c, color)

        # Alter Schwanz faded raus
        if self.old_tail:
            f, r, c = self.old_tail
            color   = lerp_color(self.old_tail_color, BLACK, p)
            cube.set(f, r, c, color)
