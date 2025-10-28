import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEvent, GameEventType

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
        self.game = Game(self.screen, self.font, self.clock, skip_god_selection=True)
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
        # Expect PRE_ROLL after purchase
        self.assertEqual(self.game.state_manager.get_state().name, 'PRE_ROLL')
        # Now roll should succeed
        events = []
        self.game.event_listener.subscribe(lambda e: events.append(e.type))
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_ROLL))
        self.assertIn(GameEventType.TURN_ROLL, events)

    def test_purchase_event_closes_shop_and_activates_relic(self):
        self.game.player.gold = 999
        self.assertTrue(self.game.relic_manager.shop_open)
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_BUY_RELIC, payload={"offer_index":0}))
        self.assertEqual(self.game.state_manager.get_state().name, 'PRE_ROLL')
        self.assertGreater(len(self.game.relic_manager.active_relics), 0)

if __name__ == '__main__':
    unittest.main()
