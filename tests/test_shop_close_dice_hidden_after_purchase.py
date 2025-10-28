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
        self.game = Game(self.screen, self.font, self.clock, skip_god_selection=True)
        # Advance level to open shop
        self.game.event_listener.publish(GameEvent(GameEventType.LEVEL_ADVANCE_FINISHED, payload={"level_index": self.game.level_index}))
        self.assertTrue(self.game.relic_manager.shop_open, 'Shop should be open after advancement finish')
        
        # Get the choice window and verify it's a shop
        window = self.game.choice_window_manager.get_active_window()
        self.assertIsNotNone(window, "Shop choice window should be open")
        self.assertEqual(window.window_type, "shop", "Window should be a shop")
        
        # Ensure player has enough gold for deterministic first offer cost (30)
        self.game.player.gold = 100
        
        # Select first offer (index 0) and confirm purchase
        window.select_item(0)
        self.game.choice_window_manager.close_window("shop")
        
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