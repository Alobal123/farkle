from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Optional

class GameEventType(Enum):
    TURN_START = auto()
    TURN_ROLL = auto()
    TURN_LOCK_ADDED = auto()
    TURN_FARKLE = auto()
    TURN_BANKED = auto()
    TURN_END = auto()
    STATE_CHANGED = auto()
    ROLL = auto()
    HOT_DICE = auto()
    FARKLE = auto()
    LOCK = auto()
    BANK = auto()
    GOAL_PROGRESS = auto()
    GOAL_FULFILLED = auto()
    GOLD_GAINED = auto()
    # Scoring application (player-mediated multiplier)
    SCORE_APPLY_REQUEST = auto()
    SCORE_APPLIED = auto()
    SCORE_PRE_MODIFIERS = auto()
    # Non-mutating preview lifecycle
    SCORE_PREVIEW_REQUEST = auto()
    SCORE_PREVIEW_COMPUTED = auto()
    # Level lifecycle
    LEVEL_COMPLETE = auto()
    LEVEL_FAILED = auto()
    LEVEL_ADVANCE_STARTED = auto()
    LEVEL_GENERATED = auto()
    LEVEL_ADVANCE_FINISHED = auto()
    # UI / intent layer
    REQUEST_ROLL = auto()
    REQUEST_BANK = auto()
    REQUEST_NEXT_TURN = auto()
    REQUEST_DENIED = auto()
    MESSAGE = auto()
    # Dice lifecycle
    PRE_ROLL = auto()
    DIE_ROLLED = auto()
    POST_ROLL = auto()
    DIE_SELECTED = auto()
    DIE_DESELECTED = auto()
    DIE_HELD = auto()
    # Shop / relic acquisition lifecycle
    SHOP_OPENED = auto()
    SHOP_CLOSED = auto()
    RELIC_OFFERED = auto()
    RELIC_PURCHASED = auto()
    RELIC_SKIPPED = auto()
    REQUEST_BUY_RELIC = auto()
    REQUEST_SKIP_SHOP = auto()
    # Abilities
    REQUEST_REROLL = auto()
    REROLL = auto()
    REQUEST_ABILITY = auto()
    ABILITY_EXECUTED = auto()
    TARGET_SELECTION_STARTED = auto()
    TARGET_SELECTION_FINISHED = auto()

@dataclass(slots=True)
class GameEvent:
    type: GameEventType
    source: Any | None = None
    payload: Optional[dict[str, Any]] = None

    def get(self, key: str, default: Any = None) -> Any:
        return self.payload.get(key, default) if self.payload else default

    def __repr__(self) -> str:  # Helpful for debugging
        return f"GameEvent(type={self.type}, payload={self.payload})"
