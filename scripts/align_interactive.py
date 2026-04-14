#!/usr/bin/env python3
"""
Interaktive Würfel-Ausrichtungshilfe.

Enter/Space → nächste Fläche
b / Backspace → vorherige Fläche
q → beenden

Pro Fläche:
  - Aktive Fläche: alle 4 Kanten eingefärbt
  - Angrenzende Flächen: nur die verbindende Kante eingefärbt (gleiche Farbe)
  - Alle anderen Flächen: schwarz
"""
import json
import sys
import threading
import termios
import tty
import urllib.request

CONTROLLERS = {
    0: ("192.168.10.241", "w1 FRONT"),
    1: ("192.168.10.233", "w2 BACK"),
    2: ("192.168.10.207", "w3 LEFT"),
    3: ("192.168.10.208", "w4 RIGHT"),
    4: ("192.168.10.215", "w5 TOP"),
    5: ("192.168.10.204", "w6 BOTTOM"),
}

R = [255,   0,   0]
G = [  0, 220,   0]
B = [  0,  80, 255]
O = [255, 130,   0]
_ = [  0,   0,   0]

T  = [1,  2,  3]    # top segs
Bo = [21, 22, 23]   # bottom segs
L  = [5,  10, 15]   # left segs
Ri = [9,  14, 19]   # right segs

# Kantenfarben (X-Y-X Muster)
FRONT_TOP    = [R,G,R];  FRONT_BOTTOM = [G,R,G]
FRONT_LEFT   = [B,O,B];  FRONT_RIGHT  = [O,B,O]
BACK_TOP     = [R,B,R];  BACK_BOTTOM  = [B,R,B]
BACK_RIGHT   = [G,O,G];  BACK_LEFT    = [O,G,O]
LEFT_TOP     = [R,O,R];  LEFT_BOTTOM  = [O,R,O]
RIGHT_TOP    = [G,B,G];  RIGHT_BOTTOM = [B,G,B]

# Pro Fläche: eigene Kanten + welche Kante auf welcher Nachbarfläche
# Format: { edge_name: (segs, pattern, neighbor_face, neighbor_segs) }
FACES = {
    0: {
        "name": "FRONT (w1)",
        "edges": {
            "oben":   (T,  FRONT_TOP,    4, Bo, "TOP unten"),
            "unten":  (Bo, FRONT_BOTTOM, 5, T,  "BOTTOM oben"),
            "links":  (L,  FRONT_LEFT,   2, Ri, "LEFT rechts"),
            "rechts": (Ri, FRONT_RIGHT,  3, L,  "RIGHT links"),
        },
    },
    1: {
        "name": "BACK (w2)",
        "edges": {
            "oben":   (T,  BACK_TOP,    4, T,  "TOP oben"),
            "unten":  (Bo, BACK_BOTTOM, 5, Bo, "BOTTOM unten"),
            "links":  (L,  BACK_RIGHT,  3, Ri, "RIGHT rechts"),
            "rechts": (Ri, BACK_LEFT,   2, L,  "LEFT links"),
        },
    },
    2: {
        "name": "LEFT (w3)",
        "edges": {
            "oben":   (T,  LEFT_TOP,    4, L,  "TOP links"),
            "unten":  (Bo, LEFT_BOTTOM, 5, L,  "BOTTOM links"),
            "links":  (L,  BACK_LEFT,   1, Ri, "BACK rechts"),
            "rechts": (Ri, FRONT_LEFT,  0, L,  "FRONT links"),
        },
    },
    3: {
        "name": "RIGHT (w4)",
        "edges": {
            "oben":   (T,  RIGHT_TOP,    4, Ri, "TOP rechts"),
            "unten":  (Bo, RIGHT_BOTTOM, 5, Ri, "BOTTOM rechts"),
            "links":  (L,  FRONT_RIGHT,  0, Ri, "FRONT rechts"),
            "rechts": (Ri, BACK_RIGHT,   1, L,  "BACK links"),
        },
    },
    4: {
        "name": "TOP (w5)",
        "edges": {
            "oben":   (T,  BACK_TOP,   1, T,  "BACK oben"),
            "unten":  (Bo, FRONT_TOP,  0, T,  "FRONT oben"),
            "links":  (L,  LEFT_TOP,   2, T,  "LEFT oben"),
            "rechts": (Ri, RIGHT_TOP,  3, T,  "RIGHT oben"),
        },
    },
    5: {
        "name": "BOTTOM (w6)",
        "edges": {
            "oben":   (T,  FRONT_BOTTOM, 0, Bo, "FRONT unten"),
            "unten":  (Bo, BACK_BOTTOM,  1, Bo, "BACK unten"),
            "links":  (L,  LEFT_BOTTOM,  2, Bo, "LEFT unten"),
            "rechts": (Ri, RIGHT_BOTTOM, 3, Bo, "RIGHT unten"),
        },
    },
}


def send(face_id: int, seg_colors: dict) -> None:
    host, _ = CONTROLLERS[face_id]
    segs = [{"id": i, "fx": 0, "col": [seg_colors.get(i, _), _, _]}
            for i in range(25)]
    payload = json.dumps({"on": True, "bri": 220, "transition": 0, "seg": segs}).encode()
    try:
        req = urllib.request.Request(
            f"http://{host}/json/state",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"\n  Fehler {host}: {e}")


def show_face(face_id: int) -> None:
    face   = FACES[face_id]
    # Alle Panels schwarz vorbereiten
    all_colors = {f: {} for f in range(6)}

    # Aktive Fläche: alle 4 Kanten
    for edge_name, (segs, pattern, neighbor, n_segs, n_label) in face["edges"].items():
        for sid, color in zip(segs, pattern):
            all_colors[face_id][sid] = color
        # Nachbarfläche: nur die verbindende Kante
        for sid, color in zip(n_segs, pattern):
            all_colors[neighbor][sid] = color

    # Parallel senden
    threads = [threading.Thread(target=send, args=(f, all_colors[f])) for f in range(6)]
    for t in threads: t.start()
    for t in threads: t.join()

    # Ausgabe
    print(f"\n{'━'*42}")
    print(f"  Aktive Fläche: {face['name']}")
    print(f"{'━'*42}")
    for edge_name, (segs, pattern, neighbor, n_segs, n_label) in face["edges"].items():
        _, n_name = CONTROLLERS[neighbor]
        names = ["R","G","B","O"]
        def cn(c):
            if c==R: return "\033[31mR\033[0m"
            if c==G: return "\033[32mG\033[0m"
            if c==B: return "\033[34mB\033[0m"
            return "\033[33mO\033[0m"
        pat = "-".join(cn(c) for c in pattern)
        print(f"  {edge_name:7s}: {pat}  →  {n_name} ({n_label})")
    print()
    print("  Enter/Space=weiter  b=zurück  q=beenden")


def getch() -> str:
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch


def main():
    current = 0
    show_face(current)
    while True:
        ch = getch()
        if ch in ('q', '\x03'):
            print("\nBeende — alles aus.")
            threads = [threading.Thread(target=send, args=(f, {})) for f in range(6)]
            for t in threads: t.start()
            for t in threads: t.join()
            break
        elif ch in ('\r', '\n', ' '):
            current = (current + 1) % 6
            show_face(current)
        elif ch in ('b', '\x7f'):
            current = (current - 1) % 6
            show_face(current)


if __name__ == "__main__":
    main()
