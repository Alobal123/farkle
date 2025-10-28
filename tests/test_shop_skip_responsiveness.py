import pygame, unittest
from farkle.game import Game
from farkle.core.game_event import GameEvent, GameEventType

class Collector:
    def __init__(self):
        self.events = []
    def on_event(self, e):  # type: ignore
        self.events.append(e)

class ShopSkipResponsivenessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((800,600))
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()

    def setUp(self):
        self.game = Game(self.screen, self.font, self.clock, skip_god_selection=True)
        self.collector = Collector()
        self.game.event_listener.subscribe(self.collector.on_event)
        # Force shop open by simulating level advancement completion
        # Directly publish LEVEL_ADVANCE_FINISHED and set relic_manager.shop_open True via event chain.
        # Easiest path: trigger advancement then completion.
        # Simplify: directly invoke create_next_level and then manually open shop via relic_manager._open_shop.
        self.game.relic_manager._open_shop()  # type: ignore[attr-defined]
        self.assertTrue(self.game.relic_manager.shop_open, 'Shop should be open for test setup')

    def test_skip_closes_shop_and_emits_events_immediately(self):
        # Skip the shop using the choice window manager
        self.game.choice_window_manager.skip_window("shop")
        self.assertFalse(self.game.relic_manager.shop_open, 'Shop should be closed immediately after skip')
        types = [e.type for e in self.collector.events]
        # CHOICE_WINDOW_CLOSED should be emitted with skipped=True
        self.assertIn(GameEventType.CHOICE_WINDOW_CLOSED, types, 'Choice window closed event missing')
        self.assertIn(GameEventType.SHOP_CLOSED, types, 'Shop closed event missing')
        # TURN_START should follow SHOP_CLOSED
        idx_closed = types.index(GameEventType.SHOP_CLOSED)
        turn_starts_after = [t for t in types[idx_closed+1:] if t == GameEventType.TURN_START]
        self.assertTrue(turn_starts_after, 'TURN_START should emit after shop close')
        self.assertEqual(self.game.state_manager.get_state().name, 'PRE_ROLL', 'State should be PRE_ROLL after skip')

if __name__ == '__main__':
    unittest.main()
