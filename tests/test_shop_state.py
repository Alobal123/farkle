import unittest, pygame
from game import Game
from settings import WIDTH, HEIGHT
from game_event import GameEvent, GameEventType

class ShopStateTests(unittest.TestCase):
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
        # Force level advancement finished to open shop
        self.game.event_listener.publish(GameEvent(GameEventType.LEVEL_ADVANCE_FINISHED, payload={"level_index": 2}))
        self.assertEqual(self.game.state_manager.get_state().name, 'SHOP')

    def test_roll_denied_in_shop(self):
        events = []
        def cap(ev):
            events.append(ev.type)
        self.game.event_listener.subscribe(cap)
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_ROLL))
        self.assertIn(GameEventType.REQUEST_DENIED, events)

    def test_purchase_closes_shop_and_enables_roll(self):
        self.game.player.gold = 999
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_BUY_RELIC))
        self.assertEqual(self.game.state_manager.get_state().name, 'START')
        # Now roll should succeed
        events = []
        self.game.event_listener.subscribe(lambda e: events.append(e.type))
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_ROLL))
        self.assertIn(GameEventType.TURN_ROLL, events)

    def test_purchase_via_renderer_click(self):
        """Simulate clicking the purchase button to ensure rects persist and purchase works."""
        # Ensure enough gold
        self.game.player.gold = 500
        # Force a draw to build rects
        self.game.renderer.draw()
        # Acquire rects
        pr = self.game.renderer.shop_purchase_rect
        self.assertIsNotNone(pr, "Purchase rect should be set after draw while shop open.")
        # mypy / static guard
        if pr is None:  # pragma: no cover - safety
            self.fail("Purchase rect unexpectedly None")
        center = (pr.centerx, pr.centery)
        self.game.renderer.handle_click(center)
        # After click, shop should close
        self.assertEqual(self.game.state_manager.get_state().name, 'START')
        # Relic should be active
        self.assertGreater(len(self.game.relic_manager.active_relics), 0)

if __name__ == '__main__':
    unittest.main()
