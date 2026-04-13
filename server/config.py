"""
Panel-Konfiguration für den WLED-Würfel.

6 Controller, jeder ein 5×5-Panel mit 480 LEDs.
Strip läuft geschlängelt: 3 physische Reihen = 1 Grid-Zeile.
LEDs pro Block je physischer Reihe: 6, 7, 6, 7, 6

Würfelaufbau:
  FRONT = w1   BACK  = w2
  LEFT  = w3   RIGHT = w4
  TOP   = w5   BOTTOM= w6
"""
from collections import defaultdict

CONTROLLERS = {
    0: "192.168.10.241",  # w1 FRONT
    1: "192.168.10.233",  # w2 BACK
    2: "192.168.10.207",  # w3 LEFT
    3: "192.168.10.208",  # w4 RIGHT
    4: "192.168.10.215",  # w5 TOP
    5: "192.168.10.204",  # w6 BOTTOM
}

FACE_NAMES   = {0: "FRONT", 1: "BACK", 2: "LEFT", 3: "RIGHT", 4: "TOP", 5: "BOTTOM"}
BLOCK_WIDTHS = [6, 7, 6, 7, 6]
GRID_ROWS    = 5
GRID_COLS    = 5
PHYS_ROWS    = GRID_ROWS * 3
LEDS_TOTAL   = 480
UDP_PORT     = 21324
FPS          = 30


def _build():
    physical_leds = []
    for phys_row in range(PHYS_ROWS):
        grid_row     = phys_row // 3
        sub_row      = phys_row % 3
        blocks_order = list(range(GRID_COLS)) if phys_row % 2 == 0 else list(reversed(range(GRID_COLS)))
        for block_col in blocks_order:
            for _ in range(BLOCK_WIDTHS[block_col]):
                physical_leds.append((grid_row, block_col, sub_row))

    block_sub_leds = defaultdict(list)
    for phys_idx, key in enumerate(physical_leds):
        block_sub_leds[key].append(phys_idx)

    segments        = []
    led_map         = []
    virtual_to_block = [None] * LEDS_TOTAL
    virtual_pos     = 0

    for grid_row in range(GRID_ROWS):
        for block_col in range(GRID_COLS):
            seg_start = virtual_pos
            for sub_row in range(3):
                leds = block_sub_leds[(grid_row, block_col, sub_row)]
                led_map.extend(leds)
                for vled in range(virtual_pos, virtual_pos + len(leds)):
                    virtual_to_block[vled] = (grid_row, block_col)
                virtual_pos += len(leds)
            segments.append({
                "id":        grid_row * GRID_COLS + block_col,
                "start":     seg_start,
                "stop":      virtual_pos,
                "grid_row":  grid_row,
                "block_col": block_col,
            })

    return segments, led_map, virtual_to_block


SEGMENTS, LED_MAP, VIRTUAL_TO_BLOCK = _build()
