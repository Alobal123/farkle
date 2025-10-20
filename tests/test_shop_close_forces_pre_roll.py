import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEvent, GameEventType

class TestShopCloseForcesPreRoll(unittest.TestCase):
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

    def test_shop_close_forces_pre_roll_even_if_state_rolling(self):
        # Simulate level advancement finishing (opens shop)
        self.game.event_listener.publish(GameEvent(GameEventType.LEVEL_ADVANCE_FINISHED, payload={"level_index": self.game.level_index}))
        self.assertTrue(self.game.relic_manager.shop_open, 'Shop should be open after LEVEL_ADVANCE_FINISHED')
        # Illegitimately force game state to ROLLING while shop open (should not normally happen)
        # This simulates a potential stray transition path.
        self.game.state_manager.state = self.game.state_manager.state.ROLLING  # type: ignore[attr-defined]
        self.assertEqual(self.game.state_manager.get_state().name, 'ROLLING')
        # Close shop
        self.game.event_listener.publish(GameEvent(GameEventType.SHOP_CLOSED, payload={"skipped": True}))
        # After closing shop the state must be PRE_ROLL and dice hidden.
        self.assertEqual(self.game.state_manager.get_state().name, 'PRE_ROLL', 'State should be forced to PRE_ROLL after shop close')
        for d in self.game.dice:
            self.assertFalse(d.should_draw(self.game), 'Dice should not draw after shop close before first roll even from stray ROLLING state')

if __name__ == '__main__':
    unittest.main()