import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_state_enum import GameState
from farkle.core.game_object import GameObject

class DummyObj(GameObject):
    def __init__(self):
        super().__init__("Dummy")
        self.draw_calls = 0
        self.visible_states = {GameState.ROLLING}
    def draw(self, surface):  # type: ignore[override]
        self.draw_calls += 1

class TestObjectVisibilityStates(unittest.TestCase):
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
        # Inject dummy object; dynamic list expects dice but draw loop tolerates generic GameObject
        dummy = DummyObj()
        self.game.ui_dynamic.append(dummy)  # type: ignore[arg-type]
        self.dummy = dummy

    def test_dummy_not_drawn_in_pre_roll(self):
        self.assertEqual(self.game.state_manager.get_state(), GameState.PRE_ROLL)
        self.game.renderer.draw()
        self.assertEqual(self.dummy.draw_calls, 0, "Dummy should not draw in PRE_ROLL")

    def test_dummy_drawn_in_rolling(self):
        self.game.state_manager.transition_to_rolling()
        self.assertEqual(self.game.state_manager.get_state(), GameState.ROLLING)
        self.game.renderer.draw()
        self.assertGreater(self.dummy.draw_calls, 0, "Dummy should draw in ROLLING")

if __name__ == '__main__':
    unittest.main()
