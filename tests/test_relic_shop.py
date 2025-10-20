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
        self.game = Game(self.screen, self.font, self.clock)
        # Give player enough gold for purchase
        self.game.player.gold = 500
        # Simulate level completion to trigger advancement and shop
        # Force LEVEL_ADVANCE_FINISHED event manually (bypassing full gameplay) to open shop
        self.game.event_listener.publish(GameEvent(GameEventType.LEVEL_ADVANCE_FINISHED, payload={"level_index": 1}))
        self.assertTrue(self.game.relic_manager.shop_open, "Shop should be open after level advance finished")

    def test_purchase_applies_selective_effects(self):
        # Request buy relic
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_BUY_RELIC))
        self.assertFalse(self.game.relic_manager.shop_open, "Shop should close after purchase")
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
