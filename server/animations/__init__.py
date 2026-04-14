from .snake import SnakeAnimation
from .snake_smooth import SnakeSmoothAnimation
from .rainbow import RainbowAnimation
from .checkerboard import CheckerboardAnimation
from .water_fill import WaterFillAnimation
from .emoji_face import EmojiFaceAnimation
from .heart import HeartAnimation
from .game_of_life import GameOfLifeAnimation
from .text_scroll import TextScrollAnimation
from .rubik_solve import RubikSolveAnimation
from .watercolor import WatercolorAnimation
from .clock import ClockAnimation
from .tetris import TetrisAnimation
from .pacman import PacmanAnimation

REGISTRY: dict = {
    "snake":        SnakeAnimation,
    "snake_smooth": SnakeSmoothAnimation,
    "rainbow":      RainbowAnimation,
    "checkerboard": CheckerboardAnimation,
    "water_fill":   WaterFillAnimation,
    "emoji_face":   EmojiFaceAnimation,
    "heart":        HeartAnimation,
    "game_of_life": GameOfLifeAnimation,
    "text_scroll":  TextScrollAnimation,
    "rubik_solve":  RubikSolveAnimation,
    "watercolor":   WatercolorAnimation,
    "clock":        ClockAnimation,
    "tetris":       TetrisAnimation,
    "pacman":       PacmanAnimation,
}
