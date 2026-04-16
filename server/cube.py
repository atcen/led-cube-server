"""
Virtuelles 3D-Modell des Würfels.

Koordinatensystem: (face, row, col)
  face: 0=FRONT, 1=BACK, 2=LEFT, 3=RIGHT, 4=TOP, 5=BOTTOM
  row:  0=oben, 4=unten  (von außen gesehen)
  col:  0=links, 4=rechts (von außen gesehen)

Kantenübergänge: wenn ein Objekt eine Fläche verlässt, auf welcher
Fläche und Position es weitergeht (+ neue Bewegungsrichtung).
"""

# Kantenübergänge: (face, kante) → (new_face, new_row, new_col, new_dir)
TRANSITIONS = {
    (0, 'N'): lambda r, c: (4, 4,   c,   'N'),
    (0, 'S'): lambda r, c: (5, 0,   c,   'S'),
    (0, 'W'): lambda r, c: (2, r,   4,   'W'),
    (0, 'E'): lambda r, c: (3, r,   0,   'E'),

    (1, 'N'): lambda r, c: (4, 0,   4-c, 'S'),
    (1, 'S'): lambda r, c: (5, 4,   4-c, 'N'),
    (1, 'W'): lambda r, c: (3, r,   4,   'W'),
    (1, 'E'): lambda r, c: (2, r,   0,   'E'),

    (2, 'N'): lambda r, c: (4, c,   0,   'E'),
    (2, 'S'): lambda r, c: (5, 4-c, 0,   'E'),
    (2, 'W'): lambda r, c: (1, r,   4,   'W'),
    (2, 'E'): lambda r, c: (0, r,   0,   'E'),

    (3, 'N'): lambda r, c: (4, 4-c, 4,   'W'),
    (3, 'S'): lambda r, c: (5, c,   4,   'W'),
    (3, 'W'): lambda r, c: (0, r,   4,   'W'),
    (3, 'E'): lambda r, c: (1, r,   0,   'E'),

    (4, 'N'): lambda r, c: (1, 0,   4-c, 'S'),
    (4, 'S'): lambda r, c: (0, 0,   c,   'S'),
    (4, 'W'): lambda r, c: (2, 0,   r,   'S'),
    (4, 'E'): lambda r, c: (3, 0,   4-r, 'S'),

    (5, 'N'): lambda r, c: (0, 4,   c,   'N'),
    (5, 'S'): lambda r, c: (1, 4,   4-c, 'N'),
    (5, 'W'): lambda r, c: (2, 4,   4-r, 'N'),
    (5, 'E'): lambda r, c: (3, 4,   r,   'N'),
}

TURN_LEFT  = {'N': 'W', 'W': 'S', 'S': 'E', 'E': 'N'}
TURN_RIGHT = {'N': 'E', 'E': 'S', 'S': 'W', 'W': 'N'}
OPPOSITE   = {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}


def move(face: int, row: int, col: int, direction: str) -> tuple:
    """Einen Schritt in Richtung direction — mit Kantenübergang."""
    dr = {'N': -1, 'S': 1,  'E': 0,  'W': 0 }[direction]
    dc = {'N': 0,  'S': 0,  'E': 1,  'W': -1}[direction]
    nr, nc = row + dr, col + dc
    if 0 <= nr <= 4 and 0 <= nc <= 4:
        return face, nr, nc, direction
    edge = 'N' if nr < 0 else 'S' if nr > 4 else 'W' if nc < 0 else 'E'
    return TRANSITIONS[(face, edge)](row, col)


class Cube:
    """Zustand aller 150 Blöcke (6 Flächen × 5×5)."""

    def __init__(self):
        self.blocks: dict[tuple, list] = {
            (f, r, c): [0, 0, 0]
            for f in range(6)
            for r in range(5)
            for c in range(5)
        }
        self.brightness: float = 1.0           # 0.0–1.0
        self.leds: dict[tuple, list] = {}      # (face, vled) → [r,g,b], überschreibt Blockfarbe

    def set(self, face: int, row: int, col: int, color: list) -> None:
        self.blocks[(face, row, col)] = color

    def get(self, face: int, row: int, col: int) -> list:
        return self.blocks[(face, row, col)]

    def fill(self, color: list) -> None:
        for key in self.blocks:
            self.blocks[key] = list(color)

    def fill_face(self, face: int, color: list) -> None:
        for r in range(5):
            for c in range(5):
                self.blocks[(face, r, c)] = list(color)
