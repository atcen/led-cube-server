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
from .dice_roll import DiceRollAnimation

REGISTRY: dict = {
    "snake":        SnakeAnimation,
    "rainbow":      RainbowAnimation,
    "water_fill":   WaterFillAnimation,
    "game_of_life": GameOfLifeAnimation,
    "text_scroll":  TextScrollAnimation,
    "rubik_solve":  RubikSolveAnimation,
    "watercolor":   WatercolorAnimation,
    "tetris":       TetrisAnimation,
    "dice_roll":    DiceRollAnimation,
}
