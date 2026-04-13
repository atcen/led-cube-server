from .snake import SnakeAnimation
from .rainbow import RainbowAnimation

REGISTRY: dict = {
    "snake":   SnakeAnimation,
    "rainbow": RainbowAnimation,
}
