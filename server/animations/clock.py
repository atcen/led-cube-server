import datetime
import math
from .base import Animation, lerp_color
from ..cube import Cube
from ..config import LEDS_TOTAL, VIRTUAL_TO_BLOCK, VLED_POS_IN_BLOCK

class ClockAnimation(Animation):
    name = "clock"
    TEST_MODE = False 

    def start(self, cube: Cube) -> None:
        super().start(cube)
        cube.fill([0, 0, 0])

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
        now = datetime.datetime.now()
        # Zeit in Winkeln (CW)
        sec_a = (now.second + now.microsecond/1000000.0) / 60.0 * 2.0 * math.pi
        min_a = (now.minute + now.second/60.0) / 60.0 * 2.0 * math.pi
        hou_a = (now.hour % 12 + now.minute/60.0) / 12.0 * 2.0 * math.pi

        # Welt-Oben: BLAUE ECKE (px=-1, py=-1, pz=1)
        world_up = [-1.0, -1.0, 1.0] 
        
        cube.fill([0, 0, 0])
        cube.leds.clear()

        face_centers = [(0,0,1), (0,0,-1), (-1,0,0), (1,0,0), (0,1,0), (0,-1,0)]

        for face in range(6):
            cx, cy, cz = face_centers[face]
            
            # Lokales "Oben" (Projektion von world_up auf die Fläche)
            ux, uy, uz = world_up[0], world_up[1], world_up[2]
            if face == 0 or face == 1: uz = 0
            elif face == 2 or face == 3: ux = 0
            else: uy = 0
            
            mag = math.sqrt(ux*ux + uy*uy + uz*uz)
            if mag > 0: ux, uy, uz = ux/mag, uy/mag, uz/mag
            
            # Lokales "Rechts" (für Uhrzeigersinn)
            # Normalen-Vektor der Fläche N = (cx, cy, cz)
            # R = N x Up
            rx = cy*uz - cz*uy
            ry = cz*ux - cx*uz
            rz = cx*uy - cy*ux

            for vled in range(LEDS_TOTAL):
                pr, pc = self._physical_position(vled)
                px, py, pz = self._surface_point(face, pr, pc)
                
                dx, dy, dz = px - cx, py - cy, pz - cz
                
                dot_u = dx*ux + dy*uy + dz*uz
                dot_r = dx*rx + dy*ry + dz*rz
                
                # Winkel (atan2(sin, cos) -> atan2(dot_r, dot_u) ergibt CW)
                angle = math.atan2(dot_r, dot_u)
                if angle < 0: angle += 2*math.pi
                
                dist = math.sqrt(dx*dx + dy*dy + dz*dz)
                if dist < 0.15: continue 

                color = [0, 0, 0]

                # --- 1. Sekunde (Rot) ---
                diff = abs(angle - sec_a)
                if diff > math.pi: diff = 2*math.pi - diff
                if diff < 0.22 and dist > 0.6:
                    color = lerp_color(color, [255, 0, 0], 1.0 - diff/0.22)

                # --- 2. Minute (Grün) ---
                diff = abs(angle - min_a)
                if diff > math.pi: diff = 2*math.pi - diff
                if diff < 0.32 and dist > 0.4:
                    color = lerp_color(color, [0, 255, 0], 1.0 - diff/0.32)

                # --- 3. Stunde (Blau) ---
                diff = abs(angle - hou_a)
                if diff > math.pi: diff = 2*math.pi - diff
                if diff < 0.5 and dist < 0.7:
                    color = lerp_color(color, [0, 120, 255], 1.0 - diff/0.5)

                if color != [0, 0, 0]:
                    cube.leds[(face, vled)] = color
