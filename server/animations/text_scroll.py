"""
Text-Animation: Zeigt Buchstaben im 5×5-Block-Raster auf den Seitenflächen.

Jede der 4 Seitenflächen (FRONT/BACK/LEFT/RIGHT) zeigt einen Buchstaben.
Der Text wird mit char_speed Sekunden pro Schritt durchgeschalten.

Parameter:
  text        – Anzuzeigender Text (default: "LCC FABLAB ")
  char_speed  – Sekunden pro Zeichen (default: 1.2)
  color       – RGB-Farbe als Liste [r,g,b] (default: [255, 200, 0])
  faces       – Face-IDs als Liste (default: [0,2,1,3] = FRONT/LEFT/BACK/RIGHT)
"""
from .base import Animation
from ..cube import Cube

# 5×5 Pixel-Font, Zeile 0 = oben, Spalte 0 = links
FONT: dict[str, list] = {
    ' ': [
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
    ],
    'A': [
        [0, 1, 1, 1, 0],
        [1, 0, 0, 0, 1],
        [1, 1, 1, 1, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
    ],
    'B': [
        [1, 1, 1, 1, 0],
        [1, 0, 0, 0, 1],
        [1, 1, 1, 1, 0],
        [1, 0, 0, 0, 1],
        [1, 1, 1, 1, 0],
    ],
    'C': [
        [0, 1, 1, 1, 1],
        [1, 0, 0, 0, 0],
        [1, 0, 0, 0, 0],
        [1, 0, 0, 0, 0],
        [0, 1, 1, 1, 1],
    ],
    'E': [
        [1, 1, 1, 1, 1],
        [1, 0, 0, 0, 0],
        [1, 1, 1, 1, 0],
        [1, 0, 0, 0, 0],
        [1, 1, 1, 1, 1],
    ],
    'F': [
        [1, 1, 1, 1, 1],
        [1, 0, 0, 0, 0],
        [1, 1, 1, 1, 0],
        [1, 0, 0, 0, 0],
        [1, 0, 0, 0, 0],
    ],
    'G': [
        [0, 1, 1, 1, 1],
        [1, 0, 0, 0, 0],
        [1, 0, 1, 1, 1],
        [1, 0, 0, 0, 1],
        [0, 1, 1, 1, 1],
    ],
    'H': [
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
        [1, 1, 1, 1, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
    ],
    'I': [
        [1, 1, 1, 1, 1],
        [0, 0, 1, 0, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 1, 0, 0],
        [1, 1, 1, 1, 1],
    ],
    'J': [
        [0, 0, 0, 1, 1],
        [0, 0, 0, 0, 1],
        [0, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
        [0, 1, 1, 1, 0],
    ],
    'K': [
        [1, 0, 0, 1, 0],
        [1, 0, 1, 0, 0],
        [1, 1, 0, 0, 0],
        [1, 0, 1, 0, 0],
        [1, 0, 0, 1, 0],
    ],
    'L': [
        [1, 0, 0, 0, 0],
        [1, 0, 0, 0, 0],
        [1, 0, 0, 0, 0],
        [1, 0, 0, 0, 0],
        [1, 1, 1, 1, 1],
    ],
    'M': [
        [1, 0, 0, 0, 1],
        [1, 1, 0, 1, 1],
        [1, 0, 1, 0, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
    ],
    'N': [
        [1, 0, 0, 0, 1],
        [1, 1, 0, 0, 1],
        [1, 0, 1, 0, 1],
        [1, 0, 0, 1, 1],
        [1, 0, 0, 0, 1],
    ],
    'O': [
        [0, 1, 1, 1, 0],
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
        [0, 1, 1, 1, 0],
    ],
    'P': [
        [1, 1, 1, 1, 0],
        [1, 0, 0, 0, 1],
        [1, 1, 1, 1, 0],
        [1, 0, 0, 0, 0],
        [1, 0, 0, 0, 0],
    ],
    'R': [
        [1, 1, 1, 1, 0],
        [1, 0, 0, 0, 1],
        [1, 1, 1, 1, 0],
        [1, 0, 1, 0, 0],
        [1, 0, 0, 1, 0],
    ],
    'S': [
        [0, 1, 1, 1, 1],
        [1, 0, 0, 0, 0],
        [0, 1, 1, 1, 0],
        [0, 0, 0, 0, 1],
        [1, 1, 1, 1, 0],
    ],
    'T': [
        [1, 1, 1, 1, 1],
        [0, 0, 1, 0, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 1, 0, 0],
    ],
    'U': [
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
        [0, 1, 1, 1, 0],
    ],
    'W': [
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 1, 0, 1],
        [1, 1, 0, 1, 1],
        [1, 0, 0, 0, 1],
    ],
    'X': [
        [1, 0, 0, 0, 1],
        [0, 1, 0, 1, 0],
        [0, 0, 1, 0, 0],
        [0, 1, 0, 1, 0],
        [1, 0, 0, 0, 1],
    ],
    'Y': [
        [1, 0, 0, 0, 1],
        [0, 1, 0, 1, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 1, 0, 0],
    ],
    'Z': [
        [1, 1, 1, 1, 1],
        [0, 0, 0, 1, 0],
        [0, 0, 1, 0, 0],
        [0, 1, 0, 0, 0],
        [1, 1, 1, 1, 1],
    ],
}


class TextScrollAnimation(Animation):
    name = "text_scroll"
    PARAMS = {
        "text":       {"type": "str",   "default": "KRONACH LEUCHTET ", "label": "Text"},
        "char_speed": {"type": "float", "default": 1.2, "min": 0.1, "max": 5.0, "step": 0.1, "label": "Zeichengeschwindigkeit"},
    }

    # Farben die pro Buchstabe durchgewechselt werden
    _COLORS = [
        [255, 200,   0],   # gelb
        [255,  80,   0],   # orange
        [255,   0,  80],   # pink
        [120,   0, 255],   # violett
        [0,   120, 255],   # blau
        [0,   220, 100],   # grün
    ]

    def __init__(
        self,
        text: str = "KRONACH LEUCHTET ",
        char_speed: float = 1.2,
        faces: list = None,
    ):
        self.text       = text
        self.char_speed = char_speed
        self.faces      = faces or [0, 1, 2, 3, 4, 5]

    def start(self, cube: Cube) -> None:
        super().start(cube)
        self._pos        = 0
        self._color_idx  = 0
        self._timer      = 0.0

    def _draw_char(self, cube: Cube, face: int, char: str, color: list) -> None:
        pattern = FONT.get(char.upper(), FONT[' '])
        for row in range(5):
            for col in range(5):
                c = color if pattern[row][col] else [0, 0, 0]
                cube.set(face, row, col, c)

    def tick(self, cube: Cube, dt: float, t: float) -> None:
        self._timer += dt
        if self._timer >= self.char_speed:
            self._timer -= self.char_speed
            self._pos       = (self._pos + 1) % len(self.text)
            self._color_idx = (self._color_idx + 1) % len(self._COLORS)

        char  = self.text[self._pos]
        color = self._COLORS[self._color_idx]
        cube.fill([0, 0, 0])
        for face in self.faces:
            self._draw_char(cube, face, char, color)
