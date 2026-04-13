#!/usr/bin/env python3
"""
Würfel-Ausrichtungshilfe.
Jede Kante hat ein eindeutiges 3-Block-Muster (symmetrisch: X-Y-X).
Die zwei Panels die sich an einer Kante treffen zeigen das gleiche Muster.
Nur 4 Farben nötig: Rot, Grün, Blau, Orange.

Segment-IDs:
  top    = [1, 2, 3]     (row 0, col 1–3)
  bottom = [21, 22, 23]  (row 4, col 1–3)
  left   = [5, 10, 15]   (col 0, row 1–3)
  right  = [9, 14, 19]   (col 4, row 1–3)
"""
import json
import threading
import urllib.request

CONTROLLERS = {
    "w1 FRONT":  "192.168.10.241",
    "w2 BACK":   "192.168.10.233",
    "w3 LEFT":   "192.168.10.207",
    "w4 RIGHT":  "192.168.10.208",
    "w5 TOP":    "192.168.10.215",
    "w6 BOTTOM": "192.168.10.204",
}

R = [255,   0,   0]
G = [  0, 220,   0]
B = [  0,  80, 255]
O = [255, 130,   0]
_ = [  0,   0,   0]  # schwarz

TOP    = [1,  2,  3]
BOTTOM = [21, 22, 23]
LEFT   = [5,  10, 15]
RIGHT  = [9,  14, 19]

# 12 Kantenmuster (X-Y-X symmetrisch → gleich in beide Richtungen lesbar)
# Kante                 Muster
FRONT_TOP    = [R,G,R]
FRONT_BOTTOM = [G,R,G]
FRONT_LEFT   = [B,O,B]
FRONT_RIGHT  = [O,B,O]
BACK_TOP     = [R,B,R]
BACK_BOTTOM  = [B,R,B]
BACK_RIGHT   = [G,O,G]   # BACK west  ↔  RIGHT east
BACK_LEFT    = [O,G,O]   # BACK east  ↔  LEFT west
LEFT_TOP     = [R,O,R]
LEFT_BOTTOM  = [O,R,O]
RIGHT_TOP    = [G,B,G]
RIGHT_BOTTOM = [B,G,B]

# Pro Panel: [(seg_ids, muster), ...]
PANEL_EDGES = {
    "w1 FRONT":  [(TOP, FRONT_TOP),    (BOTTOM, FRONT_BOTTOM), (LEFT, FRONT_LEFT),   (RIGHT, FRONT_RIGHT)],
    "w2 BACK":   [(TOP, BACK_TOP),     (BOTTOM, BACK_BOTTOM),  (LEFT, BACK_RIGHT),   (RIGHT, BACK_LEFT)],
    "w3 LEFT":   [(TOP, LEFT_TOP),     (BOTTOM, LEFT_BOTTOM),  (LEFT, BACK_LEFT),    (RIGHT, FRONT_LEFT)],
    "w4 RIGHT":  [(TOP, RIGHT_TOP),    (BOTTOM, RIGHT_BOTTOM), (LEFT, FRONT_RIGHT),  (RIGHT, BACK_RIGHT)],
    "w5 TOP":    [(TOP, BACK_TOP),     (BOTTOM, FRONT_TOP),    (LEFT, LEFT_TOP),     (RIGHT, RIGHT_TOP)],
    "w6 BOTTOM": [(TOP, FRONT_BOTTOM), (BOTTOM, BACK_BOTTOM),  (LEFT, LEFT_BOTTOM),  (RIGHT, RIGHT_BOTTOM)],
}


def send(name, host):
    colors = {}
    for seg_ids, pattern in PANEL_EDGES[name]:
        for sid, color in zip(seg_ids, pattern):
            colors[sid] = color

    segs = [{"id": sid, "fx": 0, "col": [colors.get(sid, _), _, _]}
            for sid in range(25)]

    payload = json.dumps({"on": True, "bri": 220, "seg": segs}).encode()
    try:
        req = urllib.request.Request(
            f"http://{host}/json/state",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"{name}: {resp.read().decode()}")
    except Exception as e:
        print(f"{name}: FEHLER — {e}")


threads = [threading.Thread(target=send, args=(n, h)) for n, h in CONTROLLERS.items()]
for t in threads: t.start()
for t in threads: t.join()

print("""
Kantenmuster — gleiche Sequenz = gleiche Kante:
  R-G-R   FRONT oben    ↔  TOP unten
  G-R-G   FRONT unten   ↔  BOTTOM oben
  B-O-B   FRONT links   ↔  LEFT rechts
  O-B-O   FRONT rechts  ↔  RIGHT links
  R-B-R   BACK oben     ↔  TOP oben
  B-R-B   BACK unten    ↔  BOTTOM unten
  G-O-G   BACK links    ↔  RIGHT rechts
  O-G-O   BACK rechts   ↔  LEFT links
  R-O-R   LEFT oben     ↔  TOP links
  O-R-O   LEFT unten    ↔  BOTTOM links
  G-B-G   RIGHT oben    ↔  TOP rechts
  B-G-B   RIGHT unten   ↔  BOTTOM rechts
""")
