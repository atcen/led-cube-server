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
import socket
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

MDNS_HOSTS = {
    0: ("w6.local", "192.168.10.106"),  # FRONT
    1: ("w5.local", "192.168.10.105"),  # BACK
    2: ("w3.local", "192.168.10.103"),  # LEFT
    3: ("w1.local", "192.168.10.101"),  # RIGHT
    4: ("w4.local", "192.168.10.104"),  # TOP
    5: ("w2.local", "192.168.10.102"),  # BOTTOM
}


def _resolve_one(face_id: int, hostname: str, fallback_ip: str) -> tuple[int, str]:
    try:
        ip = socket.getaddrinfo(hostname, None, socket.AF_INET)[0][4][0]
        print(f"  {hostname} → {ip}")
    except OSError:
        ip = fallback_ip
        print(f"  {hostname} → {ip} (Fallback, mDNS nicht erreichbar)")
    return face_id, ip


def _resolve_controllers() -> dict[int, str]:
    result = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {
            pool.submit(_resolve_one, face_id, hostname, fallback_ip): face_id
            for face_id, (hostname, fallback_ip) in MDNS_HOSTS.items()
        }
        for future in as_completed(futures):
            face_id, ip = future.result()
            result[face_id] = ip
    return result


print("Löse Controller-IPs auf...")
CONTROLLERS = _resolve_controllers()

FACE_NAMES   = {0: "FRONT", 1: "BACK", 2: "LEFT", 3: "RIGHT", 4: "TOP", 5: "BOTTOM"}
BLOCK_WIDTHS = [6, 7, 6, 7, 6]
GRID_ROWS    = 5
GRID_COLS    = 5
PHYS_ROWS    = GRID_ROWS * 3
LEDS_TOTAL   = 480
UDP_PORT     = 21324
FPS          = 15


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

    segments         = []
    led_map          = []
    virtual_to_block  = [None] * LEDS_TOTAL
    vled_pos_in_block = [None] * LEDS_TOTAL   # (sub_row, sub_col_spatial)
    block_to_vleds   = defaultdict(list)       # (grid_row, block_col) → [vled, ...]
    virtual_pos      = 0

    for grid_row in range(GRID_ROWS):
        for block_col in range(GRID_COLS):
            seg_start = virtual_pos
            width     = BLOCK_WIDTHS[block_col]
            for sub_row in range(3):
                phys_row = grid_row * 3 + sub_row
                is_rtl   = (phys_row % 2 == 1)
                leds     = block_sub_leds[(grid_row, block_col, sub_row)]
                led_map.extend(leds)
                for i, vled in enumerate(range(virtual_pos, virtual_pos + len(leds))):
                    virtual_to_block[vled]  = (grid_row, block_col)
                    block_to_vleds[(grid_row, block_col)].append(vled)
                    sub_col = (width - 1 - i) if is_rtl else i
                    vled_pos_in_block[vled] = (sub_row, sub_col)
                virtual_pos += len(leds)
            segments.append({
                "id":        grid_row * GRID_COLS + block_col,
                "start":     seg_start,
                "stop":      virtual_pos,
                "grid_row":  grid_row,
                "block_col": block_col,
            })

    return segments, led_map, virtual_to_block, dict(block_to_vleds), vled_pos_in_block


SEGMENTS, LED_MAP, VIRTUAL_TO_BLOCK, BLOCK_TO_VLEDS, VLED_POS_IN_BLOCK = _build()
