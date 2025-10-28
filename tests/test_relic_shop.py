import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEvent, GameEventType

class RelicShopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        flags = 0
        if hasattr(pygame, 'HIDDEN'): flags |= pygame.HIDDEN
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()

    def setUp(self):
        self.game = Game(self.screen, self.font, self.clock, rng_seed=2, skip_god_selection=True)
        # Give player enough gold for purchase
        self.game.player.gold = 500
        # Simulate level completion to trigger advancement and shop
        # Force LEVEL_ADVANCE_FINISHED event manually (bypassing full gameplay) to open shop
        self.game.event_listener.publish(GameEvent(GameEventType.LEVEL_ADVANCE_FINISHED, payload={"level_index": 1}))
        
        self.assertTrue(self.game.relic_manager.shop_open, "Shop should be open after level advance finished")

    def test_purchase_applies_selective_effects(self):
        # Find the "Charm of Fives" offer in the choice window
        window = self.game.choice_window_manager.active_window
        self.assertIsNotNone(window, "Choice window should be open for shop")
        self.assertEqual(window.window_type, "shop", "Window should be a shop window")
        
        # Find Charm of Fives in the window items
        charm_item = next((item for item in window.items if item.name == "Charm of Fives"), None)
        self.assertIsNotNone(charm_item, f"Charm of Fives should be in shop. Items: {[i.name for i in window.items]}")
        
        if charm_item:
            # Select the item
            charm_index = window.items.index(charm_item)
            window.select_item(charm_index)
            self.assertIn(charm_index, window.selected_indices, "Item should be selected")
            
            # Confirm purchase (close window with selection)
            self.game.choice_window_manager.close_window("shop")

        self.assertFalse(self.game.relic_manager.shop_open, "Shop should close after purchase")
        
        # Verify relic was purchased
        self.assertTrue(
            any(r.name == "Charm of Fives" for r in self.game.relic_manager.active_relics),
            "Charm of Fives should be in active relics"
        )
        
        # Flat five bonus relic path (level 1 Charm of Fives)
        # Simulate scoring one single five -> expect +50 flat added (50 raw -> 100 adjusted)
        for i,d in enumerate(self.game.dice):
            d.value = 5 if i == 0 else 2
            d.held = False
            d.selected = False
        self.game.mark_scoring_dice()
        self.game.dice[0].selected = True
        self.game.handle_lock()
        captured = {}
        def cap2(ev):
            if ev.type == GameEventType.SCORE_APPLIED:
                captured.update(ev.payload)
        self.game.event_listener.subscribe(cap2)
        self.game.handle_bank()
        # Pending raw now includes flat mutation (+50) -> 100 total
        self.assertEqual(captured.get("pending_raw"), 100)
        self.assertEqual(captured.get("adjusted"), 100)

if __name__ == '__main__':
    unittest.main()
