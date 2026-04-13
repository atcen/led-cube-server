"""Basis-Klasse für alle Animationen."""
from ..cube import Cube


class Animation:
    name: str = "base"

    def start(self, cube: Cube) -> None:
        """Wird einmalig beim Aktivieren der Animation aufgerufen."""
        cube.fill([0, 0, 0])

    def tick(self, cube: Cube, dt: float, t: float) -> None:
        """
        Wird jeden Frame aufgerufen.
        dt: Zeit seit letztem Frame (Sekunden)
        t:  Absolute Zeit seit Animationsstart (Sekunden)
        """
        raise NotImplementedError


def lerp_color(a: list, b: list, t: float) -> list:
    """Linearer Übergang zwischen zwei RGB-Farben."""
    t = max(0.0, min(1.0, t))
    return [int(a[i] + (b[i] - a[i]) * t) for i in range(3)]
