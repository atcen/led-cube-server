import random
import math
import colorsys
from .base import Animation, lerp_color
from ..cube import Cube
from ..config import LEDS_TOTAL, VIRTUAL_TO_BLOCK, VLED_POS_IN_BLOCK

class PucksAnimation(Animation):
    name = "pucks"
    PARAMS = {
        "count":    {"type": "int",   "default": 8,   "min": 1, "max": 15, "label": "Anzahl Pucks"},
        "speed":    {"type": "float", "default": 0.8, "min": 0.1, "max": 3.0, "step": 0.1, "label": "Geschwindigkeit"},
        "softness": {"type": "float", "default": 0.5, "min": 0.1, "max": 1.2, "step": 0.05, "label": "Größe/Glow"},
    }

    def __init__(self, count: int = 8, speed: float = 0.8, softness: float = 0.5):
        self.count = count
        self.speed = speed
        self.softness = softness
        self.pucks = []
        self._init_pucks()

    def _init_pucks(self):
        self.pucks = []
        for i in range(self.count):
            hue = i / self.count
            r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            
            # Start-Position auf einer Einheitskugel
            phi = random.uniform(0, 2 * math.pi)
            theta = math.acos(random.uniform(-1, 1))
            pos = [
                math.sin(theta) * math.cos(phi),
                math.sin(theta) * math.sin(phi),
                math.cos(theta)
            ]
            
            # Zufällige Tangential-Geschwindigkeit
            v_raw = [random.uniform(-1, 1) for _ in range(3)]
            # Projiziere auf Tangentialebene: v = v_raw - (v_raw . pos) * pos
            dot = sum(v_raw[j] * pos[j] for j in range(3))
            vel = [(v_raw[j] - dot * pos[j]) for j in range(3)]
            
            # Auf Zielgeschwindigkeit normalisieren
            v_mag = math.sqrt(sum(v*v for v in vel))
            if v_mag > 0:
                vel = [(v / v_mag) * self.speed for v in vel]
            
            self.pucks.append({
                "pos": pos,
                "vel": vel,
                "color": [int(r * 255), int(g * 255), int(b * 255)]
            })

    def start(self, cube: Cube) -> None:
        super().start(cube)
        cube.fill([0, 0, 0])
        cube.leds.clear()

    def _physical_position(self, vled: int) -> tuple[int, int]:
        grid_row, block_col = VIRTUAL_TO_BLOCK[vled]
        sub_row, sub_col = VLED_POS_IN_BLOCK[vled]
        phys_row = grid_row * 3 + sub_row
        width_before = sum(6 if col % 2 == 0 else 7 for col in range(block_col))
        phys_col = width_before + sub_col
        return phys_row, phys_col

    def _surface_point(self, face: int, phys_row: int, phys_col: int) -> tuple[float, float, float]:
        x = (phys_col / 31.0) * 2.0 - 1.0
        y = 1.0 - (phys_row / 14.0) * 2.0
        if face == 0: return x, y, 1.0
        if face == 1: return -x, y, -1.0
        if face == 2: return -1.0, y, x
        if face == 3: return 1.0, y, -x
        if face == 4: return x, 1.0, -y
        return x, -1.0, y

    def tick(self, cube: Cube, dt: float, t: float) -> None:
        # 1. Update Positionen auf der Kugeloberfläche
        for p in self.pucks:
            # Bewegung entlang des Geschwindigkeitsvektors
            for i in range(3):
                p["pos"][i] += p["vel"][i] * dt
            
            # Zurück auf die Kugeloberfläche projizieren (normalize)
            mag = math.sqrt(sum(x*x for x in p["pos"]))
            p["pos"] = [x / mag for x in p["pos"]]
            
            # Geschwindigkeit wieder tangential ausrichten
            dot = sum(p["vel"][j] * p["pos"][j] for j in range(3))
            p["vel"] = [(p["vel"][j] - dot * p["pos"][j]) for j in range(3)]
            v_mag = math.sqrt(sum(v*v for v in p["vel"]))
            if v_mag > 0:
                p["vel"] = [(v / v_mag) * self.speed for v in p["vel"]]

        # 2. Rendering: Projiziere Puck auf den Würfel
        cube.fill([0, 0, 0])
        cube.leds.clear()

        p_list = []
        for p in self.pucks:
            # Wir projizieren den Kugel-Punkt auf die Würfeloberfläche
            # Max-Norm macht aus einer Kugel einen Würfel
            max_c = max(abs(x) for x in p["pos"])
            proj_pos = [x / max_c for x in p["pos"]]
            p_list.append((proj_pos, p["color"]))

        s_sq = self.softness**2

        for face in range(6):
            for vled in range(LEDS_TOTAL):
                pr, pc = self._physical_position(vled)
                px, py, pz = self._surface_point(face, pr, pc)
                
                r_sum, g_sum, b_sum = 0.0, 0.0, 0.0
                for p_pos, p_col in p_list:
                    # 3D-Abstand auf der Würfeloberfläche
                    dx, dy, dz = px - p_pos[0], py - p_pos[1], pz - p_pos[2]
                    dist_sq = dx*dx + dy*dy + dz*dz
                    
                    intensity = math.exp(-dist_sq / s_sq)
                    if intensity > 0.02:
                        r_sum += p_col[0] * intensity
                        g_sum += p_col[1] * intensity
                        b_sum += p_col[2] * intensity
                
                if r_sum > 0.5 or g_sum > 0.5 or b_sum > 0.5:
                    cube.leds[(face, vled)] = [
                        min(255, int(r_sum)),
                        min(255, int(g_sum)),
                        min(255, int(b_sum))
                    ]
