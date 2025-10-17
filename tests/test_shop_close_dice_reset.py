import unittest, pygame
from game import Game
from settings import WIDTH, HEIGHT
from game_event import GameEvent, GameEventType

class ShopCloseDiceResetTests(unittest.TestCase):
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
        # Simulate level advancement completion to open shop
        self.game.event_listener.publish(GameEvent(GameEventType.LEVEL_ADVANCE_FINISHED, payload={"level_index": self.game.level_index}))
        # Ensure shop opened
        self.assertTrue(self.game.relic_manager.shop_open, 'Shop should open after LEVEL_ADVANCE_FINISHED')
        # Mutate dice to a held state to verify reset
        for d in self.game.dice:
            d.held = True
        # Publish SHOP_CLOSED to resume play (simulate skip)
        self.game.event_listener.publish(GameEvent(GameEventType.SHOP_CLOSED, payload={"skipped": True}))

    def test_dice_reset_after_shop_close(self):
        # After shop close and begin_turn(from_shop) dice should be recreated (held cleared)
        for d in self.game.dice:
            self.assertFalse(getattr(d, 'held', False), 'Dice should not remain held after shop close new level start')
        # State should be PRE_ROLL ready for rolling
        self.assertEqual(self.game.state_manager.get_state(), self.game.state_manager.state.PRE_ROLL)

if __name__ == '__main__':
    unittest.main()
