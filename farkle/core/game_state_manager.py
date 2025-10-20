from farkle.core.game_state_enum import GameState
from typing import Callable, Optional

StateChangeCallback = Callable[[GameState, GameState], None]

class GameStateManager:
    def __init__(self, on_change: Optional[StateChangeCallback] = None):
    # Initialize to PRE_ROLL (initial playable state before first roll)
        self.state = GameState.PRE_ROLL
        self._on_change = on_change
        # Store prior play state when entering transient modes (e.g., SELECTING_TARGETS)
        self._prior_play_state: GameState | None = None
        # Flag indicating a farkle rescue occurred during targeting
        self._rescued_farkle: bool = False

    def _set(self, new_state: GameState):
        if new_state != self.state:
            old = self.state
            self.state = new_state
            if self._on_change:
                try:
                    self._on_change(old, new_state)
                except Exception:
                    pass
    
    def set_state(self, new_state: GameState):
        self._set(new_state)

    def get_state(self):
        return self.state

    def effective_play_state(self):
        """Return the underlying play state (e.g., FARKLE or ROLLING) when in a transient selecting state.

        If currently SELECTING_TARGETS and a prior play state was stored, return that; else return current state.
        """
        from farkle.core.game_state_enum import GameState as _GS
        if self.state == _GS.SELECTING_TARGETS and self._prior_play_state:
            return self._prior_play_state
        return self.state


    def transition_to_rolling(self):
        if self.state == GameState.PRE_ROLL:
            self._set(GameState.ROLLING)

    def transition_to_farkle(self):
        if self.state in (GameState.ROLLING, GameState.PRE_ROLL):
            self._set(GameState.FARKLE)

    def rescue_farkle_to_rolling(self):
        """Reverse a FARKLE state (e.g., via a successful reroll producing scoring dice).

        Only transitions if currently in FARKLE; restores to ROLLING for continued play.
        """
        # Support rescue while in SELECTING_TARGETS with underlying prior FARKLE.
        underlying = self.effective_play_state()
        if underlying == GameState.FARKLE:
            if self.state == GameState.FARKLE:
                # Immediate transition
                self._set(GameState.ROLLING)
            # If currently selecting targets, defer the visible transition until exit_selecting_targets.
            self._rescued_farkle = True

    def transition_to_banked(self):
        if self.state == GameState.ROLLING:
            self._set(GameState.BANKED)

    def transition_to_pre_roll(self):
        """Transition from end-of-turn states to PRE_ROLL.

    Transition from end-of-turn states back to PRE_ROLL.
        """
        if self.state in (GameState.FARKLE, GameState.BANKED):
            self._set(GameState.PRE_ROLL)


    def transition_to_shop(self):
        if self.state in (GameState.PRE_ROLL, GameState.BANKED, GameState.FARKLE):
            self._set(GameState.SHOP)

    def exit_shop_to_pre_roll(self):
        if self.state == GameState.SHOP:
            self._set(GameState.PRE_ROLL)

    # Ability targeting state transitions
    def enter_selecting_targets(self):
        if self.state in (GameState.ROLLING, GameState.FARKLE):
            self._prior_play_state = self.state
            self._set(GameState.SELECTING_TARGETS)

    def exit_selecting_targets(self):
        if self.state == GameState.SELECTING_TARGETS:
            if self._rescued_farkle:
                target = GameState.ROLLING
            else:
                target = self._prior_play_state or GameState.ROLLING
            self._set(target)
            self._prior_play_state = None

