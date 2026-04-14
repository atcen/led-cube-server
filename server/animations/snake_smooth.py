"""
Snake-Smooth: Gleiche Spiellogik wie SnakeAnimation, aber weicher gerendert.

Pro LED wird die Farbe aus dem eigenen Block und den vier Nachbarblöcken
interpoliert — LEDs am Blockrand blenden in den Nachbarblock über.
Kopf hat Augen und eine rote Zunge im nächsten Block.
"""
from ..config import (LEDS_TOTAL, BLOCK_WIDTHS,
                      VIRTUAL_TO_BLOCK, BLOCK_TO_VLEDS, VLED_POS_IN_BLOCK)
from ..cube import Cube, move
from .snake import SnakeAnimation

# Wie stark die Randpixel in den Nachbarblock übergehen (0=kein Blend, 1=voll)
BLEND      = 0
# Ab welchem normalisierten Abstand vom Zentrum das Blending beginnt
THRESHOLD  = 0.30


def _edge_weight(proximity: float) -> float:
    """proximity=0: Mitte des Blocks, 1: Kante. Gibt Blend-Gewicht zurück."""
    if proximity < THRESHOLD:
        return 0.0
    return (proximity - THRESHOLD) / (1.0 - THRESHOLD) * BLEND


# Augenposition (sub_row, sub_col) relativ zur Bewegungsrichtung
# Augen sitzen an der Vorderkante des Kopf-Blocks
def _eye_positions(direction: str, width: int) -> list[tuple]:
    return {
        'E': [(0, width - 1), (2, width - 1)],
        'W': [(0, 0),         (2, 0)],
        'S': [(2, 1),         (2, width - 2)],
        'N': [(0, 1),         (0, width - 2)],
    }[direction]


# Welche Sub-Position ist die Eintrittskante des nächsten Blocks
# (nach dem Übergang mit Richtung nd)
def _is_tongue_pixel(nd: str, sub_row: int, sub_col: int, width: int) -> bool:
    if nd == 'E':
        return sub_col <= 1 and sub_row == 1
    if nd == 'W':
        return sub_col >= width - 2 and sub_row == 1
    if nd == 'S':
        mid = width // 2
        return sub_row == 0 and abs(sub_col - mid) <= 1
    if nd == 'N':
        mid = width // 2
        return sub_row == 2 and abs(sub_col - mid) <= 1
    return False


class SnakeSmoothAnimation(SnakeAnimation):
    name = "snake_smooth"

    def tick(self, cube: Cube, dt: float, t: float) -> None:
        # Spiellogik aus SnakeAnimation (setzt cube.blocks)
        super().tick(cube, dt, t)

        cube.leds.clear()

        # Im Tod-Zustand zeigt der Parent schon cube.fill(RED) — kein LED-Override nötig
        if self.dead:
            return

        bri = cube.brightness  # nicht nochmal skalieren — Renderer macht das

        # ── Gradient-Rendering ────────────────────────────────────────────
        for face in range(6):
            blocks = cube.blocks
            leds   = cube.leds

            for vled in range(LEDS_TOTAL):
                gr, bc       = VIRTUAL_TO_BLOCK[vled]
                sub_row, sub_col = VLED_POS_IN_BLOCK[vled]
                width        = BLOCK_WIDTHS[bc]

                base = blocks[(face, gr, bc)]

                # Normierte Position [0,1] im Block
                sy = sub_row / 2.0
                sx = sub_col / (width - 1) if width > 1 else 0.5

                wN = _edge_weight(1.0 - sy)   # Nähe zur oberen Kante
                wS = _edge_weight(sy)          # Nähe zur unteren Kante
                wW = _edge_weight(1.0 - sx)    # Nähe zur linken Kante
                wE = _edge_weight(sx)          # Nähe zur rechten Kante

                def nb(ngr, nbc):
                    if 0 <= ngr < 5 and 0 <= nbc < 5:
                        return blocks[(face, ngr, nbc)]
                    return [0, 0, 0]

                cN = nb(gr - 1, bc)
                cS = nb(gr + 1, bc)
                cW = nb(gr, bc - 1)
                cE = nb(gr, bc + 1)

                total = 1.0 + wN + wS + wW + wE
                r = (base[0] + wN*cN[0] + wS*cS[0] + wW*cW[0] + wE*cE[0]) / total
                g = (base[1] + wN*cN[1] + wS*cS[1] + wW*cW[1] + wE*cE[1]) / total
                b = (base[2] + wN*cN[2] + wS*cS[2] + wW*cW[2] + wE*cE[2]) / total

                leds[(face, vled)] = [round(r), round(g), round(b)]

        # ── Augen ─────────────────────────────────────────────────────────
        face, row, col = self.face, self.row, self.col
        width     = BLOCK_WIDTHS[col]
        eye_set   = set(_eye_positions(self.direction, width))

        for vled in BLOCK_TO_VLEDS[(row, col)]:
            if VLED_POS_IN_BLOCK[vled] in eye_set:
                cube.leds[(face, vled)] = [255, 255, 160]  # warmes Weiß

        # ── Zunge ─────────────────────────────────────────────────────────
        nf, nr, nc, nd = move(face, row, col, self.direction)
        if 0 <= nr < 5 and 0 <= nc < 5:
            tw = BLOCK_WIDTHS[nc]
            tongue_vleds = [
                v for v in BLOCK_TO_VLEDS[(nr, nc)]
                if _is_tongue_pixel(nd, *VLED_POS_IN_BLOCK[v], tw)
            ]
            for vled in tongue_vleds[:2]:
                cube.leds[(nf, vled)] = [255, 40, 40]   # rot
