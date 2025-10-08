from enum import Enum, auto

class GameState(Enum):
    START = auto()     # Game just started, dice hidden
    ROLLING = auto()   # Player can roll/unhold dice
    FARKLE = auto()    # Farkle occurred, show dice, stop rolling
    BANKED = auto()    # Player banked points, show dice, wait for next turn
