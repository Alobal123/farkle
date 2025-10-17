import unittest, pygame
from game import Game
from settings import WIDTH, HEIGHT
from game_state_enum import GameState
from game_object import GameObject

class DummyInteractive(GameObject):
    def __init__(self):
        super().__init__("DummyInteractive")
        self.clicks = 0
        self.visible_states = {GameState.PRE_ROLL, GameState.ROLLING}
        self.interactable_states = {GameState.ROLLING}
    def draw(self, surface):  # type: ignore[override]
        pass
    def handle_click(self, game, pos) -> bool:  # type: ignore[override]
        self.clicks += 1
        return True

class TestInteractableStates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        flags = 0
        if hasattr(pygame, 'HIDDEN'): flags |= pygame.HIDDEN
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()

    def setUp(self):
        self.game = Game(self.screen, self.font, self.clock)
        dummy = DummyInteractive()
        self.game.ui_misc.append(dummy)
        self.dummy = dummy

    def test_not_interactable_in_pre_roll(self):
        self.assertEqual(self.game.state_manager.get_state(), GameState.PRE_ROLL)
        # Simulate renderer-like interaction check
        if self.dummy.should_interact(self.game):
            self.dummy.handle_click(self.game, (0,0))
        self.assertEqual(self.dummy.clicks, 0, 'Should not register click in PRE_ROLL')

    def test_interactable_in_rolling(self):
        self.game.state_manager.transition_to_rolling()
        self.assertEqual(self.game.state_manager.get_state(), GameState.ROLLING)
        if self.dummy.should_interact(self.game):
            self.dummy.handle_click(self.game, (0,0))
        self.assertEqual(self.dummy.clicks, 1, 'Should register click in ROLLING')

if __name__ == '__main__':
    unittest.main()
