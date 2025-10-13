from game_state_enum import GameState
from typing import Callable, Optional

StateChangeCallback = Callable[[GameState, GameState], None]

class GameStateManager:
    def __init__(self, on_change: Optional[StateChangeCallback] = None):
        self.state = GameState.START
        self._on_change = on_change

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

    def transition_to_rolling(self):
        if self.state == GameState.START:
            self._set(GameState.ROLLING)

    def transition_to_farkle(self):
        if self.state in (GameState.ROLLING, GameState.START):
            self._set(GameState.FARKLE)

    def transition_to_banked(self):
        if self.state == GameState.ROLLING:
            self._set(GameState.BANKED)

    def transition_to_start(self):
        if self.state in (GameState.FARKLE, GameState.BANKED):
            self._set(GameState.START)

    def transition_to_shop(self):
        if self.state in (GameState.START, GameState.BANKED, GameState.FARKLE):
            self._set(GameState.SHOP)

    def exit_shop_to_start(self):
        if self.state == GameState.SHOP:
            self._set(GameState.START)
