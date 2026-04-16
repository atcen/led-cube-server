"""
Generiert web/js/led_mapping.json aus config.py.
Ausführen: python scripts/export_mapping.py
"""
import json
import sys
import pathlib

# Projektroot zum Pfad hinzufügen
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from server.config import VIRTUAL_TO_BLOCK, VLED_POS_IN_BLOCK, BLOCK_WIDTHS, LEDS_TOTAL

# col_offsets[block_col] = Summe BLOCK_WIDTHS[:block_col]
col_offsets = []
acc = 0
for w in BLOCK_WIDTHS:
    col_offsets.append(acc)
    acc += w

mapping = []
for vled in range(LEDS_TOTAL):
    grid_row, block_col = VIRTUAL_TO_BLOCK[vled]
    sub_row, sub_col    = VLED_POS_IN_BLOCK[vled]
    x = col_offsets[block_col] + sub_col   # 0..31
    y = grid_row * 3 + sub_row             # 0..14
    mapping.append([x, y])

width  = sum(BLOCK_WIDTHS)  # 32
height = 5 * 3               # 15

out = {"mapping": mapping, "width": width, "height": height}

dest = pathlib.Path(__file__).parent.parent / "web" / "js" / "led_mapping.json"
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(json.dumps(out))
print(f"Geschrieben: {dest}  ({len(mapping)} Einträge, {width}×{height})")
