from game_state_enum import GameState

class GameStateManager:
    def __init__(self):
        self.state = GameState.START
    
    def set_state(self, new_state):
        self.state = new_state

    def get_state(self):
        return self.state

    def transition_to_rolling(self):
        if self.state == GameState.START:
            self.state = GameState.ROLLING

    def transition_to_farkle(self):
        if self.state in (GameState.ROLLING, GameState.START):
            self.state = GameState.FARKLE

    def transition_to_banked(self):
        if self.state == GameState.ROLLING:
            self.state = GameState.BANKED

    def transition_to_start(self):
        if self.state in (GameState.FARKLE, GameState.BANKED):
            self.state = GameState.START
