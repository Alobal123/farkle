import unittest, pygame
from game import Game
from settings import WIDTH, HEIGHT
from game_event import GameEvent, GameEventType

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

    def test_purchase_increases_multiplier(self):
        base_mult = self.game.player.get_score_multiplier()
        # Request buy relic
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_BUY_RELIC))
        self.assertFalse(self.game.relic_manager.shop_open, "Shop should close after purchase")
        # Effective chain multiplier should now include relic's multiplier > base
        # Aggregate modifiers the same way player does during scoring
        # We'll approximate by comparing a sample application
        pending_raw = 100
        # Use player's handler logic indirectly: emit SCORE_APPLY_REQUEST
        events = []
        def cap(ev):
            if ev.type in (GameEventType.SCORE_APPLY_REQUEST, GameEventType.SCORE_APPLIED):
                events.append(ev)
        self.game.event_listener.subscribe(cap)
        g0 = self.game.level_state.goals[0]
        self.game.event_listener.publish(GameEvent(GameEventType.SCORE_APPLY_REQUEST, payload={"goal": g0, "pending_raw": pending_raw}))
        applied = [e for e in events if e.type == GameEventType.SCORE_APPLIED]
        self.assertTrue(applied, "Expected SCORE_APPLIED emitted")
        adjusted = applied[0].get("adjusted")
        self.assertGreater(adjusted, int(pending_raw * base_mult), "Adjusted should be greater after relic purchase")

if __name__ == '__main__':
    unittest.main()
