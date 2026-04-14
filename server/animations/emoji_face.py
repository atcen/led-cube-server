"""
Emoji-Animation: Zeigt ein Unicode-Emoji auf den Würfelflächen.

Auflösung: 32×15 Pixel (32 LEDs horizontal, 15 physische Reihen vertikal).
Das 72×72-Twemoji-PNG wird auf 32×32 skaliert und vertikal mittig auf 15 Zeilen
gecroppt, da wir nur 5 Grid-Reihen × 3 Sub-Reihen = 15 physische Reihen haben.

Emoji-Bilder werden vom Twemoji-CDN geladen und lokal gecacht.

Parameter:
  emoji  – Unicode-Zeichen, z.B. "😀" oder "🐍"
  faces  – Komma-separierte Face-IDs oder "all" (default)
           0=FRONT, 1=BACK, 2=LEFT, 3=RIGHT, 4=TOP, 5=BOTTOM

Beispiel:
  curl -X POST http://localhost:8000/animation/emoji_face/params \\
    -H "Content-Type: application/json" \\
    -d '{"emoji": "🐍"}'
"""
import os
import urllib.request
from PIL import Image

from ..config import BLOCK_WIDTHS, BLOCK_TO_VLEDS, VLED_POS_IN_BLOCK
from ..cube import Cube
from .base import Animation

PANEL_W = sum(BLOCK_WIDTHS)   # 32
PANEL_H = 15                   # 5 Gitterreihen × 3 Sub-Reihen

CACHE_DIR = os.path.join(os.path.dirname(__file__), "../../../.emoji_cache")

# ── Pixel→vled-Mapping einmalig zur Ladezeit berechnen ───────────────────────

def _build_pixel_map() -> dict:
    """Gibt {(y, x): vled} zurück für alle 32×15 Pixel-Positionen."""
    pixel_to_vled = {}
    col_offset = 0
    for bc, width in enumerate(BLOCK_WIDTHS):
        for gr in range(5):
            for vled in BLOCK_TO_VLEDS[(gr, bc)]:
                sub_row, sub_col = VLED_POS_IN_BLOCK[vled]
                y = gr * 3 + sub_row          # 0..14
                x = col_offset + sub_col       # 0..31
                pixel_to_vled[(y, x)] = vled
        col_offset += width
    return pixel_to_vled


PIXEL_TO_VLED: dict = _build_pixel_map()


# ── Twemoji laden & cachen ────────────────────────────────────────────────────

def _emoji_to_filename(emoji_char: str) -> str:
    """Unicode-Zeichen → Twemoji-Dateiname (Codepoints ohne Variation Selector)."""
    codepoints = [f"{ord(c):x}" for c in emoji_char if ord(c) != 0xFE0F]
    return "-".join(codepoints)


def _fetch_emoji(emoji_char: str) -> Image.Image:
    """Lädt das Emoji-PNG (Twemoji 72×72) und gibt ein PIL-Image zurück."""
    filename  = _emoji_to_filename(emoji_char)
    cache_path = os.path.join(CACHE_DIR, f"{filename}.png")

    if not os.path.exists(cache_path):
        os.makedirs(CACHE_DIR, exist_ok=True)
        url = (
            f"https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2"
            f"/assets/72x72/{filename}.png"
        )
        try:
            urllib.request.urlretrieve(url, cache_path)
        except Exception as exc:
            raise RuntimeError(
                f"Emoji {emoji_char!r} konnte nicht geladen werden "
                f"(Twemoji-Datei: {filename}.png): {exc}"
            ) from exc

    return Image.open(cache_path).convert("RGBA")


def render_emoji(emoji_char: str) -> dict:
    """
    Rendert ein Emoji auf die 32×15-Pixel-Matrix.
    Gibt {vled: [r, g, b]} zurück.
    """
    img = _fetch_emoji(emoji_char)

    # 1. Auf 32×32 skalieren
    img = img.resize((PANEL_W, PANEL_W), Image.LANCZOS)

    # 2. Vertikal mittig auf 15 Zeilen croppen
    top = (PANEL_W - PANEL_H) // 2   # = 8
    img = img.crop((0, top, PANEL_W, top + PANEL_H))

    # 3. Pixel auslesen, Alpha auf schwarzem Hintergrund kompositen
    pixels = img.load()
    vled_colors = {}
    for y in range(PANEL_H):
        for x in range(PANEL_W):
            vled = PIXEL_TO_VLED.get((y, x))
            if vled is None:
                continue
            r, g, b, a = pixels[x, y]
            alpha = a / 255.0
            vled_colors[vled] = [round(r * alpha), round(g * alpha), round(b * alpha)]

    return vled_colors


# ── Animation ─────────────────────────────────────────────────────────────────

class EmojiFaceAnimation(Animation):
    name = "emoji_face"

    def __init__(self, emoji: str = "😀", faces: str = "all"):
        self.emoji_char   = emoji
        self.faces_param  = faces

    def start(self, cube: Cube) -> None:
        super().start(cube)  # fill black + leds.clear()

        self._vled_colors = render_emoji(self.emoji_char)

        if self.faces_param == "all":
            self._active_faces = list(range(6))
        else:
            self._active_faces = [int(f) for f in str(self.faces_param).split(",")]

        # Statisches Bild einmalig in cube.leds schreiben
        for face in self._active_faces:
            for vled, color in self._vled_colors.items():
                cube.leds[(face, vled)] = color

    def tick(self, cube: Cube, dt: float, t: float) -> None:
        # Statisch — nichts zu tun; cube.leds bleibt vom start() gesetzt
        pass
