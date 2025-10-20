import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEvent, GameEventType

class TestShopCloseDiceHiddenAfterPurchase(unittest.TestCase):
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
        # Advance level to open shop
        self.game.event_listener.publish(GameEvent(GameEventType.LEVEL_ADVANCE_FINISHED, payload={"level_index": self.game.level_index}))
        self.assertTrue(self.game.relic_manager.shop_open, 'Shop should be open after advancement finish')
        # Ensure player has enough gold for deterministic first offer cost (30)
        self.game.player.gold = 100
        # Purchase first offer (deterministic Charm of Fives)
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_BUY_RELIC, payload={"offer_index": 0}))
        # Ensure RELIC_PURCHASED occurred and shop closed
        self.assertFalse(self.game.relic_manager.shop_open, 'Shop should be closed after purchase')
        # Dice should still be hidden (state PRE_ROLL) until manual first roll
        self.assertEqual(self.game.state_manager.get_state().name, 'PRE_ROLL', 'State should remain PRE_ROLL post purchase')
        for d in self.game.dice:
            self.assertFalse(d.should_draw(self.game), 'Dice should not draw after purchase before first roll')

    def test_dice_become_visible_after_first_roll(self):
        # Perform first roll
        self.game.handle_roll()
        for d in self.game.dice:
            self.assertTrue(d.should_draw(self.game), 'Dice should draw after first roll following purchase')

if __name__ == '__main__':
    unittest.main()