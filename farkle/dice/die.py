import pygame
from farkle.core.game_object import GameObject
from farkle.ui.settings import DICE_SIZE

# Precomputed pip layout (fractional positions within die square)
PIP_POSITIONS = {
    1: [(0.5, 0.5)],
    2: [(0.25, 0.25), (0.75, 0.75)],
    3: [(0.25, 0.25), (0.5, 0.5), (0.75, 0.75)],
    4: [(0.25, 0.25), (0.25, 0.75), (0.75, 0.25), (0.75, 0.75)],
    5: [(0.25, 0.25), (0.25, 0.75), (0.75, 0.25), (0.75, 0.75), (0.5, 0.5)],
    6: [(0.25, 0.25), (0.25, 0.5), (0.25, 0.75), (0.75, 0.25), (0.75, 0.5), (0.75, 0.75)],
}

# Simple cache for rendered die surfaces keyed by (value, held, selected, scoring_eligible)
_die_surface_cache: dict[tuple[int,bool,bool,bool], pygame.Surface] = {}

class Die(GameObject):
    def __init__(self, value, x, y, game):
        super().__init__(name="Die")
        self.game = game
        self.value = value
        self.x = x
        self.y = y
        self.held = False
        self.selected = False
        self.scoring_eligible = False
        # Sprite reference (assigned by DieSprite); use Any to avoid circular import for type checkers.
        from typing import Any as _Any
        self.sprite: _Any = None
        # Combo metadata (set when die becomes part of a locked combo)
        self.combo_rule_key: str | None = None
        self.combo_points: int | None = None
        # Visible only after first roll or during subsequent play states (never in PRE_ROLL).
        from farkle.core.game_state_enum import GameState
        self.visible_states = {GameState.ROLLING, GameState.FARKLE, GameState.SELECTING_TARGETS, GameState.BANKED}
        self.interactable_states = {GameState.ROLLING, GameState.FARKLE, GameState.SELECTING_TARGETS}

    def draw(self, surface: pygame.Surface) -> None:  # satisfy abstract base; sprite handles rendering
        return

    def rect(self):
        return pygame.Rect(self.x, self.y, DICE_SIZE, DICE_SIZE)

    def reset(self):
        self.held = False
        self.selected = False
        self.scoring_eligible = False
        self.combo_rule_key = None
        self.combo_points = None

    def hold(self):
        self.held = True
        self.selected = False
        # Holding does not itself assign combo metadata; game logic assigns when locking.

    def toggle_select(self):
        self.selected = not self.selected

    # Logical draw removed; rendering handled by DieSprite.
