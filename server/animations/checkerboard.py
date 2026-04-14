from ..cube import Cube
from .base import Animation


class CheckerboardAnimation(Animation):
    name = "checkerboard"

    def start(self, cube: Cube) -> None:
        pass

    def tick(self, cube: Cube, dt: float, t: float) -> None:
        for face in range(6):
            for row in range(5):
                for col in range(5):
                    if (row + col) % 2 == 0:
                        cube.set(face, row, col, [255, 0, 0])
                    else:
                        cube.set(face, row, col, [0, 0, 255])
