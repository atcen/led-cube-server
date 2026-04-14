"""
Snake-Animation über alle 6 Würfelflächen.

Smooth: Kopf faded pro Frame rein, Schwanz faded raus.
Der Übergang läuft software-seitig über die step_progress (0→1).

Futter: grüner Punkt — beim Fressen wächst die Snake um GROW_PER_FOOD Blöcke.
Kollision (alle 4 Richtungen blockiert): 1 Sekunde rot, dann Neustart.
"""
import colorsys
import random
from ..cube import Cube, move, TURN_LEFT, TURN_RIGHT, OPPOSITE
from .base import Animation, lerp_color

BLACK         = [0, 0, 0]
RED           = [255, 0, 0]
GROW_PER_FOOD = 3    # Blöcke Wachstum pro Futter
DEATH_DURATION = 1.0 # Sekunden roter Screen


class SnakeAnimation(Animation):
    name = "snake"
    PARAMS = {
        "start_length": {"type": "int",   "default": 5,    "min": 1,    "max": 20,  "step": 1,    "label": "Startlänge"},
        "speed":        {"type": "float", "default": 0.5,  "min": 0.05, "max": 3.0, "step": 0.05, "label": "Geschwindigkeit", "description": "Sekunden pro Schritt"},
        "hue":          {"type": "hue",   "default": 0.08, "label": "Körperfarbe"},
    }

    def __init__(self, start_length: int = 5, speed: float = 0.5, hue: float = 0.08):
        self.start_length = start_length
        self.speed        = speed   # Sekunden pro Schritt
        self.hue          = hue     # Basis-Farbton des Körpers (0=Rot, 0.08=Orange, 0.33=Grün, 0.66=Blau)

    def start(self, cube: Cube) -> None:
        cube.fill(BLACK)
        self.length        = self.start_length
        self.body          = [(0, 2, 2)]
        self.face          = 0
        self.row           = 2
        self.col           = 2
        self.direction     = 'E'
        self.step_progress = 0.0
        self.old_tail      = None
        self.old_tail_color = BLACK
        self.pending_growth = 0
        self.dead          = False
        self.death_timer   = 0.0
        self.food          = self._place_food()

    def _place_food(self) -> tuple:
        all_positions = [(f, r, c) for f in range(6) for r in range(5) for c in range(5)]
        free = [p for p in all_positions if p not in self.body]
        return random.choice(free)

    def _body_color(self, i: int) -> list:
        """Farbgradient: Kopf=weiß, Körper hue→dunkel."""
        if i == 0:
            return [255, 255, 255]
        t   = (i - 1) / max(self.length - 2, 1)
        hue = self.hue * (1.0 - t)
        val = 1.0 - t * 0.8
        r, g, b = colorsys.hsv_to_rgb(hue, 1.0, val)
        return [round(r * 255), round(g * 255), round(b * 255)]

    def _bfs_first_step(self) -> str | None:
        """BFS vom Kopf zum Futter. Gibt die erste Richtung zurück, oder None."""
        start  = (self.face, self.row, self.col)
        target = self.food
        blocked = set(self.body)

        # (position, erste Richtung vom Start)
        queue   = [(start, None)]
        visited = {start}

        while queue:
            (f, r, c), first_dir = queue.pop(0)
            for d in ('N', 'S', 'E', 'W'):
                nf, nr, nc, _ = move(f, r, c, d)
                pos = (nf, nr, nc)
                if pos in visited or pos in blocked:
                    continue
                step_dir = d if first_dir is None else first_dir
                if pos == target:
                    return step_dir
                visited.add(pos)
                queue.append((pos, step_dir))
        return None

    def _advance(self) -> bool:
        """Snake einen Schritt weiterrücken. Gibt False zurück bei Kollision."""
        dirs = [self.direction,
                TURN_LEFT[self.direction],
                TURN_RIGHT[self.direction],
                OPPOSITE[self.direction]]

        # BFS-Richtung bevorzugen, sonst erste freie Richtung
        bfs_dir = self._bfs_first_step()
        if bfs_dir:
            candidate_dirs = [bfs_dir] + [d for d in dirs if d != bfs_dir]
        else:
            candidate_dirs = dirs

        for d in candidate_dirs:
            nf, nr, nc, nd = move(self.face, self.row, self.col, d)
            if (nf, nr, nc) not in self.body:
                self.face, self.row, self.col, self.direction = nf, nr, nc, nd
                break
        else:
            return False  # alle 4 Richtungen blockiert → Kollision

        new_head = (self.face, self.row, self.col)
        self.body.insert(0, new_head)

        # Futter gefressen?
        if new_head == self.food:
            self.pending_growth += GROW_PER_FOOD
            self.food = self._place_food()

        # Schwanz kürzen — außer wenn Snake wachsen soll
        if self.pending_growth > 0:
            self.pending_growth -= 1
            self.length += 1
            self.old_tail = None
        elif len(self.body) > self.length:
            self.old_tail       = self.body.pop()
            self.old_tail_color = self._body_color(self.length - 1)
        else:
            self.old_tail = None

        return True

    def tick(self, cube: Cube, dt: float, t: float) -> None:
        # Tod-Zustand: roter Screen, dann Neustart
        if self.dead:
            self.death_timer += dt
            cube.fill(RED)
            if self.death_timer >= DEATH_DURATION:
                self.start(cube)
            return

        self.step_progress += dt / self.speed
        if self.step_progress >= 1.0:
            alive = self._advance()
            self.step_progress = max(0.0, self.step_progress - 1.0)
            if not alive:
                self.dead        = True
                self.death_timer = 0.0
                return

        p = self.step_progress  # 0=Schrittbeginn, 1=Schrittende

        cube.fill(BLACK)

        # Futter (blinkt leicht)
        ff, fr, fc = self.food
        food_bri = 0.6 + 0.4 * abs((p * 2) % 2 - 1)
        cube.set(ff, fr, fc, [0, round(255 * food_bri), 0])

        # Körper
        for i, (f, r, c) in enumerate(self.body):
            color = self._body_color(i)
            if i == 0:
                color = lerp_color(BLACK, color, p)
            cube.set(f, r, c, color)

        # Alter Schwanz faded raus
        if self.old_tail:
            f, r, c = self.old_tail
            color   = lerp_color(self.old_tail_color, BLACK, p)
            cube.set(f, r, c, color)
