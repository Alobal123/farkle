from enum import Enum, auto

class GameState(Enum):
    PRE_ROLL = auto()  # New turn started, before first roll
    ROLLING = auto()   # Player can roll/unhold dice
    FARKLE = auto()    # Farkle occurred, show dice, stop rolling
    BANKED = auto()    # Player banked points, show dice, wait for next turn
    SHOP = auto()      # Between-level relic shop open; gameplay inputs gated
    SELECTING_TARGETS = auto()  # Ability targeting mode (die clicks select targets)
